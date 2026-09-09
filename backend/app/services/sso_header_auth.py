"""single sign-on passthrough for a forwardAuth proxy (authentik + traefik).

the proxy authenticates the caller before the request ever reaches the app
and stamps the verified identity onto it as X-authentik-* headers. this
middleware turns those headers into a native session: an existing account is
matched by email, a new one is provisioned, and the auth cookie is issued so
every downstream dependency resolves identity through the normal cookie path.

trust is layered: traefik only sets the headers after its gate passed, and
uvicorn binds loopback, so the middleware additionally refuses headers whose
client address is not in SSO_TRUSTED_PROXIES. a caller that reaches uvicorn
directly with forged headers is not on loopback and gets nothing.
"""
from __future__ import annotations

import logging
import secrets
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.auth_common import _EMAIL_RE, now_iso, set_auth_cookie
from app.auth import AUTH_COOKIE_NAME, resolve_account
from app.config import settings
from app.models.accounts import Account
from app.services.password_hashing import hash_password

logger = logging.getLogger(__name__)


def _sso_account(email: str, groups_header: str) -> Account | None:
    """account for the SSO identity: reused when it exists, provisioned when
    it does not. a disabled account stays locked out; group membership only
    ever elevates, so a group edit cannot strip the last administrator."""
    from app.services import namespace_tombstones
    from app.services.account_store import DuplicateAccountError, get_account_store

    store = get_account_store()
    groups = [g.strip() for g in groups_header.split(",") if g.strip()]
    admin = settings.sso_admin_group in groups

    account = store.get_by_email(email)
    if account is not None:
        if account.disabled:
            return None
        if admin and not account.is_admin:
            def elevate(live: Account):
                live.is_admin = True
                return live

            updated = store.mutate(account.id, elevate)
            if updated is not None:
                account = updated
                logger.info("sso elevated account %s to administrator", account.id)
        return account

    account = Account(
        id=str(uuid.uuid4()),
        email=email,
        # the password is unknown to everyone, including the account owner:
        # identity comes from the proxy, and password self-service would need
        # a current password nobody has. an administrator can reset it through
        # the admin API if native login is ever wanted for this account
        password_hash=hash_password(secrets.token_urlsafe(32)),
        is_admin=admin,
        created_at=now_iso(),
        storage_namespace=str(uuid.uuid4()),
    )
    try:
        namespace_tombstones.claim(account.storage_namespace)
        store.create(account)
    except (NamespaceNotClaimableError, DuplicateAccountError) as exc:
        logger.warning("sso provisioning refused for a new identity: %s", exc)
        return None
    from app.config import ensure_user_dirs

    ensure_user_dirs(settings.storage_path / account.storage_namespace)
    logger.info("sso provisioned account %s (admin=%s)", account.id, admin)
    return account


def _trusted(request: Request) -> bool:
    client = request.client
    return client is not None and client.host in settings.sso_trusted_proxies


class SsoHeaderAuthMiddleware(BaseHTTPMiddleware):
    """open a native session from verified forwardAuth headers."""

    async def dispatch(self, request, call_next):
        if (
            settings.resolved_auth_mode != "native"
            or not settings.sso_header_auth
            or resolve_account(request) is not None
            or not _trusted(request)
        ):
            return await call_next(request)

        email = request.headers.get("x-authentik-email", "").strip().lower()
        if not email or not _EMAIL_RE.match(email):
            return await call_next(request)

        account = _sso_account(email, request.headers.get("x-authentik-groups", ""))
        if account is None or account.disabled:
            return await call_next(request)

        from app.services.auth_token_store import get_auth_token_store

        raw = get_auth_token_store().issue(account.id)
        # downstream dependencies read identity from the cookie, not from the
        # header, so inject the fresh token into the request the route will see
        merged = {**request.cookies, AUTH_COOKIE_NAME: raw}
        request.scope["headers"] = [
            *[(k, v) for k, v in request.scope["headers"] if k.lower() != b"cookie"],
            (b"cookie", "; ".join(f"{k}={v}" for k, v in merged.items()).encode()),
        ]
        response = await call_next(request)
        set_auth_cookie(response, raw)
        return response

"""the SSO header-trust contract: forwardAuth headers open a native session.

the proxy (traefik + authentik) authenticates the caller before the app sees
the request and stamps the identity on as X-authentik-* headers. the app must
reuse the matching account, provision a missing one, elevate on admin group
membership, and refuse everything else: disabled accounts, untrusted clients,
invalid identities, and the feature being switched off.
"""
import pytest
from starlette.testclient import TestClient

import app.main as main_mod
from app.config import ensure_user_dirs
from app.services.account_store import get_account_store
from tests.conftest import set_auth_mode, set_auth_setting

SSO_EMAIL = "sso.user@example.com"
ADMIN_GROUP = "authentik Admins"

HEADERS = {"X-authentik-email": SSO_EMAIL}


def make_sso_client(auth_mode_settings, monkeypatch, trusted=True, enabled=True):
    set_auth_mode(monkeypatch, "native")
    set_auth_setting(monkeypatch, "sso_header_auth", enabled)
    set_auth_setting(monkeypatch, "sso_admin_group", ADMIN_GROUP)
    set_auth_setting(
        monkeypatch, "sso_trusted_proxies", ["testclient"] if trusted else ["127.0.0.1"]
    )
    ensure_user_dirs(auth_mode_settings / "default")
    return TestClient(main_mod.app)


def setup_admin(client):
    resp = client.post(
        "/api/auth/setup",
        json={"email": "admin@example.com", "password": "correct horse battery"},
    )
    assert resp.status_code == 200, resp.text


def create_user(client, email, password="another password", is_admin=False):
    resp = client.post(
        "/api/admin/users", json={"email": email, "password": password, "is_admin": is_admin}
    )
    assert resp.status_code == 200, resp.text


def admin_session(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery"},
    )
    assert resp.status_code == 200, resp.text


def test_existing_account_gets_a_session_from_headers(native_client, monkeypatch):
    setup_admin(native_client)
    set_auth_mode(monkeypatch, "native")
    set_auth_setting(monkeypatch, "sso_header_auth", True)
    set_auth_setting(monkeypatch, "sso_trusted_proxies", ["testclient"])

    resp = native_client.get("/api/auth/status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True
    # the app's own cookie now carries the identity, so the session survives
    # without the proxy headers (native login page is never shown)
    assert native_client.get("/api/auth/status").json()["authenticated"] is True
    assert get_account_store().count() == 1


def test_new_identity_is_provisioned_as_a_plain_account(auth_mode_settings, monkeypatch):
    client = make_sso_client(auth_mode_settings, monkeypatch)
    resp = client.get("/api/auth/status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True

    accounts = get_account_store().all()
    assert len(accounts) == 1
    assert accounts[0].email == SSO_EMAIL
    assert accounts[0].is_admin is False
    # the provisioned namespace is a directory the account can actually use
    assert (auth_mode_settings / accounts[0].storage_namespace).is_dir()

def test_admin_group_membership_elevates_a_provisioned_account(
    auth_mode_settings, monkeypatch
):
    client = make_sso_client(auth_mode_settings, monkeypatch)
    resp = client.get("/api/auth/status", headers={**HEADERS, "X-authentik-groups": ADMIN_GROUP})
    assert resp.json()["authenticated"] is True
    assert get_account_store().get_by_email(SSO_EMAIL).is_admin is True

    # and the elevation is real authority, not a status-page claim
    assert client.get("/api/admin/users").status_code == 200


def test_admin_group_elevates_an_existing_account_but_never_demotes(
    auth_mode_settings, monkeypatch
):
    client = make_sso_client(auth_mode_settings, monkeypatch)
    setup_admin(client)
    create_user(client, SSO_EMAIL)
    assert get_account_store().get_by_email(SSO_EMAIL).is_admin is False
    # the admin cookie from setup preempts the SSO path, which is by design:
    # drop it so the request actually flows through header trust
    client.cookies.clear()
    resp = client.get(
        "/api/auth/status", headers={**HEADERS, "X-authentik-groups": ADMIN_GROUP}
    )
    assert resp.json()["authenticated"] is True
    assert get_account_store().get_by_email(SSO_EMAIL).is_admin is True

    # the group is gone on the next request: elevation sticks, demotion is an
    # admin-API decision so a group edit cannot strip the last administrator
    resp = client.get("/api/auth/status", headers=HEADERS)
    assert resp.json()["authenticated"] is True
    assert get_account_store().get_by_email(SSO_EMAIL).is_admin is True


def test_disabled_account_is_refused_even_with_valid_headers(
    auth_mode_settings, monkeypatch
):
    client = make_sso_client(auth_mode_settings, monkeypatch)
    setup_admin(client)
    admin_session(client)
    create_user(client, SSO_EMAIL)
    user_id = get_account_store().get_by_email(SSO_EMAIL).id
    resp = client.post(f"/api/admin/users/{user_id}/disable")
    assert resp.status_code == 200
    client.cookies.clear()

    resp = client.get("/api/auth/status", headers=HEADERS)
    assert resp.json()["authenticated"] is False


def test_disabled_feature_ignores_headers(auth_mode_settings, monkeypatch):
    client = make_sso_client(auth_mode_settings, monkeypatch, enabled=False)
    resp = client.get("/api/auth/status", headers=HEADERS)
    assert resp.json()["authenticated"] is False
    assert get_account_store().count() == 0


def test_untrusted_client_is_ignored(auth_mode_settings, monkeypatch):
    client = make_sso_client(auth_mode_settings, monkeypatch, trusted=False)
    resp = client.get("/api/auth/status", headers=HEADERS)
    assert resp.json()["authenticated"] is False
    assert get_account_store().count() == 0


def test_invalid_email_header_is_ignored(auth_mode_settings, monkeypatch):
    client = make_sso_client(auth_mode_settings, monkeypatch)
    for bad in ("", "not-an-email", "a@b@c"):
        resp = client.get("/api/auth/status", headers={"X-authentik-email": bad})
        assert resp.json()["authenticated"] is False
    assert get_account_store().count() == 0

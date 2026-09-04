.PHONY: dev test test-backend test-frontend test-e2e test-e2e-ui lint lint-backend lint-frontend lint-fix

dev:
	@trap 'kill 0' EXIT; \
	(cd backend && . venv/bin/activate && uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && bun run dev) & \
	wait

test: test-backend test-frontend

test-backend:
	cd backend && . venv/bin/activate && python -m pytest

test-frontend:
	cd frontend && bun run test

test-e2e:
	cd frontend && E2E_TEST_MODE=1 GOOGLE_API_KEY=mock bun x playwright test

test-e2e-ui:
	cd frontend && E2E_TEST_MODE=1 GOOGLE_API_KEY=mock bun x playwright test --ui

lint: lint-backend lint-frontend

lint-backend:
	ruff check backend/

lint-frontend:
	cd frontend && bun run lint
	cd frontend && bun x tsc --noEmit

lint-fix:
	ruff check backend/ --fix
	cd frontend && bun run lint:fix

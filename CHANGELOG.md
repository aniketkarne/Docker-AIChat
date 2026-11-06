# Changelog

## Unreleased

### Fixed
- `frontend/package-lock.json` no longer resolves packages from a private
  Artifactory mirror (`artifactory.insim.biz`) — `npm ci` failed with ENOTFOUND
  for anyone outside that network, including the repo's own Dockerfile and CI.
  All `resolved` URLs now point at `registry.npmjs.org`.
- Frontend production build migrated to Tailwind CSS v4: `postcss.config.js`
  now uses `@tailwindcss/postcss` (the v3 `tailwindcss` plugin throws on
  `next build`), `styles/globals.css` uses `@import "tailwindcss"` + `@config`
  to keep the custom Netflix palette. `npm run build` was failing for
  everyone — which also meant the frontend Docker image could not build.
- Frontend now actually talks to the backend: all API calls go through
  `frontend/lib/api.ts`, which targets `NEXT_PUBLIC_API_BASE_URL`
  (default `http://localhost:8000`). Previously axios had no base URL, so
  every request hit the Next.js origin and the app could never reach the API.
- `NEXT_PUBLIC_API_BASE_URL` in `docker-compose.yml` is now a build arg with a
  browser-reachable default (`http://localhost:8000`); the compose-internal
  hostname `backend` does not resolve in the user's browser, and `NEXT_PUBLIC_`
  vars are inlined at build time anyway.
- Replaced the shut-down `gpt-4` model (removed from the API 2026-10-23) with
  `gpt-6-luna`, configurable via `OPENAI_MODEL`. Dropped `temperature=0`:
  current reasoning models reject non-default sampling parameters.
- `/suggestions` no longer makes two identical AI calls per request and now
  caches the optimized result on the session. Unknown or empty sessions get a
  404/422 instead of silently optimizing an empty Dockerfile.
- `/chat` history now includes the user's question, not just the assistant
  reply — the chat transcript no longer loses user messages after each send.
- Backend boots (and serves `/upload`, `/lint`, `/layers`) without
  `OPENAI_API_KEY`; the OpenAI client is created lazily and AI-backed
  endpoints return a clear 503 when the key is missing. Previously the app
  crashed at import time on any keyless deployment.
- `/optimize` rejects an empty `dockerfile` payload with 422 instead of
  sending "None" to the model.
- README manual setup no longer instructs `poetry install` (the repo has no
  Poetry project — it's `pip install -r requirements.txt`), and the Features
  list no longer claims working lint/layer profiling (both are placeholders).

### Added
- Backend test suite (`backend/tests/`, 11 tests, no network or API key
  needed) and `.github/workflows/tests.yml` CI (pytest on Python 3.11/3.12 +
  frontend production build).

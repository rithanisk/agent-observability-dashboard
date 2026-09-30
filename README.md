# Tracewell

Tracewell is an OpenTelemetry-native flight recorder and regression alarm for
AI agents. It ingests OTLP traces, turns them into readable runs, and will
compare agent versions before they ship.

The repository includes a Next.js dashboard, a FastAPI OTLP receiver, Postgres
storage, Docker Compose, CI, and a traced Google ADK research workflow backed
by NUS SoCLaaS.

## Local development

Requirements: Docker Desktop, Python 3.12+, `uv`, Node.js 22+, and npm.

```bash
cp .env.example .env
make install
make dev
```

Then open:

- Dashboard: http://localhost:3001 when using Docker Compose, or http://localhost:3000 with `make dev-web`
- API health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

The local API accepts unauthenticated OTLP traffic. Set
`TRACEWELL_INGEST_TOKEN` in hosted environments and send it as a Bearer token.

## Run the ADK demo

Set `SOCLAAS_API_KEY` in the ignored root `.env`, start the stack, and use the
**Run the real workflow** form on the dashboard. The backend runs a research
agent followed by a synthesis agent using `qwen3.5:9b`. ADK's native
OpenTelemetry spans are ingested by Tracewell and the browser opens the real
trace waterfall when the workflow completes.

Prompt and response content capture is enabled for this local demo. Keep it
disabled or add redaction before sending production or sensitive data.

## OTLP ingestion

Send OTLP/HTTP JSON or protobuf to `POST /v1/traces`. Historical runs are
available at `GET /api/runs`, and a complete trace at
`GET /api/runs/{trace_id}`.

## Hosted architecture

- Next.js dashboard on Vercel
- FastAPI ingestion service on Railway
- Supabase Postgres using the standard Postgres connection string
- SoCLaaS-backed Google ADK demo agents in controlled local and CI runs

Before deploying the API, apply the SQL files in `supabase/migrations` to the
Supabase project. Set `TRACEWELL_AUTO_CREATE_SCHEMA=false` in Railway after the
migration has been applied.

See [docs/PRD.md](docs/PRD.md) for the full product definition.

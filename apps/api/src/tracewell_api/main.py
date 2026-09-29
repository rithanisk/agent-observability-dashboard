import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse

from tracewell_api import __version__
from tracewell_api.config import get_settings
from tracewell_api.db import create_schema
from tracewell_api.otlp import InvalidOTLPPayload, decode_otlp
from tracewell_api.repository import TraceRepository, get_repository

settings = get_settings()
RepositoryDependency = Annotated[TraceRepository, Depends(get_repository)]
AuthorizationHeader = Annotated[str | None, Header()]
RunLimit = Annotated[int, Query(ge=1, le=200)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_schema:
        await create_schema()
    yield


app = FastAPI(
    title="Tracewell API",
    version=__version__,
    description="OTLP ingestion and trace query API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/v1/traces")
async def ingest_traces(
    request: Request,
    repository: RepositoryDependency,
    authorization: AuthorizationHeader = None,
) -> Response:
    _authorize_ingestion(authorization)
    content_type = request.headers.get("content-type", "")
    try:
        spans = decode_otlp(await request.body(), content_type)
    except InvalidOTLPPayload as exc:
        code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE if "Unsupported" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    await repository.upsert_spans(spans)
    media_type = content_type.partition(";")[0].strip().lower()
    if media_type in {"application/x-protobuf", "application/protobuf"}:
        payload = ExportTraceServiceResponse().SerializeToString()
        return Response(content=payload, media_type="application/x-protobuf")
    return Response(content=b"{}", media_type="application/json")


@app.get("/api/runs")
async def list_runs(
    repository: RepositoryDependency,
    limit: RunLimit = 50,
) -> dict[str, object]:
    runs = await repository.list_runs(limit)
    return {"data": runs}


@app.get("/api/runs/{trace_id}")
async def get_trace(
    trace_id: str,
    repository: RepositoryDependency,
) -> dict[str, object]:
    trace = await repository.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


def _authorize_ingestion(authorization: str | None) -> None:
    if not settings.ingest_token:
        return
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, settings.ingest_token):
        raise HTTPException(status_code=401, detail="Invalid ingestion token")

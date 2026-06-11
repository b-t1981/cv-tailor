from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.session_middleware import SessionMiddleware
from app.services.cleanup_service import cleanup_old_outputs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_old_outputs()
    yield


app = FastAPI(
    title="CV Tailor API",
    description="Adapt your CV to job descriptions while preserving document structure",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CV Tailor API", "docs": "/docs"}

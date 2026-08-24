"""Windows toolkit application entrypoint with Enterprise AI adapter enabled."""

from __future__ import annotations

from .enterprise_ai_routes import router as enterprise_ai_router
from .main import app

app.include_router(enterprise_ai_router)

__all__ = ["app"]

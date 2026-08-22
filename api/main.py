"""
FastAPI Backend - Main application entry point.
Serves API endpoints and static frontend files.
Integrates Setup Wizard, Chat, Briefing, and all agent capabilities.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import os

from api.config import settings
from agent.core.analyst import create_analyst
from agent.models.provider import create_model_router_from_config, prefix_model_name
from agent.memory.database import db_manager

# Import route modules
from api.routes.setup import router as setup_router
from api.routes.connectors import router as connectors_router
from api.routes.briefing import router as briefing_router
from api.routes.dashboard import router as dashboard_router
from api.routes.settings import router as settings_router

# ==================== APP INITIALIZATION ====================

# Global analyst instance (initialized on startup)
analyst = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application state on startup, clean up on shutdown."""
    global analyst

    print(f"🚀 Starting {settings.app_name}")
    print(f"📊 Model config: {settings.models}")
    print(f"🔒 Security mode: air_gap={settings.security.air_gap_mode}, read_only={settings.security.read_only}")
    print(f"🌐 Newsroom: {'enabled' if settings.newsroom.enabled else 'disabled'}")

    # Ensure data directory exists
    os.makedirs(settings.data_dir, exist_ok=True)

    # Initialize the analyst from settings (setup wizard can override later)
    try:
        model_config = {
            "reasoning": settings.models.reasoning,
            "sql": settings.models.sql,
            "embedding": settings.models.embedding,
            "fallback": settings.models.fallback,
        }
        analyst = create_analyst(
            model_config,
            newsroom_enabled=settings.newsroom.enabled and not settings.security.air_gap_mode,
        )
        print("✅ Analyst initialized")
    except Exception as e:
        print(f"⚠️ Analyst initialization failed (will retry on demand): {e}")
        analyst = None

    # If setup was completed in a previous run, reload the saved
    # configuration (models + database) so restarts keep working.
    if db_manager.get_config("setup_complete", is_sensitive=False):
        reinitialize_analyst()

    # Continuous data sync: keep Drive/Gmail/Sheets knowledge fresh.
    # Runs every 6 hours while the app is up; connectors that are not
    # configured are skipped. (APScheduler replaces this with the Sense
    # loop's nightly briefing in a later build.)
    sync_task = asyncio.create_task(continuous_sync_loop())

    # Sense loop: nightly briefing with anomaly detection.
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from agent.sense.briefing import generate_briefing

    scheduler = AsyncIOScheduler(timezone=settings.briefing_timezone)

    async def run_nightly_briefing():
        global analyst
        if analyst is None:
            print("🌙 Nightly briefing skipped: analyst not initialized")
            return
        try:
            briefing = await generate_briefing(analyst)
            print(f"🌙 Nightly briefing stored: {briefing['status']} "
                  f"({len(briefing['findings'])} findings)")
            await broadcast_update({"type": "briefing", "briefing": briefing})
        except Exception as e:
            print(f"⚠️ Nightly briefing failed: {e}")

    scheduler.add_job(
        run_nightly_briefing,
        "cron",
        hour=settings.briefing_hour,
        minute=0,
        id="nightly_briefing",
        replace_existing=True,
    )
    scheduler.start()
    print(f"🌙 Sense loop scheduled: daily {settings.briefing_hour:02d}:00 ({settings.briefing_timezone})")

    yield

    sync_task.cancel()
    scheduler.shutdown(wait=False)
    print("👋 Shutting down")


async def continuous_sync_loop(interval_hours: float = 6.0):
    """Background task: sync all configured connectors on a schedule."""
    from agent.connectors import sync_all

    while True:
        try:
            results = await sync_all()
            for cid, r in results.items():
                if r.errors:
                    print(f"🔄 Sync {cid}: {r.message}")
                else:
                    print(f"🔄 Sync {cid}: {r.synced} items")
        except Exception as e:
            print(f"⚠️ Continuous sync failed: {e}")
        await asyncio.sleep(interval_hours * 3600)


app = FastAPI(
    title=settings.app_name,
    description="Autonomous AI Business Analyst - Self-hosted, model-agnostic, always learning",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development.
# NOTE: allow_credentials=True with allow_origins=["*"] is rejected by browsers,
# so credentials are only enabled when explicit origins are configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured per deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(setup_router, prefix="/api")
app.include_router(connectors_router, prefix="/api")
app.include_router(briefing_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


# ==================== ANALYST LIFECYCLE ====================

def reinitialize_analyst() -> bool:
    """
    (Re)create the analyst from saved configuration.
    Called after the setup wizard completes so the running
    instance picks up the user's model choices and database immediately.
    """
    global analyst
    try:
        models = db_manager.get_config("models", is_sensitive=False) or {}
        features = db_manager.get_config("features", is_sensitive=False) or {}
        database_url = db_manager.get_config("database_url", is_sensitive=False)
        provider = db_manager.get_config("ai_provider", is_sensitive=False) or "ollama-local"
        api_key = db_manager.get_config("api_key", is_sensitive=True)
        base_url = db_manager.get_config("base_url", is_sensitive=False)
        air_gap = features.get("air_gap", False)
        newsroom_enabled = features.get("newsroom", True) and not air_gap

        # Prefix model names for litellm (e.g. 'qwen2.5:7b' -> 'ollama/qwen2.5:7b')
        model_config = {
            "reasoning": prefix_model_name(
                models.get("reasoning") or settings.models.reasoning, provider
            ),
            "sql": prefix_model_name(
                models.get("sql") or settings.models.sql, provider
            ),
            "embedding": prefix_model_name(
                models.get("embedding") or settings.models.embedding, provider
            ),
            "fallback": prefix_model_name(
                models.get("fallback") or settings.models.fallback, provider
            ),
        }
        analyst = create_analyst(
            model_config,
            newsroom_enabled=newsroom_enabled,
            database_url=database_url,
            api_key=api_key,
            api_base=base_url,
        )
        print(f"✅ Analyst re-initialized with models: {model_config}")
        if database_url:
            print(f"🗄️  Database connected: {database_url.split('://')[0]}://***")
        return True
    except Exception as e:
        print(f"⚠️ Analyst re-initialization failed: {e}")
        analyst = None
        return False


# ==================== REQUEST/RESPONSE MODELS ====================

class AnalysisRequest(BaseModel):
    question: str
    context: Optional[Dict[str, str]] = None


class AnalysisResponse(BaseModel):
    answer: str
    confidence: float
    sql_query: Optional[str]
    needs_review: bool
    market_context: Optional[str]


class FeedbackRequest(BaseModel):
    analysis_id: str
    rating: int  # 1-5
    correction: Optional[str] = None


# ==================== API ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    Run autonomous analysis on a business question.

    Returns comprehensive answer with SQL, confidence score, and market context.
    """
    if analyst is None:
        raise HTTPException(
            status_code=503,
            detail="Analyst is not initialized. Complete the setup wizard first.",
        )

    try:
        result = await analyst.analyze(
            question=request.question,
            context=request.context,
        )

        return AnalysisResponse(
            answer=result['answer'],
            confidence=result['confidence'],
            sql_query=result.get('sql'),
            needs_review=result.get('needs_review', False),
            market_context=result.get('market_context'),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on an analysis to improve future performance.
    This feeds into the learning memory system.
    """
    # TODO: Implement memory storage for feedback
    # For now, just acknowledge receipt
    return {"status": "received", "message": "Feedback recorded for learning"}


# ==================== WEBSOCKET FOR REAL-TIME UPDATES ====================

active_connections: List[WebSocket] = []


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for pushing proactive updates to clients.
    Used for real-time briefing notifications and analysis progress.
    """
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Keep connection alive, receive heartbeats
            data = await websocket.receive_text()

            # Could handle client messages here
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_update(message: dict):
    """Broadcast update to all connected clients."""
    if not active_connections:
        return

    message_json = json.dumps(message)
    disconnected = []

    for conn in active_connections:
        try:
            await conn.send_text(message_json)
        except Exception:
            disconnected.append(conn)

    # Clean up disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


# ==================== STATIC FILES (FRONTEND) ====================

class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for client-side routes.

    Lets React Router handle /dashboard, /chat, etc. on direct navigation
    and refresh, while unknown /api/* paths still return a real 404.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


# Serve built React frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "../web/dist")
if os.path.exists(frontend_dir):
    app.mount("/", SPAStaticFiles(directory=frontend_dir, html=True), name="static")
else:
    @app.get("/")
    async def root():
        """Root endpoint - shows API info when frontend not built."""
        return {
            "message": "AI Business Analyst API",
            "docs": "/docs",
            "status": "Backend running - build frontend with: cd web && npm install && npm run build",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
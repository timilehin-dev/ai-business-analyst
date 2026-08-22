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
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import json
import os

from api.config import settings
from agent.core.analyst import create_analyst
from agent.memory.database import db_manager
from agent.memory.memory import memory_store
from agent.models.provider import prefix_model_name

# Import route modules
from api.routes.setup import router as setup_router
from api.routes.connectors import router as connectors_router
from api.routes.briefing import router as briefing_router
from api.routes.dashboard import router as dashboard_router
from api.routes.settings import router as settings_router
from api.routes.memory import router as memory_router, audit_router

# ==================== APP INITIALIZATION ====================

# Global analyst instance (initialized on startup)
analyst = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application state on startup, clean up on shutdown."""
    global analyst

    print(f"🚀 Starting {settings.app_name}")
    print(f"🔒 Security mode: air_gap={settings.security.air_gap_mode}, read_only={settings.security.read_only}")

    os.makedirs(settings.data_dir, exist_ok=True)

    # Load saved configuration when the wizard has been completed before,
    # otherwise fall back to environment/defaults so the API still answers.
    if db_manager.get_config("setup_complete", is_sensitive=False):
        reinitialize_analyst()
    else:
        try:
            analyst = create_analyst(
                {
                    "reasoning": settings.models.reasoning,
                    "sql": settings.models.sql,
                    "embedding": settings.models.embedding,
                    "fallback": settings.models.fallback,
                },
                newsroom_enabled=settings.newsroom.enabled and not settings.security.air_gap_mode,
            )
            print("✅ Analyst initialized from defaults (run setup to configure)")
        except Exception as e:
            print(f"⚠️ Analyst initialization failed (will retry on demand): {e}")
            analyst = None

    background_tasks = []
    scheduler = None

    if proactive_monitoring_enabled():
        background_tasks.append(asyncio.create_task(continuous_sync_loop()))
        scheduler = start_sense_loop()
    else:
        print("💤 Proactive monitoring disabled — no background sync or briefing")

    memory_store.audit("app.started", {"proactive": proactive_monitoring_enabled()})

    yield

    for task in background_tasks:
        task.cancel()
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    memory_store.audit("app.stopped", {})
    print("👋 Shutting down")


def proactive_monitoring_enabled() -> bool:
    """The wizard/settings toggle gates all background work."""
    features = db_manager.get_config("features", is_sensitive=False) or {}
    return bool(features.get("proactive_monitoring", True))


def briefing_schedule() -> tuple:
    """(hour, timezone) for the nightly briefing, user settings first."""
    general = db_manager.get_config("general", is_sensitive=False) or {}
    hour = general.get("briefing_hour", settings.briefing_hour)
    timezone = general.get("briefing_timezone", settings.briefing_timezone)
    try:
        hour = max(0, min(23, int(hour)))
    except (TypeError, ValueError):
        hour = settings.briefing_hour
    return hour, timezone or settings.briefing_timezone


def start_sense_loop():
    """Schedule the nightly anomaly scan + briefing."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    hour, timezone = briefing_schedule()
    try:
        scheduler = AsyncIOScheduler(timezone=timezone)
    except Exception:
        # An invalid timezone string must not prevent the app from starting.
        print(f"⚠️ Invalid briefing timezone '{timezone}', falling back to UTC")
        timezone = "UTC"
        scheduler = AsyncIOScheduler(timezone=timezone)

    scheduler.add_job(
        run_nightly_briefing,
        "cron",
        hour=hour,
        minute=0,
        id="nightly_briefing",
        replace_existing=True,
    )
    scheduler.start()
    print(f"🌙 Sense loop scheduled: daily {hour:02d}:00 ({timezone})")
    return scheduler


async def run_nightly_briefing():
    """Run the Sense loop and push the result to connected clients."""
    from agent.sense.briefing import generate_briefing

    if analyst is None:
        print("🌙 Nightly briefing skipped: analyst not initialized")
        return
    try:
        briefing = await generate_briefing(analyst)
        print(
            f"🌙 Nightly briefing stored: {briefing['status']} "
            f"({len(briefing['findings'])} findings)"
        )
        memory_store.audit(
            "briefing.generated",
            {"status": briefing["status"], "findings": len(briefing["findings"])},
        )
        await broadcast_update({"type": "briefing", "briefing": briefing})
    except Exception as e:
        print(f"⚠️ Nightly briefing failed: {e}")
        memory_store.audit("briefing.failed", {"error": str(e)}, success=False)


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
            if results:
                memory_store.audit(
                    "connectors.synced",
                    {cid: {"synced": r.synced, "errors": r.errors} for cid, r in results.items()},
                )
                await broadcast_update(
                    {
                        "type": "sync",
                        "results": {cid: r.synced for cid, r in results.items()},
                    }
                )
        except asyncio.CancelledError:
            raise
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
app.include_router(memory_router, prefix="/api")
app.include_router(audit_router, prefix="/api")


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
        code_sandbox_enabled = features.get("code_sandbox", True)

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
            code_sandbox_enabled=code_sandbox_enabled,
        )
        print(f"✅ Analyst re-initialized with models: {model_config}")
        if database_url:
            print(f"🗄️  Database connected: {database_url.split('://')[0]}://***")
        memory_store.audit(
            "analyst.initialized",
            {
                "models": model_config,
                "newsroom": newsroom_enabled,
                "code_sandbox": code_sandbox_enabled,
                "database_configured": bool(database_url),
            },
        )
        return True
    except Exception as e:
        print(f"⚠️ Analyst re-initialization failed: {e}")
        memory_store.audit("analyst.initialization_failed", {"error": str(e)}, success=False)
        analyst = None
        return False


# ==================== REQUEST/RESPONSE MODELS ====================

class AnalysisRequest(BaseModel):
    question: str
    context: Optional[Dict[str, str]] = None
    use_memory: bool = True


class AnalysisResponse(BaseModel):
    answer: str
    confidence: float
    sql_query: Optional[str]
    needs_review: bool
    market_context: Optional[str]
    episode_id: Optional[int] = None
    context_used: Optional[Dict[str, Any]] = None


class FeedbackRequest(BaseModel):
    """
    Feedback on one analysis.

    episode_id identifies the analysis; it is returned by /api/analyze.
    A rating <= 3 with a correction becomes a standing rule applied to
    every future analysis.
    """

    episode_id: int
    rating: int = Field(..., ge=1, le=5)
    correction: Optional[str] = None


# ==================== API ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/api/status")
async def system_status():
    """Runtime capability report — what is actually active right now."""
    features = db_manager.get_config("features", is_sensitive=False) or {}
    hour, timezone = briefing_schedule()
    sandbox_isolation = "unknown"
    if analyst is not None:
        from agent.tools.sandbox import CodeSandboxTool

        sandbox_isolation = CodeSandboxTool(
            enabled=analyst.code_sandbox_enabled
        ).isolation

    return {
        "analyst_ready": analyst is not None,
        "database_connected": bool(analyst and analyst.db_conn),
        "features": {
            "newsroom": bool(analyst and analyst.newsroom_tool.enabled),
            "code_sandbox": bool(analyst and analyst.code_sandbox_enabled),
            "sandbox_isolation": sandbox_isolation,
            "air_gap": features.get("air_gap", False),
            "proactive_monitoring": proactive_monitoring_enabled(),
        },
        "briefing": {"hour": hour, "timezone": timezone},
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    Run autonomous analysis on a business question.

    Returns the answer with SQL, confidence, provenance, and the episode id
    used to attach feedback.
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
            use_memory=request.use_memory,
        )
    except HTTPException:
        raise
    except Exception as e:
        memory_store.audit(
            "analysis.failed",
            {"question": request.question, "error": str(e)},
            success=False,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # Persist each interaction so chat/query history survives sessions.
    try:
        db_manager.save_chat_history(
            question=request.question,
            sql_query=result.get("sql"),
            answer=result.get("answer"),
            confidence=result.get("confidence"),
        )
    except Exception:
        pass  # Non-blocking: history is a convenience, not the analysis

    return AnalysisResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        sql_query=result.get("sql"),
        needs_review=result.get("needs_review", False),
        market_context=result.get("market_context"),
        episode_id=result.get("episode_id"),
        context_used=result.get("context_used"),
    )


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on an analysis.

    Ratings are stored on the episode. A negative rating accompanied by a
    written correction is promoted to a procedural rule, which is injected
    into the context of every subsequent analysis — this is what makes the
    system improve rather than merely record.
    """
    result = memory_store.add_feedback(
        episode_id=request.episode_id,
        rating=request.rating,
        correction=request.correction,
    )
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Analysis {request.episode_id} not found"
        )

    memory_store.audit(
        "feedback.submitted",
        {
            "episode_id": request.episode_id,
            "rating": request.rating,
            "rule_created": result["rule_created"],
        },
        actor="user",
    )

    message = "Feedback recorded."
    if result["rule_created"]:
        message = "Feedback recorded. Your correction is now a standing instruction for future analyses."

    return {"success": True, "message": message, **result}


# ==================== WEBSOCKET FOR REAL-TIME UPDATES ====================

active_connections: List[WebSocket] = []


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for pushing proactive updates to clients.
    Used for real-time briefing notifications and sync progress.
    """
    await websocket.accept()
    active_connections.append(websocket)

    try:
        # Tell the client what it connected to so it can render state
        # immediately instead of waiting for the first push.
        await websocket.send_text(
            json.dumps({"type": "connected", "analyst_ready": analyst is not None})
        )
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        # discard-style removal: a broadcast failure may have already
        # dropped this connection, and remove() would then raise.
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_update(message: dict):
    """Broadcast update to all connected clients."""
    if not active_connections:
        return

    message_json = json.dumps(message, default=str)
    disconnected = []

    for conn in active_connections:
        try:
            await conn.send_text(message_json)
        except Exception:
            disconnected.append(conn)

    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# ==================== PERSISTENT QUERY HISTORY ====================
@app.get("/api/chat/history")
async def chat_history():
    """Return persistent query history (survives across sessions)."""
    return {"history": db_manager.get_chat_history(limit=20)}


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

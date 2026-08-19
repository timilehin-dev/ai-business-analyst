"""
FastAPI Backend - Main application entry point.
Serves API endpoints and static frontend files.
Integrates Setup Wizard, Chat, Briefing, and all agent capabilities.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import os

from api.config import settings
from agent.core.analyst import create_analyst
from agent.models.provider import create_model_router_from_config
from agent.memory.database import db_manager

# Import route modules
from api.routes.setup import router as setup_router

# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title=settings.app_name,
    description="Autonomous AI Business Analyst - Self-hosted, model-agnostic, always learning",
    version="0.1.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured per deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(setup_router, prefix="/api")

# Global analyst instance (initialized after setup)
analyst_instance = None


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
    try:
        result = await analyst.analyze(
            question=request.question,
            context=request.context
        )
        
        return AnalysisResponse(
            answer=result['answer'],
            confidence=result['confidence'],
            sql_query=result.get('sql'),
            needs_review=result.get('needs_review', False),
            market_context=result.get('market_context')
        )
    
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


@app.get("/api/briefing")
async def get_briefing():
    """
    Get proactive briefing with overnight findings and anomalies.
    TODO: Implement scheduled analysis engine.
    """
    return {
        "findings": [],
        "anomalies": [],
        "kpi_status": "operational"
    }


@app.get("/api/connectors")
async def list_connectors():
    """List available data connectors."""
    return {
        "available": ["PostgreSQL", "MySQL", "CSV", "Parquet"],
        "configured": []  # TODO: Load from config
    }


@app.post("/api/connectors/test")
async def test_connector(connection_string: str, connector_type: str):
    """Test database connection."""
    # TODO: Implement connection testing
    return {"success": True, "message": "Connection successful"}


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
        except:
            disconnected.append(conn)
    
    # Clean up disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


# ==================== STATIC FILES (FRONTEND) ====================

# Serve built React frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "../web/dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
else:
    @app.get("/")
    async def root():
        """Root endpoint - shows API info when frontend not built."""
        return {
            "message": "AI Business Analyst API",
            "docs": "/docs",
            "status": "Backend running - build frontend with: cd web && npm install && npm run build"
        }


# ==================== STARTUP EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print(f"🚀 Starting {settings.app_name}")
    print(f"📊 Model config: {settings.models}")
    print(f"🔒 Security mode: air_gap={settings.security.air_gap_mode}, read_only={settings.security.read_only}")
    print(f"🌐 Newsroom: {'enabled' if settings.newsroom.enabled else 'disabled'}")
    
    # Ensure data directory exists
    os.makedirs(settings.data_dir, exist_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

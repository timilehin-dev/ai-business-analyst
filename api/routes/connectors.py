"""
Data Connectors API.

Endpoints for the knowledge-graph ingestion layer:
  - list connectors and their state
  - upload local files (CSV, DOCX, PDF, TXT, JSON)
  - sync Google Drive / Sheets / Gmail (OAuth)
  - browse and delete ingested documents
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from agent.connectors import get_connector, list_connectors, sync_all
from agent.connectors.google import google_connector
from agent.connectors.local import LocalFileConnector
from agent.connectors.storage import document_store

router = APIRouter(prefix="/connectors", tags=["connectors"])


# ==================== REQUEST MODELS ====================

class GoogleCredentials(BaseModel):
    client_id: str
    client_secret: str


class GoogleAuthResponse(BaseModel):
    auth_url: str


# ==================== CONNECTOR STATUS ====================

@router.get("")
async def get_connectors() -> Dict[str, Any]:
    """List all connectors with configuration and document counts."""
    connectors = []
    for c in list_connectors():
        info = dict(c)
        info["document_count"] = document_store.count_documents(source=c["id"])
        state = document_store.get_state(c["id"])
        info["last_sync_at"] = state["last_sync_at"]
        info["last_error"] = state["last_error"]
        connectors.append(info)
    return {
        "connectors": connectors,
        "total_documents": document_store.count_documents(),
    }


# ==================== LOCAL FILE UPLOAD ====================

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Ingest an uploaded CSV/DOCX/PDF/TXT/JSON file into the document store."""
    data = await file.read()
    connector = LocalFileConnector()
    try:
        doc = connector.ingest_bytes(file.filename or "upload", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    created = document_store.save_document(doc)
    doc_id = document_store.get_document_id(doc.source, doc.source_id)
    return {
        "success": True,
        "document": {
            "id": doc_id,
            "source": doc.source,
            "title": doc.title,
            "created": created,
            "content_preview": doc.content[:300],
        },
    }


# ==================== GOOGLE OAUTH ====================

@router.post("/google/credentials")
async def save_google_credentials(creds: GoogleCredentials) -> Dict[str, Any]:
    """Store the Google Cloud OAuth client ID/secret (encrypted)."""
    google_connector.save_credentials(creds.client_id, creds.client_secret)
    return {"success": True, "message": "Google credentials saved."}


@router.get("/google/auth", response_model=GoogleAuthResponse)
async def google_auth_url() -> GoogleAuthResponse:
    """Get the Google consent URL for the OAuth flow."""
    try:
        redirect_uri = _redirect_uri()
        return GoogleAuthResponse(auth_url=google_connector.build_auth_url(redirect_uri))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/google/callback")
async def google_callback(code: str) -> Dict[str, Any]:
    """OAuth callback: exchange the code for tokens and store them."""
    try:
        await google_connector.exchange_code(code, _redirect_uri())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google auth failed: {str(e)}")
    return {
        "success": True,
        "message": "Google Workspace connected. You can close this tab.",
    }


@router.post("/google/disconnect")
async def google_disconnect() -> Dict[str, Any]:
    """Remove stored Google tokens."""
    google_connector.disconnect()
    return {"success": True, "message": "Google disconnected."}


def _redirect_uri() -> str:
    """Callback URL registered in the Google Cloud console."""
    from api.config import settings
    return getattr(settings, "google_redirect_uri", None) or "http://localhost:3001/api/connectors/google/callback"


# ==================== SYNC ====================

@router.post("/{connector_id}/sync")
async def sync_connector(connector_id: str) -> Dict[str, Any]:
    """Run a connector sync now (Google Drive/Sheets/Gmail)."""
    try:
        connector = get_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {connector_id}")

    if not connector.is_configured():
        raise HTTPException(status_code=400, detail=f"{connector.name} is not configured.")

    result = await connector.sync()
    return {
        "success": not result.errors,
        "connector_id": connector_id,
        "synced": result.synced,
        "errors": result.errors,
        "message": result.message,
    }


@router.post("/sync-all")
async def sync_all_connectors() -> Dict[str, Any]:
    """Sync every configured connector (used by the continuous sync task too)."""
    results = await sync_all()
    return {
        "success": True,
        "results": {
            cid: {"synced": r.synced, "errors": r.errors, "message": r.message}
            for cid, r in results.items()
        },
    }


# ==================== DOCUMENTS ====================

class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    source: Optional[str] = None, limit: int = 100, offset: int = 0
) -> DocumentListResponse:
    """Browse ingested documents (the knowledge graph)."""
    return DocumentListResponse(
        documents=document_store.list_documents(source=source, limit=limit, offset=offset),
        total=document_store.count_documents(source=source),
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int) -> Dict[str, Any]:
    """Remove one document from the knowledge graph."""
    if not document_store.delete_document(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return {"success": True, "message": f"Document {doc_id} deleted."}


@router.delete("/documents/source/{source}")
async def delete_source(source: str) -> Dict[str, Any]:
    """Remove all documents from one source (e.g. 'gmail')."""
    deleted = document_store.delete_source(source)
    return {"success": True, "deleted": deleted, "message": f"Deleted {deleted} documents."}

"""
Google Connectors - Drive, Sheets, Gmail.

Full OAuth 2.0 flow (authorization code + refresh token) implemented with
httpx — no heavy google-api-python-client dependency.

Setup required once (5 minutes, documented in README):
  1. Create a Google Cloud project -> enable Drive, Sheets, Gmail APIs
  2. OAuth consent screen -> add scopes below
  3. OAuth client ID (Web application) -> add redirect URI
     http://localhost:3001/api/connectors/google/callback
  4. Enter client ID + secret in the Data Sources page

Tokens are stored encrypted in the analyst DB and refreshed automatically.
"""
import base64
import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from agent.connectors.base import BaseConnector, ConnectorResult, Document
from agent.connectors.local import LocalFileConnector
from agent.connectors.storage import document_store
from agent.memory.database import db_manager

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]
SCOPE_STR = " ".join(SCOPES)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Drive mime types we can ingest
DRIVE_TEXT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}
DRIVE_DOWNLOAD_MIME = {
    "application/pdf": ".pdf",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/json": ".json",
}


class GoogleConnector(BaseConnector):
    id = "google"
    name = "Google Workspace"
    description = "Google Drive, Sheets, and Gmail (read-only)"
    icon = "google"

    def __init__(self):
        self._local = LocalFileConnector()

    # ==================== CREDENTIALS ====================

    def _creds(self) -> Optional[Dict[str, str]]:
        return db_manager.get_config("google_oauth", is_sensitive=True)

    def _tokens(self) -> Optional[Dict[str, Any]]:
        return db_manager.get_config("google_tokens", is_sensitive=True)

    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        db_manager.save_config("google_tokens", tokens, is_sensitive=True)

    def is_configured(self) -> bool:
        return bool(self._creds() and self._tokens())

    def has_credentials(self) -> bool:
        """OAuth client ID/secret saved (tokens may not exist yet)."""
        return bool(self._creds())

    def save_credentials(self, client_id: str, client_secret: str) -> None:
        db_manager.save_config(
            "google_oauth", {"client_id": client_id, "client_secret": client_secret}, is_sensitive=True
        )

    def disconnect(self) -> None:
        db_manager.save_config("google_tokens", {}, is_sensitive=True)

    # ==================== OAUTH FLOW ====================

    def build_auth_url(self, redirect_uri: str) -> str:
        creds = self._creds()
        if not creds:
            raise ValueError("Google client ID not configured")
        params = {
            "client_id": creds["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE_STR,
            "access_type": "offline",
            "prompt": "consent",
        }
        from urllib.parse import urlencode
        return f"{AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        creds = self._creds()
        if not creds:
            raise ValueError("Google client ID not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()
        tokens["token_expiry"] = (
            datetime.now(timezone.utc).timestamp() + tokens.get("expires_in", 3600)
        )
        self._save_tokens(tokens)
        return tokens

    # ==================== TOKEN MANAGEMENT ====================

    async def _access_token(self) -> str:
        tokens = self._tokens()
        if not tokens or not tokens.get("access_token"):
            raise ValueError("Google not connected. Connect in Data Sources first.")

        expiry = tokens.get("token_expiry", 0)
        if expiry and expiry > datetime.now(timezone.utc).timestamp() + 60:
            return tokens["access_token"]

        # Refresh
        creds = self._creds()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "refresh_token": tokens.get("refresh_token", ""),
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            new = resp.json()
        tokens["access_token"] = new["access_token"]
        tokens["token_expiry"] = datetime.now(timezone.utc).timestamp() + new.get("expires_in", 3600)
        self._save_tokens(tokens)
        return tokens["access_token"]

    async def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {await self._access_token()}"}

    # ==================== SYNC ====================

    async def sync(self) -> ConnectorResult:
        result = ConnectorResult(connector_id=self.id)
        if not self.is_configured():
            result.errors.append("Google not connected")
            result.message = "Connect Google Workspace first."
            return result

        try:
            docs: List[Document] = []
            docs += await self._sync_drive()
            docs += await self._sync_gmail()
            counts = document_store.save_documents(docs)
            result.synced = counts["created"] + counts["updated"]
            result.message = f"Synced {len(docs)} items from Drive, Sheets, and Gmail."
            document_store.save_state(self.id, last_error=None)
        except Exception as e:
            result.errors.append(str(e))
            result.message = f"Sync failed: {e}"
            document_store.save_state(self.id, last_error=str(e))
        return result

    # ==================== DRIVE + SHEETS ====================

    async def _sync_drive(self) -> List[Document]:
        headers = await self._headers()
        docs: List[Document] = []
        async with httpx.AsyncClient(timeout=30) as client:
            page_token = None
            while True:
                params = {
                    "q": "trashed = false",
                    "pageSize": 100,
                    "fields": "nextPageToken,files(id,name,mimeType,modifiedTime)",
                }
                if page_token:
                    params["pageToken"] = page_token
                resp = await client.get(
                    "https://www.googleapis.com/drive/v3/files", headers=headers, params=params
                )
                resp.raise_for_status()
                data = resp.json()
                for f in data.get("files", []):
                    doc = await self._ingest_drive_file(client, headers, f)
                    if doc:
                        docs.append(doc)
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        return docs

    async def _ingest_drive_file(self, client, headers, f: Dict[str, Any]) -> Optional[Document]:
        file_id = f["id"]
        mime = f.get("mimeType", "")
        name = f.get("name", file_id)

        try:
            if mime in DRIVE_TEXT_MIME:
                # Google Docs / Sheets -> export as text
                export_mime = DRIVE_TEXT_MIME[mime]
                resp = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                    headers=headers,
                    params={"mimeType": export_mime},
                )
                resp.raise_for_status()
                content = resp.text
                if mime.endswith("spreadsheet"):
                    content = self._csv_to_markdown(content)
                source = "sheets" if mime.endswith("spreadsheet") else "drive"
            elif mime in DRIVE_DOWNLOAD_MIME:
                resp = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                    headers=headers,
                )
                resp.raise_for_status()
                ext = DRIVE_DOWNLOAD_MIME[mime]
                content = self._local._extract_text(ext, name, resp.content)
                source = "drive"
            else:
                return None  # unsupported type (folders, images, ...)

            return Document(
                source=source,
                source_id=file_id,
                title=name,
                content=content,
                metadata={
                    "drive_id": file_id,
                    "mime_type": mime,
                    "modified_time": f.get("modifiedTime"),
                    "url": f"https://drive.google.com/file/d/{file_id}/view",
                },
            )
        except Exception as e:
            # Skip files that fail individually; report in result errors.
            return Document(
                source="drive",
                source_id=file_id,
                title=f"{name} (sync error)",
                content=f"Failed to sync this file: {e}",
                metadata={"drive_id": file_id, "mime_type": mime, "error": str(e)},
            )

    @staticmethod
    def _csv_to_markdown(text: str) -> str:
        import csv
        import io

        rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
        if not rows:
            return "(empty spreadsheet)"
        lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in rows[0]) + " |"]
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    # ==================== GMAIL ====================

    async def _sync_gmail(self, query: str = "newer_than:90d", max_results: int = 50) -> List[Document]:
        headers = await self._headers()
        docs: List[Document] = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": query, "maxResults": max_results},
            )
            resp.raise_for_status()
            messages = resp.json().get("messages", [])
            for m in messages:
                doc = await self._ingest_gmail_message(client, headers, m["id"])
                if doc:
                    docs.append(doc)
        return docs

    async def _ingest_gmail_message(self, client, headers, msg_id: str) -> Optional[Document]:
        try:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
            )
            resp.raise_for_status()
            msg = resp.json()
            payload = msg.get("payload", {})
            subject = self._header(payload, "Subject") or f"Email {msg_id}"
            sender = self._header(payload, "From") or ""
            date = self._header(payload, "Date") or ""
            body = self._extract_body(payload)
            if not body.strip():
                return None
            return Document(
                source="gmail",
                source_id=msg_id,
                title=f"{subject}",
                content=body,
                metadata={
                    "from": sender,
                    "date": date,
                    "subject": subject,
                    "url": f"https://mail.google.com/mail/u/0/#inbox/{msg_id}",
                },
            )
        except Exception as e:
            return Document(
                source="gmail",
                source_id=msg_id,
                title=f"Email {msg_id} (sync error)",
                content=f"Failed to sync this email: {e}",
                metadata={"error": str(e)},
            )

    @staticmethod
    def _header(payload: Dict[str, Any], name: str) -> str:
        for h in payload.get("headers", []):
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "")
        return ""

    @staticmethod
    def _extract_body(payload: Dict[str, Any]) -> str:
        """Walk the MIME tree, prefer text/plain, fall back to stripped HTML."""
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            return GoogleConnector._decode_body(payload.get("body", {}).get("data", ""))
        if mime == "text/html":
            raw = GoogleConnector._decode_body(payload.get("body", {}).get("data", ""))
            return GoogleConnector._strip_html(raw)

        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                text = GoogleConnector._decode_body(part.get("body", {}).get("data", ""))
                if text.strip():
                    return text
        for part in parts:
            if part.get("mimeType") == "text/html":
                raw = GoogleConnector._decode_body(part.get("body", {}).get("data", ""))
                text = GoogleConnector._strip_html(raw)
                if text.strip():
                    return text
        # Nested multipart
        for part in parts:
            if part.get("parts"):
                text = GoogleConnector._extract_body(part)
                if text.strip():
                    return text
        return ""

    @staticmethod
    def _decode_body(data: str) -> str:
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _strip_html(raw: str) -> str:
        text = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
        text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</p>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return html.unescape(re.sub(r"\s+", " ", text)).strip()


# Global instance
google_connector = GoogleConnector()
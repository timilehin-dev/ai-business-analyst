"""
Memory & Audit API.

Exposes the learning layers so users can see and steer what the analyst
knows:
  - glossary  (semantic)  : how this organization defines its terms
  - history   (episodic)  : past analyses and the ratings they received
  - rules     (procedural): standing instructions learned from corrections
  - audit                 : append-only record of what the system did
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.memory.memory import memory_store

router = APIRouter(prefix="/memory", tags=["memory"])


# ==================== MODELS ====================

class TermCreate(BaseModel):
    term: str = Field(..., min_length=1, description="The business term")
    definition: str = Field(..., min_length=1, description="What it means here")


class RuleCreate(BaseModel):
    rule: str = Field(..., min_length=1, description="Standing instruction for future analyses")


# ==================== OVERVIEW ====================

@router.get("")
async def get_memory_overview() -> Dict[str, Any]:
    """Everything the analyst currently remembers."""
    return {
        "glossary": memory_store.list_terms(),
        "rules": memory_store.list_rules(active_only=False),
        "recent_episodes": memory_store.list_episodes(limit=20),
    }


# ==================== SEMANTIC (GLOSSARY) ====================

@router.get("/glossary")
async def list_glossary() -> Dict[str, Any]:
    terms = memory_store.list_terms()
    return {"terms": terms, "total": len(terms)}


@router.post("/glossary")
async def create_term(payload: TermCreate) -> Dict[str, Any]:
    term = memory_store.add_term(payload.term, payload.definition, source="user")
    memory_store.audit("memory.term_saved", {"term": payload.term}, actor="user")
    return {"success": True, "term": term}


@router.delete("/glossary/{term_id}")
async def delete_term(term_id: int) -> Dict[str, Any]:
    if not memory_store.delete_term(term_id):
        raise HTTPException(status_code=404, detail=f"Term {term_id} not found")
    memory_store.audit("memory.term_deleted", {"term_id": term_id}, actor="user")
    return {"success": True}


@router.post("/glossary/generate")
async def generate_glossary() -> Dict[str, Any]:
    """Seed glossary entries from the connected database's schema."""
    from api.main import analyst

    if analyst is None or analyst.db_conn is None:
        raise HTTPException(
            status_code=400,
            detail="No database connected. Complete the setup wizard first.",
        )
    added = memory_store.generate_glossary_from_schema(analyst.db_conn)
    memory_store.audit("memory.glossary_generated", {"terms_added": added})
    return {"success": True, "terms_added": added}


# ==================== PROCEDURAL (RULES) ====================

@router.get("/rules")
async def list_rules(active_only: bool = False) -> Dict[str, Any]:
    rules = memory_store.list_rules(active_only=active_only)
    return {"rules": rules, "total": len(rules)}


@router.post("/rules")
async def create_rule(payload: RuleCreate) -> Dict[str, Any]:
    rule = memory_store.add_rule(payload.rule)
    memory_store.audit("memory.rule_created", {"rule": payload.rule}, actor="user")
    return {"success": True, "rule": rule}


@router.delete("/rules/{rule_id}")
async def deactivate_rule(rule_id: int) -> Dict[str, Any]:
    """
    Deactivate rather than delete: the rule stays linked to the episode it
    came from, so the learning trail remains auditable.
    """
    if not memory_store.deactivate_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    memory_store.audit("memory.rule_deactivated", {"rule_id": rule_id}, actor="user")
    return {"success": True}


# ==================== EPISODIC (HISTORY) ====================

@router.get("/episodes")
async def list_episodes(limit: int = 20) -> Dict[str, Any]:
    episodes = memory_store.list_episodes(limit=limit)
    return {"episodes": episodes, "total": len(episodes)}


# ==================== AUDIT ====================

audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("")
async def list_audit(limit: int = 100, action: Optional[str] = None) -> Dict[str, Any]:
    """Append-only log of analyses, config changes, syncs, and feedback."""
    entries = memory_store.list_audit(limit=limit, action=action)
    return {"entries": entries, "total": len(entries)}

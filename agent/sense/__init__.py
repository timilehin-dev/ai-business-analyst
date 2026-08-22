"""
Sense Loop - Proactive Monitoring.

The Sense loop watches the business database while you sleep:
  1. AnomalyDetector compares recent windows against previous ones
     for every measurable table (schema-agnostic).
  2. The briefing generator turns findings into a grounded morning
     briefing (numbers verified against the data, never LLM-computed).
  3. APScheduler runs it nightly; the dashboard shows the result.
"""
from agent.sense.anomaly import AnomalyDetector, Finding
from agent.sense.briefing import BriefingStore, generate_briefing

__all__ = ["AnomalyDetector", "Finding", "BriefingStore", "generate_briefing"]

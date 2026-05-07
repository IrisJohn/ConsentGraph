"""
ConsentGraph — Research Backend
================================
FastAPI server that receives site analytics from the Chrome extension
and stores them for research analysis.

Run locally:   uvicorn main:app --reload --port 8000
Deploy to:     Railway / Render / GCP Cloud Run (see README)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import uuid
from pathlib import Path

app = FastAPI(title="ConsentGraph Research API", version="1.0.0")

# Allow Chrome extension to POST (extensions have null origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Storage (flat JSON files — swap for Postgres when ready) ──
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SITES_FILE = DATA_DIR / "sites.jsonl"   # one JSON object per line

# ── Models ──

class TrackerDomain(BaseModel):
    domain: str
    owner: str
    category: str
    risk: str
    first_seen: Optional[str] = None
    request_type: Optional[str] = None

class TrackerSummary(BaseModel):
    count: int
    domains: List[TrackerDomain] = []
    owners: List[str] = []
    categories: List[str] = []
    high_risk_count: int = 0
    medium_risk_count: int = 0

class CookieData(BaseModel):
    on_load: List[str] = []
    after_load: List[str] = []
    new_after_load: List[str] = []
    count_on_load: int = 0
    count_after_load: int = 0

class ConsentUI(BaseModel):
    banner_found: bool = False
    banner_selector: Optional[str] = None
    banner_text: Optional[str] = None
    has_accept_button: bool = False
    dark_pattern_signals: List[str] = []

class RiskSummary(BaseModel):
    overall: str
    score: int
    dpdp_concern: bool

class SitePayload(BaseModel):
    # Page meta
    url: str
    domain: str
    title: Optional[str] = None
    timestamp: Optional[str] = None
    language: Optional[str] = None

    # Data
    cookies: Optional[CookieData] = None
    consent_ui: Optional[ConsentUI] = None
    trackers: Optional[TrackerSummary] = None
    privacy_links: Optional[List[Dict]] = []
    risk_summary: Optional[RiskSummary] = None

    # Extension meta
    extension_version: Optional[str] = None
    collected_at: Optional[str] = None


# ── Routes ──

@app.get("/")
def health():
    return {"status": "ok", "service": "ConsentGraph Research API"}


@app.get("/stats")
def stats():
    """Quick stats about the dataset — useful for research dashboard."""
    if not SITES_FILE.exists():
        return {"total_sites": 0, "unique_domains": 0, "total_trackers": 0}

    records = _load_all()
    domains = set(r.get("domain", "") for r in records)
    total_trackers = sum(r.get("trackers", {}).get("count", 0) for r in records)
    dpdp_concerns = sum(1 for r in records if r.get("risk_summary", {}).get("dpdp_concern"))
    high_risk = sum(1 for r in records if r.get("risk_summary", {}).get("overall") == "high")

    dark_patterns = {}
    for r in records:
        for dp in r.get("consent_ui", {}).get("dark_pattern_signals", []):
            dark_patterns[dp] = dark_patterns.get(dp, 0) + 1

    tracker_owners = {}
    for r in records:
        for t in r.get("trackers", {}).get("domains", []):
            owner = t.get("owner", "Unknown")
            tracker_owners[owner] = tracker_owners.get(owner, 0) + 1

    return {
        "total_records": len(records),
        "unique_domains": len(domains),
        "total_tracker_detections": total_trackers,
        "dpdp_concern_count": dpdp_concerns,
        "high_risk_sites": high_risk,
        "dark_pattern_frequency": dark_patterns,
        "top_tracker_owners": dict(
            sorted(tracker_owners.items(), key=lambda x: -x[1])[:10]
        ),
    }


@app.get("/sites")
def list_sites(limit: int = 50, domain: Optional[str] = None):
    """List collected sites — optionally filter by domain."""
    records = _load_all()
    if domain:
        records = [r for r in records if domain.lower() in r.get("domain", "").lower()]
    return {
        "count": len(records),
        "sites": records[-limit:],  # most recent first
    }


@app.post("/api/collect")
async def collect(payload: SitePayload, request: Request):
    """
    Main endpoint — Chrome extension POSTs here on every page visit.
    """
    record = payload.dict()
    record["_id"] = str(uuid.uuid4())
    record["_received_at"] = datetime.utcnow().isoformat()
    record["_ip"] = request.client.host if request.client else "unknown"

    # Append to JSONL file (one record per line)
    with open(SITES_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {
        "status": "received",
        "id": record["_id"],
        "domain": payload.domain,
        "trackers": payload.trackers.count if payload.trackers else 0,
        "risk": payload.risk_summary.overall if payload.risk_summary else "unknown",
    }


@app.get("/export")
def export_json():
    """Download full dataset as JSON — for graph analysis."""
    return _load_all()


# ── Helpers ──

def _load_all() -> List[Dict]:
    if not SITES_FILE.exists():
        return []
    records = []
    with open(SITES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records

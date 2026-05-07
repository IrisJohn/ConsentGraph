"""
ConsentGraph — Research Backend
================================
FastAPI server that receives site analytics from the Chrome extension.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json, os, uuid
from pathlib import Path

app = FastAPI(title="ConsentGraph Research API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SITES_FILE = DATA_DIR / "sites.jsonl"


class SitePayload(BaseModel):
    url: Optional[str] = None
    domain: Optional[str] = None
    title: Optional[str] = None
    timestamp: Optional[str] = None
    language: Optional[str] = None
    cookies: Optional[Dict[str, Any]] = None
    consent_ui: Optional[Dict[str, Any]] = None
    trackers: Optional[Dict[str, Any]] = None
    privacy_links: Optional[List[Dict]] = []
    risk_summary: Optional[Dict[str, Any]] = None
    extension_version: Optional[str] = None
    collected_at: Optional[str] = None


@app.get("/")
def health():
    return {"status": "ok", "service": "ConsentGraph Research API"}


@app.post("/api/collect")
async def collect(payload: SitePayload, request: Request):
    record = payload.dict()
    record["_id"] = str(uuid.uuid4())
    record["_received_at"] = datetime.utcnow().isoformat()
    record["_ip"] = request.client.host if request.client else "unknown"

    with open(SITES_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {
        "status": "received",
        "id": record["_id"],
        "domain": payload.domain,
        "trackers": payload.trackers.get("count", 0) if payload.trackers else 0,
        "risk": payload.risk_summary.get("overall") if payload.risk_summary else "unknown",
    }


@app.get("/stats")
def stats():
    records = _load_all()
    if not records:
        return {"total_records": 0, "unique_domains": 0}

    domains = set(r.get("domain", "") for r in records)
    total_trackers = sum(r.get("trackers", {}).get("count", 0) if r.get("trackers") else 0 for r in records)
    dpdp_concerns = sum(1 for r in records if r.get("risk_summary", {}) and r["risk_summary"].get("dpdp_concern"))
    high_risk = sum(1 for r in records if r.get("risk_summary", {}) and r["risk_summary"].get("overall") == "high")

    dark_patterns = {}
    for r in records:
        cui = r.get("consent_ui") or {}
        for dp in cui.get("dark_pattern_signals", []):
            dark_patterns[dp] = dark_patterns.get(dp, 0) + 1

    tracker_owners = {}
    for r in records:
        t = r.get("trackers") or {}
        for td in t.get("domains", []):
            owner = td.get("owner", "Unknown")
            tracker_owners[owner] = tracker_owners.get(owner, 0) + 1

    return {
        "total_records": len(records),
        "unique_domains": len(domains),
        "total_tracker_detections": total_trackers,
        "dpdp_concern_count": dpdp_concerns,
        "high_risk_sites": high_risk,
        "dark_pattern_frequency": dark_patterns,
        "top_tracker_owners": dict(sorted(tracker_owners.items(), key=lambda x: -x[1])[:10]),
    }


@app.get("/sites")
def list_sites(limit: int = 50, domain: Optional[str] = None):
    records = _load_all()
    if domain:
        records = [r for r in records if domain.lower() in (r.get("domain") or "").lower()]
    return {"count": len(records), "sites": records[-limit:]}


@app.get("/export")
def export_json():
    return _load_all()


def _load_all():
    if not SITES_FILE.exists():
        return []
    records = []
    with open(SITES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except:
                    pass
    return records

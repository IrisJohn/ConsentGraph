from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json, uuid, os
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

app = FastAPI(title="ConsentGraph Research API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── DB connection ──
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)

# ── Create table on startup ──
@app.on_event("startup")
def startup():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS site_visits (
                    id          TEXT PRIMARY KEY,
                    domain      TEXT,
                    url         TEXT,
                    title       TEXT,
                    language    TEXT,
                    timestamp   TEXT,
                    cookies     JSONB,
                    consent_ui  JSONB,
                    trackers    JSONB,
                    privacy_links JSONB,
                    risk_summary  JSONB,
                    extension_version TEXT,
                    collected_at TEXT,
                    received_at TEXT,
                    ip          TEXT,
                    raw         JSONB
                );
            """)
        conn.commit()


# ── Model ──
class SitePayload(BaseModel):
    url: Optional[str] = None
    domain: Optional[str] = None
    title: Optional[str] = None
    timestamp: Optional[str] = None
    language: Optional[str] = None
    cookies: Optional[Dict[str, Any]] = None
    consent_ui: Optional[Dict[str, Any]] = None
    trackers: Optional[Dict[str, Any]] = None
    privacy_links: Optional[List[Dict[str, Any]]] = []
    risk_summary: Optional[Dict[str, Any]] = None
    extension_version: Optional[str] = None
    collected_at: Optional[str] = None

    model_config = {"extra": "allow"}


# ── Routes ──

@app.get("/")
def health():
    return {"status": "ok", "service": "ConsentGraph Research API"}


@app.post("/api/collect")
async def collect(payload: SitePayload, request: Request):
    record_id = str(uuid.uuid4())
    received_at = datetime.utcnow().isoformat()
    ip = request.client.host if request.client else "unknown"
    data = payload.model_dump()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO site_visits
                (id, domain, url, title, language, timestamp, cookies, consent_ui,
                 trackers, privacy_links, risk_summary, extension_version,
                 collected_at, received_at, ip, raw)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                record_id,
                payload.domain,
                payload.url,
                payload.title,
                payload.language,
                payload.timestamp,
                json.dumps(payload.cookies),
                json.dumps(payload.consent_ui),
                json.dumps(payload.trackers),
                json.dumps(payload.privacy_links),
                json.dumps(payload.risk_summary),
                payload.extension_version,
                payload.collected_at,
                received_at,
                ip,
                json.dumps(data),
            ))
        conn.commit()

    return {
        "status": "received",
        "id": record_id,
        "domain": payload.domain,
        "trackers": payload.trackers.get("count", 0) if payload.trackers else 0,
        "risk": payload.risk_summary.get("overall") if payload.risk_summary else "unknown",
    }


@app.get("/stats")
def stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM site_visits")
            total = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(DISTINCT domain) as domains FROM site_visits")
            unique_domains = cur.fetchone()["domains"]

            cur.execute("""
                SELECT SUM((trackers->>'count')::int) as total_trackers
                FROM site_visits WHERE trackers IS NOT NULL
            """)
            total_trackers = cur.fetchone()["total_trackers"] or 0

            cur.execute("""
                SELECT COUNT(*) as cnt FROM site_visits
                WHERE risk_summary->>'overall' = 'high'
            """)
            high_risk = cur.fetchone()["cnt"]

            cur.execute("""
                SELECT COUNT(*) as cnt FROM site_visits
                WHERE (risk_summary->>'dpdp_concern')::boolean = true
            """)
            dpdp_concerns = cur.fetchone()["cnt"]

            # Top tracker owners
            cur.execute("""
                SELECT owner, COUNT(*) as cnt
                FROM site_visits,
                     jsonb_array_elements(trackers->'domains') AS t,
                     jsonb_extract_path_text(t, 'owner') AS owner
                WHERE trackers IS NOT NULL
                GROUP BY owner ORDER BY cnt DESC LIMIT 10
            """)
            tracker_owners = {r["owner"]: r["cnt"] for r in cur.fetchall()}

            # Dark pattern frequency
            cur.execute("""
                SELECT dp, COUNT(*) as cnt
                FROM site_visits,
                     jsonb_array_elements_text(consent_ui->'dark_pattern_signals') AS dp
                WHERE consent_ui IS NOT NULL
                GROUP BY dp ORDER BY cnt DESC
            """)
            dark_patterns = {r["dp"]: r["cnt"] for r in cur.fetchall()}

    return {
        "total_records": total,
        "unique_domains": unique_domains,
        "total_tracker_detections": total_trackers,
        "high_risk_sites": high_risk,
        "dpdp_concern_count": dpdp_concerns,
        "top_tracker_owners": tracker_owners,
        "dark_pattern_frequency": dark_patterns,
    }


@app.get("/sites")
def list_sites(limit: int = 50, domain: Optional[str] = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if domain:
                cur.execute(
                    "SELECT * FROM site_visits WHERE domain ILIKE %s ORDER BY received_at DESC LIMIT %s",
                    (f"%{domain}%", limit)
                )
            else:
                cur.execute(
                    "SELECT * FROM site_visits ORDER BY received_at DESC LIMIT %s",
                    (limit,)
                )
            rows = cur.fetchall()
    return {"count": len(rows), "sites": [dict(r) for r in rows]}


@app.get("/export")
def export_json():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT raw FROM site_visits ORDER BY received_at DESC")
            rows = cur.fetchall()
    return [r["raw"] for r in rows]

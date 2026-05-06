"""
server.py — FastAPI + Uvicorn REST API
READ-ONLY endpoints — no DELETE/DROP operations
Run: uvicorn backend.server:app --reload --port 8000
"""

import os
import sys
import logging
from typing import Optional, List
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_articles, get_article_count, get_stats, get_categories, get_dates_with_articles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NewsPrep API",
    description="Read-only API for CA Portal articles from Neon DB",
    version="1.0.0",
)

# Allow frontend (Vercel) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "service": "NewsPrep API", "version": "1.0.0"}


@app.get("/health")
def health():
    try:
        stats = get_stats()
        return {"status": "healthy", "total_articles": stats["total"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Articles ──────────────────────────────────────────────────────────────────
@app.get("/articles")
def articles(
    date:     Optional[str] = Query(None, description="Filter by date YYYY-MM-DD"),
    date_from:Optional[str] = Query(None, description="Articles from this date"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search:   Optional[str] = Query(None, description="Search in title/summary"),
    limit:    int            = Query(100, ge=1, le=500),
    offset:   int            = Query(0,   ge=0),
    min_score:float          = Query(0.8, ge=0.0, le=1.0),
):
    """Get articles from Neon DB — read only"""
    try:
        rows = get_articles(
            date_filter=date,
            category_filter=category,
            min_confidence=min_score,
            limit=limit,
            offset=offset,
            date_from=date_from,
            search=search,
        )
        total = get_article_count(
            date_filter=date,
            category_filter=category,
            min_confidence=min_score,
            date_from=date_from,
            search=search,
        )
        # Serialize dates
        for r in rows:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
        return {
            "articles": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"GET /articles error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/stats")
def stats():
    """DB statistics — total, by category, by date"""
    try:
        s = get_stats()
        return s
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Categories ────────────────────────────────────────────────────────────────
@app.get("/categories")
def categories():
    """List all categories"""
    try:
        return {"categories": get_categories()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dates ─────────────────────────────────────────────────────────────────────
@app.get("/dates")
def dates(days: int = Query(30, ge=1, le=90)):
    """Dates that have articles"""
    try:
        return {"dates": get_dates_with_articles(days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DB Table info (terminal output) ──────────────────────────────────────────
@app.get("/db/info")
def db_info():
    """Show exam_ca_articles table stats in terminal"""
    try:
        s = get_stats()
        cats = get_categories()
        info = {
            "table": "exam_ca_articles",
            "total_articles": s["total"],
            "today": s["today"],
            "this_week": s["this_week"],
            "categories": len(cats),
            "by_category": s["by_category"],
            "recent_dates": list(s["by_date"].items())[:7],
        }
        # Print to terminal
        logger.info("=" * 50)
        logger.info(f"TABLE: exam_ca_articles")
        logger.info(f"Total articles : {s['total']}")
        logger.info(f"Today          : {s['today']}")
        logger.info(f"This week      : {s['this_week']}")
        logger.info(f"Categories     : {len(cats)}")
        for cat, cnt in s["by_category"].items():
            logger.info(f"  {cat:<35} {cnt}")
        logger.info("=" * 50)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

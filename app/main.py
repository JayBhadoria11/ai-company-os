import json
from pathlib import Path

"""FastAPI entry point for AI Company OS."""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import (
    MODEL_NAME,
    NEBIUS_API_KEY,
    NEBIUS_BASE_URL,
)
from app.core.commander import run_commander_task
from app.core.company_context import (
    get_active_company,
    get_company_dataset_analysis,
    get_company_dataset_record,
    get_company_sales_analysis,
    company_name,
)
from app.core.company_workspace import (
    PROFILE_FIELDS,
    load_company_profile,
    save_company_profile,
    list_datasets,
    get_active_dataset,
    load_dataset_preview,
    save_dataset_bytes,
    delete_dataset,
)
from app.database.db import (
    get_recent_analyses,
    clear_analysis_history,
    clear_action_history,
    clear_approval_history,
    clear_company_workspace_state,
    save_intelligence_question,
    update_intelligence_question_status,
    get_intelligence_questions,
    delete_intelligence_question,
)


app = FastAPI(
    title="AI Company OS",
    description="Autonomous business operations agent for NVIDIA x Nebius Hackathon",
    version="0.1.0",
)

# When the dashboard has been built (npm run build), the API also serves it so
# the whole app runs as a single service. The mount is added at the very bottom
# of this module, after every API route, so /api/* and /docs keep priority.
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"])
def root():
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)

    return {
        "message": "AI Company OS API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "service": "ai-company-os",
    }


@app.get("/config", tags=["config"])
def config():
    return {
        "model": MODEL_NAME,
        "base_url": NEBIUS_BASE_URL,
        "configured": bool(NEBIUS_API_KEY),
    }


class InvestigationRequest(BaseModel):
    query: str


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@app.delete("/api/history", tags=["history"])
def clear_history():
    """Reset decision/investigation/action/approval history (not the company)."""
    try:
        clear_analysis_history()
        clear_action_history()
        clear_approval_history()
        return {"status": "success", "message": "History cleared."}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/history", tags=["history"])
def history(limit: int = 20):
    try:
        items = get_recent_analyses(limit=max(1, min(limit, 100)))
        events = []

        for item in items:
            result = item.get("result") or {}
            synthesis = item.get("synthesis") or {}

            events.append({
                "id": item.get("id"),
                "task_id": item.get("task_id"),
                "query": item.get("query_text") or "",
                "timestamp": item.get("timestamp") or item.get("created_at"),
                "model": item.get("model"),
                "approval": item.get("user_approval", 0),
                "recommendations": result.get("recommendations") or [],
                "executive_summary": synthesis.get("executive_summary") or "",
            })

        return {
            "status": "success",
            "events": events,
        }

    except Exception as exc:
        return {
            "status": "error",
            "events": [],
            "message": str(exc),
        }


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.get("/api/agents", tags=["agents"])
def agents():
    """Return the configured AI Company OS agent network."""

    from app.database.memory import get_connection, initialize_memory

    initialize_memory()

    catalog = [
        {
            "name": "Commander",
            "key": "commander",
            "role": "CEO orchestrator",
            "capability": "Routes the business question, selects specialists, and coordinates the investigation.",
        },
        {
            "name": "Analyst",
            "key": "analyst",
            "role": "Business intelligence",
            "capability": "Computes deterministic metrics, financial signals, trends, and evidence.",
        },
        {
            "name": "Marketing",
            "key": "marketing",
            "role": "Market intelligence",
            "capability": "Analyzes positioning, competitors, opportunities, and customer-facing strategy.",
        },
        {
            "name": "HR & Operations",
            "key": "hr",
            "role": "Operations intelligence",
            "capability": "Evaluates operational risks, organizational considerations, and execution priorities.",
        },
        {
            "name": "Nemotron",
            "key": "nemotron",
            "role": "Executive synthesis",
            "capability": "Combines specialist evidence into an executive-level decision brief.",
        },
    ]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT agent, status, task_id, created_at
            FROM agent_memory
            ORDER BY id DESC
            """
        ).fetchall()

    latest = {}

    for row in rows:
        agent = row["agent"]
        if agent not in latest:
            latest[agent] = {
                "status": row["status"],
                "task_id": row["task_id"],
                "created_at": row["created_at"],
            }

    network = []

    for agent in catalog:
        recent = latest.get(agent["key"])

        if recent:
            status = recent["status"]
            badge = "ACTIVE" if status == "success" else status.upper()
        elif agent["key"] == "nemotron":
            status = "connected"
            badge = "CONNECTED"
        else:
            status = "available"
            badge = "READY"

        network.append(
            {
                **agent,
                "status": status,
                "badge": badge,
                "last_task_id": recent["task_id"] if recent else None,
                "last_run": recent["created_at"] if recent else None,
            }
        )

    return {
        "status": "success",
        "agents": network,
    }


# ---------------------------------------------------------------------------
# Company workspace helpers
# ---------------------------------------------------------------------------

def _safe_number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _company_metrics(analysis):
    """Return the compact, JSON-safe KPI set shared across the OS."""

    metrics = (analysis or {}).get("metrics", {}) or {}

    return {
        "net_sales": _safe_number(metrics.get("net_sales")),
        "gross_sales": _safe_number(metrics.get("gross_sales")),
        "orders": metrics.get("orders"),
        "units": metrics.get("total_units"),
        "aov": _safe_number(metrics.get("average_order_value")),
        "discounts": _safe_number(metrics.get("discounts")),
        "discount_rate": _safe_number(metrics.get("discount_rate_pct")),
        "profit": _safe_number(metrics.get("profit")),
    }


def _compact_dataset(dataset, include_columns=True):
    if not dataset:
        return None

    metadata = dataset.get("metadata", {}) or {}

    compact = {
        "id": dataset.get("id"),
        "filename": dataset.get("filename"),
        "rows": metadata.get("rows"),
        "columns": metadata.get("columns"),
        "uploaded_at": dataset.get("created_at"),
        "size_bytes": metadata.get("size_bytes"),
    }

    if include_columns:
        compact["column_names"] = metadata.get("column_names", [])
        compact["numeric_columns"] = metadata.get("numeric_columns", [])
        compact["date_candidates"] = metadata.get("date_candidates", [])
        compact["missing_values"] = metadata.get("missing_values")

    return compact


def _dataset_payload():
    """Build the shared dataset view (metadata + preview + deterministic KPIs)."""

    datasets = list_datasets()
    active = datasets[0] if datasets else None

    analysis = get_company_dataset_analysis()

    metrics = None
    dataset_type = None
    insights = []
    limitations = []

    if analysis:
        metrics = _company_metrics(analysis)
        dataset_type = analysis.get("dataset")
        insights = analysis.get("insights", [])
        limitations = analysis.get("limitations", [])

    return {
        "has_dataset": bool(datasets),
        "count": len(datasets),
        "active": _compact_dataset(active),
        "datasets": [_compact_dataset(item, include_columns=False) for item in datasets],
        "preview": load_dataset_preview(active) if active else None,
        "metrics": metrics,
        "dataset_type": dataset_type,
        "insights": insights,
        "limitations": limitations,
    }


def _build_workspace():
    profile = load_company_profile()
    dataset = _dataset_payload()

    has_profile = bool(
        profile.get("name")
        or profile.get("industry")
        or profile.get("description")
    )
    has_dataset = dataset["has_dataset"]
    active = has_profile or has_dataset

    return {
        "status": "success",
        "active": active,
        "has_profile": has_profile,
        "profile": profile,
        "configuration": {
            "currency": profile.get("currency"),
            "reporting_period": profile.get("reporting_period"),
            "primary_kpi": profile.get("primary_kpi"),
        },
        "objectives": {
            "revenue_target": profile.get("revenue_target"),
            "growth_target": profile.get("growth_target"),
        },
        "dataset": dataset,
        "connections": [
            {"name": "Intelligence", "connected": has_dataset},
            {"name": "Agents", "connected": active},
            {"name": "Financials", "connected": has_dataset},
            {"name": "Approvals", "connected": active},
        ],
    }


# ---------------------------------------------------------------------------
# Company profile
# ---------------------------------------------------------------------------

@app.get("/api/company/profile", tags=["company"])
def get_company_profile():
    return {
        "status": "success",
        "profile": load_company_profile(),
    }


@app.put("/api/company/profile", tags=["company"])
def update_company_profile(profile: dict):
    clean_profile = {
        key: "" if value is None else str(value).strip()
        for key, value in (profile or {}).items()
        if key in PROFILE_FIELDS
    }

    saved = save_company_profile(clean_profile)

    return {
        "status": "success",
        "message": "Company profile saved.",
        "profile": saved,
    }


# ---------------------------------------------------------------------------
# Company dataset
# ---------------------------------------------------------------------------

@app.get("/api/company/dataset", tags=["company"])
def get_company_dataset():
    return {
        "status": "success",
        **_dataset_payload(),
    }


@app.post("/api/company/dataset", tags=["company"])
async def upload_company_dataset(file: UploadFile = File(...)):
    try:
        data = await file.read()
        info = save_dataset_bytes(file.filename, data)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "message": f"Upload failed: {exc}"}

    payload = _dataset_payload()

    return {
        "status": "success",
        "message": f"{info.get('filename')} connected to the company workspace.",
        "uploaded": _compact_dataset(
            {"metadata": info, "filename": info.get("filename"), "created_at": info.get("saved_at")}
        ),
        **payload,
    }


@app.delete("/api/company/dataset", tags=["company"])
def remove_company_dataset(id: int | None = None):
    try:
        removed = delete_dataset(id)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "message": f"Could not remove dataset: {exc}"}

    return {
        "status": "success",
        "message": "Dataset removed from the company workspace.",
        "removed": removed,
        **_dataset_payload(),
    }


# ---------------------------------------------------------------------------
# Company workspace (source of truth)
# ---------------------------------------------------------------------------

@app.get("/api/company/workspace", tags=["company"])
def get_company_workspace():
    return _build_workspace()


@app.delete("/api/company/workspace", tags=["company"])
def reset_company_workspace():
    """Reset the entire company workspace: profile, datasets, derived state."""
    try:
        clear_company_workspace_state()
    except Exception as exc:
        return {"status": "error", "message": f"Reset failed: {exc}"}

    return {
        "status": "success",
        "message": "Company workspace reset.",
        "workspace": _build_workspace(),
    }


@app.get("/api/company", tags=["company"])
def company():
    """Return the verified company summary used by the React dashboard."""

    # Financials/Command Center must report against the connected sales dataset
    # only. Workforce/HR data is excluded so HR metrics are never presented as
    # financial metrics, and the dataset name is resolved from the same source
    # as the metrics so they can never disagree.
    analysis = get_company_sales_analysis()
    active_company = get_active_company()
    profile = load_company_profile()

    # Resolve the actual connected sales/financial dataset (never the HR
    # dataset) from the existing workspace registry. Fall back to the analyzer
    # type label only if no source dataset can be resolved.
    source_dataset = get_company_dataset_record(require_sales=True)

    metrics = (analysis or {}).get("metrics", {}) or {}
    breakdowns = (analysis or {}).get("breakdowns", {}) or {}

    return {
        "company": company_name(),
        "profile": profile,
        "configuration": {
            "currency": profile.get("currency"),
            "reporting_period": profile.get("reporting_period"),
            "primary_kpi": profile.get("primary_kpi"),
        },
        "objectives": {
            "revenue_target": profile.get("revenue_target"),
            "growth_target": profile.get("growth_target"),
        },
        "dataset": (
            (source_dataset or {}).get("filename")
            or (analysis or {}).get("dataset")
        ),
        "dataset_id": (source_dataset or {}).get("id"),
        "rows": (analysis or {}).get("rows"),
        "metrics": _company_metrics(analysis),
        "products": breakdowns.get("products", [])[:10],
        "regions": breakdowns.get("regions", []),
        "monthly": breakdowns.get("monthly", []),
        "insights": (analysis or {}).get("insights", []) if analysis else [],
        "limitations": (analysis or {}).get("limitations", []) if analysis else [],
        "active": bool(active_company.get("active")),
    }


# ---------------------------------------------------------------------------
# Intelligence
# ---------------------------------------------------------------------------

@app.get("/api/intelligence/questions", tags=["intelligence"])
def intelligence_questions(limit: int = 50):
    """Return persisted Intelligence questions, newest first."""
    try:
        questions = get_intelligence_questions(limit=limit)
        return {"status": "success", "questions": questions}
    except Exception as exc:
        return {"status": "error", "questions": [], "message": str(exc)}


@app.delete("/api/intelligence/questions/{question_id}", tags=["intelligence"])
def remove_intelligence_question(question_id: int):
    """Delete a single persisted Intelligence question.

    This only removes that question; it never touches the company dataset,
    profile, workspace, history, approvals, or actions.
    """
    try:
        removed = delete_intelligence_question(question_id)
    except Exception as exc:
        return {"status": "error", "message": f"Could not delete question: {exc}"}

    if not removed:
        return {"status": "error", "message": "Question not found."}

    return {
        "status": "success",
        "message": "Question deleted.",
        "id": question_id,
    }


@app.post("/api/intelligence/investigate", tags=["intelligence"])
def investigate(request: InvestigationRequest):
    """Run the existing Commander investigation pipeline."""

    query = request.query.strip()

    if not query:
        return {
            "status": "error",
            "message": "Investigation query cannot be empty.",
        }

    import uuid

    task_id = f"investigation-{uuid.uuid4().hex[:12]}"

    # Persist the question up front so it survives refreshes/restarts even if
    # the investigation itself fails or the user navigates away mid-run.
    question_id = None
    try:
        question_id = save_intelligence_question(query, task_id=task_id)
    except Exception:
        question_id = None

    try:
        result = run_commander_task(task_id, query)

        update_intelligence_question_status(question_id, "success")

        return {
            "status": "success",
            "task_id": task_id,
            "query": query,
            "result": result,
        }

    except Exception as exc:
        update_intelligence_question_status(question_id, "error")

        return {
            "status": "error",
            "task_id": task_id,
            "query": query,
            "message": str(exc),
        }


# ---------------------------------------------------------------------------
# Single-service deployment: serve the built React dashboard when available.
#
# This mount is registered last so every API route and /docs take precedence.
# Run `npm run build` in frontend/ first; the guard makes the mount optional so
# the API still works when the dashboard has not been built.
# ---------------------------------------------------------------------------

if FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIST), html=True),
        name="frontend",
    )

"""Shared active-company context for the whole AI Company OS."""

import json
import os

from app.core.company_workspace import (
    load_company_profile,
    list_datasets,
)

from app.database.db import get_recent_analyses

# ---------------------------------------------------------------------------
# Caching of the expensive deterministic dataset analysis.
#
# analyze_sales_dataset() reads the full dataset from disk and computes all
# metrics/breakdowns. _rank_company_datasets() runs it for EVERY connected
# dataset, and get_company_dataset_analysis() may additionally re-read and
# merge several Olist tables. Doing this on every /api/company request makes
# the React dashboard hang for seconds.
#
# These caches are keyed on the dataset registry signature (ids, filenames,
# paths, sizes, file mtimes), so they are automatically invalidated whenever a
# dataset is uploaded, replaced, deleted, or the workspace is reset. Profile
# changes never affect the analysis and therefore do not invalidate it.
# ---------------------------------------------------------------------------

_ANALYSIS_CACHE = {}
_RANK_CACHE = {}
_CACHE_MAX_SIZE = 16


def _dataset_signature():
    """Return a tuple that changes whenever any dataset file changes."""
    signature = []
    for dataset in list_datasets():
        path = dataset.get("path") or ""
        size = 0
        mtime = 0
        try:
            stat = os.stat(path)
            size = stat.st_size
            mtime = stat.st_mtime_ns
        except OSError:
            pass
        signature.append(
            (dataset.get("id"), dataset.get("filename"), path, size, mtime)
        )
    return tuple(signature)


def _cache_bounded(cache):
    """Keep the in-memory cache from growing without bound."""
    if len(cache) > _CACHE_MAX_SIZE:
        for key in list(cache)[: len(cache) - _CACHE_MAX_SIZE]:
            cache.pop(key, None)


def get_active_company():
    """Return the currently active company workspace."""

    profile = load_company_profile()
    datasets = list_datasets()

    analyses = [
        x
        for x in get_recent_analyses(50)
        if x.get("context_type") == "company"
    ]

    latest_analysis = None

    if analyses:
        latest_analysis = (
            analyses[0].get("result")
            or {}
        )

    active = bool(
        profile.get("name")
        or datasets
    )

    if not active:
        latest_analysis = None

    return {
        "profile": profile,
        "datasets": datasets,
        "analysis": latest_analysis,
        "active": active,
    }


def company_name():
    """Return the active company name."""

    return (
        get_active_company()["profile"].get("name")
        or "Company"
    )


def _rank_company_datasets():
    """Rank the connected workspace datasets by the evidence they support.

    The same deterministic analyzer used across the OS scores each connected
    dataset, so an unrelated table such as customers/employees cannot become a
    fake zero-sales company report.
    """

    ctx = get_active_company()

    if not ctx["active"] or not ctx["datasets"]:
        return []

    signature = _dataset_signature()
    cached = _RANK_CACHE.get(signature)
    if cached is not None:
        return cached

    from app.core.company_analysis import analyze_sales_dataset

    candidates = []

    for dataset in ctx["datasets"]:
        path = dataset.get("path")
        if not path:
            continue
        try:
            analysis = analyze_sales_dataset(path)
        except Exception:
            continue

        metrics = analysis.get("metrics", {})
        net_sales = metrics.get("net_sales")
        rows = analysis.get("rows") or dataset.get("metadata", {}).get("rows", 0)
        monthly = analysis.get("breakdowns", {}).get("monthly", [])
        dataset_type = analysis.get("dataset", "generic")

        # Score only evidence the analyzer actually produced. Olist gets a strong
        # preference because it is intentionally a multi-table workspace.
        score = 0
        if dataset_type == "olist":
            score += 100000
        if net_sales is not None and float(net_sales or 0) != 0:
            score += 10000
        if monthly:
            score += 1000
        if analysis.get("breakdowns", {}).get("products"):
            score += 100
        if analysis.get("breakdowns", {}).get("regions"):
            score += 100
        score += min(int(rows or 0), 100000) / 100000

        candidates.append((score, analysis, dataset))

    candidates.sort(key=lambda item: item[0], reverse=True)
    _RANK_CACHE[signature] = candidates
    _cache_bounded(_RANK_CACHE)
    return candidates


def get_company_dataset_analysis():
    """Return the best deterministic analysis for the active company workspace.

    Known multi-table workspaces (currently Olist) get their relational joins.
    Other uploaded datasets are scored by the metrics they can actually support,
    so an unrelated table such as customers/employees cannot become a fake
    zero-sales company report.
    """

    signature = _dataset_signature()
    cached = _ANALYSIS_CACHE.get(signature)
    if cached is not None:
        return cached

    candidates = _rank_company_datasets()

    if not candidates:
        return None

    _, best_analysis, best_dataset = candidates[0]

    # If the workspace contains Olist files, enrich the Olist analysis from the
    # authoritative relational tables. Do not concatenate tables by row position.
    if best_analysis.get("dataset") == "olist":
        ctx = get_active_company()
        olist_files = {}
        translation_file = None
        customer_path = None
        product_path = None
        seller_path = None
        review_path = None
        payment_path = None

        for dataset in ctx["datasets"]:
            fn = os.path.basename(dataset.get("filename") or dataset.get("path") or "").lower()
            path = dataset.get("path", "")
            if fn == "olist_orders_dataset.csv":
                olist_files["orders"] = path
            elif fn == "olist_order_items_dataset.csv":
                olist_files["order_items"] = path
            elif fn == "product_category_name_translation.csv":
                translation_file = path
            elif fn == "olist_customers_dataset.csv":
                customer_path = path
            elif fn == "olist_products_dataset.csv":
                product_path = path
            elif fn == "olist_sellers_dataset.csv":
                seller_path = path
            elif fn == "olist_order_reviews_dataset.csv":
                review_path = path
            elif fn == "olist_order_payments_dataset.csv":
                payment_path = path

        if "orders" in olist_files and "order_items" in olist_files:
            try:
                import pandas as pd

                orders_df = pd.read_csv(olist_files["orders"])
                items_df = pd.read_csv(olist_files["order_items"])

                required_orders = {"order_id", "order_purchase_timestamp"}
                required_items = {"order_id", "price"}
                if not required_orders.issubset(orders_df.columns) or not required_items.issubset(items_df.columns):
                    raise ValueError("Olist orders/order_items files do not contain the required join columns.")

                merged = items_df.merge(
                    orders_df[["order_id", "order_purchase_timestamp"]],
                    on="order_id",
                    how="left",
                    validate="many_to_one",
                )
                merged["order_purchase_timestamp"] = pd.to_datetime(
                    merged["order_purchase_timestamp"], errors="coerce"
                )
                merged["price"] = pd.to_numeric(merged["price"], errors="coerce").fillna(0.0)
                merged["_month"] = merged["order_purchase_timestamp"].dt.to_period("M")

                monthly_grp = (
                    merged.dropna(subset=["_month"])
                    .groupby("_month", as_index=False)["price"]
                    .sum()
                    .sort_values("_month")
                )

                best_analysis["rows"] = int(len(items_df))
                breakdowns = best_analysis.setdefault("breakdowns", {})
                breakdowns["monthly"] = [
                    {
                        "month": str(row["_month"]),
                        "sales": round(float(row["price"]), 2),
                        "revenue": round(float(row["price"]), 2),
                    }
                    for _, row in monthly_grp.iterrows()
                ]

                if customer_path:
                    customers_df = pd.read_csv(customer_path, usecols=["customer_id", "customer_state"])
                    state_frame = (
                        items_df[["order_id", "price"]]
                        .merge(orders_df[["order_id", "customer_id"]], on="order_id", how="left", validate="many_to_one")
                        .merge(customers_df, on="customer_id", how="left", validate="many_to_one")
                    )
                    state_group = (
                        state_frame.dropna(subset=["customer_state"])
                        .groupby("customer_state")
                        .agg(sales=("price", "sum"), units=("price", "count"), orders=("order_id", "nunique"))
                        .reset_index()
                        .sort_values("sales", ascending=False)
                    )
                    breakdowns["regions"] = [
                        {"name": str(r["customer_state"]), "sales": round(float(r["sales"]), 2),
                         "units": int(r["units"]), "orders": int(r["orders"])}
                        for _, r in state_group.iterrows()
                    ]

                products_df = None
                translation_df = None
                if product_path:
                    products_df = pd.read_csv(product_path, usecols=["product_id", "product_category_name"])
                    product_frame = items_df[["order_id", "product_id", "price"]].merge(
                        products_df, on="product_id", how="left", validate="many_to_one"
                    )
                    if translation_file:
                        translation_df = pd.read_csv(
                            translation_file,
                            usecols=["product_category_name", "product_category_name_english"],
                        )
                        product_frame = product_frame.merge(
                            translation_df, on="product_category_name", how="left", validate="many_to_one"
                        )
                    product_frame["category"] = (
                        product_frame["product_category_name_english"]
                        if "product_category_name_english" in product_frame.columns
                        else product_frame["product_category_name"]
                    ).fillna("unknown")
                    cat_group = (
                        product_frame.groupby("category")
                        .agg(sales=("price", "sum"), units=("price", "count"), orders=("order_id", "nunique"))
                        .reset_index()
                        .sort_values("sales", ascending=False)
                    )
                    breakdowns["products"] = [
                        {"name": str(r["category"]), "sales": round(float(r["sales"]), 2),
                         "units": int(r["units"]), "orders": int(r["orders"])}
                        for _, r in cat_group.iterrows()
                    ]

                if seller_path:
                    sellers_df = pd.read_csv(seller_path, usecols=["seller_id", "seller_state"])
                    seller_frame = items_df[["order_id", "seller_id", "price"]].merge(
                        sellers_df, on="seller_id", how="left", validate="many_to_one"
                    )
                    seller_group = (
                        seller_frame.groupby(["seller_id", "seller_state"])
                        .agg(sales=("price", "sum"), units=("price", "count"), orders=("order_id", "nunique"))
                        .reset_index()
                        .sort_values("sales", ascending=False)
                    )
                    breakdowns["sellers"] = [
                        {"name": str(r["seller_id"]), "state": str(r["seller_state"]),
                         "sales": round(float(r["sales"]), 2), "units": int(r["units"]),
                         "orders": int(r["orders"])}
                        for _, r in seller_group.iterrows()
                    ]

                if customer_path and products_df is not None:
                    cross = (
                        items_df[["order_id", "product_id", "price"]]
                        .merge(orders_df[["order_id", "customer_id"]], on="order_id", how="left", validate="many_to_one")
                        .merge(customers_df, on="customer_id", how="left", validate="many_to_one")
                        .merge(products_df, on="product_id", how="left", validate="many_to_one")
                    )
                    if translation_df is not None:
                        cross = cross.merge(
                            translation_df, on="product_category_name", how="left", validate="many_to_one"
                        )
                    cross["category"] = (
                        cross["product_category_name_english"]
                        if "product_category_name_english" in cross.columns
                        else cross["product_category_name"]
                    ).fillna("unknown")
                    cross_group = (
                        cross.groupby(["category", "customer_state"])
                        .agg(sales=("price", "sum"), units=("price", "count"), orders=("order_id", "nunique"))
                        .reset_index()
                        .sort_values("sales", ascending=False)
                    )
                    breakdowns["product_region"] = [
                        {"product": str(r["category"]), "region": str(r["customer_state"]),
                         "sales": round(float(r["sales"]), 2), "units": int(r["units"]),
                         "orders": int(r["orders"])}
                        for _, r in cross_group.iterrows()
                    ]

                breakdowns["channels"] = []

                if review_path:
                    reviews_df = pd.read_csv(review_path, usecols=["order_id", "review_score"])
                    rs = pd.to_numeric(reviews_df["review_score"], errors="coerce").dropna()
                    if not rs.empty:
                        breakdowns["reviews"] = {"average_score": round(float(rs.mean()), 2), "count": int(rs.size)}

                if payment_path:
                    payments_df = pd.read_csv(payment_path, usecols=["payment_type", "payment_value"])
                    payments_df["payment_value"] = pd.to_numeric(payments_df["payment_value"], errors="coerce")
                    payment_group = payments_df.dropna(subset=["payment_type", "payment_value"]).groupby("payment_type")["payment_value"].agg(["sum", "count"]).reset_index()
                    breakdowns["payments"] = {
                        str(r["payment_type"]): {"value": round(float(r["sum"]), 2), "count": int(r["count"])}
                        for _, r in payment_group.iterrows()
                    }
            except Exception:
                # Keep the verified base analysis if optional enrichment fails.
                pass

    _ANALYSIS_CACHE[signature] = best_analysis
    _cache_bounded(_ANALYSIS_CACHE)
    return best_analysis


def get_company_dataset_record(require_sales=False):
    """Return the workspace dataset selected as the primary data source.

    The selection reuses the same deterministic ranking as
    ``get_company_dataset_analysis`` and the existing workspace registry
    classification. When ``require_sales`` is True (used by Financials),
    workforce/HR datasets are excluded so HR data is never presented as
    financial data.
    """

    registry = {}
    if require_sales:
        registry = {
            record.get("id"): record
            for record in get_workspace_datasets()
        }

    for _, _, dataset in _rank_company_datasets():
        if require_sales:
            record = registry.get(dataset.get("id")) or {}
            domain = record.get("domain") or classify_dataset_domain(
                (dataset.get("metadata", {}) or {}).get("column_names", [])
            )
            if domain == "workforce":
                continue
        return dataset

    return None


def get_company_sales_analysis():
    """Return the deterministic analysis of the dataset selected for
    sales/financial reporting.

    This deliberately excludes workforce/HR datasets so HR data is never
    presented as financial metrics. It uses the same ranking and schema
    classification as ``get_company_dataset_record(require_sales=True)``, so
    the dataset name served by the API and the metrics/breakdowns computed from
    it always come from the same dataset.
    """

    registry = {
        record.get("id"): record
        for record in get_workspace_datasets()
    }

    for _, analysis, dataset in _rank_company_datasets():
        record = registry.get(dataset.get("id")) or {}
        domain = record.get("domain") or classify_dataset_domain(
            (dataset.get("metadata", {}) or {}).get("column_names", [])
        )
        if domain == "workforce":
            continue
        return analysis

    return None


# ===========================================================================
# Multi-dataset registry view (reads the existing Company Workspace datasets)
# ===========================================================================

WORKFORCE_KEYWORDS = [
    "workforce", "employee", "employees", "staff", "staffing", "hr",
    "human resources", "human resource", "attrition", "turnover", "headcount",
    "hiring", "recruit", "retention", "overtime", "workload", "capacity",
    "talent", "department", "departments", "layoff", "resignation",
]

SALES_KEYWORDS = [
    "sales", "revenue", "order", "orders", "product", "products",
    "customer", "customers", "region", "regions", "aov",
    "average order value", "units", "discount", "category", "categories",
    "channel", "channels", "segment",
]

FINANCIAL_KEYWORDS = [
    "profit", "profitability", "margin", "expense", "expenses", "cost",
    "costs", "cash", "financial", "budget", "burn",
]

GLOBAL_KEYWORDS = [
    "overall", "missing", "information",
]

DOMAIN_KEYWORDS = {
    "workforce": WORKFORCE_KEYWORDS,
    "sales": SALES_KEYWORDS + FINANCIAL_KEYWORDS,
    "financial": FINANCIAL_KEYWORDS,
    "generic": [],
}

_SALES_SCHEMA_TOKENS = [
    "sales", "revenue", "order", "product", "customer", "price",
    "units", "quantity", "discount", "category", "region", "segment",
]

_FINANCIAL_SCHEMA_TOKENS = ["profit", "expense", "cost", "margin"]


def _tokenize(text):
    tokens = set()
    for raw in str(text or "").lower().replace("-", " ").split():
        cleaned = "".join(ch for ch in raw if ch.isalnum())
        if len(cleaned) >= 3:
            tokens.add(cleaned)
    return tokens


def _read_columns(path):
    try:
        import pandas as pd

        if str(path).lower().endswith((".xlsx", ".xls")):
            frame = pd.read_excel(path, nrows=0)
        else:
            frame = pd.read_csv(path, nrows=0)
        return [str(c) for c in frame.columns]
    except Exception:
        return []


def classify_dataset_domain(columns):
    """Classify a dataset into sales / workforce / financial / generic."""

    from app.tools.workforce_analysis import has_workforce_signal

    columns = [str(c) for c in (columns or [])]
    joined = " ".join(c.lower() for c in columns)

    if has_workforce_signal(columns):
        return "workforce"

    has_financial = any(tok in joined for tok in _FINANCIAL_SCHEMA_TOKENS)
    has_sales = any(tok in joined for tok in _SALES_SCHEMA_TOKENS)

    if has_financial and not has_sales:
        return "financial"
    if has_sales:
        return "sales"
    return "generic"


def get_workspace_datasets():
    """Return the complete connected dataset collection as a read-only view.

    This never duplicates storage: it reads the existing Company Workspace
    datasets through list_datasets() and classifies each one by schema.
    """

    ctx = get_active_company()
    result = []

    for dataset in ctx["datasets"]:
        path = dataset.get("path")
        if not path:
            continue

        metadata = dataset.get("metadata", {}) or {}
        columns = metadata.get("column_names") or _read_columns(path)
        columns = [str(c) for c in columns]

        result.append(
            {
                "id": dataset.get("id"),
                "filename": dataset.get("filename"),
                "path": path,
                "metadata": metadata,
                "columns": columns,
                "domain": classify_dataset_domain(columns),
                "row_count": metadata.get("rows"),
            }
        )

    return result


def select_relevant_datasets(query, datasets):
    """Select the datasets relevant to a question.

    Falls back to the full collection when the question is broad, so
    cross-dataset questions keep every relevant source available.
    """

    lower = str(query or "").lower()
    query_tokens = _tokenize(query)

    scored = []

    for dataset in datasets:
        score = 0

        for keyword in DOMAIN_KEYWORDS.get(dataset.get("domain"), []):
            if keyword in lower:
                score += 3

        for keyword in GLOBAL_KEYWORDS:
            if keyword in lower:
                score += 1

        haystack = _tokenize(dataset.get("filename"))
        for column in dataset.get("columns", []):
            haystack.update(_tokenize(column))

        score += 2 * len(query_tokens & haystack)

        scored.append((score, dataset))

    matched = [dataset for score, dataset in scored if score > 0]

    return matched or list(datasets)


def build_company_dataset_evidence(query):
    """Build labelled, per-dataset verified evidence for the Commander."""

    datasets = get_workspace_datasets()

    if not datasets:
        return None

    from app.core.company_analysis import analyze_sales_dataset, company_evidence
    from app.tools.workforce_analysis import analyze_workforce_dataset

    relevant = select_relevant_datasets(query, datasets)

    evidence_by_dataset = {}
    datasets_used = []
    insights = []
    limitations = []

    for dataset in relevant:
        filename = dataset.get("filename")
        domain = dataset.get("domain")

        try:
            if domain == "workforce":
                payload = analyze_workforce_dataset(dataset.get("path"))
            else:
                analysis = analyze_sales_dataset(dataset.get("path"))
                payload = company_evidence(analysis)
                payload["dataset_type"] = analysis.get("dataset")

            payload["source_dataset"] = filename
            payload["domain"] = domain

            insights.extend(payload.get("insights", []) or [])
            limitations.extend(payload.get("limitations", []) or [])

        except Exception as error:
            payload = {
                "source_dataset": filename,
                "domain": domain,
                "error": f"Could not analyze {filename}.",
                "limitations": [
                    f"{filename} could not be analyzed deterministically: {error}"
                ],
            }
            limitations.append(
                f"{filename} could not be analyzed deterministically."
            )

        evidence_by_dataset[filename] = {
            "domain": domain,
            "evidence": payload,
        }

        datasets_used.append(
            {
                "filename": filename,
                "domain": domain,
                "rows": dataset.get("row_count"),
                "columns": len(dataset.get("columns", [])),
            }
        )

    return {
        "question": query,
        "datasets_used": datasets_used,
        "source_datasets": [item["filename"] for item in datasets_used],
        "evidence": evidence_by_dataset,
        "insights": insights,
        "limitations": limitations,
    }


def company_context_text(max_chars=20000):
    """Build authoritative company context for the AI system."""

    ctx = get_active_company()

    if not ctx["active"]:
        return (
            "No company workspace is currently configured."
        )

    profile = ctx["profile"]

    parts = [
        "IMPORTANT: Company Workspace data is authoritative "
        "for this investigation.",

        f"COMPANY: "
        f"{profile.get('name', 'Unknown')}",

        f"INDUSTRY: "
        f"{profile.get('industry', 'Unknown')}",

        f"BUSINESS MODEL: "
        f"{profile.get('model', 'Unknown')}",

        f"MARKETS: "
        f"{profile.get('markets', 'Unknown')}",

        f"PRODUCTS/SERVICES: "
        f"{profile.get('products', 'Unknown')}",

        f"BUSINESS GOALS: "
        f"{profile.get('goals', 'Unknown')}",

        f"COMPETITORS: "
        f"{profile.get('competitors', 'Unknown')}",

        f"DESCRIPTION: "
        f"{profile.get('description', 'Unknown')}",
    ]

    datasets = ctx["datasets"]

    if datasets:

        dataset_descriptions = []

        for dataset in datasets[:10]:

            metadata = dataset.get(
                "metadata",
                {},
            )

            domain = classify_dataset_domain(
                metadata.get("column_names", [])
            )

            dataset_descriptions.append(
                f"{dataset.get('filename', 'Unknown')} "
                f"[{domain}] "
                f"({metadata.get('rows', 0)} rows)"
            )

        parts.append(
            "DATASETS: "
            + "; ".join(
                dataset_descriptions
            )
        )

    analysis = get_company_dataset_analysis()

    if analysis:

        from app.core.company_analysis import (
            company_evidence,
        )

        evidence = company_evidence(
            analysis
        )

        parts.append(
            "VERIFIED DATA EVIDENCE:\n"
            + json.dumps(
                evidence,
                indent=2,
                default=str,
            )
        )

    elif ctx["analysis"]:

        parts.append(
            "LATEST SAVED COMPANY ANALYSIS:\n"
            + json.dumps(
                ctx["analysis"],
                indent=2,
                default=str,
            )
        )

    return "\n".join(parts)[:max_chars]
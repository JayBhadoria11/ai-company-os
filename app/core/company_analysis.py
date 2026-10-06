"""Deterministic analysis of uploaded company datasets.

All numerical business claims should originate here rather than from the LLM.
"""

from pathlib import Path
import pandas as pd


def _find_column(columns, candidates):
    normalized = {str(c).strip().lower(): c for c in columns}

    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    for c in columns:
        low = str(c).strip().lower()
        if any(candidate in low for candidate in candidates):
            return c

    return None


def _discount_amount(series):
    """Convert absolute discount amounts into numeric values.

    The current NovaMart dataset stores discounts as currency amounts.
    Example:
        100 = ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹100 discount
        200 = ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¹200 discount
    """
    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0.0)


def _sales_frame(df):
    """Create a normalized sales dataframe from common sales schemas."""

    frame = df.copy()

    units_col = _find_column(
        frame.columns,
        ["units", "quantity", "qty"],
    )

    price_col = _find_column(
        frame.columns,
        ["unit_price", "unit price", "price"],
    )

    sales_col = _find_column(
        frame.columns,
        [
            "net_sales",
            "net sales",
            "sales",
            "revenue",
            "amount",
        ],
    )

    discount_col = _find_column(
        frame.columns,
        [
            "discount",
            "discount_amount",
            "discount amount",
        ],
    )

    # -------------------------
    # Units
    # -------------------------
    if units_col:
        frame["_units"] = (
            pd.to_numeric(
                frame[units_col],
                errors="coerce",
            ).fillna(0.0)
        )
    else:
        # A sales row is not necessarily one physical unit. Keep units
        # unavailable unless the dataset actually provides quantity/units.
        frame["_units"] = pd.NA

    # -------------------------
    # Gross sales
    # -------------------------
    if sales_col:
        frame["_gross_sales"] = (
            pd.to_numeric(
                frame[sales_col],
                errors="coerce",
            ).fillna(0.0)
        )

    elif price_col:
        price = (
            pd.to_numeric(
                frame[price_col],
                errors="coerce",
            ).fillna(0.0)
        )

        frame["_gross_sales"] = (
            frame["_units"] * price
        )

    else:
        frame["_gross_sales"] = 0.0

    # -------------------------
    # Absolute discount
    # -------------------------
    if discount_col:
        frame["_discount_amount"] = (
            _discount_amount(
                frame[discount_col]
            )
        )
    else:
        frame["_discount_amount"] = 0.0

    # -------------------------
    # Net sales
    # -------------------------
    frame["_net_sales"] = (
        frame["_gross_sales"]
        - frame["_discount_amount"]
    )

    return (
        frame,
        units_col,
        price_col,
        sales_col,
        discount_col,
    )


def _group(frame, column, order_col=None, units_available=True):
    """Group sales by a business dimension using true order counts when available."""

    if not column or column not in frame.columns:
        return []

    aggregations = {
        "sales": ("_net_sales", "sum"),
        "units": ("_units", "sum"),
    }
    if order_col and order_col in frame.columns:
        aggregations["orders"] = (order_col, "nunique")
    else:
        aggregations["orders"] = ("_net_sales", "size")

    grouped = (
        frame.groupby(
            column,
            dropna=False,
        )
        .agg(**aggregations)
        .reset_index()
        .rename(
            columns={
                column: "name"
            }
        )
        .sort_values(
            "sales",
            ascending=False,
        )
    )

    return [
        {
            "name": str(row["name"]),
            "sales": round(
                float(row["sales"]),
                2,
            ),
            "units": (
                int(round(row["units"]))
                if units_available and pd.notna(row["units"])
                else None
            ),
            "orders": int(
                row["orders"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


def _monthly(frame, date_col):
    """Calculate monthly net sales."""

    if not date_col or date_col not in frame.columns:
        return []

    dates = pd.to_datetime(
        frame[date_col],
        errors="coerce",
    )

    valid = frame.loc[
        dates.notna()
    ].copy()

    if valid.empty:
        return []

    valid["_date"] = pd.to_datetime(
        valid[date_col],
        errors="coerce",
    )

    grouped = (
        valid.groupby(
            valid["_date"].dt.to_period("M")
        )["_net_sales"]
        .sum()
    )

    return [
        {
            "month": str(period),
            "sales": round(
                float(value),
                2,
            ),
        }
        for period, value in grouped.items()
    ]


def _detect_dataset_type(df, source_name=""):
    """Detect known datasets and fall back to generic schema inference."""

    columns = {str(c).strip().lower() for c in df.columns}
    source = str(source_name).lower()

    if "olist_" in source or "product_category_name_translation" in source:
        return "olist"

    strong_olist = {
        "order_item_id",
        "product_category_name",
        "customer_state",
        "seller_state",
        "payment_value",
        "review_score",
        "freight_value",
    }
    if len(columns.intersection(strong_olist)) >= 3:
        return "olist"

    apex_signals = {
        "date", "order_id", "product", "category", "region",
        "marketing_channel", "unit_price", "units", "discount",
    }
    if len(columns.intersection(apex_signals)) >= 3:
        return "apexmt"

    return "generic"

def _apexmt_analyze(df, dataset_name="apexmt"):
    """Analyze a single-table sales dataset using schema inference."""

    import pandas as pd

    # Identify columns
    date_col = _find_column(
        df.columns,
        ["date", "order_date", "order_date_time", "month", "time", "timestamp", "created_at", "transaction_date"],
    )

    product_col = _find_column(
        df.columns,
        ["product_name", "product name", "product", "item_name", "item name", "item", "sku", "item_id", "product_id"],
    )

    category_col = _find_column(
        df.columns,
        ["category", "product_category", "product_category_name", "subcategory", "sub_category"],
    )

    region_col = _find_column(
        df.columns,
        ["region", "state", "customer_state", "country", "city", "zone", "market"],
    )

    channel_col = _find_column(
        df.columns,
        ["marketing_channel", "marketing channel", "channel", "sales_channel", "source", "platform"],
    )

    order_col = _find_column(
        df.columns,
        ["order_id", "order id", "transaction_id", "invoice_id", "order", "order_number"],
    )

    # Normalize sales data
    (
        frame,
        units_col,
        price_col,
        sales_col,
        discount_col,
    ) = _sales_frame(df)

    # Overall metrics
    orders = int(frame[order_col].nunique()) if order_col else None

    total_units = (
        int(round(float(frame["_units"].sum())))
        if units_col
        else None
    )

    gross_sales = float(frame["_gross_sales"].sum())

    discount_rate_pct = None
    discount_is_rate = False
    if discount_col:
        raw_discount = pd.to_numeric(frame[discount_col], errors="coerce").dropna()
        discount_is_rate = (
            not raw_discount.empty
            and float(raw_discount.min()) >= 0
            and float(raw_discount.max()) <= 1
            and any(token in str(discount_col).strip().lower() for token in ["discount", "rate", "pct", "percent"])
        )
        if discount_is_rate:
            discount_rate_pct = round(float(raw_discount.mean()) * 100, 2)

    discounts = (
        None if discount_is_rate else
        (round(float(frame["_discount_amount"].sum()), 2) if discount_col else None)
    )

    # A fractional discount field such as 0.10 is a rate, not $0.10.
    # Do not subtract it from sales. Preserve sales as reported and expose the
    # rate separately. Keep the normalized row-level value consistent so monthly
    # and dimensional breakdowns cannot disagree with the KPI.
    if discount_is_rate:
        frame["_net_sales"] = frame["_gross_sales"]

    net_sales = float(frame["_net_sales"].sum())

    average_order_value = (
        net_sales / orders if orders else None
    )

    # Breakdowns
    # Prefer an actual product dimension. If only category exists, use it as the
    # product-like breakdown rather than pretending the category is a product.
    dimension_col = product_col or category_col
    products = _group(frame, dimension_col, order_col, units_available=bool(units_col))

    regions = _group(frame, region_col, order_col, units_available=bool(units_col))

    channels = _group(frame, channel_col, order_col, units_available=bool(units_col))

    monthly = _monthly(frame, date_col)

    # Product x Channel breakdown
    product_channel = []
    if dimension_col and channel_col:
        channel_groups = (
            frame.groupby(channel_col, dropna=False)
            .agg(sales=("_net_sales", "sum"), units=("_units", "sum"), orders=("_net_sales", "size"))
            .reset_index()
            .rename(columns={channel_col: "channel"})
            .sort_values("sales", ascending=False)
        )
        for _, row in channel_groups.iterrows():
            ch = str(row["channel"])
            product_channels = (
                frame[frame[channel_col] == ch]
                .groupby(dimension_col)
                .agg(sales=("_net_sales", "sum"), units=("_units", "sum"), orders=("_net_sales", "size"))
                .reset_index()
                .rename(columns={dimension_col: "product"})
            )
            for _, prod_row in product_channels.iterrows():
                product_channel.append({
                    "product": str(prod_row["product"]),
                    "channel": ch,
                    "sales": round(float(prod_row["sales"]), 2),
                    "units": int(round(prod_row["units"])),
                    "orders": int(prod_row["orders"]),
                })

    # Product x Region breakdown
    product_region = []
    if dimension_col and region_col:
        region_groups = (
            frame.groupby(region_col, dropna=False)
            .agg(sales=("_net_sales", "sum"), units=("_units", "sum"), orders=("_net_sales", "size"))
            .reset_index()
            .rename(columns={region_col: "region"})
            .sort_values("sales", ascending=False)
        )
        for _, row in region_groups.iterrows():
            reg = str(row["region"])
            product_regions = (
                frame[frame[region_col] == reg]
                .groupby(dimension_col)
                .agg(sales=("_net_sales", "sum"), units=("_units", "sum"), orders=("_net_sales", "size"))
                .reset_index()
                .rename(columns={dimension_col: "product"})
            )
            for _, prod_row in product_regions.iterrows():
                product_region.append({
                    "product": str(prod_row["product"]),
                    "region": reg,
                    "sales": round(float(prod_row["sales"]), 2),
                    "units": int(round(prod_row["units"])),
                    "orders": int(prod_row["orders"]),
                })

    # Declining products
    declining_products = []

    if date_col and dimension_col:
        tmp = frame.copy()
        tmp["_date"] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp[tmp["_date"].notna()]

        for name, grp in tmp.groupby(dimension_col):
            trend = (
                grp.groupby(grp["_date"].dt.to_period("M"))["_net_sales"]
                .sum()
            )
            if len(trend) >= 2:
                first_sales = float(trend.iloc[0])
                latest_sales = float(trend.iloc[-1])
                if latest_sales < first_sales:
                    change_pct = (
                        (latest_sales - first_sales) / first_sales * 100
                        if first_sales else None
                    )
                    declining_products.append({
                        "name": str(name),
                        "first_month_sales": round(first_sales, 2),
                        "latest_month_sales": round(latest_sales, 2),
                        "change_pct": (
                            round(change_pct, 2) if change_pct is not None else None
                        ),
                    })

    # Declining regions
    declining_regions = []

    if date_col and region_col:
        tmp = frame.copy()
        tmp["_date"] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp[tmp["_date"].notna()]

        for name, grp in tmp.groupby(region_col):
            trend = (
                grp.groupby(grp["_date"].dt.to_period("M"))["_net_sales"]
                .sum()
            )
            if len(trend) >= 2:
                first_sales = float(trend.iloc[0])
                latest_sales = float(trend.iloc[-1])
                if latest_sales < first_sales:
                    change_pct = (
                        (latest_sales - first_sales) / first_sales * 100
                        if first_sales else None
                    )
                    declining_regions.append({
                        "name": str(name),
                        "first_month_sales": round(first_sales, 2),
                        "latest_month_sales": round(latest_sales, 2),
                        "change_pct": (
                            round(change_pct, 2) if change_pct is not None else None
                        ),
                    })

    # Optional profit semantics. Never infer profit from sales.
    profit_col = _find_column(df.columns, ["profit", "net_profit", "gross_profit", "profit_amount"])
    profit = None
    if profit_col:
        profit_series = pd.to_numeric(df[profit_col], errors="coerce")
        if profit_series.notna().any():
            profit = round(float(profit_series.sum()), 2)

    # Limitations
    limitations = []

    if not (sales_col or price_col):
        limitations.append(
            "No sales/revenue or unit-price column was found."
        )

    if not discount_col:
        limitations.append(
            "No discount column was found, so discounted net sales cannot be "
            "independently verified from this dataset."
        )

    if profit is None:
        limitations.append(
            "Profit is unavailable because the uploaded dataset does not contain a profit field."
        )
    limitations.append(
        "Costs, CAC, ROI and profit margin remain unavailable unless the uploaded dataset contains the required fields."
    )

    # Deterministic insights
    insights = []

    if products:
        insights.append(
            f"{products[0]['name']} has the highest "
            f"net sales at ${products[0]['sales']:,.2f}."
        )
        unit_candidates = [
            item for item in products
            if item.get("units") is not None
        ]
        if unit_candidates:
            unit_leader = max(unit_candidates, key=lambda x: x["units"])
            insights.append(
                f"{unit_leader['name']} has the highest "
                f"unit volume at {unit_leader['units']:,} units."
            )

    if regions:
        insights.append(
            f"{regions[0]['name']} has the highest "
            f"net sales among regions at ${regions[0]['sales']:,.2f}."
        )

    if channels:
        insights.append(
            f"{channels[0]['name']} has the highest "
            f"net sales among marketing channels at ${channels[0]['sales']:,.2f}."
        )

    if monthly:
        insights.append(
            f"Net sales move from ${monthly[0]['sales']:,.2f} in "
            f"{monthly[0]['month']} to ${monthly[-1]['sales']:,.2f} in "
            f"{monthly[-1]['month']}."
        )

    return {
        "dataset": dataset_name,
        "rows": int(len(df)),

        "metrics": {
            "orders": orders,
            "total_units": total_units,
            "gross_sales": round(gross_sales, 2),
            "discounts": discounts,
            "discount_rate_pct": discount_rate_pct,
            "profit": profit,
            "net_sales": round(net_sales, 2),
            "average_order_value": (
                round(average_order_value, 2) if average_order_value is not None else None
            ),
        },

        "breakdowns": {
            "products": products,
            "regions": regions,
            "channels": channels,
            "monthly": monthly,
            "product_channel": product_channel,
            "product_region": product_region,
        },

        "declining": {
            "products": declining_products,
            "regions": declining_regions,
        },

        "insights": insights,

        "limitations": limitations,
    }



def _generic_analyze(df):
    """Analyze a common single-table business dataset without dataset-specific assumptions."""

    return _apexmt_analyze(df, dataset_name="generic")

def _olist_analyze_from_uploaded(df):
    """Analyze Olist dataset from a single uploaded CSV, using available columns."""

    import pandas as pd

    # Use order_items price as product sales (NOT freight_value)
    price_col = _find_column(df.columns, ["price", "unit_price", "unit price"])

    # Determine order_id column
    order_id_col = _find_column(df.columns, ["order_id", "order id"])

    # Determine product_id column
    product_id_col = _find_column(df.columns, ["product_id", "product id"])

    # Determine seller_id column
    seller_id_col = _find_column(df.columns, ["seller_id", "seller id"])

    # Determine review_score column
    review_score_col = _find_column(df.columns, ["review_score", "review score"])

    # Determine payment_type column
    payment_type_col = _find_column(df.columns, ["payment_type", "payment type"])

    # Determine payment_value column
    payment_value_col = _find_column(df.columns, ["payment_value", "payment value"])

    # Determine category translation availability
    has_translation = "product_category_name_translation" in str(df.columns).lower()

    # --- Overall metrics ---
    if order_id_col:
        orders = int(df[order_id_col].nunique())
    else:
        orders = int(len(df))

    total_units = int(df.shape[0]) if price_col else 0

    if price_col:
        price_series = pd.to_numeric(df[price_col], errors="coerce")
        gross_sales = round(float(price_series.sum()), 2)
        net_sales = gross_sales  # No discounts column by default in Olist single CSV
    else:
        gross_sales = 0.0
        net_sales = 0.0

    average_order_value = (
        round(net_sales / max(orders, 1), 2) if orders else 0.0
    )

    # --- Product sales (by category if possible) ---
    category_sales = {}
    category_units_map = {}
    category_orders_map = {}

    if price_col and product_id_col:
        items = df.copy()
        items["_product_id"] = pd.to_numeric(
            items[product_id_col], errors="coerce"
        ).astype(str)

        # Try to get category from column if present
        if "product_category_name" in df.columns and has_translation:
            cat_map = dict(
                zip(
                    df["product_category_name"],
                    df["product_category_name_english"]
                    if "product_category_name_english" in df.columns
                    else df["product_category_name"],
                )
            )
            items["_category"] = items["_product_id"].map(cat_map).fillna("unknown")
        else:
            items["_category"] = "unknown"

        if items["_category"].nunique() > 1 or "unknown" in items["_category"].unique():
            cat_grp = (
                items.groupby("_category")
                .agg(sales=(price_col, "sum"), units=(price_col, "count"), orders=(order_id_col, "nunique"))
                .reset_index()
            )
            for _, row in cat_grp.iterrows():
                cn = str(row["_category"])
                category_sales[cn] = round(float(row["sales"]), 2)
                category_units_map[cn] = int(row["units"])
                category_orders_map[cn] = int(row["orders"])

    # --- Seller sales ---
    seller_sales = {}
    seller_units_map = {}
    seller_orders_map = {}

    if price_col and seller_id_col:
        items = df.copy()
        items["_seller_id"] = pd.to_numeric(
            items[seller_id_col], errors="coerce"
        ).astype(str)

        seller_map = (
            items.groupby("_seller_id")["price"]
            .agg(["sum", "count", lambda o: pd.Series(o.index).nunique()])
            .reset_index()
        )
        seller_map.columns = ["_seller_id", "sales", "units", "orders_tmp"]

        for _, row in seller_map.iterrows():
            st = str(row["_seller_id"])
            seller_sales[st] = round(float(row["sales"]), 2)
            seller_units_map[st] = int(row["units"])
            seller_orders_map[st] = int(row["orders_tmp"]) if pd.notna(row["orders_tmp"]) else 1

    # --- Customer state ---
    customer_state_sales = {}
    customer_state_units_map = {}
    customer_state_orders_map = {}

    # --- Review metrics ---
    avg_review_score = None
    review_count = 0

    if review_score_col:
        rs = pd.to_numeric(df[review_score_col], errors="coerce")
        review_count = int(rs.notna().sum())
        if review_count > 0:
            avg_review_score = float(rs.mean())

    # --- Payment metrics ---
    payment_types = {}

    if payment_type_col and payment_value_col:
        pv = df.copy()
        pv["_pv"] = pd.to_numeric(pv[payment_value_col], errors="coerce")
        pt_grp = pv.groupby(payment_type_col).agg(
            total_value=("_pv", "sum"), count=("_pv", "count")
        ).reset_index()
        for _, row in pt_grp.iterrows():
            payment_types[str(row[payment_type_col])] = {
                "value": round(float(row["total_value"]), 2),
                "count": int(row["count"]),
            }

    # --- Delivery metrics ---
    delivered = 0
    avg_delivery_time = None

    # --- monthly sales ---
    monthly_sales = []

    # --- build result ---
    result = {
        "dataset": "olist",

        "metrics": {
            "orders": orders,
            "total_units": total_units,
            "gross_sales": gross_sales,
            "discounts": None,
            "net_sales": net_sales,
            "average_order_value": average_order_value,
        },

        "breakdowns": {
            "categories": [
                {
                    "name": name,
                    "sales": category_sales.get(name, 0),
                    "units": category_units_map.get(name, 0),
                    "orders": category_orders_map.get(name, 0),
                }
                for name in sorted(category_sales.keys())
            ]
            if category_sales
            else [],
            "sellers": [
                {
                    "name": state,
                    "sales": seller_sales.get(state, 0),
                    "units": seller_units_map.get(state, 0),
                    "orders": seller_orders_map.get(state, 0),
                }
                for state in sorted(seller_sales.keys())
            ]
            if seller_sales
            else [],
            "customer_state": customer_state_sales
            if customer_state_sales
            else [],
            "payments": payment_types if payment_types else None,
            "reviews": {
                "average_score": avg_review_score,
                "count": review_count,
            }
            if avg_review_score is not None or review_count > 0
            else None,
            "delivery": {
                "delivered_orders": delivered,
                "average_delivery_time_hours": avg_delivery_time,
            }
            if delivered > 0 or avg_delivery_time is not None
            else None,
        },

        "limitations": [
            "Freight_value excluded from product sales per Olist spec."
            if gross_sales > 0 and "freight_value" in str(df.columns).lower()
            else "Limited to uploaded CSV columns only.",
        ],
    }

    return result


def analyze_sales_dataset(path):
    """Analyze a CSV or Excel sales dataset."""

    from pathlib import Path
    import pandas as pd

    path = Path(path)

    # Load dataset
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError("Only CSV and Excel datasets are supported.")

    # Detect dataset type
    dataset_type = _detect_dataset_type(df, path.name)

    # Olist multi-table analysis
    if dataset_type == "olist":
        result = _olist_analyze_from_uploaded(df)
        return result

    # Known single-table sales schema.
    if dataset_type == "apexmt":
        return _apexmt_analyze(df, dataset_name="apexmt")

    # Generic fallback: infer only what the uploaded columns support.
    return _generic_analyze(df)

def company_evidence(analysis):
    """Create a compact factual evidence pack for the LLM.

    The full deterministic analysis remains available to the application.
    Only the most decision-relevant rows are sent to the LLM so large
    datasets cannot overflow the model context window.
    """

    breakdowns = analysis.get("breakdowns", {})

    products = breakdowns.get("products", []) or []
    regions = breakdowns.get("regions", []) or []
    channels = breakdowns.get("channels", []) or []
    monthly = breakdowns.get("monthly", []) or []
    product_channel = breakdowns.get("product_channel", []) or []
    product_region = breakdowns.get("product_region", []) or []
    sellers = breakdowns.get("sellers", []) or []

    declining = analysis.get("declining", {}) or {}

    # Keep the highest-value product/region records. The source analysis
    # remains complete; these limits apply only to the LLM evidence pack.
    products = products[:50]
    regions = regions[:20]
    channels = channels[:20]
    monthly = monthly[-24:]
    product_channel = product_channel[:50]
    product_region = product_region[:100]
    sellers = sellers[:20]

    if isinstance(declining, list):
        declining = declining[:50]
    elif isinstance(declining, dict):
        compact_declining = {}
        for key, value in declining.items():
            if isinstance(value, list):
                compact_declining[key] = value[:50]
            else:
                compact_declining[key] = value
        declining = compact_declining

    return {
        "dataset": analysis.get("dataset"),
        "metrics": analysis.get("metrics", {}),
        "products": products,
        "regions": regions,
        "channels": channels,
        "monthly": monthly,
        "product_channel": product_channel,
        "product_region": product_region,
        "sellers": sellers,
        "reviews": breakdowns.get("reviews"),
        "payments": breakdowns.get("payments"),
        "insights": analysis.get("insights", []),
        "declining": declining,
        "limitations": analysis.get("limitations", []),
    }


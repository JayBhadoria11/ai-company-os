"""Deterministic workforce/HR analytics for uploaded company datasets.

The Intelligence layer must be able to answer HR/workforce questions from the
dataset the user actually connected (for example an HR analytics export), not
only from a fixed internal employee file.

This module inspects whatever workforce columns a dataset happens to contain
and computes only the metrics those columns can genuinely support. Missing
fields are reported explicitly so the LLM never fabricates them.
"""

from pathlib import Path

import pandas as pd


WORKFORCE_STRONG_TOKENS = {
    "attrition",
    "overtime",
    "employee",
    "employeeid",
    "employeenumber",
    "employeecount",
    "jobrole",
    "monthlyincome",
    "worklifebalance",
    "yearsatcompany",
    "department",
    "headcount",
    "staff",
    "humanresources",
}

WORKFORCE_WEAK_TOKENS = {
    "gender",
    "age",
    "role",
    "salary",
    "income",
    "performance",
    "satisfaction",
    "tenure",
    "hiring",
    "workload",
}


def _normalise(name):
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


def _find_column(columns, candidates):
    normalised = {_normalise(c): c for c in columns}

    for candidate in candidates:
        key = _normalise(candidate)
        if key in normalised:
            return normalised[key]

    for column in columns:
        low = str(column).strip().lower()
        if any(candidate in low for candidate in candidates):
            return column

    return None


def has_workforce_signal(columns):
    """Return True when a dataset schema looks like workforce/HR data."""

    tokens = set()
    for column in columns:
        tokens.add(_normalise(column))

    strong = len(tokens.intersection(WORKFORCE_STRONG_TOKENS))
    weak = len(tokens.intersection(WORKFORCE_WEAK_TOKENS))

    return strong >= 2 or (strong >= 1 and weak >= 1) or weak >= 4


def _as_yes_no(series):
    values = series.astype(str).str.strip().str.lower()
    return values.map(
        {
            "yes": True,
            "y": True,
            "true": True,
            "1": True,
            "no": False,
            "n": False,
            "false": False,
            "0": False,
        }
    )


def _numeric(series):
    return pd.to_numeric(series, errors="coerce")


def analyze_workforce_dataframe(df):
    """Compute deterministic workforce metrics from an HR-like dataframe."""

    columns = list(df.columns)

    department_col = _find_column(
        columns, ["department", "dept", "division", "team", "unit"]
    )
    attrition_col = _find_column(
        columns, ["attrition", "left", "terminated", "resigned", "employee status"]
    )
    overtime_col = _find_column(
        columns, ["overtime", "over time", "over_time"]
    )
    income_col = _find_column(
        columns,
        ["monthlyincome", "monthly income", "salary", "monthlysalary", "income"],
    )
    age_col = _find_column(columns, ["age", "employee age"])
    tenure_col = _find_column(
        columns, ["yearsatcompany", "years at company", "tenure"]
    )
    total_years_col = _find_column(
        columns, ["totalworkingyears", "total working years"]
    )
    job_role_col = _find_column(
        columns, ["jobrole", "job role", "role", "job title", "title", "position"]
    )
    gender_col = _find_column(columns, ["gender", "sex"])
    satisfaction_col = _find_column(
        columns,
        ["jobsatisfaction", "job satisfaction", "worksatisfaction"],
    )
    work_life_col = _find_column(
        columns, ["worklifebalance", "work life balance"]
    )
    performance_col = _find_column(
        columns, ["performancerating", "performance rating"]
    )

    row_count = int(len(df))

    metrics = {
        "row_count": row_count,
    }

    limitations = []

    # ------------------------------------------------------------------
    # Attrition
    # ------------------------------------------------------------------
    attrition = None
    if attrition_col:
        flags = _as_yes_no(df[attrition_col]).dropna()
        total = int(flags.size)
        if total:
            left = int(flags.sum())
            attrition = {
                "column": str(attrition_col),
                "employees_left": left,
                "employees_stayed": total - left,
                "attrition_rate": round(left / total, 4),
                "attrition_rate_pct": round(left / total * 100, 2),
            }
            metrics["attrition_rate_pct"] = attrition["attrition_rate_pct"]
            metrics["employees_left"] = left
        else:
            limitations.append(
                f"Column '{attrition_col}' is present but contains no usable Yes/No values."
            )
    else:
        limitations.append(
            "No attrition/turnover column is present, so attrition risk cannot be verified."
        )

    # ------------------------------------------------------------------
    # Overtime
    # ------------------------------------------------------------------
    overtime = None
    if overtime_col:
        flags = _as_yes_no(df[overtime_col]).dropna()
        total = int(flags.size)
        if total:
            overtime_count = int(flags.sum())
            overtime = {
                "column": str(overtime_col),
                "employees_with_overtime": overtime_count,
                "overtime_rate_pct": round(overtime_count / total * 100, 2),
            }
            metrics["overtime_rate_pct"] = overtime["overtime_rate_pct"]
    else:
        limitations.append(
            "No overtime column is present, so workload pressure cannot be verified from overtime."
        )

    # ------------------------------------------------------------------
    # Compensation
    # ------------------------------------------------------------------
    income_summary = None
    if income_col:
        income = _numeric(df[income_col]).dropna()
        if not income.empty:
            income_summary = {
                "column": str(income_col),
                "mean": round(float(income.mean()), 2),
                "median": round(float(income.median()), 2),
                "min": round(float(income.min()), 2),
                "max": round(float(income.max()), 2),
            }
            metrics["average_monthly_income"] = income_summary["mean"]
            metrics["median_monthly_income"] = income_summary["median"]
    else:
        limitations.append(
            "No compensation/income column is present, so pay-related risks cannot be verified."
        )

    # ------------------------------------------------------------------
    # Other averages
    # ------------------------------------------------------------------
    def _average(column, key):
        if not column:
            return None
        values = _numeric(df[column]).dropna()
        if values.empty:
            return None
        value = round(float(values.mean()), 2)
        metrics[key] = value
        return value

    average_age = _average(age_col, "average_age")
    average_tenure = _average(tenure_col, "average_years_at_company")
    average_total_years = _average(total_years_col, "average_total_working_years")
    average_satisfaction = _average(satisfaction_col, "average_job_satisfaction")
    average_work_life = _average(work_life_col, "average_work_life_balance")
    average_performance = _average(performance_col, "average_performance_rating")

    # ------------------------------------------------------------------
    # Department and role breakdowns
    # ------------------------------------------------------------------
    def _distribution(column, limit=25):
        if not column:
            return []
        grouped = (
            df.groupby(column, dropna=False)
            .size()
            .reset_index(name="headcount")
            .sort_values("headcount", ascending=False)
        )
        rows = []
        for _, row in grouped.head(limit).iterrows():
            rows.append(
                {
                    "name": str(row[column]),
                    "headcount": int(row["headcount"]),
                }
            )
        return rows

    departments = _distribution(department_col)
    job_roles = _distribution(job_role_col)

    if department_col and attrition_col:
        flags = df[attrition_col].astype(str).str.strip().str.lower()
        dept_attrition = (
            df.assign(_left=flags.map({"yes": 1, "no": 0, "1": 1, "0": 0}))
            .dropna(subset=["_left"])
            .groupby(department_col, dropna=False)["_left"]
            .agg(["count", "sum"])
            .reset_index()
        )
        rates = {}
        for _, row in dept_attrition.iterrows():
            count = int(row["count"])
            if count:
                rates[str(row[department_col])] = round(
                    float(row["sum"]) / count * 100, 2
                )
        for row in departments:
            if row["name"] in rates:
                row["attrition_rate_pct"] = rates[row["name"]]

    gender_distribution = _distribution(gender_col)

    available_fields = [
        label
        for label, column in [
            ("department", department_col),
            ("attrition", attrition_col),
            ("overtime", overtime_col),
            ("income", income_col),
            ("age", age_col),
            ("tenure", tenure_col),
            ("job_role", job_role_col),
            ("gender", gender_col),
            ("job_satisfaction", satisfaction_col),
            ("work_life_balance", work_life_col),
            ("performance_rating", performance_col),
        ]
        if column
    ]

    missing_fields = [
        label
        for label, column in [
            ("attrition", attrition_col),
            ("department", department_col),
            ("income", income_col),
            ("overtime", overtime_col),
            ("tenure", tenure_col),
            ("job_role", job_role_col),
        ]
        if not column
    ]

    # ------------------------------------------------------------------
    # Deterministic insights (no fabrication)
    # ------------------------------------------------------------------
    insights = []

    if attrition:
        insights.append(
            f"Attrition rate is {attrition['attrition_rate_pct']}% "
            f"({attrition['employees_left']} of "
            f"{attrition['employees_left'] + attrition['employees_stayed']} employees)."
        )

    if departments:
        insights.append(
            f"{departments[0]['name']} is the largest department with "
            f"{departments[0]['headcount']} employees."
        )

    if overtime:
        insights.append(
            f"{overtime['overtime_rate_pct']}% of employees work overtime."
        )

    if income_summary:
        insights.append(
            f"Average monthly income is {income_summary['mean']:,.2f}."
        )

    if average_tenure is not None:
        insights.append(
            f"Average tenure is {average_tenure:,.2f} years."
        )

    return {
        "domain": "workforce",
        "row_count": row_count,
        "headcount": row_count,
        "metrics": metrics,
        "attrition": attrition,
        "overtime": overtime,
        "income": income_summary,
        "insights": insights,
        "averages": {
            "age": average_age,
            "years_at_company": average_tenure,
            "total_working_years": average_total_years,
            "job_satisfaction": average_satisfaction,
            "work_life_balance": average_work_life,
            "performance_rating": average_performance,
        },
        "departments": departments,
        "job_roles": job_roles,
        "gender_distribution": gender_distribution,
        "available_fields": available_fields,
        "missing_fields": missing_fields,
        "limitations": limitations,
    }


def analyze_workforce_dataset(path):
    """Load a dataset from disk and compute workforce metrics."""

    path = Path(path)

    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    return analyze_workforce_dataframe(df)

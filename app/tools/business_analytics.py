"""Business analysis tools for LLM-selected financial analysis."""

import pandas as pd


def analyze_revenue_trend(revenue_data: list[dict]) -> dict:
    """Analyze revenue trend over time.
    
    Args:
        revenue_data: List of dicts with 'date' and 'revenue' keys
    
    Returns:
        Dict with direction ('growing'/'declining'/'stable'), change_pct, and strength
    """
    if not revenue_data:
        return {"direction": "stable", "change_pct": 0.0, "strength": "none"}
    
    df = pd.DataFrame(revenue_data)
    
    if len(df) < 2:
        return {"direction": "stable", "change_pct": 0.0, "strength": "none"}
    
    # Sort by date if date column exists
    if "date" in df.columns:
        df = df.sort_values("date")
    
    values = df["revenue"].values.astype(float)
    
    if len(values) < 2:
        return {"direction": "stable", "change_pct": 0.0, "strength": "none"}
    
    # Split into first half and second half
    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]
    
    first_avg = float(first_half.mean()) if len(first_half) > 0 else 0.0
    second_avg = float(second_half.mean()) if len(second_half) > 0 else 0.0
    
    if first_avg == 0:
        change_pct = 0.0
    else:
        change_pct = ((second_avg - first_avg) / abs(first_avg)) * 100
    
    if abs(change_pct) < 5.0:
        direction = "stable"
    elif change_pct > 0:
        direction = "growing"
    else:
        direction = "declining"
    
    if abs(change_pct) >= 15.0:
        strength = "strong"
    elif abs(change_pct) >= 5.0:
        strength = "moderate"
    else:
        strength = "weak"
    
    return {
        "direction": direction,
        "change_pct": round(change_pct, 2),
        "strength": strength,
    }


def analyze_expense_ratio(expenses: float, revenue: float) -> dict:
    """Analyze expense ratio as percentage of revenue.
    
    Args:
        expenses: Total expenses amount
        revenue: Total revenue amount
    
    Returns:
        Dict with ratio_pct and assessment ('healthy'/'attention needed'/'critical')
    """
    if revenue == 0:
        return {"ratio_pct": 0.0, "assessment": "no revenue"}
    
    ratio = (expenses / revenue) * 100
    
    if ratio < 30.0:
        assessment = "healthy"
    elif ratio < 70.0:
        assessment = "attention needed"
    else:
        assessment = "critical"
    
    return {
        "ratio_pct": round(ratio, 2),
        "assessment": assessment,
    }
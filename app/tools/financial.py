"""Deterministic financial calculation tools for business analysis."""


def calculate_profit(revenue: float, expenses: float) -> float:
    """Calculate profit = revenue - expenses.
    
    Args:
        revenue: Total revenue amount
        expenses: Total expenses amount
    
    Returns:
        Profit amount (revenue - expenses)
    """
    return revenue - expenses


def calculate_profit_margin(revenue: float, profit: float) -> float:
    """Calculate profit margin as a percentage of revenue.
    
    Args:
        revenue: Total revenue amount
        profit: Profit amount
    
    Returns:
        Profit margin percentage (profit / revenue * 100)
    """
    if revenue == 0:
        return 0.0
    return (profit / revenue) * 100


def calculate_growth_rate(current: float, previous: float) -> float:
    """Calculate year-over-year growth rate percentage.
    
    Args:
        current: Current period value
        previous: Previous period value
    
    Returns:
        Growth rate percentage ((current - previous) / |previous| * 100)
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / abs(previous)) * 100
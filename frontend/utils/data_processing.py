"""
Data processing utilities
"""

import pandas as pd


def detect_chart_type(df: pd.DataFrame) -> str:
    """
    Intelligently detect chart type based on DataFrame characteristics.

    Args:
        df: DataFrame to analyze

    Returns:
        Chart type ('line', 'bar') or None
    """
    if df is None or len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]
    x_dtype = df.dtypes[0]
    y_dtype = df.dtypes[1]

    if not pd.api.types.is_numeric_dtype(y_dtype):
        return None

    # Don't chart if the Y-axis column looks like a dimension
    dimension_keywords = ['year', 'month', 'day', 'date', 'id', 'latitude', 'longitude', 'lat', 'lon']
    # Check if y_col CONTAINS any dimension keyword (not just equals)
    if any(keyword in y_col.lower() for keyword in dimension_keywords):
        return None

    temporal_keywords = ['year', 'date', 'time', 'month', 'day', 'season']
    if any(keyword in x_col.lower() for keyword in temporal_keywords):
        return 'line'

    if pd.api.types.is_object_dtype(x_dtype) or pd.api.types.is_integer_dtype(x_dtype):
        return 'bar'

    return None

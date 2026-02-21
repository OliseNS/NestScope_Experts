"""
Services module for API communication and configuration
"""

from .api_client import (
    ask_question_to_backend,
    ask_question_streaming,
    get_stats_from_backend,
    run_cv_inference,
    get_example_images,
    fetch_example_image,
    execute_custom_sql,
    get_ai_insights,
    get_tables,
    get_table_data,
    get_table_schema,
    update_table_row,
    delete_table_row,
    insert_table_row
)
from .config import API_BASE_URL

__all__ = [
    'ask_question_to_backend',
    'ask_question_streaming',
    'get_stats_from_backend',
    'run_cv_inference',
    'get_example_images',
    'fetch_example_image',
    'execute_custom_sql',
    'get_ai_insights',
    'get_tables',
    'get_table_data',
    'get_table_schema',
    'update_table_row',
    'delete_table_row',
    'insert_table_row',
    'API_BASE_URL'
]

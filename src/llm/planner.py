"""
LLM query planner - converts natural language to function calls.

This module handles the interaction with OpenRouter API to:
1. Understand user's natural language question
2. Select appropriate query function(s)
3. Extract parameters from the question
4. Return function calls with structured parameters

Person 2 (LLM/AI Developer) implementation
"""

import os
from typing import Dict, Any, List
from openai import OpenAI

from src.llm.functions import get_function_schemas


class QueryPlanner:
    """Plans and executes queries based on natural language input."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the query planner with OpenRouter API.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model to use (defaults to OPENROUTER_MODEL env var or anthropic/claude-3.5-sonnet)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.function_schemas = get_function_schemas()

    def plan_query(self, user_question: str) -> Dict[str, Any]:
        """
        Convert natural language question to function call.

        Args:
            user_question: User's natural language question

        Returns:
            Dict containing function name and parameters
        """
        # TODO: Implement Claude API call with function calling
        # Example structure:
        # {
        #     "function_name": "species_trend",
        #     "parameters": {
        #         "species": "Brown Pelican",
        #         "start_year": 2015,
        #         "end_year": 2021
        #     }
        # }
        pass

    def execute_with_context(
        self,
        user_question: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Plan query with conversation context for multi-turn interactions.

        Args:
            user_question: Current user question
            conversation_history: Previous conversation turns

        Returns:
            Dict containing function name and parameters
        """
        # TODO: Implement context-aware query planning
        pass


if __name__ == "__main__":
    # Test the query planner
    planner = QueryPlanner()
    # TODO: Add test queries
    print("Query planner initialized")

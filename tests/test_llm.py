"""
Test cases for LLM query planner and formatter.

Person 4 (Project Manager/QA) implementation
"""

import pytest
# from src.llm.planner import QueryPlanner
# from src.llm.formatter import ResponseFormatter


class TestQueryPlanner:
    """Test suite for query planning."""

    def test_plan_species_trend(self):
        """Test planning a species trend query."""
        # TODO: Implement test
        # planner = QueryPlanner()
        # result = planner.plan_query(
        #     "Show brown pelican trends from 2015-2021"
        # )
        # assert result['function_name'] == 'species_trend'
        # assert result['parameters']['species'] == 'Brown Pelican'
        # assert result['parameters']['start_year'] == 2015
        # assert result['parameters']['end_year'] == 2021
        pass

    def test_plan_top_species(self):
        """Test planning a top species query."""
        # TODO: Implement test
        # planner = QueryPlanner()
        # result = planner.plan_query(
        #     "What were the top 5 species in 2020?"
        # )
        # assert result['function_name'] == 'top_species'
        # assert result['parameters']['n'] == 5
        # assert result['parameters']['year'] == 2020
        pass

    def test_plan_comparison(self):
        """Test planning a regional comparison query."""
        # TODO: Implement test
        pass


class TestResponseFormatter:
    """Test suite for AI response generation."""

    def test_format_response(self):
        """Test generating natural language response."""
        # TODO: Implement test
        # formatter = ResponseFormatter()
        # result = formatter.format_response(
        #     query_result=sample_dataframe,
        #     user_question="Show brown pelican trends",
        #     function_name="species_trend",
        #     parameters={"species": "Brown Pelican", ...}
        # )
        # assert isinstance(result, str)
        # assert len(result) > 0
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

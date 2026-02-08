"""Test the query() API method for frontend integration"""

from sql_chatbot import SQLChatbot
import json


def test_api():
    print("TESTING FRONTEND API")
    print("=" * 80)

    chatbot = SQLChatbot()

    # Test successful query
    print("\n[TEST 1] Successful query")
    response = chatbot.query("What are the top 5 most observed species?")

    print(f"Success: {response['success']}")
    print(f"SQL: {response['sql']}")
    print(f"Row count: {response['row_count']}")
    print(f"Answer preview: {response['answer'][:150]}...")

    # Test error handling
    print("\n[TEST 2] Invalid query")
    response = chatbot.query("What's the weather today?")

    print(f"Success: {response['success']}")
    print(f"Error: {response['error']}")

    chatbot.close()
    print("\n" + "=" * 80)
    print("API TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_api()
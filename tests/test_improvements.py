"""Test the improved SQL chatbot with validation and repair"""

from sql_chatbot import SQLChatbot


def test_chatbot():
    print("TESTING AI IMPROVEMENTS")
    print("=" * 80)

    chatbot = SQLChatbot()

    # Test queries
    test_questions = [
        "What are the top 5 most observed species?",
        "Which colonies had oil in 2010?",
        "Show Brown Pelican observations",
        "How many colonies are in Louisiana?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n\n{'=' * 80}")
        print(f"TEST {i}/{len(test_questions)}")
        print(f"{'=' * 80}")

        try:
            answer = chatbot.ask(question)
            if answer:
                print(f"\nSUCCESS")
            else:
                print(f"\nNo answer returned")
        except Exception as e:
            print(f"\nFAILED: {e}")

    chatbot.close()
    print("\n\nTesting complete!")


if __name__ == "__main__":
    test_chatbot()
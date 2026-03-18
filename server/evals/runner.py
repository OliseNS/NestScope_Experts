"""
NestEval Runner — Runs DeepEval evaluations against the live NestChat pipeline.

HOW DEEPEVAL WORKS (the concept):
  DeepEval acts as a "judge LLM" — it reads what NestChat said and scores it.
  Think of it like a teacher grading a student's answer against the source material.

  The two metrics we use:
  1. AnswerRelevancyMetric  — Did the answer actually answer the question?
                              (Scores 0.0 to 1.0, we require >= 0.7)
  2. FaithfulnessMetric     — Is the answer grounded in the retrieved data?
                              (Prevents hallucination — making up bird counts)

  Both metrics use a "judge LLM" (the same OpenRouter model) to evaluate.

HOW IT PLUGS INTO NESTCHAT:
  EvalRunner calls chatbot.ask(question) which returns:
    { sql_query, results, answer, success, error }
  Then wraps that in a DeepEval LLMTestCase and measures both metrics.

BACKGROUND EXECUTION:
  The runner is called from a background thread (via FastAPI BackgroundTasks)
  so the server stays responsive while evals run (they can take 2-5 minutes).
"""

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# DeepEval imports
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.models import DeepEvalBaseLLM

from server.evals.test_cases import NESTCHAT_TEST_CASES

# Directory where results JSON files are saved
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ============================================================================
# CUSTOM LLM ADAPTER FOR DEEPEVAL
# ============================================================================

class OpenRouterEvalLLM(DeepEvalBaseLLM):
    """
    Adapts our existing OpenRouter client to the DeepEval LLM interface.

    WHY WE NEED THIS:
    DeepEval was designed to work with OpenAI by default. But our project
    uses OpenRouter (a gateway to many models). This class acts as a bridge:
    it wraps our OpenRouter client and makes it look like a DeepEval-compatible
    LLM. DeepEval will call generate() whenever it needs to evaluate something.

    It's like giving DeepEval a universal power adapter — same plug, different socket.
    """

    def __init__(self, openai_client, model_name: str):
        """
        Args:
            openai_client: The OpenAI client instance already configured
                           to point at OpenRouter's API base URL.
            model_name: The model identifier (e.g. 'anthropic/claude-sonnet-4.6')
        """
        self._client = openai_client
        self._model_name = model_name

    def load_model(self):
        """DeepEval calls this to 'load' the model. We just return the name."""
        return self._model_name

    def generate(self, prompt: str) -> str:
        """
        Called by DeepEval metrics to score a test case.
        Sends the prompt to our OpenRouter model and returns the response text.
        """
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Temperature=0 for deterministic, consistent scoring
            max_tokens=1000,
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        """Async version of generate. DeepEval requires this for async eval runs."""
        # DeepEval sometimes calls this. We delegate to the sync version.
        return self.generate(prompt)

    def get_model_name(self) -> str:
        """Returns the model identifier string."""
        return self._model_name


# ============================================================================
# EVAL RUNNER
# ============================================================================

class EvalRunner:
    """
    Orchestrates a full evaluation run against NestChat.

    Usage:
        runner = EvalRunner(chatbot=chatbot, openai_client=client, model_name=model)
        runner.run(eval_state)  # eval_state dict is updated in-place with progress
    """

    # Metric thresholds — score must be >= threshold to pass
    # 0.7 means "70% confident this is a good answer". A common starting point.
    ANSWER_RELEVANCY_THRESHOLD = 0.7
    FAITHFULNESS_THRESHOLD = 0.7

    def __init__(self, chatbot, openai_client, model_name: str):
        """
        Args:
            chatbot:       SQLChatbot instance (from server/main.py)
            openai_client: OpenAI-compatible client configured for OpenRouter
            model_name:    Model to use for both NestChat AND evaluation scoring
        """
        self.chatbot = chatbot
        self.eval_llm = OpenRouterEvalLLM(openai_client, model_name)
        self.model_name = model_name

    def run(self, eval_state: dict) -> dict:
        """
        Runs all test cases and returns the full results dict.
        Also updates eval_state in-place so the API can report progress.

        Args:
            eval_state: Shared dict (modified in-place) with keys:
                        running, progress, total, current_test, run_id, error

        Returns:
            dict matching the results JSON schema
        """
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        start_time = time.time()

        eval_state.update({
            "running": True,
            "run_id": run_id,
            "progress": 0,
            "total": len(NESTCHAT_TEST_CASES),
            "current_test": "",
            "error": None,
        })

        test_results = []
        passed_count = 0

        # Build the metrics once — reuse for each test case
        # (Creating them is cheap, but explicit is clear)
        answer_relevancy_metric = AnswerRelevancyMetric(
            threshold=self.ANSWER_RELEVANCY_THRESHOLD,
            model=self.eval_llm,
            include_reason=True,  # Gives us a human-readable explanation of the score
        )
        faithfulness_metric = FaithfulnessMetric(
            threshold=self.FAITHFULNESS_THRESHOLD,
            model=self.eval_llm,
            include_reason=True,
        )

        for i, test_case in enumerate(NESTCHAT_TEST_CASES):
            question = test_case["question"]
            eval_state["current_test"] = test_case["description"]
            eval_state["progress"] = i  # 0-indexed progress

            result_entry = {
                "id": test_case["id"],
                "description": test_case["description"],
                "question": question,
                "category": test_case["category"],
                "sql_query": None,
                "answer": None,
                "success": False,
                "error": None,
                "metrics": {},
                "overall_passed": False,
            }

            try:
                # ── STEP 1: Ask NestChat ──────────────────────────────────────
                # chatbot.ask() is the same method NestChat uses for real queries.
                # It returns: { success, sql_query, results, answer, error }
                chat_result = self.chatbot.ask(question)

                result_entry["sql_query"] = chat_result.get("sql_query", "")
                result_entry["answer"] = chat_result.get("answer", "")
                result_entry["success"] = chat_result.get("success", False)
                result_entry["error"] = chat_result.get("error")

                if not chat_result.get("success") or not chat_result.get("answer"):
                    # If NestChat itself failed (bad SQL, DB error), mark as failed
                    # and skip metric scoring — there's nothing useful to evaluate.
                    result_entry["overall_passed"] = False
                    test_results.append(result_entry)
                    continue

                # ── STEP 2: Format retrieval context ─────────────────────────
                # FaithfulnessMetric needs to know what data NestChat retrieved
                # so it can check if the answer is grounded in that data.
                # We pass the SQL results as a text table (list of strings).
                raw_results = chat_result.get("results") or []
                if raw_results:
                    # Format as a readable table: "col1 | col2\nval1 | val2\n..."
                    if len(raw_results) > 0:
                        headers = " | ".join(str(k) for k in raw_results[0].keys())
                        rows = [" | ".join(str(v) for v in row.values()) for row in raw_results[:20]]
                        context_str = headers + "\n" + "\n".join(rows)
                    else:
                        context_str = "No results returned."
                else:
                    context_str = "No results returned."

                # ── STEP 3: Build DeepEval test case ─────────────────────────
                # LLMTestCase is the core unit in DeepEval:
                #   input            = the question the user asked
                #   actual_output    = what NestChat actually said
                #   retrieval_context = the data NestChat retrieved (for faithfulness)
                deepeval_case = LLMTestCase(
                    input=question,
                    actual_output=result_entry["answer"],
                    retrieval_context=[context_str],
                )

                # ── STEP 4: Score the metrics ─────────────────────────────────
                metrics_result = {}

                # --- Answer Relevancy ---
                # Question: "Did the answer actually answer what was asked?"
                try:
                    answer_relevancy_metric.measure(deepeval_case)
                    metrics_result["answer_relevancy"] = {
                        "score": round(answer_relevancy_metric.score, 3),
                        "passed": answer_relevancy_metric.is_successful(),
                        "threshold": self.ANSWER_RELEVANCY_THRESHOLD,
                        "reason": answer_relevancy_metric.reason,
                    }
                except Exception as e:
                    metrics_result["answer_relevancy"] = {
                        "score": None,
                        "passed": False,
                        "threshold": self.ANSWER_RELEVANCY_THRESHOLD,
                        "error": str(e),
                    }

                # --- Faithfulness ---
                # Question: "Is the answer grounded in the retrieved data?
                #            (Did it make something up, or stick to the facts?)"
                try:
                    faithfulness_metric.measure(deepeval_case)
                    metrics_result["faithfulness"] = {
                        "score": round(faithfulness_metric.score, 3),
                        "passed": faithfulness_metric.is_successful(),
                        "threshold": self.FAITHFULNESS_THRESHOLD,
                        "reason": faithfulness_metric.reason,
                    }
                except Exception as e:
                    metrics_result["faithfulness"] = {
                        "score": None,
                        "passed": False,
                        "threshold": self.FAITHFULNESS_THRESHOLD,
                        "error": str(e),
                    }

                result_entry["metrics"] = metrics_result

                # Overall pass: ALL metrics must pass (and NestChat must succeed)
                all_metrics_passed = all(
                    m.get("passed", False) for m in metrics_result.values()
                )
                result_entry["overall_passed"] = all_metrics_passed

                if all_metrics_passed:
                    passed_count += 1

            except Exception as e:
                # Unexpected error in the eval loop itself
                result_entry["error"] = f"Eval error: {e}\n{traceback.format_exc()}"
                result_entry["overall_passed"] = False

            test_results.append(result_entry)
            eval_state["progress"] = i + 1  # 1-indexed after completion

        # ── Build final results dict ──────────────────────────────────────────
        duration = round(time.time() - start_time, 1)
        total = len(NESTCHAT_TEST_CASES)
        failed = total - passed_count

        results = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": total,
            "passed": passed_count,
            "failed": failed,
            "pass_rate": round(passed_count / total, 3) if total > 0 else 0.0,
            "model": self.model_name,
            "duration_seconds": duration,
            "test_results": test_results,
        }

        # ── Save results to disk ──────────────────────────────────────────────
        # Save two copies:
        #   latest.json  → always overwritten, easy to fetch the most recent run
        #   {run_id}.json → permanent archive for tracking trends over time
        latest_path = RESULTS_DIR / "latest.json"
        archive_path = RESULTS_DIR / f"{run_id}.json"

        for path in [latest_path, archive_path]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)

        # ── Mark eval as complete ─────────────────────────────────────────────
        eval_state.update({
            "running": False,
            "progress": total,
            "current_test": "Complete",
        })

        return results

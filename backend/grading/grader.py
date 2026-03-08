import json
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Lazy import — ai_chat.main triggers heavy torch/embeddings loads
_ai = None


def _get_ai():
    global _ai
    if _ai is None:
        import ai_chat.main as ai
        _ai = ai
    return _ai


# Separate low-temperature LLM for deterministic grading
_grading_llm = None


def _get_grading_llm():
    global _grading_llm
    if _grading_llm is None:
        ai = _get_ai()
        ai._ensure_initialized()
        # Create a separate low-temperature LLM for deterministic grading
        if ai.OllamaLLM is None:
            raise RuntimeError("OllamaLLM not available")
        _grading_llm = ai.OllamaLLM(model=ai.LLM_MODEL, temperature=0.15, num_predict=ai._NUM_PREDICT)
    return _grading_llm


def _extract_json(text: str) -> dict | None:
    """Robustly extract a JSON object from LLM output that may contain extra text."""
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # Try full string first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try to find the first {...} block
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


class Grader:

    def grade(self, question, answer, academic_standard, subject=None):

        ai = _get_ai()
        ai._ensure_initialized()

        # -------- STEP 1: Retrieve context using the question --------
        retriever = ai.get_retriever(subject)
        docs = retriever.invoke(question)

        context = "\n\n".join([d.page_content for d in docs if hasattr(d, 'page_content')])

        # -------- STEP 2: Build grading prompt --------
        prompt = f"""Grade the student answer. Use the study material if relevant, else use your knowledge.
Consider the academic standard ({academic_standard}) for strictness.
Evaluate: accuracy, completeness, clarity, depth of understanding, and use of key terminology.

Question:
{question}

Study material:
{context}

Student Answer:
{answer}

Scoring (0-10, 0.5 increments):
0 = unanswered, 1-2 = very incomplete, 3-4 = incomplete, 5-6 = partial, 7-8 = mostly correct, 9-10 = excellent.

Return ONLY valid JSON:
{{"score": <number>, "errors": [<strings>], "strengths": [<strings>], "remarks": "<feedback>"}}
"""

        # -------- STEP 3: Run LLM (low temperature for consistency) --------
        grading_llm = _get_grading_llm()
        response = str(grading_llm.invoke(prompt))

        result = _extract_json(response)
        if result and "score" in result:
            result.setdefault("errors", [])
            result.setdefault("strengths", [])
            result.setdefault("remarks", "")
            return result

        # Retry once with even simpler prompt
        retry_prompt = f"""Score this answer 0-10. Question: {question}\nAnswer: {answer}\nReturn ONLY JSON: {{"score": <number>, "errors": [], "strengths": [], "remarks": ""}}"""
        response2 = str(grading_llm.invoke(retry_prompt))
        result2 = _extract_json(response2)
        if result2 and "score" in result2:
            result2.setdefault("errors", [])
            result2.setdefault("strengths", [])
            result2.setdefault("remarks", "")
            return result2

        return {
            "score": 0,
            "errors": ["Could not parse grading response after retry"],
            "strengths": [],
            "remarks": ""
        }
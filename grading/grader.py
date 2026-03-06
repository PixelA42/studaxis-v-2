import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ai_chat.main as ai


class Grader:

    def grade(self, question, answer , academic_standard):

        # -------- STEP 1: Retrieve context using the question --------
        retriever = ai.get_retriever()
        docs = retriever.invoke(question)

        context = "\n\n".join([d.page_content for d in docs])

        # -------- STEP 2: Build grading prompt --------
        prompt = f"""
You are grading a student's answer.

Question:
{question}

Relevant study material:
{context}

Student Answer:
{answer}

Instructions:
- Use the study material if relevant.
- If the study material is unrelated, rely on your subject knowledge.
- Consider the academic standard of the question when grading strictly.
- Evaluate accuracy, completeness, length  (if needed), and clarity according to the academic standard of the answer.
- give marks if the answer is only directly related to the question and subject and not beating around the bush.
- depth of understanding and critical thinking is more important than breadth of content.
- Using natural language processing (NLP) to compare the answer with a model answer, checking for similar meaning rather than identical wording.
- analyze the presence of essential terminology, technical concepts, or synonyms that indicate deep understanding.
- assess if the answer directly addresses the question asked, rather than including off-topic information.
1. Determine what a correct answer should contain.
2. Compare the student answer with those points.
3. Assign a score based on the scoring guide.
4. Explain mistakes like a teacher.
- Also give the remarks in a constructive way, highlighting strengths as well as areas for improvement.


Scoring:
0–10 with 0.5 increments.

Score Guide:
consider the academic standard of the question when grading strictly.

0 → Completely incorrect or unanswered
1–2 → Very incomplete understanding
3–4 → Incomplete understanding
5–6 → Partially correct but missing key ideas
7–8 → Mostly correct with minor missing details
9–10 → Complete and well-explained answer

Return ONLY JSON:
{{
 "score": number,
 "errors": [],
 "strengths": []
 "remarks": "Constructive feedback here"
}}
"""

        # -------- STEP 3: Run LLM --------
        response = ai.llm.invoke(prompt)

        response = str(response).replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(response)
        except Exception:

            return {
                "score": 0,
                "errors": ["Could not parse grading response"],
                "strengths": []
            }
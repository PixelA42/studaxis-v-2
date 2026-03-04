import json
import uuid
import re
from datetime import datetime


def extract_json(text: str):

    text = re.sub(r"```json|```", "", text)

    match = re.search(r"\[.*\]", text, re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except:
        return None


class FlashcardGenerator:

    def __init__(self, retriever, llm, storage, student_model):

        self.retriever = retriever
        self.llm = llm
        self.storage = storage
        self.student_model = student_model


# ---------------------------
# AGENT ROUTER
# ---------------------------

    def flashcard_agent(self, topic):

        prompt = f"""
You are an AI planning agent.

Decide the BEST flashcard generation strategy.

Topic: {topic}

Options:
conceptual
definition
application
formula
mixed

Return ONLY the strategy word.
"""

        decision = self.llm.invoke(prompt)

        decision = str(decision).strip().lower()

        allowed = ["conceptual", "definition", "application", "formula", "mixed"]

        if decision not in allowed:
            decision = "mixed"

        return decision


# ---------------------------
# MAIN GENERATOR
# ---------------------------

    def generate(self, topic: str, num_cards: int = 5):

        strategy = self.flashcard_agent(topic)

        docs = self.retriever.invoke(topic)

        if not docs:
            print("No relevant chunks found.")
            return []

        context = "\n\n".join(d.page_content for d in docs)

        difficulty = self.student_model.get_difficulty(topic)

        prompt = f"""
You are an expert academic tutor creating high-quality flashcards.

FLASHCARD STRATEGY: {strategy}

GOAL:
Create conceptually deep, exam-ready flashcards.

KNOWLEDGE STRATEGY:
1. Use retrieved context for factual grounding.
2. Improve explanations using your own knowledge.
3. Add conceptual clarity and examples.
4. Never contradict retrieved context.

DIFFICULTY LEVEL: {difficulty}

CARD TYPES ALLOWED:
definition
conceptual
application

STRICT RULES:
Return ONLY JSON.

FORMAT:
[
{{
"question": "...",
"answer": "...",
"type": "definition | conceptual | application"
}}
]

RETRIEVED CONTEXT:
{context}

TOPIC:
{topic}

Generate exactly {num_cards} flashcards.
"""

        cards = None

        for attempt in range(2):

            response = self.llm.invoke(prompt)

            cards = extract_json(str(response))

            if cards:
                break

        if not cards:
            print("❌ Model failed to return valid JSON.")
            return []

        enriched = []

        for card in cards:

            card["card_id"] = str(uuid.uuid4())
            card["topic"] = topic
            card["created_at"] = datetime.now().isoformat()

            # spaced repetition defaults
            card["interval"] = 1
            card["repetitions"] = 0
            card["ease_factor"] = 2.5
            card["next_review"] = datetime.now().isoformat()

            enriched.append(card)

        self.storage.add_flashcards(enriched)

        print(f"✅ Generated {len(enriched)} flashcards using strategy: {strategy}")

        return enriched
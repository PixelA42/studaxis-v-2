import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ai_chat.main as ai

from local_app.utils.local_storage import LocalStorage
from generator import FlashcardGenerator
from review import ReviewEngine
from student_model import StudentModel


def main():

    # Initialize shared systems
    retriever = ai.get_retriever()

    storage = LocalStorage()

    student_model = StudentModel(storage)

    generator = FlashcardGenerator(
        retriever,
        ai.llm,
        storage,
        student_model
    )

    review_engine = ReviewEngine(storage, student_model)

    while True:

        q = input("\nEnter command: ").strip()

        # Generate flashcards
        if q.startswith("flashcards"):

            topic = q.replace("flashcards", "").strip()

            cards = generator.generate(topic)

            print(f"\nGenerated {len(cards)} cards\n")

            for c in cards:
                print("Q:", c["question"])
                print("A:", c["answer"])
                print()

        # Start review session
        elif q == "review":

            review_engine.start_review()

        # Exit program
        elif q == "exit":

            break

        else:
            print("Commands:")
            print("flashcards <topic>")
            print("review")
            print("exit")


if __name__ == "__main__":
    main()
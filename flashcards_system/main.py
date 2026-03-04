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

            if not topic:
                print("Please provide a topic.")
                continue

            cards = generator.generate(topic)
            print_flashcards(cards)

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


def print_flashcards(cards):

    if not cards:
        print("No flashcards generated.")
        return

    print("\n" + "="*50)
    print("FLASHCARDS")
    print("="*50)

    for i, card in enumerate(cards, start=1):

        print(f"\nCard {i}")
        print("-"*40)
        print(f"Topic: {card['topic']}")
        print(f"Type : {card.get('type','unknown')}")

        print("\nQ:", card["question"])

        input("\nPress ENTER to reveal answer...")

        print("\nA:", card["answer"])
        print("\n" + "-"*40)

if __name__ == "__main__":
    main()
from spaced_repetition import update_card

class ReviewEngine:

    def __init__(self, storage, student_model):
        self.storage = storage
        self.student_model = student_model

    def start_review(self):

        due_cards = self.storage.get_due_cards()

        if not due_cards:
            print("No cards due.")
            return

        data = self.storage.load_user_stats()

        for card in due_cards:

            print("\nQ:", card["question"])
            input("Press Enter to show answer...")
            print("A:", card["answer"])

            quality = int(input("Rate yourself (0-5): "))

            correct = quality >= 3

            self.student_model.update_topic_performance(
                card["topic"], correct
            )

            update_card(card, quality)

        self.storage.save_user_stats(data)
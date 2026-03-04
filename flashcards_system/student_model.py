class StudentModel:
    def __init__(self, storage):
        self.storage = storage

    def get_difficulty(self, topic: str):
        stats = self.storage.load_stats()

        topic_stats = stats.get("topic_performance", {}).get(topic)

        if not topic_stats:
            return "medium"

        accuracy = topic_stats.get("accuracy", 0.7)

        if accuracy > 0.8:
            return "hard"
        elif accuracy < 0.5:
            return "easy"
        return "medium"

    def update_topic_performance(self, topic, correct: bool):
        stats = self.storage.load_stats()

        if "topic_performance" not in stats:
            stats["topic_performance"] = {}

        if topic not in stats["topic_performance"]:
            stats["topic_performance"][topic] = {
                "correct": 0,
                "wrong": 0,
                "accuracy": 0
            }

        if correct:
            stats["topic_performance"][topic]["correct"] += 1
        else:
            stats["topic_performance"][topic]["wrong"] += 1

        c = stats["topic_performance"][topic]["correct"]
        w = stats["topic_performance"][topic]["wrong"]

        stats["topic_performance"][topic]["accuracy"] = c / (c + w)

        self.storage.save_stats(stats)
import json
from pathlib import Path

DATA_FILE = Path("data/user_stats.json")


class AnswerStorage:

    def __init__(self):

        if DATA_FILE.exists():

            with open(DATA_FILE , encoding="utf-8") as f:
                self.data = json.load(f)

        else:
            self.data = {}

    def store(self, user_id, result):

        if user_id not in self.data:
            self.data[user_id] = []

        self.data[user_id].append(result)

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
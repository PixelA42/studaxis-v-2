import json
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BACKEND_DIR / "data"


class AnswerStorage:

    def __init__(self, user_id: str = "student_001"):
        self._user_id = user_id
        self._file = _DATA_DIR / "users" / user_id / "user_stats.json"
        self._file.parent.mkdir(parents=True, exist_ok=True)

        if self._file.exists():
            with open(self._file, encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def store(self, user_id, result):
        grading_results = self.data.setdefault("grading_results", [])
        grading_results.append(result)

        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
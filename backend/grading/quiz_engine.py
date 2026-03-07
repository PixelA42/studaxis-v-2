from grading.grader import Grader
from grading.red_pen_feedback import RedPenFeedback
from grading.answer_storage import AnswerStorage


class QuizEngine:

    def __init__(self):

        self.grader = Grader()
        self.feedback = RedPenFeedback()
        self.storage = AnswerStorage()

    def submit(self, user_id, question, answer, academic_standard):

        grading = self.grader.grade(question, answer, academic_standard)

        feedback = self.feedback.generate(
            question,
            answer,
            grading
        )

        result = {
            "question": question,
            "answer": answer,
            "score": grading["score"],
            "feedback": feedback
        }

        self.storage.store(user_id, result)

        return result
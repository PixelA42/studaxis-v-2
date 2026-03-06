class RedPenFeedback:

    def generate(self, question, answer, grading):

        feedback = []

        feedback.append("Question:")
        feedback.append(question)
        feedback.append("")

        feedback.append("Original Answer:")
        feedback.append(answer)
        feedback.append("")

        feedback.append("Score:")
        feedback.append(str(grading["score"]) + " / 10")
        feedback.append("")

        if grading.get("errors"):

            feedback.append("❌ Errors:")

            for e in grading["errors"]:

                if isinstance(e, dict):
                    e = list(e.values())[0]

                feedback.append("- " + str(e))

        if grading.get("strengths"):

            feedback.append("")
            feedback.append("✔ Strengths:")

            for s in grading["strengths"]:

                if isinstance(s, dict):
                    s = list(s.values())[0]

                feedback.append("- " + str(s))

        return "\n".join(feedback)
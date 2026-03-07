# created for testing grading system 


from quiz_engine import QuizEngine


def main():

    print("\n=== Studaxis Grading Prototype ===")

    quiz = QuizEngine()


    user_id = "test_user"


    question = input("\nEnter question:\n> ")

    while True:

        academic_standard = input("\nEnter academic standard (or exit):\n> ")

        if academic_standard.lower() == "exit":
            break

        answer = input("\nEnter answer (or exit):\n> ")

        if answer.lower() == "exit" :
            break

        result = quiz.submit(user_id, question, answer, academic_standard)

        print("\nScore:", result["score"])
        print("\nFeedback:\n")
        print(result["feedback"])


if __name__ == "__main__":
    main()
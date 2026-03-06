"""
Examples for Studaxis AI Integration Layer.
Run: python example_ai_integration_layer.py
"""

from ai_integration_layer import AIEngine, AITaskType


def print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run_examples() -> None:
    engine = AIEngine(base_path=".")

    print_section("1) Offline Chat Request")
    chat_response = engine.request(
        task_type=AITaskType.CHAT,
        user_input="Explain Newton's second law in simple words.",
        context_data={"subject": "Physics", "difficulty": "Beginner"},
        offline_mode=True,
        privacy_sensitive=True,
        user_id="student_demo",
    )
    print("Text:", chat_response.text)
    print("Metadata:", chat_response.metadata)

    print_section("2) Clarify Request")
    clarify_response = engine.request(
        task_type=AITaskType.CLARIFY,
        user_input="What does 'net force' mean here?",
        context_data={"parent_response": "F = ma ..."},
        offline_mode=True,
        privacy_sensitive=True,
    )
    print("Text:", clarify_response.text)
    print("Follow-ups:", clarify_response.follow_up_suggestions)

    print_section("3) Teacher Analytics (Online -> Cloud)")
    teacher_response = engine.request(
        task_type=AITaskType.TEACHER_ANALYTICS_INSIGHT,
        user_input="Summarize weak topics for class 10-B.",
        context_data={"class_code": "10-B", "period": "last_7_days"},
        offline_mode=False,
        privacy_sensitive=False,
    )
    print("Target:", teacher_response.metadata.get("execution_target"))
    print("Model:", teacher_response.metadata.get("model_name"))


if __name__ == "__main__":
    run_examples()

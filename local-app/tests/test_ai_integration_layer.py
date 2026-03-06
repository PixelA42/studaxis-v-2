import os
import tempfile
import unittest

from ai_integration_layer import AIConfig, AIEngine, AIState, AITaskType


class TestAIIntegrationLayer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base_path = self.tmpdir.name
        config = AIConfig()
        config.ENABLE_AI_LOGGING = True
        config.AI_TIMEOUT_SECONDS = 2
        self.engine = AIEngine(base_path=self.base_path, config=config)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_chat_request_returns_standard_response(self) -> None:
        response = self.engine.request(
            task_type=AITaskType.CHAT,
            user_input="Explain momentum in simple terms.",
            context_data={"subject": "Physics"},
            offline_mode=True,
            privacy_sensitive=True,
            user_id="student_1",
        )
        self.assertTrue(response.text)
        self.assertIn("request_id", response.metadata)
        self.assertIn("execution_target", response.metadata)
        self.assertEqual(response.state, AIState.RESPONSE_RECEIVED)

    def test_offline_forces_local_target(self) -> None:
        response = self.engine.request(
            task_type=AITaskType.CHAT,
            user_input="What is osmosis?",
            context_data={},
            offline_mode=True,
            privacy_sensitive=False,
        )
        self.assertEqual(response.metadata.get("execution_target"), "local")

    def test_teacher_analytics_can_route_cloud_when_online(self) -> None:
        response = self.engine.request(
            task_type=AITaskType.TEACHER_ANALYTICS_INSIGHT,
            user_input="Summarize weak algebra trends.",
            context_data={"class_code": "10-B"},
            offline_mode=False,
            privacy_sensitive=False,
        )
        self.assertEqual(response.metadata.get("execution_target"), "cloud")

    def test_timeout_returns_fallback(self) -> None:
        config = AIConfig()
        config.AI_TIMEOUT_SECONDS = 0
        config.ENABLE_AI_LOGGING = False
        engine = AIEngine(base_path=self.base_path, config=config)

        response = engine.request(
            task_type=AITaskType.CHAT,
            user_input="Long operation test",
            context_data={},
            offline_mode=False,
            privacy_sensitive=False,
        )
        self.assertEqual(response.state, AIState.FALLBACK_RESPONSE)
        self.assertIsNotNone(response.error_message)

    def test_log_file_created(self) -> None:
        self.engine.request(
            task_type=AITaskType.CHAT,
            user_input="Test log entry.",
            context_data={},
            offline_mode=True,
            privacy_sensitive=True,
        )
        log_path = os.path.join(self.base_path, "data", "ai_request_log.jsonl")
        self.assertTrue(os.path.exists(log_path))
        self.assertGreater(os.path.getsize(log_path), 0)


if __name__ == "__main__":
    unittest.main()

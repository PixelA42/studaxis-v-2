"""
Studaxis AI Integration Layer

Centralized AI orchestration between UI pages and inference backends.
This module intentionally uses placeholder model/template configuration
for values that should come from requirements or environment config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Optional


class AITaskType(str, Enum):
    CHAT = "chat"
    CLARIFY = "clarify"
    GRADING = "grading"
    FLASHCARD_EXPLANATION = "flashcard_explanation"
    WEAK_TOPIC_DETECTION = "weak_topic_detection"
    STUDY_RECOMMENDATION = "study_recommendation"
    TEACHER_ANALYTICS_INSIGHT = "teacher_analytics_insight"


class AIState(str, Enum):
    IDLE = "IDLE"
    REQUEST_SENT = "REQUEST_SENT"
    AI_PROCESSING = "AI_PROCESSING"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    DISPLAYED = "DISPLAYED"
    TIMEOUT = "TIMEOUT"
    FALLBACK_RESPONSE = "FALLBACK_RESPONSE"
    ERROR = "ERROR"


class AIExecutionTarget(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class AIConfig:
    # Placeholders are preserved until finalized in requirements/config.
    LOCAL_AI_MODEL: str = "[LOCAL_AI_MODEL]"
    CLOUD_AI_MODEL: str = "[CLOUD_AI_MODEL]"
    EMBEDDING_MODEL: str = "[EMBEDDING_MODEL]"
    AI_TIMEOUT_SECONDS: int = 30
    AI_RESPONSE_MAX_TOKENS: int = 512
    MAX_INPUT_CHARS: int = 6000
    MAX_CONTEXT_ITEMS: int = 12
    MAX_CHAT_HISTORY_ITEMS: int = 20
    LOG_FILE_RELATIVE_PATH: str = os.path.join("data", "ai_request_log.jsonl")
    ENABLE_CLOUD_INFERENCE: bool = True
    ENABLE_LOCAL_INFERENCE: bool = True
    ENABLE_AI_LOGGING: bool = True


@dataclass
class AIRequest:
    task_type: AITaskType
    user_input: str
    context_data: dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    offline_mode: bool = False
    privacy_sensitive: bool = False
    request_id: str = field(default_factory=lambda: f"ai_{int(time.time() * 1000)}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AIResponse:
    text: str
    confidence_score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    citations: list[dict[str, Any]] = field(default_factory=list)
    follow_up_suggestions: list[str] = field(default_factory=list)
    state: AIState = AIState.RESPONSE_RECEIVED
    error_message: Optional[str] = None


@dataclass
class PromptTemplate:
    name: str
    system_instruction: str
    context_rules: str
    response_format_rules: str


class PromptTemplateLibrary:
    """Task-based prompt template selector with placeholders."""

    def __init__(self) -> None:
        self._templates: dict[AITaskType, PromptTemplate] = {
            AITaskType.CHAT: PromptTemplate(
                name="[PROMPT_TEMPLATE_CHAT]",
                system_instruction=(
                    "You are Studaxis AI Tutor. Keep responses educational, "
                    "grounded, and aligned with user-selected difficulty."
                ),
                context_rules=(
                    "Inject subject, active textbook, and recent chat history. "
                    "If context is missing, ask one concise follow-up."
                ),
                response_format_rules=(
                    "Return clear explanation, optional bullet steps, and short recap."
                ),
            ),
            AITaskType.CLARIFY: PromptTemplate(
                name="[PROMPT_TEMPLATE_CLARIFY]",
                system_instruction=(
                    "Provide a concise clarification of the selected phrase."
                ),
                context_rules=(
                    "Use parent answer and active topic context when available."
                ),
                response_format_rules=(
                    "Keep response within 50-100 words when possible."
                ),
            ),
            AITaskType.GRADING: PromptTemplate(
                name="[PROMPT_TEMPLATE_GRADING]",
                system_instruction=(
                    "Grade student free-form answer using rubric and explain strengths and gaps."
                ),
                context_rules=(
                    "Inject expected answer, rubric, question metadata, and difficulty."
                ),
                response_format_rules=(
                    "Return score guidance and actionable feedback with error-specific notes."
                ),
            ),
            AITaskType.FLASHCARD_EXPLANATION: PromptTemplate(
                name="[PROMPT_TEMPLATE_FLASHCARD_EXPLANATION]",
                system_instruction="Explain flashcard answer in simple, exam-relevant language.",
                context_rules="Inject card front/back, chapter, and related examples if available.",
                response_format_rules="Return concise explanation and one memory tip.",
            ),
            AITaskType.WEAK_TOPIC_DETECTION: PromptTemplate(
                name="[PROMPT_TEMPLATE_WEAK_TOPIC_DETECTION]",
                system_instruction="Identify weak topics from performance trends.",
                context_rules="Inject recent quiz scores, streaks, and topic accuracy.",
                response_format_rules="Return prioritized weak topics with reason and confidence.",
            ),
            AITaskType.STUDY_RECOMMENDATION: PromptTemplate(
                name="[PROMPT_TEMPLATE_STUDY_RECOMMENDATION]",
                system_instruction="Generate a practical study plan for the learner.",
                context_rules="Inject weak topics, available study time, and exam timeline.",
                response_format_rules="Return daily/weekly steps and checkpoints.",
            ),
            AITaskType.TEACHER_ANALYTICS_INSIGHT: PromptTemplate(
                name="[PROMPT_TEMPLATE_TEACHER_ANALYTICS]",
                system_instruction="Summarize class-level learning insights for teacher action.",
                context_rules="Inject anonymized student metrics and class trends.",
                response_format_rules="Return top risks, interventions, and follow-up actions.",
            ),
        }

    def select(self, task_type: AITaskType) -> PromptTemplate:
        return self._templates.get(task_type, self._templates[AITaskType.CHAT])


class AIStateMachine:
    """Small state tracker for observability and UI-state mapping."""

    def __init__(self) -> None:
        self._states: dict[str, AIState] = {}

    def set_state(self, request_id: str, state: AIState) -> None:
        self._states[request_id] = state

    def get_state(self, request_id: str) -> AIState:
        return self._states.get(request_id, AIState.IDLE)


class AIEngine:
    """
    Centralized AI integration service.

    UI components should call only this interface:
      request(task_type, user_input, context_data, ...)
    """

    def __init__(self, base_path: str = ".", config: Optional[AIConfig] = None) -> None:
        self.base_path = base_path
        self.config = config or AIConfig()
        self.templates = PromptTemplateLibrary()
        self.state_machine = AIStateMachine()
        self._log_lock = threading.Lock()

    def request(
        self,
        task_type: AITaskType,
        user_input: str,
        context_data: Optional[dict[str, Any]] = None,
        *,
        offline_mode: bool = False,
        privacy_sensitive: bool = False,
        user_id: Optional[str] = None,
    ) -> AIResponse:
        request = AIRequest(
            task_type=task_type,
            user_input=user_input,
            context_data=context_data or {},
            user_id=user_id,
            offline_mode=offline_mode,
            privacy_sensitive=privacy_sensitive,
        )
        self.state_machine.set_state(request.request_id, AIState.REQUEST_SENT)

        try:
            sanitized_input = self._sanitize_input(request.user_input)
            bounded_context = self._sanitize_context(request.context_data)
            template = self.templates.select(request.task_type)
            prompt = self._build_prompt(template, sanitized_input, bounded_context)

            target = self._select_inference_target(request)
            model_name = self._resolve_model_name(target)

            self.state_machine.set_state(request.request_id, AIState.AI_PROCESSING)
            raw_response = self._run_inference_with_timeout(
                target=target,
                model_name=model_name,
                prompt=prompt,
                timeout_seconds=self.config.AI_TIMEOUT_SECONDS,
            )

            parsed = self._parse_response(
                request=request,
                raw_response=raw_response,
                target=target,
                model_name=model_name,
                template=template,
            )
            self._log_request_and_response(request, parsed)
            return parsed
        except TimeoutError:
            self.state_machine.set_state(request.request_id, AIState.TIMEOUT)
            fallback = self._make_fallback_response(
                request,
                "AI response timeout. Returning safe fallback response.",
            )
            self._log_request_and_response(request, fallback)
            return fallback
        except Exception as exc:  # pragma: no cover - defensive path
            self.state_machine.set_state(request.request_id, AIState.ERROR)
            fallback = self._make_fallback_response(
                request,
                f"AI processing failed: {exc}",
            )
            self._log_request_and_response(request, fallback)
            return fallback

    def mark_displayed(self, request_id: str) -> None:
        self.state_machine.set_state(request_id, AIState.DISPLAYED)

    def _sanitize_input(self, user_input: str) -> str:
        text = (user_input or "").strip()
        if len(text) > self.config.MAX_INPUT_CHARS:
            text = text[: self.config.MAX_INPUT_CHARS]
        # Minimal control-character scrubbing.
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
        return text

    def _sanitize_context(self, context_data: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        if not isinstance(context_data, dict):
            return sanitized

        keys = list(context_data.keys())[: self.config.MAX_CONTEXT_ITEMS]
        for key in keys:
            value = context_data.get(key)
            if key == "chat_history" and isinstance(value, list):
                sanitized[key] = value[-self.config.MAX_CHAT_HISTORY_ITEMS :]
            else:
                sanitized[key] = value
        return sanitized

    def _build_prompt(
        self,
        template: PromptTemplate,
        user_input: str,
        context_data: dict[str, Any],
    ) -> str:
        return (
            f"[TEMPLATE_NAME]\n{template.name}\n\n"
            f"[SYSTEM_INSTRUCTION]\n{template.system_instruction}\n\n"
            f"[CONTEXT_RULES]\n{template.context_rules}\n\n"
            f"[RESPONSE_FORMAT_RULES]\n{template.response_format_rules}\n\n"
            f"[CONTEXT_DATA]\n{json.dumps(context_data, ensure_ascii=False)}\n\n"
            f"[USER_INPUT]\n{user_input}\n"
        )

    def _select_inference_target(self, request: AIRequest) -> AIExecutionTarget:
        # Rule 1: Offline always forces local inference.
        if request.offline_mode:
            return AIExecutionTarget.LOCAL
        # Rule 2: Privacy-sensitive tasks prefer local inference.
        if request.privacy_sensitive:
            return AIExecutionTarget.LOCAL
        # Rule 3: Teacher analytics can use cloud when available.
        if request.task_type == AITaskType.TEACHER_ANALYTICS_INSIGHT and self.config.ENABLE_CLOUD_INFERENCE:
            return AIExecutionTarget.CLOUD
        # Rule 4: Grading remains local by policy in MVP.
        if request.task_type == AITaskType.GRADING:
            return AIExecutionTarget.LOCAL
        # Rule 5: Default to local-first unless cloud is explicitly preferred by task.
        return AIExecutionTarget.LOCAL

    def _resolve_model_name(self, target: AIExecutionTarget) -> str:
        if target == AIExecutionTarget.CLOUD:
            return self.config.CLOUD_AI_MODEL
        return self.config.LOCAL_AI_MODEL

    def _run_inference_with_timeout(
        self,
        *,
        target: AIExecutionTarget,
        model_name: str,
        prompt: str,
        timeout_seconds: int,
    ) -> str:
        """
        Simulated inference with timeout handling.
        Intentionally does not call external APIs.
        """
        started = time.time()
        simulated_latency = 0.08 if target == AIExecutionTarget.LOCAL else 0.05
        if simulated_latency > timeout_seconds:
            raise TimeoutError("Inference exceeded timeout.")
        time.sleep(simulated_latency)
        elapsed = time.time() - started
        if elapsed > timeout_seconds:
            raise TimeoutError("Inference exceeded timeout.")

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:10]
        return (
            f"[SIMULATED_{target.value.upper()}_INFERENCE]"
            f" model={model_name} hash={prompt_hash} "
            f"response=This is a placeholder AI response generated by AIEngine."
        )

    def _parse_response(
        self,
        *,
        request: AIRequest,
        raw_response: str,
        target: AIExecutionTarget,
        model_name: str,
        template: PromptTemplate,
    ) -> AIResponse:
        # Keep response content deterministic and compact for UI consistency.
        normalized_text = self._extract_text(raw_response)
        response = AIResponse(
            text=normalized_text,
            confidence_score=0.72,
            metadata={
                "request_id": request.request_id,
                "task_type": request.task_type.value,
                "execution_target": target.value,
                "model_name": model_name,
                "template_name": template.name,
                "timeout_seconds": self.config.AI_TIMEOUT_SECONDS,
                "max_tokens": self.config.AI_RESPONSE_MAX_TOKENS,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            citations=self._extract_citations(request.context_data),
            follow_up_suggestions=self._generate_follow_ups(request.task_type),
            state=AIState.RESPONSE_RECEIVED,
        )
        self.state_machine.set_state(request.request_id, AIState.RESPONSE_RECEIVED)
        return response

    def _extract_text(self, raw_response: str) -> str:
        if "response=" in raw_response:
            return raw_response.split("response=", 1)[1].strip()
        return raw_response.strip()

    def _extract_citations(self, context_data: dict[str, Any]) -> list[dict[str, Any]]:
        sources = context_data.get("sources", [])
        if not isinstance(sources, list):
            return []
        citations: list[dict[str, Any]] = []
        for src in sources[:3]:
            if isinstance(src, dict):
                citations.append(
                    {
                        "source": src.get("source", "[SOURCE_UNKNOWN]"),
                        "chapter": src.get("chapter", "[CHAPTER_UNKNOWN]"),
                        "page": src.get("page", "[PAGE_UNKNOWN]"),
                    }
                )
        return citations

    def _generate_follow_ups(self, task_type: AITaskType) -> list[str]:
        if task_type == AITaskType.GRADING:
            return [
                "Would you like a model answer for comparison?",
                "Should I generate two practice questions on this topic?",
            ]
        if task_type in (AITaskType.CHAT, AITaskType.CLARIFY):
            return [
                "Do you want a simpler explanation?",
                "Should I provide a quick practice question?",
            ]
        return ["Would you like a concise action plan next?"]

    def _make_fallback_response(self, request: AIRequest, reason: str) -> AIResponse:
        self.state_machine.set_state(request.request_id, AIState.FALLBACK_RESPONSE)
        return AIResponse(
            text=(
                "I could not complete that AI request right now. "
                "Please retry, or continue with offline study resources."
            ),
            confidence_score=0.2,
            metadata={
                "request_id": request.request_id,
                "task_type": request.task_type.value,
                "fallback_reason": reason,
                "timeout_seconds": self.config.AI_TIMEOUT_SECONDS,
            },
            follow_up_suggestions=[
                "Retry now",
                "Switch to a shorter prompt",
            ],
            state=AIState.FALLBACK_RESPONSE,
            error_message=reason,
        )

    def _log_request_and_response(self, request: AIRequest, response: AIResponse) -> None:
        if not self.config.ENABLE_AI_LOGGING:
            return
        log_path = os.path.join(self.base_path, self.config.LOG_FILE_RELATIVE_PATH)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": {
                "request_id": request.request_id,
                "task_type": request.task_type.value,
                "user_id": request.user_id,
                "offline_mode": request.offline_mode,
                "privacy_sensitive": request.privacy_sensitive,
                "input_preview": request.user_input[:250],
            },
            "response": {
                "state": response.state.value,
                "confidence_score": response.confidence_score,
                "model_name": response.metadata.get("model_name"),
                "execution_target": response.metadata.get("execution_target"),
                "text_preview": response.text[:250],
                "error_message": response.error_message,
            },
        }

        with self._log_lock:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

from __future__ import annotations

import json

from pydantic import ValidationError

from app.config import get_settings
from app.core.online_tests import provider_calls_disabled_under_pytest
from app.guardrails.prompts import TOPIC_CLASSIFIER_PROMPT
from app.guardrails.schemas import GuardrailParseError, GuardrailProviderError, TopicScopeDecision


class TopicClassifier:
    async def classify(self, text: str) -> TopicScopeDecision:
        raise NotImplementedError


class GemmaTopicClassifier(TopicClassifier):
    async def classify(self, text: str) -> TopicScopeDecision:
        settings = get_settings()
        keys = [settings.google_api_key.strip()] if settings.google_api_key.strip() else []
        if settings.google_api_keys:
            keys.extend(key.strip() for key in settings.google_api_keys.replace(";", ",").split(",") if key.strip())
        if not keys:
            raise GuardrailProviderError("Gemma topic classifier needs GOOGLE_API_KEY or GOOGLE_API_KEYS")

        prompt = TOPIC_CLASSIFIER_PROMPT.replace("{{USER_MESSAGE}}", text)
        last_error: Exception | None = None
        for api_key in keys:
            try:
                raw_text = _gemini_generate_json(api_key, settings.topic_classifier_model, prompt)
                return TopicScopeDecision.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise GuardrailParseError("Gemma topic classifier returned invalid JSON") from exc
            except Exception as exc:
                last_error = exc
                continue
        raise GuardrailProviderError("Gemma topic classifier request failed") from last_error


def _gemini_generate_json(api_key: str, model: str, prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    raise GuardrailProviderError("Gemma topic classifier returned empty response")


def should_skip_provider_calls() -> bool:
    return provider_calls_disabled_under_pytest()

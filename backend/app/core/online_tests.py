from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}


def online_llm_tests_enabled() -> bool:
    return os.environ.get("ONLINE_LLM_TESTS", "").strip().lower() in _TRUE_VALUES


def provider_calls_disabled_under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ and not online_llm_tests_enabled()


def strict_online_llm_test_mode() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ and online_llm_tests_enabled()

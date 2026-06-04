from __future__ import annotations

import json
import copy
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests
from django.conf import settings

from .schemas import LLM_EXTRACTION_SCHEMA


logger = logging.getLogger(__name__)


class LLMProviderUnavailable(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


class LLMRateLimitError(LLMProviderError):
    def __init__(self, message: str, *, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LLMTransientProviderError(LLMProviderError):
    pass


def _extract_retry_after_seconds(response: requests.Response) -> float | None:
    header_value = response.headers.get("Retry-After")
    if header_value:
        try:
            return max(0.0, float(header_value))
        except (TypeError, ValueError):
            pass

    try:
        body = response.json()
    except ValueError:
        body = {}
    message = str(((body.get("error") or {}) if isinstance(body, dict) else {}).get("message") or "")
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return max(0.0, float(match.group(1)))
    except (TypeError, ValueError):
        return None


def _extract_json_object(text: str) -> dict[str, Any]:
    raw_text = str(text or "").strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()

    try:
        parsed = _loads_json_with_minimal_repairs(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0:
            recovered = _recover_single_string_payload(raw_text)
            if recovered:
                return recovered
            raise LLMProviderError(f"LLM JSON parse failed; response_prefix={raw_text[:240]!r}")
        candidate_text = raw_text[start : end + 1] if end > start else raw_text[start:]
        try:
            parsed = _loads_json_with_minimal_repairs(candidate_text)
        except json.JSONDecodeError as exc:
            recovered = _recover_single_string_payload(candidate_text)
            if recovered:
                return recovered
            raise LLMProviderError(f"LLM JSON parse failed; response_prefix={raw_text[:240]!r}") from exc

    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM JSON response must be an object.")
    return parsed


def _loads_json_with_minimal_repairs(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # LLMs sometimes emit invalid JSON escapes, especially for French
        # apostrophes: "d\'experience". JSON valid escapes are limited to
        # \" \\ \/ \b \f \n \r \t and \uXXXX, so remove only backslashes
        # before non-JSON escape characters after strict parsing has failed.
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', "", value)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            control_repaired = _escape_control_chars_inside_json_strings(repaired)
            if control_repaired == repaired:
                raise
            return json.loads(control_repaired)


def _escape_control_chars_inside_json_strings(value: str) -> str:
    """
    Escape literal control characters emitted inside JSON strings.

    Gemini occasionally returns a JSON object where a string value contains a
    literal newline instead of "\\n". Strict JSON rejects that with
    "Invalid control character". This repair keeps structure outside strings
    untouched and only escapes control characters while inside a string.
    """
    output: list[str] = []
    in_string = False
    escaped = False

    for char in str(value or ""):
        if escaped:
            output.append(char)
            escaped = False
            continue

        if char == "\\" and in_string:
            output.append(char)
            escaped = True
            continue

        if char == '"':
            output.append(char)
            in_string = not in_string
            continue

        if in_string:
            if char == "\n":
                output.append("\\n")
                continue
            if char == "\r":
                output.append("\\r")
                continue
            if char == "\t":
                output.append("\\t")
                continue
            if ord(char) < 32:
                output.append(" ")
                continue

        output.append(char)

    return "".join(output)


def _recover_single_string_payload(value: str) -> dict[str, Any]:
    """
    Recover action responses where the provider produced one large JSON string
    field with invalid escaping. This is intentionally narrow: it only supports
    known assistant payload fields and returns the raw text as content.
    """
    text = str(value or "")
    for key in ("optimization_markdown", "analysis_markdown", "summary_markdown", "cover_letter_markdown", "interview_markdown"):
        marker = f'"{key}"'
        key_index = text.find(marker)
        if key_index < 0:
            continue

        colon_index = text.find(":", key_index + len(marker))
        if colon_index < 0:
            continue

        quote_index = text.find('"', colon_index + 1)
        if quote_index < 0:
            continue

        raw_value = text[quote_index + 1 :]
        for end_marker in ('",\n  "next_step"', '",\n "next_step"', '", "next_step"'):
            marker_index = raw_value.find(end_marker)
            if marker_index >= 0:
                raw_value = raw_value[:marker_index]
                break
        else:
            raw_value = raw_value.rstrip()
            if raw_value.endswith('"}'):
                raw_value = raw_value[:-2]
            elif raw_value.endswith('"'):
                raw_value = raw_value[:-1]

        if not raw_value.strip():
            continue

        content = _decode_loose_json_string(raw_value)
        next_step = ""
        next_step_match = re.search(r'"next_step"\s*:\s*"((?:\\.|[^"\\])*)"', text, flags=re.DOTALL)
        if next_step_match:
            next_step = _decode_loose_json_string(next_step_match.group(1))
        return {key: content.strip(), "next_step": next_step.strip()}

    return {}


def _decode_loose_json_string(value: str) -> str:
    repaired = re.sub(r'\\(?!["\\/bfnrtu])', "", str(value or ""))
    try:
        return json.loads(f'"{repaired}"')
    except json.JSONDecodeError:
        return (
            repaired
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )


def _schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a Gemini responseSchema-compatible subset of JSON Schema."""
    cleaned = copy.deepcopy(schema)

    def strip_unsupported(value: Any) -> Any:
        if isinstance(value, dict):
            value.pop("additionalProperties", None)
            raw_type = value.get("type")
            if isinstance(raw_type, list):
                non_null_types = [item for item in raw_type if item != "null"]
                if len(non_null_types) == 1 and "null" in raw_type:
                    value["type"] = non_null_types[0]
                    value["nullable"] = True
            return {key: strip_unsupported(child) for key, child in value.items()}
        if isinstance(value, list):
            return [strip_unsupported(item) for item in value]
        return value

    return strip_unsupported(cleaned)


class LLMProvider(Protocol):
    provider_name: str
    model: str

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GeminiProvider:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    temperature: float
    max_output_tokens: int

    provider_name: str = "gemini"

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise LLMProviderUnavailable("GEMINI_API_KEY is not configured.")

        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        if schema:
            payload["generationConfig"]["responseSchema"] = _schema_for_gemini(schema)

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise LLMProviderError(f"Gemini request failed: {exc.__class__.__name__}") from exc

        if response.status_code >= 400:
            logger.warning("Gemini request failed status=%s body=%s", response.status_code, response.text[:500])
            if response.status_code == 429:
                retry_after = _extract_retry_after_seconds(response)
                message = "Gemini quota/rate limit exceeded (HTTP 429)"
                if retry_after is not None:
                    message = f"{message}; retry_after_seconds={retry_after:.0f}"
                raise LLMRateLimitError(message, retry_after_seconds=retry_after)
            if response.status_code in {500, 502, 503, 504}:
                raise LLMTransientProviderError(f"Gemini transient failure HTTP {response.status_code}")
            raise LLMProviderError(f"Gemini returned HTTP {response.status_code}")

        try:
            data = response.json()
            candidate = data["candidates"][0]
            finish_reason = str(candidate.get("finishReason") or "unknown")
            parts = candidate["content"].get("parts", [])
            text = "\n".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))
            if not text.strip():
                raise LLMProviderError(f"Gemini response had no text part; finishReason={finish_reason}")
            if finish_reason and finish_reason.upper() != "STOP":
                logger.warning(
                    "Gemini response finishReason=%s text_prefix=%r",
                    finish_reason,
                    text[:180],
                )
            parsed = _extract_json_object(text)
        except LLMProviderError:
            raise
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderError("Gemini response did not contain valid JSON.") from exc

        return parsed


@dataclass(frozen=True)
class OllamaProvider:
    model: str
    base_url: str
    timeout_seconds: float
    temperature: float
    max_output_tokens: int
    keep_alive: str = ""

    provider_name: str = "ollama"

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.model:
            raise LLMProviderUnavailable("OLLAMA_MODEL is not configured.")

        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": (
                f"{prompt}\n\n"
                "Return only one valid JSON object. Do not include markdown fences, commentary, or prose."
            ),
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_output_tokens,
            },
        }
        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive
        if schema:
            payload["format"] = schema
        else:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise LLMTransientProviderError(f"Ollama request failed: {exc.__class__.__name__}") from exc

        if response.status_code >= 400:
            body = response.text[:500]
            logger.warning("Ollama request failed status=%s body=%s", response.status_code, body)
            if response.status_code in {500, 502, 503, 504}:
                raise LLMTransientProviderError(f"Ollama transient failure HTTP {response.status_code}")
            raise LLMProviderError(f"Ollama returned HTTP {response.status_code}")

        try:
            data = response.json()
            text = str(data.get("response") or "")
            if not text.strip():
                raise LLMProviderError("Ollama response had no text payload.")
            return _extract_json_object(text)
        except LLMProviderError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderError("Ollama response did not contain valid JSON.") from exc


@dataclass(frozen=True)
class FallbackLLMProvider:
    providers: tuple[LLMProvider, ...]
    max_retries: int
    retry_delay_seconds: float
    retry_backoff_factor: float

    provider_name: str = "fallback"
    model: str = "provider-chain"

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.providers:
            raise LLMProviderUnavailable("No LLM providers are configured.")

        errors: list[str] = []
        saw_rate_limit = False
        shortest_retry_after: float | None = None
        for provider_index, provider in enumerate(self.providers):
            attempts = max(1, int(self.max_retries) + 1)
            for attempt in range(attempts):
                try:
                    if provider_index or attempt:
                        logger.info(
                            "LLM provider attempt provider=%s model=%s attempt=%s",
                            getattr(provider, "provider_name", ""),
                            getattr(provider, "model", ""),
                            attempt + 1,
                        )
                    return provider.generate_json(prompt, schema=schema)
                except LLMRateLimitError as exc:
                    saw_rate_limit = True
                    if exc.retry_after_seconds is not None:
                        shortest_retry_after = (
                            exc.retry_after_seconds
                            if shortest_retry_after is None
                            else min(shortest_retry_after, exc.retry_after_seconds)
                        )
                    errors.append(
                        f"{getattr(provider, 'provider_name', 'unknown')}:{getattr(provider, 'model', '')}:"
                        f"{exc.__class__.__name__}:{exc}"
                    )
                    # Quota exhaustion is not fixed by immediately retrying the same provider.
                    break
                except LLMTransientProviderError as exc:
                    errors.append(
                        f"{getattr(provider, 'provider_name', 'unknown')}:{getattr(provider, 'model', '')}:"
                        f"{exc.__class__.__name__}:{exc}"
                    )
                    if attempt + 1 < attempts:
                        delay = self.retry_delay_seconds * (self.retry_backoff_factor ** attempt)
                        if delay > 0:
                            time.sleep(delay)
                        continue
                    break
                except LLMProviderUnavailable as exc:
                    errors.append(
                        f"{getattr(provider, 'provider_name', 'unknown')}:{getattr(provider, 'model', '')}:"
                        f"{exc.__class__.__name__}:{exc}"
                    )
                    break

        compact_errors = " | ".join(errors[-4:])
        if saw_rate_limit:
            message = "All configured cloud LLM providers are rate-limited"
            if shortest_retry_after is not None:
                message = f"{message}; retry_after_seconds={shortest_retry_after:.0f}"
            if compact_errors:
                message = f"{message}: {compact_errors}"
            raise LLMRateLimitError(message, retry_after_seconds=shortest_retry_after)

        raise LLMTransientProviderError("All LLM providers failed: " + compact_errors)


class DisabledLLMProvider:
    provider_name = "disabled"
    model = ""

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        raise LLMProviderUnavailable("LLM enrichment is disabled.")


def get_llm_provider() -> LLMProvider:
    if not bool(getattr(settings, "LLM_ENRICHMENT_ENABLED", False)):
        return DisabledLLMProvider()

    provider = str(getattr(settings, "LLM_PROVIDER", "gemini") or "gemini").strip().lower()
    providers = _build_provider_chain(provider)
    if len(providers) == 1:
        return providers[0]

    return FallbackLLMProvider(
        providers=tuple(providers),
        max_retries=int(getattr(settings, "LLM_PROVIDER_MAX_RETRIES", 1)),
        retry_delay_seconds=float(getattr(settings, "LLM_PROVIDER_RETRY_DELAY_SECONDS", 5.0)),
        retry_backoff_factor=float(getattr(settings, "LLM_PROVIDER_RETRY_BACKOFF_FACTOR", 2.0)),
    )


def _gemini_provider(model: str | None = None) -> GeminiProvider:
    return GeminiProvider(
        api_key=str(getattr(settings, "GEMINI_API_KEY", "") or "").strip(),
        model=str(model or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash"),
        base_url=str(getattr(settings, "GEMINI_API_BASE_URL", "") or "").rstrip("/"),
        timeout_seconds=float(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 20.0)),
        temperature=float(getattr(settings, "GEMINI_TEMPERATURE", 0.1)),
        max_output_tokens=int(getattr(settings, "GEMINI_MAX_OUTPUT_TOKENS", 2500)),
    )


def _ollama_provider() -> OllamaProvider:
    return OllamaProvider(
        model=str(getattr(settings, "OLLAMA_MODEL", "") or "").strip(),
        base_url=str(getattr(settings, "OLLAMA_BASE_URL", "") or "http://host.docker.internal:11434").rstrip("/"),
        timeout_seconds=float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 45.0)),
        temperature=float(getattr(settings, "OLLAMA_TEMPERATURE", 0.0)),
        max_output_tokens=int(getattr(settings, "OLLAMA_MAX_OUTPUT_TOKENS", 1200)),
        keep_alive=str(getattr(settings, "OLLAMA_KEEP_ALIVE", "") or "").strip(),
    )


def _configured_fallback_models() -> list[str]:
    raw = str(getattr(settings, "GEMINI_FALLBACK_MODELS", "") or "").strip()
    if not raw:
        return []
    primary = str(getattr(settings, "GEMINI_MODEL", "") or "").strip()
    models = []
    for item in raw.split(","):
        model = item.strip()
        if model and model != primary and model not in models:
            models.append(model)
    return models


def _build_provider_chain(provider: str) -> list[LLMProvider]:
    if provider == "gemini":
        chain: list[LLMProvider] = [_gemini_provider()]
        chain.extend(_gemini_provider(model) for model in _configured_fallback_models())
        if bool(getattr(settings, "OLLAMA_FALLBACK_ENABLED", False)):
            chain.append(_ollama_provider())
        return chain

    if provider == "ollama":
        return [_ollama_provider()]

    if provider in {"gemini_ollama", "hybrid"}:
        chain = [_gemini_provider()]
        chain.extend(_gemini_provider(model) for model in _configured_fallback_models())
        chain.append(_ollama_provider())
        return chain

    raise LLMProviderUnavailable(f"Unsupported LLM_PROVIDER: {provider}")


def generate_extraction_json(prompt: str, *, provider: LLMProvider | None = None) -> dict[str, Any]:
    llm_provider = provider or get_llm_provider()
    return llm_provider.generate_json(prompt, schema=LLM_EXTRACTION_SCHEMA)

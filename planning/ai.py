"""Bounded, opt-in NVIDIA transport. No alternate provider or automatic retries."""

import hashlib
import json
import os
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from django.conf import settings
from django.db import transaction, OperationalError
from django.db.models import F, Sum
from django.utils import timezone
from .models import AIQuotaLedger, AIRequestLog

KEY_NAMES = ("NVIDIA_API_KEY", "NVDIA_API_KEY")
PROMPT_VERSION = "evidence-drafting-v1"


class AIUnavailable(ValueError):
    def __init__(self, message, metadata=None):
        super().__init__(message)
        self.metadata = metadata or {}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def urlopen(request, timeout):
    # Preserve configured proxy/CA trust, but never forward a credential through a redirect.
    return build_opener(NoRedirect()).open(request, timeout=timeout)


def key_binding():
    for name in KEY_NAMES:
        if os.environ.get(name):
            return name, os.environ[name]
    return "", None


def local_status():
    name, key = key_binding()
    return {
        "configured": bool(key),
        "binding_name": name,
        "provider": "NVIDIA",
        "model": settings.APASA_AI_MODEL,
        "allowed": settings.APASA_AI_MODEL in settings.APASA_AI_ALLOWED_MODELS,
        "requests_per_minute": settings.APASA_AI_RPM,
        "requests_per_day": settings.APASA_AI_RPD,
        "token_budget_per_minute": settings.APASA_AI_TPM,
        "max_output_tokens": settings.APASA_AI_MAX_OUTPUT_TOKENS,
        "note": "NVIDIA controls model access, quotas and credits. Local limits are application safeguards, not a free-service guarantee. APASA never switches providers or models automatically.",
    }


@transaction.atomic
def reserve(key, model, estimated_tokens, user=None, operation="generate"):
    digest = hashlib.sha256((key + "\0" + model).encode()).hexdigest()
    ledger, _ = AIQuotaLedger.objects.get_or_create(fingerprint=digest)
    # A write acquires a serialization lock on SQLite as well as PostgreSQL.
    AIQuotaLedger.objects.filter(pk=ledger.pk).update(touch=F("touch") + 1)
    now = timezone.now()
    entries = AIRequestLog.objects.filter(ledger=ledger)
    minute = entries.filter(created_at__gte=now - timedelta(minutes=1))
    if minute.count() >= settings.APASA_AI_RPM:
        raise AIUnavailable(
            "The local per-minute AI request limit has been reached. Try again after a minute; no request was sent."
        )
    if (
        entries.filter(created_at__gte=now - timedelta(hours=24)).count()
        >= settings.APASA_AI_RPD
    ):
        raise AIUnavailable(
            "The local rolling 24-hour AI limit has been reached. Local drafting remains available."
        )
    reserved = minute.aggregate(total=Sum("estimated_tokens"))["total"] or 0
    if reserved + estimated_tokens > settings.APASA_AI_TPM:
        raise AIUnavailable(
            "The local token budget is temporarily exhausted. No provider request was sent."
        )
    return AIRequestLog.objects.create(
        ledger=ledger,
        user=user,
        model=model,
        operation=operation,
        estimated_tokens=estimated_tokens,
        status="reserved",
    )


def request_api(path, payload=None, user=None, operation="generate"):
    _, key = key_binding()
    if not key:
        raise AIUnavailable(
            "No API key is configured here. Set NVIDIA_API_KEY (or NVDIA_API_KEY) in your environment or ignored .env file; local drafting still works."
        )
    base_url = settings.NVIDIA_BASE_URL.rstrip("/")
    # Restrict credential destinations; redirects are denied below as well.
    if base_url != "https://integrate.api.nvidia.com/v1":
        raise AIUnavailable(
            "NVIDIA_BASE_URL must be https://integrate.api.nvidia.com/v1. No request was sent."
        )
    model = settings.APASA_AI_MODEL
    if model not in settings.APASA_AI_ALLOWED_MODELS:
        raise AIUnavailable(
            "The configured model is not in the permitted model list. No alternative model was tried."
        )
    encoded = json.dumps(payload).encode() if payload is not None else None
    estimated = (
        len(encoded) + settings.APASA_AI_MAX_OUTPUT_TOKENS + 512 if encoded else 0
    )
    try:
        record = reserve(key, model, estimated, user, operation)
    except OperationalError:
        raise AIUnavailable(
            "AI request accounting is not ready or is busy. Apply migrations or retry shortly; no provider request was sent."
        )
    request = Request(
        base_url + "/" + path,
        data=encoded,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read(512000))
        if not isinstance(result, dict):
            raise ValueError("Invalid provider response")
        usage = result.get("usage") or {}
        if not isinstance(usage, dict):
            raise ValueError("Invalid usage metadata")
        record.status = "completed"
        record.usage = {
            k: usage[k]
            for k in ["prompt_tokens", "completion_tokens", "total_tokens"]
            if k in usage
        }
        record.save(update_fields=["status", "usage"])
        return result, {
            "model": model,
            "provider": "NVIDIA",
            "prompt_version": PROMPT_VERSION,
            "usage": record.usage,
            "request_log_id": record.pk,
        }
    except HTTPError as exc:
        code = "provider_error"
        try:
            body = json.loads(exc.read(64000))
            raw = body.get("error", {}).get("code") or body.get("error", {}).get("type")
            if raw in {
                "invalid_api_key",
                "insufficient_quota",
                "rate_limit_exceeded",
                "model_not_found",
                "permission_denied",
                "unsupported_country_region_territory",
            }:
                code = raw
        except (ValueError, AttributeError):
            pass
        if code == "provider_error":
            code = {
                401: "invalid_api_key",
                403: "permission_denied",
                429: "rate_limit_exceeded",
            }.get(exc.code, code)
        record.status = code
        record.save(update_fields=["status"])
        explanations = {
            "invalid_api_key": "The API key was rejected. Check the local key and project permissions.",
            "insufficient_quota": "NVIDIA reports insufficient quota or credits. Check your NVIDIA account allowance.",
            "rate_limit_exceeded": "The provider rate limit was reached, possibly including other applications using this key.",
            "model_not_found": "The selected model is unavailable to this NVIDIA account. No alternative or higher-cost model was tried.",
            "permission_denied": "This NVIDIA account does not permit the requested operation.",
        }
        raise AIUnavailable(
            explanations.get(
                code,
                "The provider rejected the request. Check model access and NVIDIA account settings; no automatic retry was made.",
            ),
            {
                "provider_call": True,
                "request_log_id": record.pk,
                "model": model,
                "error_code": code,
            },
        )
    except (URLError, ValueError, KeyError, TimeoutError, OSError):
        record.status = "unavailable"
        record.save(update_fields=["status"])
        raise AIUnavailable(
            "The AI service could not be reached or returned an invalid response. Local factual drafting remains available.",
            {
                "provider_call": True,
                "request_log_id": record.pk,
                "model": model,
                "error_code": "unavailable",
            },
        )


def check_access(user=None):
    result, metadata = request_api("models", user=user, operation="check_access")
    ids = {item.get("id") for item in result.get("data", []) if isinstance(item, dict)}
    return {
        "model": settings.APASA_AI_MODEL,
        "model_available": settings.APASA_AI_MODEL in ids,
        "permitted_available_models": sorted(
            ids.intersection(settings.APASA_AI_ALLOWED_MODELS)
        ),
        "note": "This read-only model listing confirms visibility only, not generation quota, available credits or free billing.",
    }


def generate(instructions, facts, user=None):
    if len(facts.encode()) > 24000:
        raise AIUnavailable(
            "This evidence context is too large for the bounded AI request. Use the factual local draft."
        )
    payload = {
        "model": settings.APASA_AI_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": facts},
        ],
        "max_tokens": settings.APASA_AI_MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
        "stream": False,
    }
    result, metadata = request_api("chat/completions", payload, user)
    choices = result.get("choices")
    choice = (
        choices[0]
        if isinstance(choices, list) and choices and isinstance(choices[0], dict)
        else {}
    )
    if choice.get("finish_reason") == "length":
        AIRequestLog.objects.filter(pk=metadata["request_log_id"]).update(
            status="incomplete"
        )
        raise AIUnavailable(
            "The provider reached the output limit. The factual local draft was retained; no automatic retry was made.",
            dict(metadata, provider_call=True),
        )
    message = choice.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    # Do not expose private reasoning/reasoning_content as a user answer.
    text = (
        content.strip()
        if isinstance(content, str) and choice.get("finish_reason") == "stop"
        else ""
    )
    if not text:
        AIRequestLog.objects.filter(pk=metadata["request_log_id"]).update(
            status="invalid_output"
        )
        raise AIUnavailable(
            "The provider returned no usable explanation. The factual local draft was retained.",
            dict(metadata, provider_call=True),
        )
    metadata["facts_sha256"] = hashlib.sha256(facts.encode()).hexdigest()
    return text[:16000], metadata

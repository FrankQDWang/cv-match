from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from seektalent.config import load_process_env


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class ProbeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    age: int
    email: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe Bailian structured output support for a model on the OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--model",
        default="deepseek-v3.2",
        help="Model name on Bailian. Default: deepseek-v3.2",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL,
        help="OpenAI-compatible base URL. Default: OPENAI_BASE_URL or Bailian Beijing endpoint.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"),
        help="API key. Default: DASHSCOPE_API_KEY or OPENAI_API_KEY",
    )
    parser.add_argument(
        "--mode",
        choices=("json_object", "json_schema", "both"),
        default="both",
        help="Which response_format mode to probe. Default: both",
    )
    parser.add_argument(
        "--enable-thinking",
        action="store_true",
        help="Send enable_thinking=true. Default is false.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds. Default: 30",
    )
    return parser


def make_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Return JSON only. Do not include markdown fences, prose, or commentary. "
                "Extract the fields name, age, and email."
            ),
        },
        {
            "role": "user",
            "content": (
                "My name is Alex Brown, I am 34 years old, and my email is alexbrown@example.com."
            ),
        },
    ]


def json_schema_payload() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "profile_probe",
            "strict": True,
            "schema": ProbeOutput.model_json_schema(),
        },
    }


def build_request_body(*, model: str, mode: str, enable_thinking: bool) -> dict[str, Any]:
    response_format: dict[str, Any]
    if mode == "json_object":
        response_format = {"type": "json_object"}
    else:
        response_format = json_schema_payload()
    body: dict[str, Any] = {
        "model": model,
        "messages": make_messages(),
        "response_format": response_format,
    }
    if enable_thinking:
        body["enable_thinking"] = True
    return body


def extract_message_content(payload: dict[str, Any]) -> str | None:
    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return "".join(parts) if parts else None
    return None


def probe_once(
    *,
    client: httpx.Client,
    base_url: str,
    api_key: str,
    model: str,
    mode: str,
    enable_thinking: bool,
) -> tuple[dict[str, Any], bool]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = build_request_body(model=model, mode=mode, enable_thinking=enable_thinking)
    result: dict[str, Any] = {
        "mode": mode,
        "request": body,
    }
    try:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    except httpx.HTTPError as exc:
        result["transport_error"] = f"{type(exc).__name__}: {exc}"
        return result, False

    result["http_status"] = response.status_code
    if response.status_code != 200:
        try:
            result["error"] = response.json()
        except json.JSONDecodeError:
            result["error_text"] = response.text
        return result, False

    payload = response.json()
    content = extract_message_content(payload)
    result["response_id"] = payload.get("id")
    result["usage"] = payload.get("usage")
    result["content"] = content
    if content is None:
        result["parse_error"] = "choices[0].message.content is missing or not a string."
        return result, False

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"
        return result, False

    result["parsed_json"] = parsed
    try:
        validated = ProbeOutput.model_validate(parsed)
    except ValidationError as exc:
        result["validation_error"] = exc.errors(include_url=False)
        return result, False

    result["validated"] = validated.model_dump(mode="json")
    return result, True


def main() -> int:
    load_process_env()
    args = build_parser().parse_args()
    if not args.api_key:
        print("Missing API key. Set DASHSCOPE_API_KEY or pass --api-key.", file=sys.stderr)
        return 2

    modes = ["json_object", "json_schema"] if args.mode == "both" else [args.mode]
    results: list[dict[str, Any]] = []
    all_ok = True
    with httpx.Client(timeout=args.timeout) as client:
        for mode in modes:
            result, ok = probe_once(
                client=client,
                base_url=args.base_url,
                api_key=args.api_key,
                model=args.model,
                mode=mode,
                enable_thinking=args.enable_thinking,
            )
            results.append(result)
            all_ok = all_ok and ok

    print(json.dumps({"model": args.model, "base_url": args.base_url, "results": results}, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

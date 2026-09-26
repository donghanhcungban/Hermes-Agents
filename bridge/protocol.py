"""Strict transport/CLI boundaries. No network, execution, or automatic repair."""
from __future__ import annotations
import json
import math


def _nonfinite(_):
    raise ValueError("Non-finite JSON numbers are not supported")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not supported")
        result[key] = value
    return result


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite JSON numbers are not supported")
    return result


def strict_json(text):
    return json.loads(text, parse_constant=_nonfinite, parse_float=_finite_float, object_pairs_hook=_unique)


def validate_chat(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 2048:
        raise ValueError("messages must contain 1..2048 entries")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {
            "system", "developer", "user", "assistant", "tool", "function"
        }:
            raise ValueError("Invalid message role or shape")
        if not isinstance(message.get("content"), (str, list, type(None))):
            raise ValueError("Invalid message content")
    if "stream" in payload and not isinstance(payload["stream"], bool):
        raise ValueError("stream must be boolean")
    if "model" in payload and (not isinstance(payload["model"], str) or not payload["model"].strip() or len(payload["model"]) > 256):
        raise ValueError("model must be a non-empty string up to 256 characters")
    tools = payload.get("tools", [])
    if tools is not None and (not isinstance(tools, list) or len(tools) > 128):
        raise ValueError("tools must contain at most 128 entries")
    names = set()
    for tool in tools or []:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict) or tool.get("type") != "function":
            raise ValueError("Only function tools are supported")
        name = function.get("name")
        if not isinstance(name, str) or not name or len(name) > 256 or name in names:
            raise ValueError("Tool names must be unique non-empty strings")
        names.add(name)
    choice = payload.get("tool_choice")
    if isinstance(choice, dict):
        fn = choice.get("function")
        if choice.get("type") != "function" or not isinstance(fn, dict) or fn.get("name") not in names:
            raise ValueError("Invalid forced tool choice")
    elif choice is not None and choice not in ("none", "auto", "required"):
        raise ValueError("Invalid tool_choice")
    if choice == "required" and not names:
        raise ValueError("tool_choice required needs an offered tool")
    return payload


def normalize_tool_calls(calls, tools, tool_choice=None, *, string_arguments=False):
    """Validate the offered-tool boundary; domain argument schemas are checked by Hermes."""
    if not isinstance(calls, list) or len(calls) > 128:
        raise ValueError("Invalid tool call list")
    allowed = {tool["name"] for tool in tools}
    if tool_choice == "none" and calls:
        raise ValueError("Tool calls are disabled for this request")
    if tool_choice == "required" and not calls:
        raise ValueError("A tool call was required")
    forced = None
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function")
        forced = function.get("name") if isinstance(function, dict) else None
        if not isinstance(forced, str) or forced not in allowed or not calls:
            raise ValueError("Invalid or unfulfilled tool choice")
    result = []
    for call in calls:
        if not isinstance(call, dict):
            raise ValueError("Invalid tool call")
        name, args = call.get("name"), call.get("arguments")
        if not isinstance(name, str) or name not in allowed:
            raise ValueError("Tool not offered by Hermes")
        if forced is not None and name != forced:
            raise ValueError("Tool call does not match the requested tool")
        if string_arguments and isinstance(args, str):
            args = strict_json(args)
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")
        encoded = json.dumps(args, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > 250000:
            raise ValueError("Tool arguments exceed size limit")
        result.append({"name": name, "arguments": args})
    return result

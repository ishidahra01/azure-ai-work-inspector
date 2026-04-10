from __future__ import annotations

import logging
import os
from pathlib import Path

import agent_framework as agent_framework_module
from dotenv import load_dotenv
from agent_framework_claude import ClaudeAgent


if not hasattr(agent_framework_module, "BaseContextProvider") and hasattr(agent_framework_module, "ContextProvider"):
    agent_framework_module.BaseContextProvider = agent_framework_module.ContextProvider
if not hasattr(agent_framework_module, "ContextProvider") and hasattr(agent_framework_module, "BaseContextProvider"):
    agent_framework_module.ContextProvider = agent_framework_module.BaseContextProvider
if not hasattr(agent_framework_module, "BaseHistoryProvider") and hasattr(agent_framework_module, "HistoryProvider"):
    agent_framework_module.BaseHistoryProvider = agent_framework_module.HistoryProvider
if not hasattr(agent_framework_module, "HistoryProvider") and hasattr(agent_framework_module, "BaseHistoryProvider"):
    agent_framework_module.HistoryProvider = agent_framework_module.BaseHistoryProvider

from azure.ai.agentserver.agentframework import from_agent_framework


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGGER = logging.getLogger("analysis_artifact_agent")
DEFAULT_PORT = 8088
FOUNDRY_MODEL_PIN_KEYS = [
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
]
VALID_EFFORT_LEVELS = {"low", "medium", "high", "max", "auto"}
BUILTIN_TOOLS = [
    "Read",
    "Glob",
    "Grep",
]


def _first_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _resolve_port(default: int = DEFAULT_PORT) -> int:
    raw = os.getenv("PORT")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("Invalid PORT=%r. Falling back to %s.", raw, default)
        return default


def _resolve_effort_level(default: str = "high") -> str:
    raw = os.getenv("CLAUDE_EFFORT") or os.getenv("CLAUDE_CODE_EFFORT_LEVEL") or default
    normalized = raw.strip().lower()
    if normalized == "middle":
        normalized = "medium"
    if normalized not in VALID_EFFORT_LEVELS:
        LOGGER.warning(
            "Invalid effort level %r. Falling back to %s. Valid values are: %s.",
            raw,
            default,
            ", ".join(sorted(VALID_EFFORT_LEVELS)),
        )
        return default
    return normalized


def _build_claude_process_env() -> dict[str, str]:
    env = {
        "CLAUDE_CODE_USE_POWERSHELL_TOOL": os.getenv("CLAUDE_CODE_USE_POWERSHELL_TOOL", "1"),
        "CLAUDE_CODE_USE_FOUNDRY": os.getenv("CLAUDE_CODE_USE_FOUNDRY", "1"),
        "CLAUDE_CODE_EFFORT_LEVEL": _resolve_effort_level(),
    }

    env_aliases = {
        "ANTHROPIC_FOUNDRY_RESOURCE": ("ANTHROPIC_FOUNDRY_RESOURCE",),
        "ANTHROPIC_FOUNDRY_BASE_URL": ("ANTHROPIC_FOUNDRY_BASE_URL", "FOUNDRY_CLAUDE_BASE_URL"),
        "ANTHROPIC_FOUNDRY_API_KEY": ("ANTHROPIC_FOUNDRY_API_KEY", "FOUNDRY_CLAUDE_API_KEY"),
        "ANTHROPIC_DEFAULT_OPUS_MODEL": ("ANTHROPIC_DEFAULT_OPUS_MODEL",),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": (
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "FOUNDRY_CLAUDE_REPORT_MODEL",
            "FOUNDRY_CLAUDE_ANALYSIS_MODEL",
        ),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": ("ANTHROPIC_DEFAULT_HAIKU_MODEL",),
        "ANTHROPIC_MODEL": ("ANTHROPIC_MODEL",),
    }
    for target_key, candidate_keys in env_aliases.items():
        value = _first_env(*candidate_keys)
        if value:
            env[target_key] = value

    return env


def _validate_foundry_configuration() -> None:
    use_foundry = os.getenv("CLAUDE_CODE_USE_FOUNDRY", "1").strip().lower()
    if use_foundry not in {"1", "true", "yes", "on"}:
        LOGGER.warning(
            "CLAUDE_CODE_USE_FOUNDRY is not enabled. This project is intended to run against Microsoft Foundry."
        )

    resource = _first_env("ANTHROPIC_FOUNDRY_RESOURCE")
    base_url = _first_env("ANTHROPIC_FOUNDRY_BASE_URL", "FOUNDRY_CLAUDE_BASE_URL")
    if not resource and not base_url:
        raise RuntimeError(
            "Microsoft Foundry is not configured. Set ANTHROPIC_FOUNDRY_RESOURCE or "
            "ANTHROPIC_FOUNDRY_BASE_URL before starting the server."
        )

    auth_mode = "API key" if _first_env("ANTHROPIC_FOUNDRY_API_KEY", "FOUNDRY_CLAUDE_API_KEY") else "Entra ID"
    target = base_url or resource or "<unknown>"
    LOGGER.info("Microsoft Foundry target: %s", target)
    LOGGER.info("Microsoft Foundry authentication mode: %s", auth_mode)

    model_pin_values = {
        "ANTHROPIC_DEFAULT_OPUS_MODEL": _first_env("ANTHROPIC_DEFAULT_OPUS_MODEL"),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": _first_env(
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "FOUNDRY_CLAUDE_REPORT_MODEL",
            "FOUNDRY_CLAUDE_ANALYSIS_MODEL",
        ),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": _first_env("ANTHROPIC_DEFAULT_HAIKU_MODEL"),
    }
    missing_model_pins = [key for key in FOUNDRY_MODEL_PIN_KEYS if not model_pin_values.get(key)]
    if missing_model_pins:
        LOGGER.warning(
            "Foundry model version pinning is incomplete. Set %s to deployment names to avoid breakage on future Claude releases.",
            ", ".join(missing_model_pins),
        )


def _build_agent() -> ClaudeAgent:
    default_options = {
        "cwd": str(PROJECT_ROOT),
        "allowed_tools": BUILTIN_TOOLS,
        "permission_mode": os.getenv("CLAUDE_PERMISSION_MODE", "dontAsk"),
        "model": os.getenv("CLAUDE_MODEL", "sonnet"),
        "max_turns": int(os.getenv("CLAUDE_MAX_TURNS", "12")),
        "effort": _resolve_effort_level(),
        "env": _build_claude_process_env(),
    }

    return ClaudeAgent(
        name="analysis-artifact-agent",
        description="Claude Agent SDK based analysis artifact agent hosted through Microsoft Agent Framework.",
        instructions=(
            "You are hosted behind Microsoft Agent Framework and Azure AI Agent Server. "
            "Respond in Japanese unless the user explicitly requests another language. "
            "Your role is secondary interpretation of already generated analysis artifacts for AI Work Inspector. "
            "Prefer reading selected result files, metadata, reports, and frame paths over making assumptions. "
            "Stay inside narrow business operations such as result comparison, timestamp/frame lookup, chunk caption re-summary, "
            "work standard search under data/work_item_descripton, selective report section regeneration, and provider comparison planning. "
            "Do not edit repository files and do not use shell commands. "
            "If the caller asks for a structured workspace response, follow the requested JSON contract exactly."
        ),
        tools=BUILTIN_TOOLS,
        default_options=default_options,
    )


def main() -> None:
    load_dotenv(override=False)
    _configure_logging()
    _validate_foundry_configuration()

    port = _resolve_port()
    agent = _build_agent()

    LOGGER.info("Starting analysis-artifact-agent on http://localhost:%s/responses", port)
    from_agent_framework(agent).run(port=port)


if __name__ == "__main__":
    main()
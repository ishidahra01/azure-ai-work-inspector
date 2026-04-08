import os
from abc import ABC, abstractmethod
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

try:
    from anthropic import AnthropicFoundry
except ImportError:
    AnthropicFoundry = None


load_dotenv(override=False)

AZURE_OPENAI_PROVIDER = "azure_openai"
FOUNDRY_CLAUDE_PROVIDER = "foundry_claude"

PROVIDER_LABELS = {
    AZURE_OPENAI_PROVIDER: "Azure OpenAI",
    FOUNDRY_CLAUDE_PROVIDER: "Claude (Foundry)",
}

DEFAULT_PROVIDER_NAME = os.getenv("DEFAULT_LLM_PROVIDER", AZURE_OPENAI_PROVIDER)

DEFAULT_MODEL_SELECTIONS = {
    AZURE_OPENAI_PROVIDER: {
        "analysis_model": os.getenv("AZURE_OPENAI_ANALYSIS_MODEL", "gpt-4.1"),
        "report_model": os.getenv("AZURE_OPENAI_REPORT_MODEL", "o4-mini"),
    },
    FOUNDRY_CLAUDE_PROVIDER: {
        "analysis_model": os.getenv("FOUNDRY_CLAUDE_ANALYSIS_MODEL", "claude-sonnet-4-6"),
        "report_model": os.getenv("FOUNDRY_CLAUDE_REPORT_MODEL", "claude-sonnet-4-6"),
    },
}


def get_provider_options() -> dict[str, str]:
    return PROVIDER_LABELS.copy()


def get_default_model_selection(provider_name: str) -> dict[str, str]:
    return DEFAULT_MODEL_SELECTIONS.get(provider_name, DEFAULT_MODEL_SELECTIONS[AZURE_OPENAI_PROVIDER]).copy()


def _require_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _extract_openai_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            text_value = getattr(item, "text", None)
            if text_value:
                text_parts.append(text_value)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "\n".join(part for part in text_parts if part)
    return str(content or "")


def _extract_claude_text(response: Any) -> str:
    text_parts = []
    for block in getattr(response, "content", []):
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            text_parts.append(block.text)
    return "\n".join(text_parts)


def _split_data_uri(data_uri: str) -> tuple[str, str]:
    if not data_uri.startswith("data:") or "," not in data_uri:
        raise ValueError("Expected image data as a data URI.")
    header, encoded = data_uri.split(",", 1)
    mime_type = header[5:].split(";", 1)[0]
    return mime_type, encoded


def _is_reasoning_model(model_name: str) -> bool:
    normalized_name = model_name.lower()
    reasoning_prefixes = (
        "gpt-5",
        "o1",
        "o3",
        "o4",
        "codex-mini",
        "gpt-oss",
    )
    return normalized_name.startswith(reasoning_prefixes)


def build_analysis_system_prompt(task_name: str, history_captions: list[str], custom_system_prompt: str | None = None) -> str:
    if custom_system_prompt:
        return f"{custom_system_prompt}\n\nHere is the history of captions for the previous frames:\n{history_captions}"

    return f"""
        You are an expert in analyzing vehicle inspection procedures from video footage, especially {task_name} tasks.
        Given a set of frames extracted from a continuous video, along with descriptions of prior tasks already completed, your tasks are as follows:

        - Describe the sequence of actions observed in the frames, including the time taken for each action and any notable changes in the inspection process.
        - Identify inefficient movements or suboptimal work methods observed during the inspection process and propose concrete improvements.
        - Discover implicit knowledge and expert techniques demonstrated by experienced workers that may not be documented but contribute to efficient task execution.

        You should focus on the following aspects:
        - Analyze the sequence as a time-continuous process, not as isolated frames.
        - Consider temporal consistency and motion cues to understand how the inspection unfolds.
        - Take into account the context of previously completed tasks to infer the purpose and position of the current action within the overall workflow.
        - Provide a concise explanation in English (max 400 characters per task), explaining your reasoning based on observed changes across frames and the prior task context.

        Here is the history of captions for the previous frames:
        {history_captions}
        """


def build_report_system_prompt(task_name: str, custom_system_prompt: str | None = None) -> str:
    if custom_system_prompt:
        return custom_system_prompt

    return f"""
        You are an expert in generating structured reports based on video analysis of vehicle inspection work, especially {task_name}.
        Analyze the video and create a detailed report with the following instructions:

        - Structure the findings into clear, organized sections ("Task description"," "Inefficient Movements", "Improvement Suggestions", "Implicit Expert Knowledge").
        - Do not omit any tasks and any insights you observe from the video. Even minor observations should be included if they provide meaningful insight.
        - Use bullet points, subheadings, and concise descriptions to make the report easy to read and actionable.
        - The output must be in Markdown format and in Japanese.
        - For each reported item, include one or more corresponding time frames (e.g., 00:01:23–00:01:35) from the video as supporting evidence, to ensure traceability and allow reviewers to reference the specific moments where the observations were made.

        Note: The original frame analysis results are based only on a limited time segment, so there may be inaccuracies due to missing context from preceding and following frames. Please review the full sequence of results, and revise any inconsistencies using information from the surrounding context.
        """


class BaseVideoAnalysisProvider(ABC):
    def __init__(self, analysis_model: str, report_model: str):
        self.analysis_model = analysis_model
        self.report_model = report_model

    @abstractmethod
    def create_caption(
        self,
        image_infos: list[dict[str, Any]],
        history_captions: list[str],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_report(
        self,
        filtered_data: list[dict[str, Any]],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError


class AzureOpenAIProvider(BaseVideoAnalysisProvider):
    def __init__(self, analysis_model: str, report_model: str):
        super().__init__(analysis_model=analysis_model, report_model=report_model)
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        client_kwargs: dict[str, Any] = {
            "azure_endpoint": _require_env_var("AZURE_OPENAI_ENDPOINT"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
        }

        if api_key:
            client_kwargs["api_key"] = api_key
        else:
            client_kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                DefaultAzureCredential(), "https://ai.azure.com/.default"
            )

        self._client = AzureOpenAI(**client_kwargs)

    def _build_chat_completion_options(self, model_name: str, token_limit: int) -> dict[str, Any]:
        if _is_reasoning_model(model_name):
            options: dict[str, Any] = {
                "max_completion_tokens": token_limit,
            }
            reasoning_effort = os.getenv("AZURE_OPENAI_REASONING_EFFORT")
            if reasoning_effort:
                options["reasoning_effort"] = reasoning_effort
            return options

        return {
            "temperature": 0,
            "max_tokens": token_limit,
            "top_p": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }

    def create_caption(
        self,
        image_infos: list[dict[str, Any]],
        history_captions: list[str],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        system_message = build_analysis_system_prompt(task_name, history_captions, custom_system_prompt)

        user_content = []
        for index, info in enumerate(image_infos, start=1):
            user_content.append(
                {
                    "type": "text",
                    "text": f"Frame {index}: time={info['timestamp']:.2f} sec, frame_number={info['frame_number']}."
                }
            )
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": info["base64_data"]},
                }
            )

        completion = self._client.chat.completions.create(
            model=self.analysis_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content},
            ],
            **self._build_chat_completion_options(self.analysis_model, 1000),
        )
        return _extract_openai_text(completion.choices[0].message)

    def generate_report(
        self,
        filtered_data: list[dict[str, Any]],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        system_message = build_report_system_prompt(task_name, custom_system_prompt)
        completion = self._client.chat.completions.create(
            model=self.report_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": str(filtered_data)},
            ],
            **self._build_chat_completion_options(self.report_model, 10000),
        )
        return _extract_openai_text(completion.choices[0].message)


class FoundryClaudeProvider(BaseVideoAnalysisProvider):
    def __init__(self, analysis_model: str, report_model: str):
        super().__init__(analysis_model=analysis_model, report_model=report_model)

        if AnthropicFoundry is None:
            raise ImportError("The anthropic package is required to use Claude in Foundry.")

        base_url = _require_env_var("FOUNDRY_CLAUDE_BASE_URL")
        api_key = os.getenv("FOUNDRY_CLAUDE_API_KEY")

        if api_key:
            self._client = AnthropicFoundry(api_key=api_key, base_url=base_url)
        else:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://ai.azure.com/.default"
            )
            self._client = AnthropicFoundry(
                azure_ad_token_provider=token_provider,
                base_url=base_url,
            )

    def create_caption(
        self,
        image_infos: list[dict[str, Any]],
        history_captions: list[str],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        system_message = build_analysis_system_prompt(task_name, history_captions, custom_system_prompt)

        user_content = []
        for index, info in enumerate(image_infos, start=1):
            user_content.append(
                {
                    "type": "text",
                    "text": f"Frame {index}: time={info['timestamp']:.2f} sec, frame_number={info['frame_number']}."
                }
            )
            mime_type, encoded_data = _split_data_uri(info["base64_data"])
            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": encoded_data,
                    },
                }
            )

        response = self._client.messages.create(
            model=self.analysis_model,
            system=system_message,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=1000,
            temperature=0,
        )
        return _extract_claude_text(response)

    def generate_report(
        self,
        filtered_data: list[dict[str, Any]],
        task_name: str,
        custom_system_prompt: str | None = None,
    ) -> str:
        system_message = build_report_system_prompt(task_name, custom_system_prompt)
        response = self._client.messages.create(
            model=self.report_model,
            system=system_message,
            messages=[{"role": "user", "content": str(filtered_data)}],
            max_tokens=8192,
            temperature=0,
        )
        return _extract_claude_text(response)


def get_video_analysis_provider(
    provider_name: str | None = None,
    analysis_model: str | None = None,
    report_model: str | None = None,
) -> BaseVideoAnalysisProvider:
    selected_provider = provider_name or DEFAULT_PROVIDER_NAME
    defaults = get_default_model_selection(selected_provider)
    selected_analysis_model = analysis_model or defaults["analysis_model"]
    selected_report_model = report_model or defaults["report_model"]

    if selected_provider == AZURE_OPENAI_PROVIDER:
        return AzureOpenAIProvider(
            analysis_model=selected_analysis_model,
            report_model=selected_report_model,
        )
    if selected_provider == FOUNDRY_CLAUDE_PROVIDER:
        return FoundryClaudeProvider(
            analysis_model=selected_analysis_model,
            report_model=selected_report_model,
        )

    raise ValueError(f"Unsupported LLM provider: {selected_provider}")
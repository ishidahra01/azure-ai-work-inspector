import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from utils.result_manager import get_all_result_dirs, get_result_info, load_error_log, load_metadata, load_report


DEFAULT_AGENT_ENDPOINT = os.getenv("AGENT_WORKSPACE_URL", "http://127.0.0.1:8088/responses")
DEFAULT_AGENT_TIMEOUT = int(os.getenv("AGENT_WORKSPACE_REQUEST_TIMEOUT", "180"))
DEFAULT_EDITOR_TEXT = """# Analysis Artifact Workspace

ここでは、既に生成済みの解析結果をもとに二次解釈・再整理を行います。

## この Agent が担当すること
- 過去の解析結果の比較
- レポートや chunk caption の再要約
- タイムスタンプやフレーム根拠の掘り下げ
- 作業標準書との突き合わせ
- レポートの一部だけの書き直し案作成

## 作業メモ
- 右ペインは最終成果物の下書きとして使う
- 元データの確認が必要なときは、選択した結果ディレクトリの metadata/report/frame を参照する
"""

WORK_STANDARD_DIR = Path("data") / "work_item_descripton"


def ensure_agent_workspace_state(session_state: Any) -> None:
    if "agent_workspace_messages" not in session_state:
        session_state.agent_workspace_messages = [
            {
                "role": "assistant",
                "content": "AI Work Inspector ワークスペースです。左で会話し、右で成果物を更新できます。",
            }
        ]
    if "agent_workspace_editor_text" not in session_state:
        session_state.agent_workspace_editor_text = DEFAULT_EDITOR_TEXT
    if "agent_workspace_editor_area" not in session_state:
        session_state.agent_workspace_editor_area = session_state.agent_workspace_editor_text
    if "agent_workspace_endpoint" not in session_state:
        session_state.agent_workspace_endpoint = DEFAULT_AGENT_ENDPOINT
    if "agent_workspace_logs" not in session_state:
        session_state.agent_workspace_logs = []
    if "agent_workspace_history" not in session_state:
        session_state.agent_workspace_history = []
    if "agent_workspace_selected_result_dirs" not in session_state:
        session_state.agent_workspace_selected_result_dirs = []
    if "agent_workspace_pending_editor_text" not in session_state:
        session_state.agent_workspace_pending_editor_text = None


def reset_agent_workspace(session_state: Any) -> None:
    session_state.agent_workspace_messages = [
        {
            "role": "assistant",
            "content": "会話を初期化しました。新しい依頼をどうぞ。",
        }
    ]
    session_state.agent_workspace_logs = []
    session_state.agent_workspace_history = []


def reset_editor_document(session_state: Any) -> None:
    session_state.agent_workspace_editor_text = DEFAULT_EDITOR_TEXT
    session_state.agent_workspace_editor_area = DEFAULT_EDITOR_TEXT


def import_text_into_editor(session_state: Any, content: str, source_label: str) -> None:
    session_state.agent_workspace_editor_text = content
    session_state.agent_workspace_editor_area = content
    session_state.agent_workspace_history.insert(
        0,
        {
            "timestamp": _now_iso(),
            "summary": f"{source_label} を編集ペインに読み込みました。",
            "document": content,
        },
    )


def build_agent_input(prompt: str, editor_text: str, messages: list[dict[str, str]]) -> str:
    return build_agent_input_with_context(prompt, editor_text, messages, {"summary": "", "entries": [], "available_paths": []})


def build_agent_input_with_context(
    prompt: str,
    editor_text: str,
    messages: list[dict[str, str]],
    selected_results_context: dict[str, Any],
) -> str:
    recent_messages = messages[-8:]
    history_text = "\n".join(
        f"{message['role']}: {message['content']}" for message in recent_messages
    )

    selected_results_summary = selected_results_context.get("summary") or "(未選択)"
    available_paths = selected_results_context.get("available_paths") or []
    available_paths_text = "\n".join(f"- {path}" for path in available_paths) or "- results/ 以下は未選択"
    work_standard_path = WORK_STANDARD_DIR.as_posix()

    return f"""
あなたは AI Work Inspector の二次解釈 Agent です。
あなたの役割は、既に生成済みの動画解析アーティファクトを読み直し、追加探索・再要約・再構成を行うことです。

前提:
- 一次生成は既存の動画解析バッチが担当する
- あなたは二次解釈と再操作だけを担当する
- 汎用自律実行ではなく、業務に閉じた限定操作を優先する

優先タスク:
- 結果一覧の比較と要点整理
- タイムスタンプ指定から根拠フレームや chunk の特定
- chunk caption の再要約
- data/work_item_descripton 配下の作業標準書との突き合わせ
- レポートの特定節だけ再生成
- provider 差分や再評価観点の整理

要件:
- 日本語で簡潔に返答する
- 必要なら選択された結果ファイルを Read/Glob/Grep で参照する
- 指定されていない結果や無関係なパスは勝手に探索しない
- 右ペインを更新する場合は document に完全な本文を返す
- 右ペインを変更しない場合は document を null にする
- 必ず JSON のみを返す

JSON schema:
{{
  "reply": "会話ペインに出す返答",
  "document": "右ペインに反映する完全な本文。変更なしなら null",
  "change_summary": "右ペインの更新内容を一文で要約。変更なしでも可"
}}

現在選択されている解析結果の要約:
{selected_results_summary}

参照可能な主なパス:
{available_paths_text}

作業標準書の検索先:
- {work_standard_path}

現在の会話:
{history_text or "(まだ会話はありません)"}

現在のドキュメント:
{editor_text}

最新のユーザー依頼:
{prompt}
""".strip()


def invoke_agent_workspace(
    endpoint: str,
    prompt: str,
    editor_text: str,
    messages: list[dict[str, str]],
    selected_results_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "input": build_agent_input_with_context(
            prompt,
            editor_text,
            messages,
            selected_results_context or {"summary": "", "entries": [], "available_paths": []},
        )
    }
    request_data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=DEFAULT_AGENT_TIMEOUT) as response:
            raw_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agent endpoint returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            "Agent endpoint に接続できませんでした。agent_workspace/main.py を起動しているか確認してください。"
        ) from exc

    response_payload = _load_json_or_text(raw_body)
    raw_text = _extract_response_text(response_payload)
    parsed = _parse_workspace_response(raw_text, editor_text)
    parsed["raw_response"] = raw_body
    return parsed


def append_workspace_result(session_state: Any, prompt: str, result: dict[str, Any]) -> None:
    session_state.agent_workspace_messages.append({"role": "user", "content": prompt})
    session_state.agent_workspace_messages.append(
        {"role": "assistant", "content": result["reply"]}
    )

    new_document = result.get("document")
    if new_document is not None and new_document != session_state.agent_workspace_editor_text:
        session_state.agent_workspace_editor_text = new_document
        session_state.agent_workspace_pending_editor_text = new_document
        session_state.agent_workspace_history.insert(
            0,
            {
                "timestamp": _now_iso(),
                "summary": result.get("change_summary") or "ドキュメントを更新しました。",
                "document": new_document,
            },
        )

    session_state.agent_workspace_logs.insert(
        0,
        {
            "timestamp": _now_iso(),
            "prompt": prompt,
            "change_summary": result.get("change_summary") or "",
            "raw_response": result.get("raw_response") or "",
        },
    )
    session_state.agent_workspace_logs = session_state.agent_workspace_logs[:20]
    session_state.agent_workspace_history = session_state.agent_workspace_history[:20]


def _load_json_or_text(raw_body: str) -> Any:
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body


def _extract_response_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for key in ("output_text", "response", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

        output = payload.get("output")
        if isinstance(output, list):
            candidate_texts = []
            text_parts = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            text_value = block.get("text")
                            if isinstance(text_value, str) and text_value.strip():
                                candidate_texts.append(text_value)
                                text_parts.append(text_value)
                text_value = item.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    candidate_texts.append(text_value)
                    text_parts.append(text_value)
            for candidate_text in reversed(candidate_texts):
                extracted_json = _extract_json_candidate(candidate_text)
                if extracted_json:
                    return extracted_json
            if text_parts:
                return "\n".join(text_parts)

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_workspace_response(raw_text: str, current_document: str) -> dict[str, Any]:
    candidate = _extract_json_candidate(raw_text) or _strip_code_fence(raw_text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {
            "reply": raw_text,
            "document": current_document,
            "change_summary": "応答は取得できましたが、JSON ではなかったため右ペインは維持しました。",
        }

    if not isinstance(parsed, dict):
        return {
            "reply": raw_text,
            "document": current_document,
            "change_summary": "予期しない応答形式だったため右ペインは維持しました。",
        }

    reply = parsed.get("reply") or parsed.get("message") or "応答を受け取りました。"
    document = parsed.get("document", current_document)
    if document is None:
        document = current_document
    elif not isinstance(document, str):
        document = json.dumps(document, ensure_ascii=False, indent=2)

    change_summary = parsed.get("change_summary") or "ドキュメントを確認しました。"
    return {
        "reply": str(reply),
        "document": document,
        "change_summary": str(change_summary),
    }


def _strip_code_fence(text: str) -> str:
    fenced_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text.strip(), re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)
    return text


def _extract_json_candidate(text: str) -> str | None:
    fenced_matches = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_matches:
        return fenced_matches[-1]

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    last_object_start = stripped.rfind("{")
    if last_object_start == -1:
        return None

    candidate = stripped[last_object_start:]
    try:
        json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return candidate


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_result_catalog(base_path: str = "results") -> list[dict[str, Any]]:
    catalog = []
    for result_dir in get_all_result_dirs(base_path):
        info = get_result_info(result_dir)
        catalog.append(
            {
                "dir": result_dir,
                "label": format_result_label(info),
                "timestamp": info["timestamp"],
                "video_name": info["video_name"],
                "has_report": info["has_report"],
                "has_metadata": info["has_metadata"],
                "has_error_log": info["has_error_log"],
            }
        )
    return catalog


def format_result_label(info: dict[str, Any]) -> str:
    title = info.get("video_name") or info.get("timestamp") or "unknown"
    flags = []
    if info.get("has_report"):
        flags.append("report")
    if info.get("has_metadata"):
        flags.append("metadata")
    if info.get("has_error_log"):
        flags.append("error")
    suffix = f" [{' / '.join(flags)}]" if flags else ""
    return f"{title} | {info.get('timestamp', '')}{suffix}"


def build_selected_results_context(selected_result_dirs: list[str]) -> dict[str, Any]:
    entries = []
    available_paths: list[str] = []

    for result_dir in selected_result_dirs:
        info = get_result_info(result_dir)
        entry: dict[str, Any] = {
            "dir": _to_posix_relative(result_dir),
            "video_name": info.get("video_name"),
            "timestamp": info.get("timestamp"),
            "available_files": [],
        }

        if info.get("video_file"):
            video_path = os.path.join(result_dir, info["video_file"])
            entry["video_path"] = _to_posix_relative(video_path)
            entry["available_files"].append(entry["video_path"])
        if info.get("metadata_file"):
            metadata_path = os.path.join(result_dir, info["metadata_file"])
            entry["metadata_path"] = _to_posix_relative(metadata_path)
            entry["available_files"].append(entry["metadata_path"])
            metadata = load_metadata(result_dir, info["metadata_file"])
            if metadata:
                entry.update(_summarize_metadata(metadata))
        if info.get("report_file"):
            report_path = os.path.join(result_dir, info["report_file"])
            entry["report_path"] = _to_posix_relative(report_path)
            entry["available_files"].append(entry["report_path"])
        if info.get("error_log_file"):
            error_log_path = os.path.join(result_dir, info["error_log_file"])
            entry["error_log_path"] = _to_posix_relative(error_log_path)
            entry["available_files"].append(entry["error_log_path"])

        frames_dir = os.path.join(result_dir, "frames")
        if os.path.isdir(frames_dir):
            entry["frames_dir"] = _to_posix_relative(frames_dir)
            entry["available_files"].append(f"{entry['frames_dir']}/")

        available_paths.extend(entry["available_files"])
        entries.append(entry)

    available_paths.append(WORK_STANDARD_DIR.as_posix() + "/")
    summary = json.dumps(entries, ensure_ascii=False, indent=2) if entries else "(未選択)"
    return {
        "entries": entries,
        "summary": summary,
        "available_paths": available_paths,
    }


def build_selected_results_table(selected_result_dirs: list[str]) -> list[dict[str, Any]]:
    table = []
    for result_dir in selected_result_dirs:
        info = get_result_info(result_dir)
        row = {
            "結果": format_result_label(info),
            "ディレクトリ": _to_posix_relative(result_dir),
            "Report": "yes" if info.get("has_report") else "no",
            "Metadata": "yes" if info.get("has_metadata") else "no",
            "Error": "yes" if info.get("has_error_log") else "no",
        }
        if info.get("has_metadata") and info.get("metadata_file"):
            metadata = load_metadata(result_dir, info["metadata_file"])
            if metadata:
                row.update(
                    {
                        "Chunks": len(metadata),
                        "Frames": sum(len(chunk.get("frames", [])) for chunk in metadata),
                    }
                )
        table.append(row)
    return table


def merge_selected_reports(selected_result_dirs: list[str]) -> str:
    sections = []
    for result_dir in selected_result_dirs:
        info = get_result_info(result_dir)
        title = format_result_label(info)
        if info.get("has_report") and info.get("report_file"):
            report_content = load_report(result_dir, info["report_file"])
            if report_content:
                sections.append(f"# {title}\n\n{report_content}")
                continue
        if info.get("has_error_log") and info.get("error_log_file"):
            error_content = load_error_log(result_dir, info["error_log_file"])
            sections.append(f"# {title}\n\n```text\n{error_content or ''}\n```")
        else:
            sections.append(f"# {title}\n\nレポートはありません。metadata を参照してください。")
    return "\n\n---\n\n".join(sections)


def _summarize_metadata(metadata: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = []
    frame_count = 0
    for chunk in metadata:
        frames = chunk.get("frames", [])
        frame_count += len(frames)
        timestamps.extend(frame.get("timestamp") for frame in frames if isinstance(frame.get("timestamp"), (int, float)))
    summary: dict[str, Any] = {
        "chunk_count": len(metadata),
        "frame_count": frame_count,
    }
    if timestamps:
        summary["time_range"] = f"{min(timestamps):.1f}s - {max(timestamps):.1f}s"
    first_chunk_caption = metadata[0].get("chunk_caption") if metadata else None
    if isinstance(first_chunk_caption, str) and first_chunk_caption.strip():
        summary["first_chunk_caption_preview"] = first_chunk_caption[:300]
    return summary


def _to_posix_relative(path: str) -> str:
    return Path(path).as_posix()
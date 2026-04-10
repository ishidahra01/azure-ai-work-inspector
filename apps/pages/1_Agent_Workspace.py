from pathlib import Path

import pandas as pd
import streamlit as st

from utils.agent_workspace import (
    append_workspace_result,
    build_selected_results_context,
    build_selected_results_table,
    ensure_agent_workspace_state,
    get_result_catalog,
    import_text_into_editor,
    invoke_agent_workspace,
    merge_selected_reports,
    reset_agent_workspace,
    reset_editor_document,
)
from utils.result_manager import get_result_info, load_report


def load_css() -> None:
    css_file = Path(__file__).resolve().parents[1] / "css" / "style.css"
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


ensure_agent_workspace_state(st.session_state)
if st.session_state.agent_workspace_pending_editor_text is not None:
    st.session_state.agent_workspace_editor_text = st.session_state.agent_workspace_pending_editor_text
    st.session_state.agent_workspace_editor_area = st.session_state.agent_workspace_pending_editor_text
    st.session_state.agent_workspace_pending_editor_text = None
load_css()

st.markdown("<h1 class='page-title'>Agent Workspace</h1>", unsafe_allow_html=True)
st.caption("生成済みの動画解析アーティファクトを再解釈・再編集するための 2 ペイン UI です。")

catalog = get_result_catalog()
catalog_dirs = [item["dir"] for item in catalog]
catalog_labels = {item["dir"]: item["label"] for item in catalog}

if st.session_state.get("current_result_dir") and st.session_state.current_result_dir not in st.session_state.agent_workspace_selected_result_dirs:
    if st.session_state.current_result_dir in catalog_dirs:
        st.session_state.agent_workspace_selected_result_dirs = [
            st.session_state.current_result_dir,
            *st.session_state.agent_workspace_selected_result_dirs,
        ]

selection_left, selection_right = st.columns([3, 2], gap="large")

with selection_left:
    selected_result_dirs = st.multiselect(
        "参照対象の解析結果",
        options=catalog_dirs,
        default=[directory for directory in st.session_state.agent_workspace_selected_result_dirs if directory in catalog_dirs],
        format_func=lambda directory: catalog_labels.get(directory, directory),
        help="Agent が参照してよい過去結果を選択します。選択された結果の report / metadata / frames を優先参照します。",
    )
    st.session_state.agent_workspace_selected_result_dirs = selected_result_dirs

with selection_right:
    import_col1, import_col2 = st.columns(2)
    with import_col1:
        if st.button("選択レポートを読込", width="stretch", disabled=not selected_result_dirs):
            import_text_into_editor(
                st.session_state,
                merge_selected_reports(selected_result_dirs),
                "選択結果レポート",
            )
            st.rerun()
    with import_col2:
        if st.button("現在の結果を選択", width="stretch", disabled=not st.session_state.get("current_result_dir")):
            current_dir = st.session_state.get("current_result_dir")
            if current_dir and current_dir in catalog_dirs and current_dir not in st.session_state.agent_workspace_selected_result_dirs:
                st.session_state.agent_workspace_selected_result_dirs = [current_dir, *st.session_state.agent_workspace_selected_result_dirs]
            st.rerun()

selected_results_context = build_selected_results_context(selected_result_dirs)

with st.expander("選択中アーティファクト", expanded=bool(selected_result_dirs)):
    if selected_result_dirs:
        table = build_selected_results_table(selected_result_dirs)
        if table:
            st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
        st.markdown("**Agent が参照できる主なパス**")
        st.code("\n".join(selected_results_context["available_paths"]), language="text")
    else:
        st.info("ここで結果を選ぶと、Agent はその結果の report / metadata / frames を前提に追加探索できます。")

toolbar_left, toolbar_right = st.columns([3, 2], gap="large")

with toolbar_left:
    endpoint = st.text_input(
        "Agent Endpoint",
        value=st.session_state.agent_workspace_endpoint,
        help="通常は agent_workspace/main.py の既定 URL を使います。",
    ).strip()
    st.session_state.agent_workspace_endpoint = endpoint

with toolbar_right:
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("会話を初期化", width="stretch"):
            reset_agent_workspace(st.session_state)
            st.rerun()
    with action_col2:
        if st.button("下書きを初期化", width="stretch"):
            reset_editor_document(st.session_state)
            st.rerun()
    with action_col3:
        st.download_button(
            "Markdown 保存",
            data=st.session_state.agent_workspace_editor_text,
            file_name="analysis-artifact-draft.md",
            mime="text/markdown",
            width="stretch",
        )

if st.session_state.get("current_result_dir"):
    result_info = get_result_info(st.session_state.current_result_dir)
    if result_info.get("has_report"):
        import_col1, import_col2 = st.columns([3, 1])
        with import_col1:
            st.info("現在選択中の動画解析レポートを右ペインに取り込めます。")
        with import_col2:
            if st.button("分析レポートを読込", width="stretch"):
                report_content = load_report(
                    st.session_state.current_result_dir,
                    result_info["report_file"],
                )
                if report_content:
                    import_text_into_editor(st.session_state, report_content, "動画解析レポート")
                    st.rerun()

left_pane, right_pane = st.columns([7, 5], gap="large")

with left_pane:
    st.subheader("Chat")
    chat_container = st.container(height=640)
    with chat_container:
        for message in st.session_state.agent_workspace_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

with right_pane:
    st.subheader("Editor")
    editor_tab, preview_tab, history_tab, log_tab = st.tabs(["Editor", "Preview", "History", "Logs"])

    with editor_tab:
        st.text_area(
            "成果物",
            height=520,
            key="agent_workspace_editor_area",
        )
        st.session_state.agent_workspace_editor_text = st.session_state.agent_workspace_editor_area

    with preview_tab:
        st.markdown(st.session_state.agent_workspace_editor_text)

    with history_tab:
        if st.session_state.agent_workspace_history:
            for item in st.session_state.agent_workspace_history:
                with st.expander(f"{item['timestamp']} | {item['summary']}"):
                    st.code(item["document"], language="markdown")
        else:
            st.info("まだドキュメント更新履歴はありません。")

    with log_tab:
        if st.session_state.agent_workspace_logs:
            for item in st.session_state.agent_workspace_logs:
                with st.expander(f"{item['timestamp']} | {item['change_summary'] or 'raw response'}"):
                    st.markdown(f"**Prompt**\n\n{item['prompt']}")
                    st.code(item["raw_response"], language="json")
        else:
            st.info("まだログはありません。")

prompt = st.chat_input("選択結果の比較、タイムスタンプ調査、レポート追記、標準書突合などを依頼")

if prompt:
    try:
        with st.spinner("Agent が応答中です..."):
            result = invoke_agent_workspace(
                endpoint=st.session_state.agent_workspace_endpoint,
                prompt=prompt,
                editor_text=st.session_state.agent_workspace_editor_text,
                messages=st.session_state.agent_workspace_messages,
                selected_results_context=selected_results_context,
            )
        append_workspace_result(st.session_state, prompt, result)
        st.rerun()
    except Exception as exc:
        st.error(str(exc))
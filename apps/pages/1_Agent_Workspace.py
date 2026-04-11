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


SKILL_GUIDES = [
    {
        "key": "evidence-audit-confidence-map",
        "title": "Evidence Audit",
        "tag": "根拠監査",
        "summary": "レポートの主張を chunk・timestamp・frame にさかのぼって、観測と推定を分けて整理します。",
        "ask": "このレポートの主張を根拠監査して、直接観測・強い推定・弱い推定・根拠不足に分けて。",
        "inputs": "report / metadata / frames",
        "outputs": "信頼度マップ、根拠表、追加確認ポイント",
    },
    {
        "key": "pattern-miner-across-runs",
        "title": "Pattern Miner",
        "tag": "横断分析",
        "summary": "複数 run をまとめて読み、繰り返し出る良い癖、ムダ動作、リスク傾向を抽出します。",
        "ask": "選択した run 全体から recurring pattern を抽出して、頻出のムダ動作と良い実践をまとめて。",
        "inputs": "複数 results の report / metadata",
        "outputs": "頻出パターン一覧、ばらつき、改善優先度",
    },
    {
        "key": "sop-coverage-gap-analyzer",
        "title": "SOP Coverage",
        "tag": "標準書照合",
        "summary": "作業標準書の各手順に対して、動画解析結果で確認済みか、未確認か、判定不能かを整理します。",
        "ask": "この結果を標準書と突き合わせて、確認済み・未確認・判定不能を表にして。",
        "inputs": "report / metadata / data/work_item_descripton",
        "outputs": "手順カバレッジ表、ギャップ、追加確認項目",
    },
    {
        "key": "prompt-and-pipeline-optimizer",
        "title": "Prompt Optimizer",
        "tag": "一次生成改善",
        "summary": "chunk caption 用 prompt と最終 report 統合 prompt を見直し、一次生成品質を上げる改善案を作ります。",
        "ask": "chunk caption prompt と report synthesis prompt を改善して。曖昧な caption と過剰推論を減らしたい。",
        "inputs": "現在の prompt、弱い出力例、代表 report / metadata",
        "outputs": "改訂 prompt、原因診断、実験計画",
    },
    {
        "key": "coaching-artifact-generator",
        "title": "Coaching Artifact",
        "tag": "現場展開",
        "summary": "分析結果を、作業者向け指導メモ、監督者向け要点、教育用ケースなどに変換します。",
        "ask": "この分析結果から、作業者向けの短い指導メモと監督者向けの要約を作って。",
        "inputs": "report / metadata / 必要なら標準書",
        "outputs": "対象者別の成果物ドラフト",
    },
]


def render_skill_cards() -> None:
    columns = st.columns(len(SKILL_GUIDES), gap="small")
    for column, guide in zip(columns, SKILL_GUIDES):
        with column:
            st.markdown(f"<div class='skill-card-tag'>{guide['tag']}</div>", unsafe_allow_html=True)
            st.markdown(f"**{guide['title']}**")
            st.caption(guide["summary"])


def render_skill_navigator() -> None:
    with st.expander("できることを見る", expanded=False):
        st.markdown("<div class='navigator-title'>Skill Navigator</div>", unsafe_allow_html=True)
        st.caption("必要なときだけ開いて、依頼の仕方を確認できます。")
        render_skill_cards()

        options = {f"{guide['title']} | {guide['tag']}": guide for guide in SKILL_GUIDES}
        selected_label = st.selectbox(
            "やりたい分析タイプ",
            options=list(options.keys()),
            help="選ぶと、この Skill が向いている依頼例と返ってくる成果物を確認できます。",
        )
        selected_guide = options[selected_label]

        detail_left, detail_right = st.columns([3, 2], gap="large")
        with detail_left:
            st.markdown(f"### {selected_guide['title']}")
            st.write(selected_guide["summary"])
            st.markdown("**依頼例**")
            st.code(selected_guide["ask"], language="text")
        with detail_right:
            st.markdown("**主な入力**")
            st.write(selected_guide["inputs"])
            st.markdown("**返ってくるもの**")
            st.write(selected_guide["outputs"])


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
render_skill_navigator()

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
    st.info("上の Skill Navigator で用途を選び、依頼例をそのままチャットで使うと意図が伝わりやすくなります。")
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

prompt = st.chat_input("根拠監査、横断分析、標準書照合、一次生成 prompt 改善、指導メモ作成などを依頼")

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
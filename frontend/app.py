import streamlit as st
import requests
import time

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DocMind",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">

<style>

/* ─── Reset & Base ─────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, .stApp {
    font-family: 'DM Sans', sans-serif;
    background: #020d07;
    color: #e8f5ee;
    height: 100%;
}

/* Deep layered background */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 10%, rgba(16, 90, 50, 0.35) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 80%, rgba(6, 60, 35, 0.30) 0%, transparent 55%),
        radial-gradient(ellipse 40% 40% at 60% 30%, rgba(30, 120, 70, 0.12) 0%, transparent 50%),
        linear-gradient(160deg, #020d07 0%, #030f09 40%, #021008 100%);
    z-index: 0;
    pointer-events: none;
}

/* Subtle grid texture */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(30, 180, 90, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(30, 180, 90, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    z-index: 0;
    pointer-events: none;
}

/* ─── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(10, 30, 18, 0.65) !important;
    backdrop-filter: blur(28px) saturate(180%);
    -webkit-backdrop-filter: blur(28px) saturate(180%);
    border-right: 1px solid rgba(52, 211, 120, 0.12) !important;
    box-shadow: 4px 0 40px rgba(0,0,0,0.5);
}

[data-testid="stSidebar"] > div:first-child {
    padding: 28px 20px;
}

/* ─── Sidebar Logo / Brand ─────────────────────────── */
.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 36px;
}

.brand-icon {
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg, #10b981, #059669);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.4), inset 0 1px 0 rgba(255,255,255,0.2);
}

.brand-name {
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #34d399, #10b981);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ─── Sidebar Section Labels ───────────────────────── */
.sidebar-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(52, 211, 152, 0.5);
    margin-bottom: 12px;
    margin-top: 8px;
}

/* ─── Upload Zone ──────────────────────────────────── */
.upload-zone {
    background: rgba(16, 185, 129, 0.05);
    border: 1.5px dashed rgba(52, 211, 152, 0.25);
    border-radius: 16px;
    padding: 28px 16px;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
    margin-bottom: 20px;
}

.upload-zone:hover {
    background: rgba(16, 185, 129, 0.09);
    border-color: rgba(52, 211, 152, 0.45);
}

.upload-icon {
    font-size: 32px;
    margin-bottom: 8px;
    display: block;
}

.upload-text {
    font-size: 13px;
    color: rgba(232, 245, 238, 0.65);
    line-height: 1.5;
}

.upload-text strong {
    color: #34d399;
    display: block;
    font-size: 14px;
    margin-bottom: 4px;
}

/* ─── Status Cards ─────────────────────────────────── */
.status-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(52, 211, 152, 0.1);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.status-dot.idle    { background: rgba(148, 163, 184, 0.4); }
.status-dot.active  { background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse-dot 1.5s infinite; }
.status-dot.loading { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; animation: pulse-dot 0.8s infinite; }
.status-dot.done    { background: #10b981; }

@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.8); }
}

.status-text { color: rgba(232, 245, 238, 0.8); }
.status-text span { display: block; font-size: 11px; color: rgba(232, 245, 238, 0.4); margin-top: 2px; }

/* Doc info pill */
.doc-pill {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 12px;
    font-family: 'DM Mono', monospace;
    color: #34d399;
    word-break: break-all;
    margin-top: 16px;
    display: flex;
    align-items: flex-start;
    gap: 8px;
}

/* Reset button */
.reset-hint {
    font-size: 11px;
    color: rgba(239, 68, 68, 0.5);
    text-align: center;
    margin-top: 24px;
    cursor: pointer;
    transition: color 0.2s;
}
.reset-hint:hover { color: rgba(239, 68, 68, 0.85); }

/* ─── Hide Streamlit chrome ────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Sidebar collapse / expand tab ─────────────────── */
/* Always keep it visible and styled */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: fixed !important;
    top: 50% !important;
    left: 0 !important;
    transform: translateY(-50%) !important;
    z-index: 99999 !important;
    background: rgba(10, 30, 18, 0.92) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
    border: 1px solid rgba(52, 211, 152, 0.28) !important;
    border-left: none !important;
    border-radius: 0 12px 12px 0 !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.5), 0 0 0 1px rgba(52,211,152,0.08) !important;
    padding: 14px 10px !important;
    cursor: pointer !important;
    transition: background 0.2s, box-shadow 0.2s !important;
}

[data-testid="collapsedControl"]:hover {
    background: rgba(16, 50, 30, 0.95) !important;
    box-shadow: 6px 0 32px rgba(16,185,129,0.2), 0 0 0 1px rgba(52,211,152,0.2) !important;
}

[data-testid="collapsedControl"] button {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

[data-testid="collapsedControl"] svg {
    width: 18px !important;
    height: 18px !important;
    color: #34d399 !important;
    stroke: #34d399 !important;
    fill: none !important;
}

/* Glowing dot accent on the tab */
[data-testid="collapsedControl"]::before {
    content: '';
    position: absolute;
    top: 10px;
    right: 8px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
    animation: pulse-dot 2s infinite;
}

/* Suggested questions */
.suggested-questions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 560px;
    margin: 28px auto 0;
    padding: 0 16px;
}

.sq-label {
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(52, 211, 152, 0.4);
    margin-bottom: 4px;
    text-align: center;
}

/* Override for suggested question buttons in main area */
.suggested-q-wrap .stButton button {
    background: rgba(255,255,255,0.03) !important;
    color: rgba(209, 250, 229, 0.75) !important;
    border: 1px solid rgba(52,211,152,0.14) !important;
    border-radius: 12px !important;
    font-size: 13.5px !important;
    font-weight: 400 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 11px 18px !important;
    text-align: left !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    backdrop-filter: blur(10px) !important;
    letter-spacing: 0.01em !important;
}

.suggested-q-wrap .stButton button:hover {
    background: rgba(16, 185, 129, 0.08) !important;
    color: #6ee7b7 !important;
    border-color: rgba(52,211,152,0.3) !important;
    transform: translateX(4px) !important;
    box-shadow: 0 4px 20px rgba(16,185,129,0.1) !important;
}

/* ─── Main Column Padding ──────────────────────────── */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ─── Welcome Screen ───────────────────────────────── */
.welcome-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 44px 40px 20px;
}

.welcome-glyph {
    width: 140px;
    height: 60px;
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(5,150,105,0.05));
    border: 1px solid rgba(52, 211, 152, 0.2);
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    margin: 0 auto 18px;
    box-shadow:
        0 0 0 1px rgba(52,211,152,0.08),
        0 0 40px rgba(16,185,129,0.08),
        inset 0 1px 0 rgba(255,255,255,0.08);
    animation: float 4s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-8px); }
}

.welcome-title {
    font-size: clamp(20px, 2.8vw, 30px);
    font-weight: 600;
    letter-spacing: -0.7px;
    color: #e8f5ee;
    margin-bottom: 10px;
    line-height: 1.15;
}

.welcome-title em {
    font-style: normal;
    background: linear-gradient(90deg, #34d399, #6ee7b7, #10b981);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.welcome-sub {
    font-size: 13.5px;
    color: rgba(232, 245, 238, 0.42);
    max-width: 340px;
    line-height: 1.6;
    font-weight: 300;
    margin-bottom: 0;
}

/* Hint pills row */
.hint-row {
    display: flex;
    gap: 8px;
    margin-top: 20px;
    flex-wrap: wrap;
    justify-content: center;
}

/* Hint buttons — styled via Streamlit button override below */
div[data-testid="stHorizontalBlock"] .stButton button,
.hint-btn-wrap .stButton button {
    background: rgba(255,255,255,0.04) !important;
    color: rgba(232,245,238,0.6) !important;
    border: 1px solid rgba(52,211,152,0.15) !important;
    border-radius: 100px !important;
    font-size: 13px !important;
    padding: 8px 18px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 400 !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
    width: auto !important;
}

div[data-testid="stHorizontalBlock"] .stButton button:hover,
.hint-btn-wrap .stButton button:hover {
    background: rgba(52,211,152,0.1) !important;
    color: #34d399 !important;
    border-color: rgba(52,211,152,0.35) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(16,185,129,0.15) !important;
}

/* ─── Chat Area ────────────────────────────────────── */
.chat-area {
    padding: 32px 24px 140px;
    max-width: 640px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
}

/* ─── Messages ─────────────────────────────────────── */
.msg-row {
    display: flex;
    margin-bottom: 20px;
    animation: msg-in 0.35s cubic-bezier(0.34, 1.2, 0.64, 1) both;
}

@keyframes msg-in {
    from { opacity: 0; transform: translateY(14px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

.msg-row.user  { justify-content: flex-end; }
.msg-row.bot   { justify-content: flex-start; }

/* User bubble — deep royal blue */
.bubble-user {
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    color: #fff;
    padding: 14px 20px;
    border-radius: 18px 18px 4px 18px;
    max-width: 78%;
    font-size: 16px;
    line-height: 1.7;
    box-shadow:
        0 4px 24px rgba(37, 99, 235, 0.35),
        inset 0 1px 0 rgba(255,255,255,0.15);
    word-wrap: break-word;
}

/* Bot bubble — glass light-blue / green tinted */
.bubble-bot {
    background: rgba(209, 250, 229, 0.06);
    border: 1px solid rgba(52, 211, 152, 0.15);
    backdrop-filter: blur(16px);
    color: #d1fae5;
    padding: 14px 20px;
    border-radius: 18px 18px 18px 4px;
    max-width: 82%;
    font-size: 16px;
    line-height: 1.8;
    box-shadow:
        0 4px 24px rgba(0,0,0,0.25),
        inset 0 1px 0 rgba(255,255,255,0.06);
    word-wrap: break-word;
    letter-spacing: 0.01em;
}

/* Avatar dots */
.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    margin-top: 2px;
}

.avatar-bot {
    background: linear-gradient(135deg, #059669, #10b981);
    margin-right: 10px;
    box-shadow: 0 0 12px rgba(16,185,129,0.3);
}

.avatar-user {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6);
    margin-left: 10px;
    box-shadow: 0 0 12px rgba(59,130,246,0.3);
}

/* Typing indicator */
.typing-indicator {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 4px 2px;
}

.typing-dot {
    width: 6px;
    height: 6px;
    background: #34d399;
    border-radius: 50%;
    animation: typing 1.2s infinite ease-in-out;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
    40%            { transform: scale(1.1); opacity: 1; }
}

/* ─── Chat Input ───────────────────────────────────── */
/* Float the input bar above bottom */
[data-testid="stBottom"] {
    background: transparent !important;
}

[data-testid="stBottom"] > div {
    background: transparent !important;
    padding: 0 24px 28px !important;
    max-width: 640px !important;
    margin: 0 auto !important;
}

[data-testid="stChatInput"] {
    background: rgba(12, 32, 20, 0.7) !important;
    border: 1px solid rgba(52, 211, 152, 0.2) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(24px) !important;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(52,211,152,0.06) !important;
}

[data-testid="stChatInputTextArea"] {
    color: #e8f5ee !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 16px !important;
}

[data-testid="stChatInputTextArea"]::placeholder {
    color: rgba(232, 245, 238, 0.28) !important;
}

/* Send button green glow */
[data-testid="stChatInputSubmitButton"] button {
    background: linear-gradient(135deg, #059669, #10b981) !important;
    border-radius: 10px !important;
    box-shadow: 0 0 16px rgba(16,185,129,0.4) !important;
}

/* ─── File uploader override ───────────────────────── */
[data-testid="stFileUploader"] {
    background: transparent !important;
}

[data-testid="stFileUploader"] section {
    background: rgba(16,185,129,0.04) !important;
    border: 1.5px dashed rgba(52,211,152,0.22) !important;
    border-radius: 14px !important;
    padding: 20px !important;
}

[data-testid="stFileUploader"] section:hover {
    background: rgba(16,185,129,0.08) !important;
    border-color: rgba(52,211,152,0.42) !important;
}

[data-testid="stFileUploader"] label {
    color: rgba(232,245,238,0.7) !important;
    font-size: 13px !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] {
    color: rgba(232,245,238,0.55) !important;
    font-size: 12px !important;
}

/* Button overrides — sidebar remove doc button */
[data-testid="stSidebar"] .stButton button {
    background: rgba(239,68,68,0.1) !important;
    color: rgba(252,165,165,0.8) !important;
    border: 1px solid rgba(239,68,68,0.2) !important;
    border-radius: 10px !important;
    font-size: 12px !important;
    padding: 6px 14px !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.2s !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(239,68,68,0.18) !important;
    border-color: rgba(239,68,68,0.35) !important;
}

/* Spinner */
[data-testid="stSpinner"] {
    color: #34d399 !important;
}

/* Divider */
.sidebar-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(52,211,152,0.15), transparent);
    margin: 20px 0;
}

/* scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(52,211,152,0.2); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(52,211,152,0.4); }

/* ─── Main Upload Zone ─────────────────────────────── */
.main-upload-zone {
    margin-top: 4px;
}

.main-upload-zone [data-testid="stFileUploader"] section {
    background: rgba(16,185,129,0.05) !important;
    border: 1.5px dashed rgba(52,211,152,0.3) !important;
    border-radius: 20px !important;
    padding: 40px 32px !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}

.main-upload-zone [data-testid="stFileUploader"] section:hover {
    background: rgba(16,185,129,0.09) !important;
    border-color: rgba(52,211,152,0.55) !important;
    box-shadow: 0 0 40px rgba(16,185,129,0.08) !important;
}

.main-upload-zone [data-testid="stFileUploaderDropzoneInstructions"] div span {
    font-size: 15px !important;
    color: rgba(232,245,238,0.75) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.main-upload-zone [data-testid="stFileUploaderDropzoneInstructions"] div small {
    color: rgba(52,211,152,0.6) !important;
    font-size: 12px !important;
}

</style>
""", unsafe_allow_html=True)


# ─── Session State ──────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "doc_name" not in st.session_state:
    st.session_state.doc_name = None
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "status" not in st.session_state:
    st.session_state.status = "idle"  # idle | processing | ready | thinking


# ─── Sidebar ────────────────────────────────────────────────
with st.sidebar:

    # Brand
    st.markdown("""
        <div class="brand">
            <div class="brand-icon">✦</div>
            <div class="brand-name">DocMind</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">Document</div>', unsafe_allow_html=True)

    if st.session_state.session_id is None:
        st.markdown('<div style="font-size:11px; color:rgba(232,245,238,0.35); margin-bottom:10px;">Or upload here if sidebar is open</div>', unsafe_allow_html=True)
        # Upload widget (sidebar copy — main panel also has one)
        uploaded_file = st.file_uploader(
            "Drop your PDF here",
            type=["pdf"],
            label_visibility="collapsed",
            key="sidebar_uploader"
        )

        if uploaded_file:
            st.session_state.status = "processing"
            with st.spinner("Embedding document…"):
                try:
                    response = requests.post(
                        f"{API_URL}/upload",
                        files={"file": uploaded_file}
                    )
                    result = response.json()
                    st.session_state.session_id = result["session_id"]
                    st.session_state.doc_name = uploaded_file.name
                    st.session_state.status = "ready"
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    st.session_state.status = "idle"
            st.rerun()
    else:
        # Show uploaded doc info
        st.markdown(f"""
            <div class="doc-pill">
                <span>📄</span>
                <span>{st.session_state.doc_name or "document.pdf"}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        if st.button("✕ Remove document"):
            st.session_state.session_id = None
            st.session_state.doc_name = None
            st.session_state.messages = []
            st.session_state.status = "idle"
            st.rerun()

    # ── Status Panel ──
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">Status</div>', unsafe_allow_html=True)

    # Connection
    st.markdown("""
        <div class="status-card">
            <div class="status-dot active"></div>
            <div class="status-text">
                API Connected
                <span>localhost:8000</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Document status
    if st.session_state.status == "idle":
        doc_dot = "idle"
        doc_label = "No document loaded"
        doc_sub = "Upload a PDF to begin"
    elif st.session_state.status == "processing":
        doc_dot = "loading"
        doc_label = "Processing…"
        doc_sub = "Chunking & embedding"
    elif st.session_state.status == "ready":
        doc_dot = "done"
        doc_label = "Document ready"
        doc_sub = "Ask anything below"
    elif st.session_state.status == "thinking":
        doc_dot = "loading"
        doc_label = "Thinking…"
        doc_sub = "Retrieving context"
    else:
        doc_dot = "idle"
        doc_label = "Standby"
        doc_sub = ""

    st.markdown(f"""
        <div class="status-card">
            <div class="status-dot {doc_dot}"></div>
            <div class="status-text">
                {doc_label}
                <span>{doc_sub}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Message count
    msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.markdown(f"""
        <div class="status-card">
            <div class="status-dot {'active' if msg_count > 0 else 'idle'}"></div>
            <div class="status-text">
                {msg_count} question{"s" if msg_count != 1 else ""} asked
                <span>this session</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ─── Main Area ──────────────────────────────────────────────

SUGGESTED_QUESTIONS = [
    ("📋", "Give me a summary of the entire document"),
    ("🔍", "What are the key findings or conclusions?"),
    ("💡", "Explain the main concepts in simple terms"),
    ("📊", "Are there any tables, numbers, or statistics mentioned?"),
    ("📌", "What are the most important sections?"),
    ("❓", "What questions does this document answer?"),
]

if not st.session_state.session_id:
    # Welcome + upload screen
    st.markdown("""
        <div class="welcome-wrap">
            <div class="welcome-glyph">✦DocMind</div>
            <h1 class="welcome-title">
                Ask anything about<br>
                <em>your documents</em>
            </h1>
            <p class="welcome-sub">
                Drop a PDF below to get started. Then ask questions in plain English —
                DocMind retrieves the exact context and answers precisely.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Centered upload widget ──
    _, upload_col, _ = st.columns([1, 1.6, 1])
    with upload_col:
        st.markdown('<div class="main-upload-zone">', unsafe_allow_html=True)
        uploaded_file_main = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            label_visibility="collapsed",
            key="main_uploader"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_file_main:
            st.session_state.status = "processing"
            with st.spinner("Processing document…"):
                try:
                    response = requests.post(
                        f"{API_URL}/upload",
                        files={"file": uploaded_file_main}
                    )
                    result = response.json()
                    st.session_state.session_id = result["session_id"]
                    st.session_state.doc_name = uploaded_file_main.name
                    st.session_state.status = "ready"
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    st.session_state.status = "idle"
            st.rerun()

    # Hint pills
    st.markdown("""
        <div style="display:flex; justify-content:center; margin-top: 16px; margin-bottom: 4px;">
            <div class="hint-row">
                <div class="hint-pill">📋 Summarize key points</div>
                <div class="hint-pill">🔍 Find specific data</div>
                <div class="hint-pill">💡 Explain concepts</div>
                <div class="hint-pill">📊 Extract tables</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

else:
    # Chat history
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
                <div class="msg-row user">
                    <div class="bubble-user">{message["content"]}</div>
                    <div class="avatar avatar-user">U</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="msg-row bot">
                    <div class="avatar avatar-bot">✦</div>
                    <div class="bubble-bot">{message["content"]}</div>
                </div>
            """, unsafe_allow_html=True)

    # Typing indicator when thinking
    if st.session_state.is_thinking:
        st.markdown("""
            <div class="msg-row bot">
                <div class="avatar avatar-bot">✦</div>
                <div class="bubble-bot">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Suggested questions (shown only before first message)
    if not st.session_state.messages and not st.session_state.is_thinking:
        st.markdown("""
            <div style="margin-top: 32px; margin-bottom: 8px;">
                <div class="sq-label" style="text-align:left; padding-left: 48px;">Suggested questions</div>
            </div>
        """, unsafe_allow_html=True)
        _, sq_col, _ = st.columns([1, 3, 1])
        with sq_col:
            st.markdown('<div class="suggested-q-wrap">', unsafe_allow_html=True)
            for icon, question in SUGGESTED_QUESTIONS:
                if st.button(f"{icon}  {question}", key=f"chat_sq_{question[:20]}"):
                    st.session_state["pending_hint"] = question
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Consume pending hint as a message
    if "pending_hint" in st.session_state and st.session_state.session_id:
        hint_msg = st.session_state.pop("pending_hint")
        st.session_state.messages.append({"role": "user", "content": hint_msg})
        st.session_state.is_thinking = True
        st.session_state.status = "thinking"
        st.rerun()

    # Chat input
    user_input = st.chat_input("Type your question here…")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.is_thinking = True
        st.session_state.status = "thinking"
        st.rerun()

# Answer fetch on rerun when thinking
if st.session_state.is_thinking and st.session_state.messages:
    last_user_msg = next(
        (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
        None
    )
    if last_user_msg:
        try:
            response = requests.post(
                f"{API_URL}/ask",
                params={
                    "session_id": st.session_state.session_id,
                    "question": last_user_msg
                }
            )
            answer = response.json().get("answer", "Sorry, I could not get a response.")
        except Exception as e:
            answer = f"⚠️ Error contacting the API: {e}"

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.is_thinking = False
        st.session_state.status = "ready"
        st.rerun()
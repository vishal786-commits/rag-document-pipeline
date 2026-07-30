import streamlit as st
import requests
import time
import os

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="DocMind",
    page_icon="âœ¦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">

<style>

/* â”€â”€â”€ Reset & Base â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Sidebar Logo / Brand â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Sidebar Section Labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.sidebar-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(52, 211, 152, 0.5);
    margin-bottom: 12px;
    margin-top: 8px;
}

/* â”€â”€â”€ Upload Zone â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Status Cards â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Hide Streamlit chrome â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* â”€â”€ Sidebar collapse / expand tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ Main Column Padding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* â”€â”€â”€ Welcome Screen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* Hint buttons â€” styled via Streamlit button override below */
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

/* â”€â”€â”€ Chat Area â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.chat-area {
    padding: 32px 24px 140px;
    max-width: 640px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
}

/* â”€â”€â”€ Messages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* User bubble â€” deep royal blue */
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

/* Bot bubble â€” glass light-blue / green tinted */
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

/* â”€â”€â”€ Chat Input â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€â”€ File uploader override â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* Button overrides â€” sidebar remove doc button */
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

/* â”€â”€â”€ Main Upload Zone â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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


# â”€â”€â”€ API helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@st.cache_data(ttl=60)
def fetch_policies():
    """The policy list, from the API. Cached so the sidebar is cheap."""
    try:
        response = requests.get(f"{API_URL}/policies", timeout=10)
        response.raise_for_status()
        return response.json()["policies"], None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


@st.cache_data(ttl=15)
def fetch_health():
    """Actually probe the API. The old status card was hardcoded to green."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# â”€â”€â”€ Session State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False

policies, policies_error = fetch_policies()
health, health_error = fetch_health()


# â”€â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with st.sidebar:
    st.markdown("""
        <div class="brand">
            <div class="brand-icon">âœ¦</div>
            <div class="brand-name">Aster Policy Assistant</div>
        </div>
    """, unsafe_allow_html=True)

    # â”€â”€ Connection (a real probe, not a hardcoded green dot) â”€â”€
    st.markdown('<div class="sidebar-label">Status</div>', unsafe_allow_html=True)
    if health:
        ready = health.get("knowledge_base") == "ready"
        st.markdown(f"""
            <div class="status-card">
                <div class="status-dot {'active' if ready else 'idle'}"></div>
                <div class="status-text">
                    {"Knowledge base ready" if ready else "Knowledge base unavailable"}
                    <span>{API_URL}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="status-card">
                <div class="status-dot idle"></div>
                <div class="status-text">
                    API unreachable
                    <span>{health_error}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

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

    if st.session_state.messages and st.button("âœ• Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    # â”€â”€ Policies in the knowledge base â”€â”€
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sidebar-label">Knowledge base Â· {len(policies)} policies</div>',
        unsafe_allow_html=True,
    )

    if policies_error:
        st.error(f"Could not load policies: {policies_error}")
    else:
        expired = [p for p in policies if p["status"] == "expired"]
        if expired:
            st.markdown(
                f'<div style="font-size:11px; color:#f0b429; margin-bottom:8px;">'
                f'âš  {len(expired)} past their review date</div>',
                unsafe_allow_html=True,
            )
        with st.expander("Browse policies"):
            for p in policies:
                badge = " âš " if p["status"] == "expired" else ""
                st.markdown(
                    f'<div style="font-size:11px; padding:3px 0; '
                    f'color:rgba(232,245,238,0.7);">{p["title"]}{badge}</div>',
                    unsafe_allow_html=True,
                )


# â”€â”€â”€ Main Area â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SUGGESTED_QUESTIONS = [
    ("ðŸ ", "How quickly must we respond to a report of damp and mould?"),
    ("ðŸ”§", "What are a tenant's responsibilities for reporting repairs?"),
    ("ðŸ”¥", "What does the Fire Safety Policy require for risk assessments?"),
    ("âš–ï¸", "How does the complaints process work and what are the timescales?"),
    ("ðŸ›¡ï¸", "What support is available under the Domestic Abuse Policy?"),
    ("ðŸ“‹", "Which policies are past their review date?"),
]


def render_answer(message):
    """An assistant turn: the answer, an expiry banner, and its citations."""
    with st.chat_message("assistant"):
        st.markdown(message["content"])

        if message.get("expired_warning"):
            st.warning(message["expired_warning"], icon="âš ï¸")

        citations = message.get("citations") or []
        if citations:
            inferred = citations[0].get("inferred")
            label = (
                f"Sources consulted ({len(citations)})"
                if inferred
                else f"Sources cited ({len(citations)})"
            )
            with st.expander(label):
                if inferred:
                    st.caption(
                        "The answer did not cite specific extracts, so everything "
                        "retrieved is listed."
                    )
                for c in citations:
                    flag = " Â· expired" if c["status"] == "expired" else ""
                    st.markdown(
                        f"**[{c['n']}] {c['source_file']}** â€” page {c['page']}{flag}  \n"
                        f'<span style="font-size:11px; color:rgba(232,245,238,0.5);">'
                        f"{c['heading_path']}</span>",
                        unsafe_allow_html=True,
                    )


if not st.session_state.messages and not st.session_state.is_thinking:
    st.markdown("""
        <div class="welcome-wrap">
            <div class="welcome-glyph">âœ¦ Aster Policy Assistant</div>
            <h1 class="welcome-title">
                Ask anything about<br>
                <em>Aster's policies</em>
            </h1>
            <p class="welcome-sub">
                Answers come only from the policy library, with a citation to the
                document and page they came from.
            </p>
        </div>
    """, unsafe_allow_html=True)

    _, sq_col, _ = st.columns([1, 3, 1])
    with sq_col:
        st.markdown('<div class="suggested-q-wrap">', unsafe_allow_html=True)
        for icon, question in SUGGESTED_QUESTIONS:
            if st.button(f"{icon}  {question}", key=f"sq_{question[:24]}"):
                st.session_state["pending_hint"] = question
        st.markdown('</div>', unsafe_allow_html=True)
else:
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
            render_answer(message)

    if st.session_state.is_thinking:
        st.markdown("""
            <div class="msg-row bot">
                <div class="avatar avatar-bot">âœ¦</div>
                <div class="bubble-bot">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# Consume a suggested question as if it had been typed.
if "pending_hint" in st.session_state:
    st.session_state.messages.append(
        {"role": "user", "content": st.session_state.pop("pending_hint")}
    )
    st.session_state.is_thinking = True
    st.rerun()

user_input = st.chat_input("Ask about an Aster policyâ€¦")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.is_thinking = True
    st.rerun()


# â”€â”€â”€ Fetch the answer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if st.session_state.is_thinking and st.session_state.messages:
    question = next(
        (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), None
    )
    if question:
        # Prior turns, as (question, answer) pairs the API replays to the model.
        history, pending = [], None
        for m in st.session_state.messages[:-1]:
            if m["role"] == "user":
                pending = m["content"]
            elif pending is not None:
                history.append((pending, m["content"]))
                pending = None

        try:
            response = requests.post(
                f"{API_URL}/ask",
                json={"question": question, "history": history},
                timeout=90,
            )
            response.raise_for_status()
            result = response.json()
            message = {
                "role": "assistant",
                "content": result["answer"],
                "citations": result.get("citations", []),
                "expired_warning": result.get("expired_warning"),
            }
        except Exception as e:
            message = {
                "role": "assistant",
                "content": f"âš ï¸ Could not reach the API: {type(e).__name__}: {e}",
                "citations": [],
                "expired_warning": None,
            }

        st.session_state.messages.append(message)
        st.session_state.is_thinking = False
        st.rerun()

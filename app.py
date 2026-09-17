from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from crc_utils import calculate_crc32, format_crc, verify_crc
from error_simulator import ERROR_TYPES, simulate_error

try:
    import plotly.express as px
except ImportError:  # Plotly is optional at runtime; Streamlit charts are the fallback.
    px = None


APP_TITLE = "🔐 CRC-32 Communication Reliability Monitor"
APP_SUBTITLE = "Real-Time Message Integrity, Error Detection & Retransmission System"

LOG_COLUMNS = [
    "Time",
    "Sender",
    "Receiver",
    "Message",
    "Error Type",
    "Reference CRC",
    "Current CRC",
    "Status",
    "Action",
]

STATE_DEFAULTS = {
    "original_message": None,
    "reference_crc": None,
    "received_message": "",
    "current_crc": None,
    "verification_status": "WAITING",
    "error_type": "No Error",
    "messages_sent": 0,
    "valid_messages": 0,
    "corrupted_messages": 0,
    "retransmissions": 0,
    "total_attempts": 0,
    "communication_log": [],
    "test_results": [],
    "last_action": "System ready",
    "message_input": "HELLO",
    "navigation": "🏠 Dashboard",
    "auto_retransmission": False,
}

# Populate missing Streamlit session keys while preserving any state from the current visit.
def init_session_state() -> None:
    # Streamlit reruns this script for each interaction, so these keys persist the UI workflow.
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value

# Restore every application counter, message field, log, and navigation setting to defaults.
def reset_session() -> None:
    # Copy list defaults so a reset starts with fresh logs/results rather than shared list objects.
    for key, value in STATE_DEFAULTS.items():
        st.session_state[key] = value.copy() if isinstance(value, list) else value

# Report whether a sender message and its reference CRC have already been created.
def has_message() -> bool:
    return st.session_state.original_message is not None

# Render a status label as escaped HTML with the matching visual state class.
def status_badge(status: str) -> str:
    status = (status or "WAITING").upper()
    classes = {
        "VALID": "badge-valid",
        "CORRUPTED": "badge-corrupted",
        "WAITING": "badge-waiting",
    }
    return f"<span class='status-badge {classes.get(status, 'badge-waiting')}'>{escape(status)}</span>"

# Convert a numerator and denominator into a one-decimal percentage for analytics metrics.
def rate(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0

# Count completed valid and corrupted verification outcomes.
def total_outcomes() -> int:
    return st.session_state.valid_messages + st.session_state.corrupted_messages

# Calculate the percentage of completed attempts whose CRCs matched.
def success_rate() -> float:
    return rate(st.session_state.valid_messages, total_outcomes())

# Calculate the percentage of completed attempts whose CRCs differed.
def error_rate() -> float:
    return rate(st.session_state.corrupted_messages, total_outcomes())

# Provide a readable dashboard label for missing, empty, or populated message text.
def display_message(message: str | None) -> str:
    if message is None:
        return "No message sent yet"
    if message == "":
        return "(empty message)"
    return message

# Append one timestamped sender/receiver event with the current CRC values to the log.
def add_log(status: str, action: str, error_type: str | None = None, message: str | None = None) -> None:
    # The log captures the complete sender-to-receiver result used by analytics and CSV export.
    error_label = "None" if error_type in (None, "No Error") else error_type.replace(" Error", "")
    st.session_state.communication_log.append(
        {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Sender": "User A",
            "Receiver": "User B",
            "Message": display_message(message if message is not None else st.session_state.original_message),
            "Error Type": error_label,
            "Reference CRC": format_crc(st.session_state.reference_crc),
            "Current CRC": format_crc(st.session_state.current_crc),
            "Status": status,
            "Action": action,
        }
    )

# Increment total attempts and the matching valid/corrupted analytics counter.
def record_attempt(status: str) -> None:
    # Attempts include the initial delivery, simulated checks, manual verification, and retransmissions.
    st.session_state.total_attempts += 1
    if status == "VALID":
        st.session_state.valid_messages += 1
    elif status == "CORRUPTED":
        st.session_state.corrupted_messages += 1

# Store received text, calculate its CRC, and update the receiver verification status.
def set_received_message(received: str, error_type: str = "No Error") -> str:
    # Receiver CRC is calculated from received text, then compared with the sender's stored reference.
    st.session_state.received_message = received
    st.session_state.current_crc = calculate_crc32(received)
    st.session_state.error_type = error_type
    status = "VALID" if st.session_state.reference_crc == st.session_state.current_crc else "CORRUPTED"
    st.session_state.verification_status = status
    return status


# Sender stores the original message and creates the reference CRC.
def send_message(message: str) -> str:
    # Sending creates the reference CRC before the first received-message verification.
    st.session_state.original_message = message
    st.session_state.reference_crc = calculate_crc32(message)
    st.session_state.messages_sent += 1
    status = set_received_message(message, "No Error")
    record_attempt(status)
    st.session_state.last_action = "Message sent and CRC generated"
    add_log(status, "Delivered" if status == "VALID" else "Retransmission Required", "No Error", message)
    return status

# Recalculate and verify the currently received message, then record the verification action.
def verify_current_message(action: str = "Verified") -> str | None:
    # The receiver recomputes CRC from its current text; a mismatch drives the retransmission path.
    if not has_message():
        return None

    st.session_state.current_crc = calculate_crc32(st.session_state.received_message)
    status = "VALID" if verify_crc(st.session_state.received_message, st.session_state.reference_crc) else "CORRUPTED"
    st.session_state.verification_status = status
    record_attempt(status)
    st.session_state.last_action = "CRC verification complete"
    add_log(status, "Delivered" if status == "VALID" else "Retransmission Required", st.session_state.error_type)
    return status

# Restore the original text as a valid delivery and log a manual or automatic retransmission.
def perform_retransmission(auto: bool = False) -> str | None:
    # Retransmission replaces corrupted text with the original and records a successful recovery attempt.
    if not has_message():
        return None

    original = st.session_state.original_message or ""
    st.session_state.retransmissions += 1
    st.session_state.received_message = original
    st.session_state.current_crc = calculate_crc32(original)
    st.session_state.error_type = "No Error"
    st.session_state.verification_status = "VALID"
    record_attempt("VALID")
    action = "Auto Retransmitted" if auto else "Retransmitted"
    st.session_state.last_action = action
    add_log("VALID", action, "No Error", original)
    return "VALID"

# Load the HELLO demonstration into session state without creating a new communication log row.
def load_demo() -> None:
    # Demo state is populated directly so the presentation opens on a known valid HELLO exchange.
    reset_session()
    demo_message = "HELLO"
    st.session_state.message_input = demo_message
    st.session_state.original_message = demo_message
    st.session_state.reference_crc = calculate_crc32(demo_message)
    st.session_state.received_message = demo_message
    st.session_state.current_crc = calculate_crc32(demo_message)
    st.session_state.verification_status = "VALID"
    st.session_state.navigation = "📡 Communication"
    st.session_state.last_action = "Demo loaded with HELLO"

# Convert the session's communication-event dictionaries into the table displayed by Streamlit.
def communication_log_dataframe() -> pd.DataFrame:
    # Keep column order stable so the on-screen table and downloaded report have the same schema.
    return pd.DataFrame(st.session_state.communication_log, columns=LOG_COLUMNS)

# Serialize the communication table as UTF-8 CSV bytes for the download control.
def csv_report_bytes() -> bytes:
    return communication_log_dataframe().to_csv(index=False).encode("utf-8")

# Inject the dashboard's visual theme and layout CSS into the Streamlit page.
def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #07111f;
                --panel: #0d1726;
                --panel-2: #101f33;
                --border: #21405f;
                --text: #f4f8ff;
                --muted: #9fb4c8;
                --blue: #2bb7ff;
                --cyan: #36e1d4;
                --green: #25d07f;
                --red: #ff5268;
                --orange: #ffb84d;
                --purple: #9b7cff;
            }

            .stApp {
                background:
                    linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
                    linear-gradient(135deg, #07111f 0%, #0b1625 45%, #091423 100%);
                background-size: 36px 36px, 36px 36px, auto;
                color: var(--text);
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #08111e 0%, #0e1a2c 100%);
                border-right: 1px solid rgba(54, 225, 212, 0.2);
            }

            [data-testid="stSidebar"] * {
                color: #eef7ff;
            }

            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                max-width: 1400px;
            }

            h1, h2, h3 {
                letter-spacing: 0;
            }

            h1 {
                color: #f7fbff;
                font-weight: 800;
            }

            .app-subtitle {
                color: var(--muted);
                font-size: 1.1rem;
                margin-top: -0.7rem;
                margin-bottom: 1.5rem;
            }

            .section-title {
                font-size: 1.4rem;
                font-weight: 750;
                margin: 1rem 0 0.65rem 0;
                color: #f6fbff;
            }

            .metric-card {
                background: linear-gradient(180deg, rgba(16, 31, 51, 0.98), rgba(11, 22, 37, 0.98));
                border: 1px solid rgba(43, 183, 255, 0.22);
                border-left: 4px solid var(--accent);
                border-radius: 8px;
                padding: 1rem;
                min-height: 116px;
                box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
            }

            .metric-label {
                color: var(--muted);
                font-size: 0.88rem;
                font-weight: 650;
                text-transform: uppercase;
            }

            .metric-value {
                color: var(--text);
                font-size: 2.1rem;
                font-weight: 850;
                line-height: 1.05;
                margin-top: 0.55rem;
            }

            .metric-note {
                color: #b8c8d9;
                font-size: 0.82rem;
                margin-top: 0.45rem;
            }

            .info-panel, .comm-panel {
                background: rgba(13, 23, 38, 0.88);
                border: 1px solid rgba(57, 105, 150, 0.5);
                border-radius: 8px;
                padding: 1rem 1.1rem;
                box-shadow: 0 16px 42px rgba(0, 0, 0, 0.18);
            }

            .status-box {
                border-radius: 8px;
                padding: 1.35rem;
                margin: 1rem 0;
                border: 1px solid;
            }

            .status-valid {
                background: rgba(37, 208, 127, 0.12);
                border-color: rgba(37, 208, 127, 0.55);
            }

            .status-corrupted {
                background: rgba(255, 82, 104, 0.12);
                border-color: rgba(255, 82, 104, 0.62);
            }

            .status-waiting {
                background: rgba(255, 184, 77, 0.11);
                border-color: rgba(255, 184, 77, 0.55);
            }

            .status-heading {
                font-size: clamp(1.3rem, 2vw, 2rem);
                font-weight: 850;
                margin-bottom: 0.4rem;
            }

            .status-message {
                color: #d8e8f6;
                font-size: 1rem;
            }

            .kv-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 0.5rem;
            }

            .kv-item {
                background: rgba(255, 255, 255, 0.035);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0.78rem;
                min-height: 82px;
            }

            .kv-label {
                color: var(--muted);
                font-size: 0.78rem;
                text-transform: uppercase;
                font-weight: 700;
            }

            .kv-value {
                color: #f8fbff;
                font-size: 1rem;
                font-weight: 700;
                margin-top: 0.35rem;
                word-break: break-word;
            }

            .crc-value {
                color: var(--cyan);
                font-family: Consolas, Monaco, monospace;
                letter-spacing: 0.04em;
            }

            .status-badge {
                display: inline-block;
                border-radius: 999px;
                padding: 0.28rem 0.68rem;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0;
            }

            .badge-valid {
                background: rgba(37, 208, 127, 0.18);
                border: 1px solid rgba(37, 208, 127, 0.58);
                color: #8affc3;
            }

            .badge-corrupted {
                background: rgba(255, 82, 104, 0.18);
                border: 1px solid rgba(255, 82, 104, 0.62);
                color: #ffacb8;
            }

            .badge-waiting {
                background: rgba(255, 184, 77, 0.16);
                border: 1px solid rgba(255, 184, 77, 0.58);
                color: #ffd99c;
            }

            .flow-strip {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                align-items: center;
                margin: 1rem 0 0.5rem 0;
            }

            .flow-step {
                background: rgba(43, 183, 255, 0.11);
                border: 1px solid rgba(43, 183, 255, 0.28);
                color: #dff5ff;
                border-radius: 8px;
                padding: 0.45rem 0.65rem;
                font-size: 0.85rem;
                font-weight: 700;
            }

            .flow-arrow {
                color: var(--cyan);
                font-weight: 900;
            }

            .demo-box {
                background: rgba(54, 225, 212, 0.08);
                border: 1px solid rgba(54, 225, 212, 0.3);
                border-radius: 8px;
                padding: 0.85rem;
                color: #dffcff;
                font-size: 0.88rem;
                line-height: 1.45;
                margin-top: 0.8rem;
            }

            div.stButton > button,
            div.stDownloadButton > button {
                border-radius: 8px;
                border: 1px solid rgba(43, 183, 255, 0.45);
                background: linear-gradient(90deg, rgba(43, 183, 255, 0.22), rgba(54, 225, 212, 0.16));
                color: #f5fbff;
                font-weight: 750;
                min-height: 2.55rem;
            }

            div.stButton > button:hover,
            div.stDownloadButton > button:hover {
                border-color: rgba(54, 225, 212, 0.85);
                color: #ffffff;
                background: linear-gradient(90deg, rgba(43, 183, 255, 0.32), rgba(54, 225, 212, 0.25));
            }

            [data-testid="stMetric"] {
                background: rgba(16, 31, 51, 0.82);
                border: 1px solid rgba(43, 183, 255, 0.22);
                border-radius: 8px;
                padding: 0.75rem;
            }

            @media (max-width: 900px) {
                .kv-grid {
                    grid-template-columns: 1fr;
                }
                .metric-card {
                    min-height: 96px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Render the shared application title and subtitle at the top of each page.
def render_header() -> None:
    st.markdown(f"# {APP_TITLE}")
    st.markdown(f"<div class='app-subtitle'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)

# Render one styled metric card with an escaped label, value, note, and accent color.
def render_metric_card(label: str, value: str | int, note: str = "", color: str = "#2bb7ff") -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent:{color}">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(str(value))}</div>
            <div class="metric-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Arrange the four headline transmission, integrity, corruption, and retransmission metrics.
def render_core_metrics() -> None:
    cols = st.columns(4)
    metrics = [
        ("📤 Messages Sent", st.session_state.messages_sent, "Original transmissions", "#2bb7ff"),
        ("✅ Valid Messages", st.session_state.valid_messages, "CRC matched", "#25d07f"),
        ("❌ Corrupted Messages", st.session_state.corrupted_messages, "CRC mismatch", "#ff5268"),
        ("🔄 Retransmissions", st.session_state.retransmissions, "Recovered deliveries", "#ffb84d"),
    ]
    for col, metric in zip(cols, metrics):
        with col:
            render_metric_card(*metric)

# Select the status-specific message and render the valid, corrupted, or waiting banner.
def render_status_box() -> None:
    status = st.session_state.verification_status
    if status == "VALID":
        class_name = "status-valid"
        heading = "🟢 MESSAGE VALID"
        message = "CRC verification successful. Message integrity confirmed."
    elif status == "CORRUPTED":
        class_name = "status-corrupted"
        heading = "🔴 MESSAGE CORRUPTED"
        message = "CRC mismatch detected. Retransmission required."
    else:
        class_name = "status-waiting"
        heading = "🟡 WAITING FOR TRANSMISSION"
        message = "Send a message to generate CRC-32 and begin verification."

    st.markdown(
        f"""
        <div class="status-box {class_name}">
            <div class="status-heading">{heading}</div>
            <div class="status-message">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Render current message/CRC details plus attempt, error-rate, and success-rate metrics.
def render_current_status_panel() -> None:
    st.markdown("<div class='section-title'>Communication Status</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="info-panel">
            <div class="kv-grid">
                <div class="kv-item">
                    <div class="kv-label">Current Message</div>
                    <div class="kv-value">{escape(display_message(st.session_state.original_message))}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Reference CRC-32</div>
                    <div class="kv-value crc-value">{format_crc(st.session_state.reference_crc)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Received Message</div>
                    <div class="kv-value">{escape(display_message(st.session_state.received_message if has_message() else None))}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Current CRC-32</div>
                    <div class="kv-value crc-value">{format_crc(st.session_state.current_crc)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Verification Status</div>
                    <div class="kv-value">{status_badge(st.session_state.verification_status)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Last Action</div>
                    <div class="kv-value">{escape(st.session_state.last_action)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_status_box()

    cols = st.columns(3)
    cols[0].metric("Total Attempts", st.session_state.total_attempts)
    cols[1].metric("Error Rate", f"{error_rate()}%")
    cols[2].metric("Success Rate", f"{success_rate()}%")

# Render the ordered visual path from message creation through logging and CSV export.
def render_flow() -> None:
    steps = [
        "Message",
        "CRC-32 Generation",
        "Transmission",
        "Error Simulation",
        "CRC Verification",
        "VALID / CORRUPTED",
        "Retransmission",
        "Successful Delivery",
        "Communication Log",
        "CSV Report",
    ]
    html = "<div class='flow-strip'>"
    for index, step in enumerate(steps):
        html += f"<span class='flow-step'>{escape(step)}</span>"
        if index < len(steps) - 1:
            html += "<span class='flow-arrow'>→</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# Render the communication event table and expose its CSV report download.
def render_communication_log() -> None:
    # This shared component is called by dashboard, communication, simulator, and analytics pages.
    st.markdown("<div class='section-title'>Communication Log</div>", unsafe_allow_html=True)
    df = communication_log_dataframe()
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button(
        "📥 DOWNLOAD CSV REPORT",
        data=csv_report_bytes(),
        file_name="crc32_communication_report.csv",
        mime="text/csv",
        width="stretch",
    )

# Show the receiver's retransmission controls based on current verification state.
def render_retransmission_panel() -> None:
    # Only corrupted state exposes a recovery action; valid and waiting states show guidance instead.
    if st.session_state.verification_status == "CORRUPTED":
        st.error("🔴 ERROR DETECTED")
        st.write("CRC mismatch detected. The receiver requests retransmission.")
        if st.button("🔄 RETRANSMIT ORIGINAL MESSAGE", width="stretch"):
            perform_retransmission(auto=False)
            st.success("🔄 Retransmitting... CRC verification complete. 🟢 MESSAGE SUCCESSFULLY VERIFIED")
    elif has_message():
        st.success("🟢 Receiver has a valid CRC match for the current message.")
    else:
        st.info("Send a message first to enable verification and retransmission.")

# Build sidebar actions for demo/reset, auto-retransmission, navigation, and instructions.
def render_sidebar() -> str:
    # Sidebar buttons mutate session state, while the radio selection determines the page rendered below.
    with st.sidebar:
        st.markdown("## Network Monitor")
        st.success("System Status: 🟢 ONLINE")

        if st.button("🎬 LOAD DEMO", width="stretch"):
            load_demo()
            st.success("Demo loaded: HELLO with CRC 3610A686")

        if st.button("🗑️ RESET SESSION", width="stretch"):
            reset_session()
            st.success("Session reset")

        st.checkbox("☑ Auto retransmission", key="auto_retransmission")

        page = st.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "📡 Communication",
                "⚡ Error Simulator",
                "📊 Analytics",
                "🧪 Test Center",
            ],
            key="navigation",
        )

        st.markdown(
            """
            <div class="demo-box">
                <strong>Demo Instructions</strong><br>
                1️⃣ Enter/send message<br>
                2️⃣ Generate CRC-32<br>
                3️⃣ Simulate communication error<br>
                4️⃣ Verify received message<br>
                5️⃣ Detect CRC mismatch<br>
                6️⃣ Request retransmission<br>
                7️⃣ Verify successful delivery
            </div>
            """,
            unsafe_allow_html=True,
        )
    return page

# Compose the dashboard overview from shared metrics, flow, status, and log components.
def dashboard_page() -> None:
    render_header()
    render_core_metrics()
    render_flow()
    render_current_status_panel()
    render_communication_log()

# Render sender and receiver controls for sending, verifying, and retransmitting messages.
def communication_page() -> None:
    # Sender controls create the reference CRC; receiver controls verify current text or request recovery.
    render_header()

    sender, receiver = st.columns(2)

    with sender:
        st.markdown("<div class='section-title'>👤 USER A — SENDER</div>", unsafe_allow_html=True)
        message = st.text_input("Enter message", key="message_input")
        if st.button("📤 SEND MESSAGE", width="stretch"):
            status = send_message(message)
            if status == "VALID":
                st.success("Message sent. CRC-32 generated and delivered successfully.")
            else:
                st.error("Message sent, but CRC mismatch was detected.")

        st.markdown(
            f"""
            <div class="comm-panel">
                <div class="kv-grid">
                    <div class="kv-item">
                        <div class="kv-label">Original Message</div>
                        <div class="kv-value">{escape(display_message(st.session_state.original_message))}</div>
                    </div>
                    <div class="kv-item">
                        <div class="kv-label">Generated CRC-32</div>
                        <div class="kv-value crc-value">{format_crc(st.session_state.reference_crc)}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with receiver:
        st.markdown("<div class='section-title'>👤 USER B — RECEIVER</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="comm-panel">
                <div class="kv-grid">
                    <div class="kv-item">
                        <div class="kv-label">Received Message</div>
                        <div class="kv-value">{escape(display_message(st.session_state.received_message if has_message() else None))}</div>
                    </div>
                    <div class="kv-item">
                        <div class="kv-label">Current CRC-32</div>
                        <div class="kv-value crc-value">{format_crc(st.session_state.current_crc)}</div>
                    </div>
                    <div class="kv-item">
                        <div class="kv-label">Verification</div>
                        <div class="kv-value">{status_badge(st.session_state.verification_status)}</div>
                    </div>
                    <div class="kv-item">
                        <div class="kv-label">Error Type</div>
                        <div class="kv-value">{escape(st.session_state.error_type)}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        verify_col, retransmit_col = st.columns(2)
        with verify_col:
            if st.button("🔍 VERIFY MESSAGE", width="stretch"):
                status = verify_current_message("Manual Verification")
                if status is None:
                    st.warning("Send a message first, then verify it at the receiver.")
                elif status == "VALID":
                    st.success("CRC verification successful. Message integrity confirmed.")
                else:
                    st.error("CRC mismatch detected. Retransmission required.")
                    if st.session_state.auto_retransmission:
                        perform_retransmission(auto=True)
                        st.success("Auto retransmission restored the original message and verified it.")

        with retransmit_col:
            if st.button("🔄 REQUEST RETRANSMISSION", width="stretch"):
                status = perform_retransmission(auto=False)
                if status is None:
                    st.warning("Send a message first before requesting retransmission.")
                else:
                    st.success("🔄 Retransmitting... CRC verification complete. 🟢 MESSAGE SUCCESSFULLY VERIFIED")

    render_current_status_panel()
    render_communication_log()

# Run a selected deterministic text corruption mode and immediately verify the resulting CRC.
def error_simulator_page() -> None:
    # The simulator deliberately changes visible characters, not raw wire bits, for clear classroom output.
    render_header()
    st.markdown("<div class='section-title'>⚡ Communication Error Simulator</div>", unsafe_allow_html=True)
    st.info("Select an error condition to simulate transmission corruption.")

    selected_error = st.radio("Error condition", ERROR_TYPES, horizontal=True)
    if st.button("⚡ SIMULATE ERROR", width="stretch"):
        if not has_message():
            st.warning("Send a message first. The simulator needs transmitted data to corrupt.")
        else:
            # Each selected corruption is logged as a receiver attempt before optional auto-retransmission.
            received = simulate_error(st.session_state.original_message or "", selected_error)
            status = set_received_message(received, selected_error)
            record_attempt(status)
            action = "Delivered" if status == "VALID" else "Retransmission Required"
            add_log(status, action, selected_error)
            st.session_state.last_action = f"{selected_error} simulated"
            if status == "VALID":
                st.success("No corruption detected. CRC values match.")
            else:
                st.error("CRC mismatch detected. Retransmission required.")
                if st.session_state.auto_retransmission:
                    perform_retransmission(auto=True)
                    st.success("Auto retransmission restored the original message and verified it.")

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="kv-grid">
                <div class="kv-item">
                    <div class="kv-label">Original</div>
                    <div class="kv-value">{escape(display_message(st.session_state.original_message))}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Received</div>
                    <div class="kv-value">{escape(display_message(st.session_state.received_message if has_message() else None))}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Reference CRC</div>
                    <div class="kv-value crc-value">{format_crc(st.session_state.reference_crc)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Current CRC</div>
                    <div class="kv-value crc-value">{format_crc(st.session_state.current_crc)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Status</div>
                    <div class="kv-value">{status_badge(st.session_state.verification_status)}</div>
                </div>
                <div class="kv-item">
                    <div class="kv-label">Error Type</div>
                    <div class="kv-value">{escape(st.session_state.error_type)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_status_box()
    render_retransmission_panel()
    render_communication_log()

# Build analytics tables and charts for outcomes, error types, retransmissions, and statuses.
def analytics_page() -> None:
    # Analytics derives chart data from counters and the same communication log used by the dashboard.
    render_header()
    st.markdown("<div class='section-title'>📊 Analytics</div>", unsafe_allow_html=True)

    metric_cols = st.columns(6)
    metric_cols[0].metric("Total Messages", st.session_state.messages_sent)
    metric_cols[1].metric("Valid Messages", st.session_state.valid_messages)
    metric_cols[2].metric("Corrupted Messages", st.session_state.corrupted_messages)
    metric_cols[3].metric("Retransmissions", st.session_state.retransmissions)
    metric_cols[4].metric("Success Rate", f"{success_rate()}%")
    metric_cols[5].metric("Error Rate", f"{error_rate()}%")

    status_df = pd.DataFrame(
        {
            "Status": ["VALID", "CORRUPTED"],
            "Count": [st.session_state.valid_messages, st.session_state.corrupted_messages],
        }
    )
    log_df = communication_log_dataframe()
    error_df = (
        log_df[log_df["Error Type"] != "None"]["Error Type"].value_counts().rename_axis("Error Type").reset_index(name="Count")
        if not log_df.empty
        else pd.DataFrame({"Error Type": [], "Count": []})
    )
    retransmission_df = pd.DataFrame({"Action": ["Retransmissions"], "Count": [st.session_state.retransmissions]})
    communication_df = (
        log_df["Status"].value_counts().rename_axis("Status").reset_index(name="Count")
        if not log_df.empty
        else pd.DataFrame({"Status": [], "Count": []})
    )

    chart_a, chart_b = st.columns(2)
    with chart_a:
        st.subheader("Valid vs Corrupted Messages")
        if px:
            fig = px.bar(status_df, x="Status", y="Count", color="Status", color_discrete_map={"VALID": "#25d07f", "CORRUPTED": "#ff5268"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch", key="analytics_chart_1")
        else:
            st.bar_chart(status_df.set_index("Status"))

    with chart_b:
        st.subheader("Error Type Distribution")
        if error_df.empty:
            st.info("No corrupted error types logged yet.")
        elif px:
            fig = px.pie(error_df, names="Error Type", values="Count", hole=0.42, color_discrete_sequence=["#ff5268", "#ffb84d", "#9b7cff"])
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch", key="analytics_chart_2")
        else:
            st.bar_chart(error_df.set_index("Error Type"))

    chart_c, chart_d = st.columns(2)
    with chart_c:
        st.subheader("Retransmissions")
        if px:
            fig = px.bar(retransmission_df, x="Action", y="Count", color_discrete_sequence=["#ffb84d"])
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch", key="analytics_chart_3")
        else:
            st.bar_chart(retransmission_df.set_index("Action"))

    with chart_d:
        st.subheader("Communication Status")
        if communication_df.empty:
            st.info("No communication events logged yet.")
        elif px:
            fig = px.bar(communication_df, x="Status", y="Count", color="Status", color_discrete_map={"VALID": "#25d07f", "CORRUPTED": "#ff5268"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch ", key="analytics_chart_4")
        else:
            st.bar_chart(communication_df.set_index("Status"))

    render_communication_log()

# Execute the predefined CRC/error combinations and return pass/fail records for the test UI.
def run_test_cases() -> list[dict[str, str]]:
    # Each case follows the production path: reference CRC, simulated receive text, current CRC, status.
    cases = [
        ("TC01", "HELLO", "No Error", "VALID"),
        ("TC02", "HELLO", "Single-Bit Error", "CORRUPTED"),
        ("TC03", "HELLO", "Multiple-Bit Error", "CORRUPTED"),
        ("TC04", "HELLO", "Burst Error", "CORRUPTED"),
    ]
    results = []
    for test_case, input_message, error_type, expected in cases:
        reference_crc = calculate_crc32(input_message)
        received = simulate_error(input_message, error_type)
        current_crc = calculate_crc32(received)
        actual = "VALID" if reference_crc == current_crc else "CORRUPTED"
        results.append(
            {
                "Test Case": test_case,
                "Input": input_message,
                "Error Type": error_type,
                "Reference CRC": format_crc(reference_crc),
                "Current CRC": format_crc(current_crc),
                "Expected": expected,
                "Actual": actual,
                "Result": "PASS" if expected == actual else "FAIL",
            }
        )
    return results

# Render the predefined test catalog and, on request, display its execution results.
def test_center_page() -> None:
    # The test page stores results in session state so Streamlit reruns keep the latest test table visible.
    render_header()
    st.markdown("<div class='section-title'>🧪 Test Center</div>", unsafe_allow_html=True)
    st.write("Predefined CRC-32 transmission tests for the live demonstration.")

    if st.button("🧪 RUN ALL TESTS", width="stretch"):
        st.session_state.test_results = run_test_cases()
        passed = sum(1 for row in st.session_state.test_results if row["Result"] == "PASS")
        st.success(f"✅ {passed} / {len(st.session_state.test_results)} TESTS PASSED")

    if st.session_state.test_results:
        results_df = pd.DataFrame(st.session_state.test_results)
        st.dataframe(results_df, width="stretch", hide_index=True)
        passed = int((results_df["Result"] == "PASS").sum())
        if passed == len(results_df):
            st.success(f"✅ {passed} / {len(results_df)} TESTS PASSED")
        else:
            st.warning(f"⚠️ {passed} / {len(results_df)} TESTS PASSED")
    else:
        preview_df = pd.DataFrame(
            [
                {"Test Case": "TC01", "Input": "HELLO", "Error Type": "No Error", "Expected": "VALID"},
                {"Test Case": "TC02", "Input": "HELLO", "Error Type": "Single-Bit Error", "Expected": "CORRUPTED"},
                {"Test Case": "TC03", "Input": "HELLO", "Error Type": "Multiple-Bit Error", "Expected": "CORRUPTED"},
                {"Test Case": "TC04", "Input": "HELLO", "Error Type": "Burst Error", "Expected": "CORRUPTED"},
            ]
        )
        st.dataframe(preview_df, width="stretch", hide_index=True)

# Configure Streamlit, initialize state/styles, route the selected page, and start the app.
def main() -> None:
    # All page actions rerun through this router after shared configuration and session initialization.
    st.set_page_config(
        page_title="CRC-32 Communication Reliability Monitor",
        page_icon="🔐",
        layout="wide",
    )
    init_session_state()
    inject_css()
    page = render_sidebar()

    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "📡 Communication":
        communication_page()
    elif page == "⚡ Error Simulator":
        error_simulator_page()
    elif page == "📊 Analytics":
        analytics_page()
    elif page == "🧪 Test Center":
        test_center_page()


if __name__ == "__main__":
    main()

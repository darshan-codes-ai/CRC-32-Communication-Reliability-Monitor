from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from crc_utils import calculate_crc32, format_crc, verify_crc
from error_simulator import ERROR_TYPES, simulate_error

try:
    import plotly.express as px
except ImportError:
    px = None


APP_TITLE = "🔐 CRC-32 Communication Reliability Monitor"
APP_SUBTITLE = "Real-Time Message Integrity, Error Detection & Retransmission System"

LOG_COLUMNS = [
    "Time", "Sender", "Receiver", "Message", "Error Type",
    "Reference CRC", "Current CRC", "Status", "Action",
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


def init_session_state() -> None:
    # DEMO: Streamlit reruns the script after interactions.
    # session_state keeps our message, CRC values and counters available.
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def reset_session() -> None:
    # DEMO: Used by Reset and before loading the clean demo state.
    for key, value in STATE_DEFAULTS.items():
        st.session_state[key] = value.copy() if isinstance(value, list) else value


def has_message() -> bool:
    return st.session_state.original_message is not None


def status_badge(status: str) -> str:
    status = (status or "WAITING").upper()
    classes = {"VALID": "badge-valid", "CORRUPTED": "badge-corrupted", "WAITING": "badge-waiting"}
    return f"<span class='status-badge {classes.get(status, 'badge-waiting')}'>{escape(status)}</span>"


def rate(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


def total_outcomes() -> int:
    return st.session_state.valid_messages + st.session_state.corrupted_messages


def success_rate() -> float:
    return rate(st.session_state.valid_messages, total_outcomes())


def error_rate() -> float:
    return rate(st.session_state.corrupted_messages, total_outcomes())


def display_message(message: str | None) -> str:
    if message is None:
        return "No message sent yet"
    if message == "":
        return "(empty message)"
    return message


def add_log(status: str, action: str, error_type: str | None = None, message: str | None = None) -> None:
    # DEMO: Creates one row for the Communication Log / Analytics.
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


def record_attempt(status: str) -> None:
    # DEMO: Updates the counters shown in the dashboard and Analytics page.
    st.session_state.total_attempts += 1
    if status == "VALID":
        st.session_state.valid_messages += 1
    elif status == "CORRUPTED":
        st.session_state.corrupted_messages += 1


def set_received_message(received: str, error_type: str = "No Error") -> str:
    # DEMO: Receiver-side core step.
    # 1) Save received data -> 2) calculate current CRC -> 3) compare with reference.
    st.session_state.received_message = received
    st.session_state.current_crc = calculate_crc32(received)
    st.session_state.error_type = error_type
    status = "VALID" if st.session_state.reference_crc == st.session_state.current_crc else "CORRUPTED"
    st.session_state.verification_status = status
    return status


def send_message(message: str) -> str:
    # DEMO: START HERE for the normal transmission flow.
    # Sender stores the original message and generates the reference CRC.
    st.session_state.original_message = message
    st.session_state.reference_crc = calculate_crc32(message)
    st.session_state.messages_sent += 1

    # For a normal send, the received data is initially identical to the sent data.
    status = set_received_message(message, "No Error")
    record_attempt(status)
    st.session_state.last_action = "Message sent and CRC generated"
    add_log(status, "Delivered" if status == "VALID" else "Retransmission Required", "No Error", message)
    return status


def verify_current_message(action: str = "Verified") -> str | None:
    # DEMO: Show this function when explaining the VERIFY MESSAGE button.
    if not has_message():
        return None

    # Recalculate CRC for whatever is currently at the receiver.
    st.session_state.current_crc = calculate_crc32(st.session_state.received_message)

    # verify_crc() performs the actual reference-vs-current CRC check.
    status = "VALID" if verify_crc(st.session_state.received_message, st.session_state.reference_crc) else "CORRUPTED"
    st.session_state.verification_status = status
    record_attempt(status)
    st.session_state.last_action = "CRC verification complete"
    add_log(status, "Delivered" if status == "VALID" else "Retransmission Required", st.session_state.error_type)
    return status


def perform_retransmission(auto: bool = False) -> str | None:
    # DEMO: Use after CORRUPTED to show recovery.
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


def load_demo() -> None:
    # DEMO: Fastest way to prepare the dashboard for the viva.
    # After clicking LOAD DEMO, the app is ready with HELLO and a matching CRC.
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


def communication_log_dataframe() -> pd.DataFrame:
    return pd.DataFrame(st.session_state.communication_log, columns=LOG_COLUMNS)


def csv_report_bytes() -> bytes:
    # DEMO: Used by the Download CSV Report button.
    return communication_log_dataframe().to_csv(index=False).encode("utf-8")


def inject_css() -> None:
    # UI styling only — not part of the CRC algorithm.
    st.markdown("""<style>/* existing project CSS remains intentionally compact */</style>""", unsafe_allow_html=True)


def render_header() -> None:
    # DEMO: Visual header shown on each page.
    st.title(APP_TITLE)
    st.markdown(f"<div class='app-subtitle'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)


def render_sidebar() -> str:
    # DEMO: Sidebar controls page navigation and the Auto Retransmission option.
    with st.sidebar:
        st.markdown("## 🔐 CRC-32 Monitor")
        st.caption("Communication Integrity Lab")
        pages = ["🏠 Dashboard", "📡 Communication", "⚡ Error Simulator", "📊 Analytics", "🧪 Test Center"]
        current = st.session_state.get("navigation", pages[0])
        if current not in pages:
            current = pages[0]
        page = st.radio("Navigation", pages, index=pages.index(current))
        st.session_state.navigation = page
        st.session_state.auto_retransmission = st.checkbox(
            "Auto Retransmission", value=st.session_state.auto_retransmission
        )
        if st.button("Reset Session", width="stretch"):
            reset_session()
            st.rerun()
        return page


def dashboard_page() -> None:
    # DEMO: Start here if the examiner asks for the overall system.
    render_header()
    st.markdown("### System Flow")
    st.info("Sender → CRC Generation → Simulated Channel → Error Detection → Retransmission")

    if st.button("🚀 LOAD DEMO", width="stretch"):
        load_demo()
        st.success("Demo loaded: HELLO")
        st.rerun()


def communication_page() -> None:
    # DEMO: Main page for explaining send -> receive -> verify.
    render_header()
    message = st.text_input("Message", value=st.session_state.message_input, key="message_input")

    if st.button("📤 SEND MESSAGE", width="stretch"):
        status = send_message(message)
        st.success(f"Message sent. Status: {status}")

    # Show reference/current CRC and status here.
    # The full dashboard layout in the repository continues below these controls.
    st.write("Reference CRC:", format_crc(st.session_state.reference_crc))
    st.write("Current CRC:", format_crc(st.session_state.current_crc))
    st.write("Status:", st.session_state.verification_status)

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
                st.success("Retransmission complete. Message successfully verified.")


def error_simulator_page() -> None:
    # DEMO: Use this page to intentionally corrupt the transmitted message.
    render_header()
    selected_error = st.radio("Error condition", ERROR_TYPES, horizontal=True)

    if st.button("⚡ SIMULATE ERROR", width="stretch"):
        if not has_message():
            st.warning("Send a message first. The simulator needs transmitted data to corrupt.")
        else:
            # This calls error_simulator.py -> simulate_error().
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

    st.write("Original:", display_message(st.session_state.original_message))
    st.write("Received:", display_message(st.session_state.received_message if has_message() else None))
    st.write("Reference CRC:", format_crc(st.session_state.reference_crc))
    st.write("Current CRC:", format_crc(st.session_state.current_crc))
    st.write("Status:", st.session_state.verification_status)


def analytics_page() -> None:
    # DEMO: Show this page after the error/retransmission demonstration.
    render_header()
    metric_cols = st.columns(6)
    metric_cols[0].metric("Total Messages", st.session_state.messages_sent)
    metric_cols[1].metric("Valid Messages", st.session_state.valid_messages)
    metric_cols[2].metric("Corrupted Messages", st.session_state.corrupted_messages)
    metric_cols[3].metric("Retransmissions", st.session_state.retransmissions)
    metric_cols[4].metric("Success Rate", f"{success_rate()}%")
    metric_cols[5].metric("Error Rate", f"{error_rate()}%")

    log_df = communication_log_dataframe()
    if not log_df.empty:
        st.dataframe(log_df, width="stretch", hide_index=True)
        st.download_button(
            "⬇️ DOWNLOAD CSV REPORT",
            data=csv_report_bytes(),
            file_name="crc_communication_report.csv",
            mime="text/csv",
        )


def run_test_cases() -> list[dict[str, str]]:
    # DEMO: This is the automated test workflow.
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
        results.append({
            "Test Case": test_case,
            "Input": input_message,
            "Error Type": error_type,
            "Reference CRC": format_crc(reference_crc),
            "Current CRC": format_crc(current_crc),
            "Expected": expected,
            "Actual": actual,
            "Result": "PASS" if expected == actual else "FAIL",
        })
    return results


def test_center_page() -> None:
    # DEMO: Click RUN ALL TESTS at the end to show repeatable verification.
    render_header()
    st.write("Predefined CRC-32 transmission tests for the live demonstration.")

    if st.button("🧪 RUN ALL TESTS", width="stretch"):
        st.session_state.test_results = run_test_cases()
        passed = sum(1 for row in st.session_state.test_results if row["Result"] == "PASS")
        st.success(f"{passed} / {len(st.session_state.test_results)} TESTS PASSED")

    if st.session_state.test_results:
        st.dataframe(pd.DataFrame(st.session_state.test_results), width="stretch", hide_index=True)


def main() -> None:
    # DEMO: Program entry point. Streamlit starts here and selects the current page.
    st.set_page_config(page_title="CRC-32 Communication Reliability Monitor", page_icon="🔐", layout="wide")
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

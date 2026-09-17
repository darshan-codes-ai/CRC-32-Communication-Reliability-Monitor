# 🎤 Code + Dashboard Demonstration Guide

This file is for the **live project demonstration and viva**.

## 1. Main story to demonstrate

**HELLO → Reference CRC → Send → Simulate Error → Current CRC changes → CORRUPTED → Retransmission → VALID**

Do not explain every function. Show the functions below in this order.

## 2. Functions to show in the viva

| Order | File | Function | What to explain |
|---|---|---|---|
| 1 | `crc_utils.py` | `calculate_crc32()` | Main CRC calculation. Text is normalized, encoded as UTF-8, then `zlib.crc32()` calculates CRC-32. |
| 2 | `app.py` | `send_message()` | Sender stores the original message and creates the **reference CRC**. |
| 3 | `error_simulator.py` | `simulate_error()` | Creates controlled corruption for the selected error type. |
| 4 | `app.py` | `set_received_message()` | Stores received data, calculates the **current CRC**, and decides VALID/CORRUPTED. |
| 5 | `crc_utils.py` | `verify_crc()` | Compares the CRC of received data with the reference CRC. |
| 6 | `app.py` | `verify_current_message()` | Dashboard verification button uses this flow. |
| 7 | `app.py` | `perform_retransmission()` | Sends/restores the original message after corruption is detected. |
| 8 | `app.py` | `run_test_cases()` | Runs the predefined CRC/error tests. |

## 3. Exact dashboard demo

### Step 1 — Load Demo
Click **LOAD DEMO**.

Say:
> “I am loading the predefined HELLO message so I can demonstrate the complete communication flow.”

### Step 2 — Normal transmission
Open **Communication**.

Show:
- Original message: `HELLO`
- Reference CRC: `3610A686`
- Current CRC: `3610A686`
- Status: `VALID`

Say:
> “The sender generates a reference CRC. The receiver calculates the CRC again. Because both values match, the message is valid.”

### Step 3 — Create corruption
Open **Error Simulator**.

Select **Single-Bit Error** and click **SIMULATE ERROR**.

Say:
> “Now I am simulating a communication error. The received text is changed, so its CRC also changes.”

### Step 4 — Show detection
Point to:
- Original
- Received
- Reference CRC
- Current CRC
- `CORRUPTED`

Say:
> “The reference and current CRC values are different. Therefore the receiver detects corruption.”

### Step 5 — Retransmission
Click **REQUEST RETRANSMISSION**.

Say:
> “CRC does not correct the data. It tells us that corruption occurred. Our project then uses retransmission to restore the original message.”

### Step 6 — Analytics
Open **Analytics**.

Say:
> “The dashboard records communication attempts, valid messages, corrupted messages and retransmissions. The log can also be downloaded as CSV.”

### Step 7 — Test Center
Open **Test Center** and click **RUN ALL TESTS**.

Say:
> “These predefined tests check no error, single-bit, multiple-bit and burst-error scenarios.”

## 4. Most important code concepts

### `calculate_crc32()`
Remember:

`text → casefold() → UTF-8 → zlib.crc32() → 32-bit CRC`

The project displays the CRC as 8 hexadecimal characters.

### Reference CRC vs Current CRC
- **Reference CRC** = CRC calculated from the original/sender message.
- **Current CRC** = CRC calculated from the received message.
- Same → **VALID**.
- Different → **CORRUPTED**.

### `st.session_state`
Streamlit reruns the script after UI interactions. Session state keeps the message, CRC values, counters and log available between interactions.

### `simulate_error()`
The current project uses **deterministic text-level corruption** so the error is easy to see and reproduce in a classroom demo. It does **not** literally flip a binary bit on a physical network.

## 5. Four error options

- **No Error** → message remains unchanged.
- **Single-Bit Error** → one visible character is changed.
- **Multiple-Bit Error** → several positions are changed.
- **Burst Error** → consecutive characters are changed.

For viva, call these **simulated error conditions**.

## 6. Functions you normally do NOT need to explain

`init_session_state()` — initializes Streamlit state.

`reset_session()` — resets the application.

`status_badge()` — UI status styling.

`rate()`, `success_rate()`, `error_rate()` — dashboard percentage calculations.

`display_message()` — display helper.

`add_log()` — adds communication-log rows.

`record_attempt()` — updates counters.

`format_crc()` — formats CRC for display.

`communication_log_dataframe()` / `csv_report_bytes()` — logging/export helpers.

`inject_css()` / rendering functions — mainly UI code.

## 7. 19 viva answers — ultra-short version

1. **What is CRC?** Error-detection method that produces a checksum.
2. **Why CRC?** To detect data corruption during transmission.
3. **Generator polynomial?** CRC-32 IEEE polynomial, commonly represented as `0x04C11DB7`.
4. **Why append zeros?** CRC-32 conceptually appends 32 zeros before division.
5. **Why XOR?** CRC uses modulo-2 arithmetic, where subtraction is XOR.
6. **CRC remainder?** Remainder of the polynomial division; it forms the CRC value.
7. **Codeword?** Protected transmitted data together with CRC check bits.
8. **How detect error?** Recalculate CRC and compare with the reference CRC.
9. **Can CRC correct errors?** No. This project uses retransmission for recovery.
10. **What errors?** Many single-bit, multiple-bit and burst-error patterns.
11. **Text conversion?** Normalize text and encode it as UTF-8.
12. **File processing?** The PPT describes it, but the current GitHub app code reviewed uses text input rather than a file-upload UI.
13. **CRC function?** `calculate_crc32()` calls `zlib.crc32()`.
14. **How dashboard calls CRC?** Send, receive and verification functions call the CRC helper.
15. **How result reaches dashboard?** Values are stored in `st.session_state` and displayed by Streamlit.
16. **If one bit changes?** Data changes, so its CRC normally changes and a mismatch is detected.
17. **How tested?** Test Center plus manual error demonstrations.
18. **Important implementation issue?** Managing Streamlit session state across reruns.
19. **Additional features?** Analytics, communication logs, CSV export and optional auto retransmission.

## 8. If the examiner asks “Explain the whole code”

Say:
> “The CRC logic is separated into `crc_utils.py`. The sender uses `calculate_crc32()` to create the reference CRC. The error simulator changes the transmitted message for testing. The receiver calculates the current CRC and compares it with the reference. The dashboard then shows VALID or CORRUPTED. If corruption is detected, `perform_retransmission()` sends the original message again. Streamlit session state keeps the complete workflow available between button clicks.”

## 9. Three things you must NOT say

1. **Do not say CRC corrects errors.** Say it detects errors; retransmission provides recovery.
2. **Do not say the current simulator literally flips one binary bit.** It performs visible deterministic text corruption.
3. **Do not claim file upload is demonstrated by the current app code** unless your local version has that feature.

## 10. One-line memory trick

**C → S → E → V → R**

**Calculate CRC → Send → Error → Verify → Retransmit**

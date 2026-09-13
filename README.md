# CRC-32 Communication Reliability Monitor

A Streamlit dashboard for demonstrating message integrity checking in a simulated local communication system.

## Problem Statement

Two users exchange text messages through a simulated local chat application. Communication errors may alter message bits, producing incorrect or incomplete messages at the receiver. The application detects corrupted messages using CRC-32 and requests retransmission when an error is detected.

## Features

- Send messages from User A to User B
- Generate real CRC-32 values with Python `zlib`
- Simulate no error, single-bit, multiple-bit, and burst errors
- Verify received messages by comparing reference CRC and current CRC
- Manual and automatic retransmission
- Communication log with CSV export
- Analytics dashboard with chart fallback when Plotly is unavailable
- Test center with predefined CRC validation cases
- Demo mode using `HELLO`, which produces CRC `3610A686`

## Technology Stack

- Python
- Streamlit
- `zlib.crc32`
- pandas
- Plotly
- CSV export

## How CRC-32 Works

CRC-32 generates a 32-bit checksum from the original message. The sender transmits both the message and the checksum. The receiver recalculates CRC-32 from the received message and compares it with the sender's reference CRC. If both values match, the message is treated as valid. If they differ, the message is corrupted and retransmission is required.

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Demonstration Workflow

1. Open the app and click **🎬 LOAD DEMO** in the sidebar.
2. Go to **📡 Communication** and send `HELLO`.
3. Confirm the generated CRC-32 is `3610A686`.
4. Go to **⚡ Error Simulator** and simulate a **Single-Bit Error**.
5. Verify that the receiver detects a CRC mismatch and marks the message as corrupted.
6. Click **🔄 RETRANSMIT ORIGINAL MESSAGE**.
7. Confirm the retransmitted message is verified successfully.
8. Open **📊 Analytics** and download the CSV report from the communication log.
9. Open **🧪 Test Center** and run all predefined tests.

"""CRC-32 helper functions for the communication reliability monitor."""

import zlib

# Normalize text and calculate the unsigned CRC-32 checksum used by sender and receiver.
def calculate_crc32(data: str) -> int:
    """Calculate the project's CRC-32 checksum for text data."""
    # DEMO: This is the main CRC function to show in the viva.
    # Flow: text -> case-normalize -> UTF-8 bytes -> CRC-32 -> 32-bit integer.
    if data is None:
        data = ""

    # The project intentionally treats upper/lower case as equivalent.
    normalized = str(data).casefold()

    # zlib.crc32() performs the actual CRC-32 calculation.
    # & 0xFFFFFFFF keeps the result in the unsigned 32-bit range.
    return zlib.crc32(normalized.encode("utf-8")) & 0xFFFFFFFF

# Convert a CRC integer into the fixed-width hexadecimal form shown in the dashboard.
def format_crc(crc: int | None) -> str:
    """Format a CRC-32 integer as uppercase 8-character hexadecimal."""
    # DEMO: Used by the dashboard so CRC values are easy to read.
    if crc is None:
        return "--------"
    return f"{crc & 0xFFFFFFFF:08X}"

# Recalculate the received text checksum and compare it with the sender's reference value.
def verify_crc(data: str, reference_crc: int | None) -> bool:
    """Verify received data against the sender's reference CRC."""
    # DEMO: This is the key receiver-side comparison.
    # True  -> CRCs match -> VALID
    # False -> CRCs differ -> CORRUPTED
    if reference_crc is None:
        return False

    current_crc = calculate_crc32(data)
    return current_crc == (reference_crc & 0xFFFFFFFF)

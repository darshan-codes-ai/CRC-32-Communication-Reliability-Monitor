"""CRC-32 helper functions for the communication reliability monitor."""

import zlib


# DEMO: Main CRC calculation function.
# Use this first when explaining how the CRC value is generated.
# Input: message
# Output: CRC-32 value
def calculate_crc32(data: str) -> int:
    """Return the unsigned CRC-32 checksum for normalized text data."""
    if data is None:
        data = ""
    normalized = str(data).casefold()
    return zlib.crc32(normalized.encode("utf-8")) & 0xFFFFFFFF


def format_crc(crc: int | None) -> str:
    """Format a CRC-32 integer as uppercase 8-character hexadecimal."""
    if crc is None:
        return "--------"
    return f"{crc & 0xFFFFFFFF:08X}"


def verify_crc(data: str, reference_crc: int | None) -> bool:
    """Verify text data by comparing its current CRC-32 with a reference CRC."""
    if reference_crc is None:
        return False
    return calculate_crc32(data) == (reference_crc & 0xFFFFFFFF)

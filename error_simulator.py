"""Deterministic text-safe error simulation for local message transmission."""

ERROR_TYPES = [
    "No Error",
    "Single-Bit Error",
    "Multiple-Bit Error",
    "Burst Error",
]


def normalize_error_type(error_type: str) -> str:
    """Return a supported error type, defaulting to No Error."""
    return error_type if error_type in ERROR_TYPES else "No Error"


def _change_char(char: str) -> str:
    """Change one visible character while keeping the result presentation-safe."""
    if not char:
        return "X"
    if char == " ":
        return "_"
    if char == "_":
        return "-"
    if char.isdigit():
        return str((int(char) + 1) % 10)
    if "A" <= char <= "Z":
        return chr(((ord(char) - ord("A") + 1) % 26) + ord("A"))
    if "a" <= char <= "z":
        return chr(((ord(char) - ord("a") + 1) % 26) + ord("a"))
    return "!" if char != "!" else "?"


def _replace_at(message: str, index: int) -> str:
    chars = list(message)
    chars[index] = _change_char(chars[index])
    return "".join(chars)


def simulate_error(message: str, error_type: str) -> str:
    """Return a received message after applying the selected error condition."""
    error_type = normalize_error_type(error_type)
    message = "" if message is None else str(message)

    if error_type == "No Error":
        return message

    if error_type == "Single-Bit Error":
        if not message:
            return "X"
        index = len(message) // 2
        return _replace_at(message, index)

    if error_type == "Multiple-Bit Error":
        if not message:
            return "XX"
        if len(message) == 1:
            return _change_char(message[0]) + "X"

        chars = list(message)
        positions = sorted({0, len(message) // 2, len(message) - 1})
        for index in positions:
            chars[index] = _change_char(chars[index])
        return "".join(chars)

    if error_type == "Burst Error":
        if not message:
            return "BURST"

        chars = list(message)
        burst_length = min(len(chars), max(2, len(chars) // 3))
        start = min(len(chars) - 1, max(0, len(chars) // 3))
        end = min(len(chars), start + burst_length)
        for index in range(start, end):
            chars[index] = _change_char(chars[index])
        return "".join(chars)

    return message

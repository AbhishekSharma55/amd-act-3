def hm(s: str) -> int:
    """'HH:MM' -> minutes since 00:00. Raises ValueError on anything else."""
    if not isinstance(s, str):
        raise ValueError("Time must be HH:MM")
    parts = s.split(":")
    if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError("Time must be HH:MM")
    h, m = map(int, parts)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Invalid clock time")
    return h * 60 + m


def fmt(x: int) -> str:
    return f"{x // 60:02d}:{x % 60:02d}"

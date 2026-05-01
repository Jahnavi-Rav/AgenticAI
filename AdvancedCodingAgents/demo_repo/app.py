import requests


def greet(name: str) -> str:
    """Return a greeting for a non-empty name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    return f"Hello, {name.strip()}"

"""Centralized datetime utilities with Python 3.12+ compliant UTC handling."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return timezone-naive UTC datetime.
    
    Compatible with SQLAlchemy/SQLite DateTime columns while avoiding
    Python 3.12+ deprecation warnings on datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

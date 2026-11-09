from datetime import datetime, timezone

DISCLAIMER = "For research and pharmacovigilance decision support only. Not medical advice."

def current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


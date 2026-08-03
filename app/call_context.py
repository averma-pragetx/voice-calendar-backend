"""
Remembers the phone number of the most recently triggered outbound call, so
tool webhooks can SMS that number even when ElevenLabs doesn't echo back the
phone_number dynamic variable as a tool parameter.

# ponytail: single global, not keyed by conversation_id — correct only for
# one call in flight at a time. Upgrade to a dict keyed by conversation_id
# once ElevenLabs tool payloads carry it, or once concurrent calls matter.
"""
_last_to_number: str | None = None


def set_last_to_number(to_number: str) -> None:
    global _last_to_number
    _last_to_number = to_number


def get_last_to_number() -> str | None:
    return _last_to_number

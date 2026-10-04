"""Run pyezvizapi writes with a hard cap on their internal retries."""

import threading
from typing import Any

# pyezvizapi 1.0.0.7 set_camera_defence retries a 504 ("camera timed out") by
# calling itself with max_retries passed as channel_no, so the retry counter
# never grows and a sleeping camera can trigger hundreds of cloud requests.
SELF_RETRYING = frozenset({"set_camera_defence"})
MAX_ATTEMPTS = 3
_LOCK = threading.Lock()


def bounded_call(client: Any, name: str, serial: str, *args: Any) -> Any:
    """Call one client method; self-retrying methods get at most MAX_ATTEMPTS."""
    method = getattr(client, name)
    if name not in SELF_RETRYING:
        return method(serial, *args)
    from pyezvizapi.exceptions import PyEzvizError

    attempts = 0
    owner = threading.get_ident()

    def guarded(*call_args: Any, **call_kwargs: Any) -> Any:
        nonlocal attempts
        if threading.get_ident() != owner:
            # HA core's own concurrent calls pass through with their own budget.
            return method(*call_args, **call_kwargs)
        attempts += 1
        if attempts > MAX_ATTEMPTS:
            raise PyEzvizError("EZVIZ retry budget exhausted")
        return method(*call_args, **call_kwargs)

    # The recursive retry resolves self.<name> on the instance first, so a
    # temporary instance attribute bounds it without touching the class.
    with _LOCK:
        setattr(client, name, guarded)
        try:
            return guarded(serial, *args)
        finally:
            delattr(client, name)

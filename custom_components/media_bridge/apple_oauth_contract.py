"""Pure OAuth callback bounds for the Vistoda Apple companion."""

from collections.abc import Mapping
from urllib.parse import urlencode

CALLBACK_PATH = "/api/media_bridge/apple/auth"
CALLBACK_SCHEME = "vistoda"


def native_callback(values: Mapping[str, str]) -> str | None:
    """Build a bounded native callback for a valid OAuth result."""
    state = values.get("state", "")
    code = values.get("code", "")
    error = values.get("error", "")
    if not 16 <= len(state) <= 256:
        return None
    if bool(code) == bool(error):
        return None
    if len(code) > 2048 or len(error) > 128:
        return None
    query = {"state": state}
    if code:
        query["code"] = code
    else:
        query["error"] = error
    return f"{CALLBACK_SCHEME}://auth?{urlencode(query)}"

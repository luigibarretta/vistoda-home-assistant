"""Constants for Vistoda."""

DOMAIN = "media_bridge"
INTEGRATION_VERSION = "0.49.0"
PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "button",
    "camera",
    "event",
    "number",
    "sensor",
    "switch",
]

CONF_PROVIDER = "provider"
CONF_URL = "url"
CONF_API_TOKEN = "api_token"
CONF_ALIAS = "alias"
CONF_DISCOVERY_TOKENS = "discovery_tokens"
CONF_MANAGED_APP = "managed_app"
CONF_RING_AUTO_RECORD = "ring_auto_record"
CONF_RING_DELEGATE_CONTROLS = "ring_delegate_controls"
CONF_EZVIZ_DELEGATE_CONTROLS = "ezviz_delegate_controls"
# EZVIZ event archive on the network storage (opt-in) and its retention in days.
CONF_EVENT_ARCHIVE = "event_archive"
CONF_EVENT_RETENTION_DAYS = "event_retention_days"
CONF_SCENETROVE_URL = "scenetrove_url"
CONF_SCENETROVE_DEVICE = "scenetrove_device"
CONF_CLIP_DESTINATION = "clip_destination"
CONF_SHARED_STORAGE = "shared_storage"
CLIP_DESTINATIONS = ("vistoda", "shared")

PROVIDER_BLINK = "blink"
PROVIDER_EZVIZ = "ezviz"
PROVIDER_RING = "ring"
PROVIDERS = [PROVIDER_BLINK, PROVIDER_EZVIZ, PROVIDER_RING]

DEFAULT_BLINK_ALIAS = "blink"
DEFAULT_EZVIZ_ALIAS = "front-door"
DEFAULT_RING_ALIAS = "entrance"

BLINK_BRIDGE_DOMAIN = "blink_live_bridge"
DISCOVERY_TYPE = "_vistoda._tcp.local."
SIGNAL_RING_POLICY_CHANGED = f"{DOMAIN}_ring_policy_changed"


def ring_event_signal(entry_id: str) -> str:
    """Return the private dispatcher signal for one Ring config entry."""
    return f"{DOMAIN}_ring_event_{entry_id}"


EVENT_EZVIZ_ALARM = "vistoda_ezviz_alarm"


def ezviz_event_archive_signal(entry_id: str) -> str:
    """Dispatcher signal for event archive availability changes of one EZVIZ entry."""
    return f"{DOMAIN}_ezviz_event_archive_{entry_id}"


def ezviz_alarm_signal(entry_id: str) -> str:
    """Return the private dispatcher signal for one EZVIZ camera entry."""
    return f"{DOMAIN}_ezviz_alarm_{entry_id}"

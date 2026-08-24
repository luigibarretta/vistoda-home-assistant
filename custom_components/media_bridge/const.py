"""Constants for Vistoda."""

DOMAIN = "media_bridge"
INTEGRATION_VERSION = "0.11.1"
PLATFORMS = ["binary_sensor", "button", "camera", "event", "number", "sensor", "switch"]

CONF_PROVIDER = "provider"
CONF_URL = "url"
CONF_API_TOKEN = "api_token"
CONF_ALIAS = "alias"
CONF_DISCOVERY_TOKENS = "discovery_tokens"
CONF_MANAGED_APP = "managed_app"
CONF_RING_AUTO_RECORD = "ring_auto_record"
CONF_RING_DELEGATE_CONTROLS = "ring_delegate_controls"

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

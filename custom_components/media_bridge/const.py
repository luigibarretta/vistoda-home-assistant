"""Constants for Vistoda."""

DOMAIN = "media_bridge"
PLATFORMS = ["binary_sensor", "button", "camera", "event", "number", "sensor"]

CONF_PROVIDER = "provider"
CONF_URL = "url"
CONF_API_TOKEN = "api_token"
CONF_ALIAS = "alias"
CONF_DISCOVERY_TOKENS = "discovery_tokens"

PROVIDER_BLINK = "blink"
PROVIDER_EZVIZ = "ezviz"
PROVIDER_RING = "ring"
PROVIDERS = [PROVIDER_BLINK, PROVIDER_EZVIZ, PROVIDER_RING]

DEFAULT_BLINK_ALIAS = "blink"
DEFAULT_EZVIZ_ALIAS = "front-door"
DEFAULT_RING_ALIAS = "entrance"

BLINK_BRIDGE_DOMAIN = "blink_live_bridge"
DISCOVERY_TYPE = "_vistoda._tcp.local."

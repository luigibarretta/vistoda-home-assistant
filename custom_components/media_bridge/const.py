"""Constants for Media Bridge."""

DOMAIN = "media_bridge"
PLATFORMS = ["binary_sensor", "camera"]

CONF_PROVIDER = "provider"
CONF_URL = "url"
CONF_API_TOKEN = "api_token"
CONF_ALIAS = "alias"

PROVIDER_EZVIZ = "ezviz"
PROVIDER_RING = "ring"
PROVIDERS = [PROVIDER_EZVIZ, PROVIDER_RING]

DEFAULT_EZVIZ_ALIAS = "front-door"
DEFAULT_RING_ALIAS = "entrance"

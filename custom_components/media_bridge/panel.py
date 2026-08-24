"""Serve and register the Vistoda provider panels."""

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import INTEGRATION_VERSION

PANEL_PATH = "vistoda"
PROVIDER_PATHS = {
    "vistoda-ring": ("ring", "Vistoda · Ring", "mdi:phone-in-talk"),
    "vistoda-blink": ("blink", "Vistoda · Blink", "mdi:cctv"),
    "vistoda-ezviz": ("ezviz", "Vistoda · EZVIZ", "mdi:doorbell-video"),
}
STATIC_ROOT = "/vistoda_static"
STATIC_URL = "/vistoda_static/vistoda-panel.js"


def _custom_panel_config(provider: str) -> dict:
    """Build the same private panel contract used by panel_custom."""
    return {
        "provider": provider,
        "_panel_custom": {
            "name": "vistoda-panel",
            "embed_iframe": False,
            "trust_external": False,
            "handle_safe_area": False,
            "module_url": f"{STATIC_URL}?v={INTEGRATION_VERSION}",
        },
    }


async def async_register(hass: HomeAssistant) -> None:
    """Register one sidebar hub plus hidden provider-compatible routes."""
    source = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_ROOT, str(source), cache_headers=False)]
    )
    for path in (PANEL_PATH, *PROVIDER_PATHS):
        if frontend.async_panel_exists(hass, path):
            frontend.async_remove_panel(hass, path)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="vistoda-panel",
        sidebar_title="Vistoda",
        sidebar_icon="mdi:shield-home",
        module_url=f"{STATIC_URL}?v={INTEGRATION_VERSION}",
        config={"provider": "overview"},
        config_panel_domain="media_bridge",
    )
    for path, (provider, title, icon) in PROVIDER_PATHS.items():
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=title,
            sidebar_icon=icon,
            frontend_url_path=path,
            config=_custom_panel_config(provider),
            config_panel_domain="media_bridge",
            show_in_sidebar=False,
        )

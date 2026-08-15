"""Serve and register the Vistoda user panel."""

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

PANEL_PATH = "vistoda"
STATIC_URL = "/vistoda_static/vistoda-panel.js"


async def async_register(hass: HomeAssistant) -> None:
    """Register immutable static assets and one dynamic sidebar panel."""
    source = Path(__file__).parent / "frontend" / "vistoda-panel.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(source), cache_headers=False)]
    )
    if frontend.async_panel_exists(hass, PANEL_PATH):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="vistoda-panel",
        sidebar_title="Vistoda",
        sidebar_icon="mdi:doorbell-video",
        module_url=f"{STATIC_URL}?v=0.4.0",
        config_panel_domain="media_bridge",
    )

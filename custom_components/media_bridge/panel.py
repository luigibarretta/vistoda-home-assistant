"""Serve and register the Vistoda user panel."""

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

PANEL_PATH = "vistoda-ring"
STATIC_URL = "/vistoda_static/vistoda-panel.js"
SESSION_URL = "/vistoda_static/ring-audio-session.js"
CONTROLS_URL = "/vistoda_static/ring-controls.js"
RECORDINGS_URL = "/vistoda_static/ring-recordings.js"
LOCAL_RECORDER_URL = "/vistoda_static/ring-local-recorder.js"


async def async_register(hass: HomeAssistant) -> None:
    """Register immutable static assets and one dynamic sidebar panel."""
    source = Path(__file__).parent / "frontend" / "vistoda-panel.js"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(STATIC_URL, str(source), cache_headers=False),
            StaticPathConfig(
                SESSION_URL,
                str(source.with_name("ring-audio-session.js")),
                cache_headers=False,
            ),
            StaticPathConfig(
                CONTROLS_URL,
                str(source.with_name("ring-controls.js")),
                cache_headers=False,
            ),
            StaticPathConfig(
                RECORDINGS_URL,
                str(source.with_name("ring-recordings.js")),
                cache_headers=False,
            ),
            StaticPathConfig(
                LOCAL_RECORDER_URL,
                str(source.with_name("ring-local-recorder.js")),
                cache_headers=False,
            ),
        ]
    )
    if frontend.async_panel_exists(hass, PANEL_PATH):
        frontend.async_remove_panel(hass, PANEL_PATH)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="vistoda-panel",
        sidebar_title="Vistoda · Ring",
        sidebar_icon="mdi:phone-in-talk",
        module_url=f"{STATIC_URL}?v=0.8.0",
        config_panel_domain="media_bridge",
    )

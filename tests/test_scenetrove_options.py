"""Options linking an EZVIZ entry to SceneTrove: address and device folder."""

from test_event_archive_options import options_flow

BASE = {"backup_storage": "family_archive", "event_archive": False, "event_retention_days": 0}


async def test_scenetrove_url_is_normalized_or_refused(monkeypatch):
    flow = options_flow(monkeypatch)
    result = await flow.async_step_init({**BASE, "scenetrove_url": " https://st.example/ "})
    assert result["data"]["scenetrove_url"] == "https://st.example"
    for refused in ("ftp://st.example", "https://u:p@st.example", "https://st.example/x?y", "st"):
        result = await flow.async_step_init({**BASE, "scenetrove_url": refused})
        assert result["errors"] == {"base": "invalid_scenetrove_url"}, refused
    cleared = await flow.async_step_init({**BASE, "scenetrove_url": ""})
    assert cleared["data"]["scenetrove_url"] == ""


async def test_scenetrove_device_defaults_to_the_alias(monkeypatch):
    flow = options_flow(monkeypatch)
    result = await flow.async_step_init({**BASE, "scenetrove_url": "https://st.example"})
    assert result["data"]["scenetrove_device"] == "entrance"
    named = await flow.async_step_init({**BASE, "scenetrove_device": "spioncino"})
    assert named["data"]["scenetrove_device"] == "spioncino"
    for refused in ("front door", "x" * 65, "../etc"):
        result = await flow.async_step_init({**BASE, "scenetrove_device": refused})
        assert result["errors"] == {"base": "invalid_scenetrove_device"}, refused


async def test_blink_entries_have_no_scenetrove_link(monkeypatch):
    flow = options_flow(monkeypatch, provider="blink")
    result = await flow.async_step_init({**BASE, "scenetrove_url": "https://st.example"})
    assert "scenetrove_url" not in result["data"]

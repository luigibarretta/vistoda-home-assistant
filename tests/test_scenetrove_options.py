"""Options linking an EZVIZ entry to SceneTrove: address and device folder."""

import sys

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
        linked = {**BASE, "scenetrove_url": "https://st.example", "scenetrove_device": refused}
        result = await flow.async_step_init(linked)
        assert result["errors"] == {"base": "invalid_scenetrove_device"}, refused


async def test_blink_entries_have_no_scenetrove_link(monkeypatch):
    flow = options_flow(monkeypatch, provider="blink")
    result = await flow.async_step_init({**BASE, "scenetrove_url": "https://st.example"})
    assert "scenetrove_url" not in result["data"]


async def test_the_form_suggests_the_link_instead_of_defaulting_it(monkeypatch):
    # Home Assistant drops a cleared optional field: a default would bring it back.
    flow = options_flow(monkeypatch)
    flow.config_entry.options = {"scenetrove_url": "https://st.example"}
    form = await flow.async_step_init()
    keys = {str(key): key for key in form["data_schema"]}
    for name, suggested in (
        ("scenetrove_url", "https://st.example"),
        ("scenetrove_device", "entrance"),
    ):
        assert "default" not in keys[name].options
        assert keys[name].options["description"] == {"suggested_value": suggested}


async def test_an_invalid_device_does_not_block_other_options_without_a_link(monkeypatch):
    flow = options_flow(monkeypatch)
    result = await flow.async_step_init({**BASE, "scenetrove_device": "front door"})
    assert result["type"] == "create_entry"
    assert result["data"]["scenetrove_device"] == "entrance"


TOKEN = "scenetrove_pat_" + "b" * 43


def probed_flow(monkeypatch, answer=None):
    """An options flow whose SceneTrove token probe answers `answer` and records calls."""
    flow = options_flow(monkeypatch)
    probes = []

    async def verify(session, url, token):
        probes.append((url, token))
        return answer

    monkeypatch.setattr(sys.modules[type(flow).__module__], "verify_sync_token", verify)
    return flow, probes


async def test_the_sync_token_is_write_only_kept_when_blank_and_dropped_on_unlink(monkeypatch):
    flow, _probes = probed_flow(monkeypatch)
    linked = {**BASE, "scenetrove_url": "https://st.example"}
    result = await flow.async_step_init({**linked, "scenetrove_token": f" {TOKEN} "})
    assert result["data"]["scenetrove_token"] == TOKEN
    flow.config_entry.options = result["data"]
    kept = await flow.async_step_init({**linked, "scenetrove_token": ""})
    assert kept["data"]["scenetrove_token"] == TOKEN
    form = await flow.async_step_init()
    key = next(key for key in form["data_schema"] if str(key) == "scenetrove_token")
    assert "default" not in key.options and "description" not in key.options
    unlinked = await flow.async_step_init({**BASE, "scenetrove_url": ""})
    assert "scenetrove_token" not in unlinked["data"]


async def test_a_malformed_sync_token_is_refused(monkeypatch):
    flow, probes = probed_flow(monkeypatch)
    linked = {**BASE, "scenetrove_url": "https://st.example"}
    for refused in ("secret", "scenetrove_pat_short", "scenetrove_pat_" + "x" * 40 + " y"):
        result = await flow.async_step_init({**linked, "scenetrove_token": refused})
        assert result["errors"] == {"base": "invalid_scenetrove_token"}, refused
    assert probes == [], "a malformed token is never sent to SceneTrove"


async def test_a_new_token_is_stored_only_when_scenetrove_proves_it_narrow(monkeypatch):
    linked = {**BASE, "scenetrove_url": "https://st.example", "scenetrove_token": TOKEN}
    for answer in (
        "scenetrove_token_too_broad",
        "scenetrove_token_rejected",
        "scenetrove_token_unverified",
    ):
        flow, probes = probed_flow(monkeypatch, answer)
        result = await flow.async_step_init(linked)
        assert result["type"] == "form"
        assert result["errors"] == {"base": answer}
        assert probes == [("https://st.example", TOKEN)]
    flow, probes = probed_flow(monkeypatch)
    stored = await flow.async_step_init(linked)
    assert stored["data"]["scenetrove_token"] == TOKEN


async def test_the_saved_token_is_probed_again_only_for_a_new_address(monkeypatch):
    flow, probes = probed_flow(monkeypatch)
    flow.config_entry.options = {"scenetrove_url": "https://st.example", "scenetrove_token": TOKEN}
    same = await flow.async_step_init({**BASE, "scenetrove_url": "https://st.example"})
    assert same["type"] == "create_entry" and probes == []
    await flow.async_step_init({**BASE, "scenetrove_url": "https://st2.example"})
    assert probes == [("https://st2.example", TOKEN)]
    await flow.async_step_init({**BASE, "scenetrove_url": ""})
    assert len(probes) == 1, "unlinking forgets the token without probing"

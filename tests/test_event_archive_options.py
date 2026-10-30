"""Options for the EZVIZ event archive: opt-in, ready mount and retention bounds."""

from release_flow_support import entry, framework


def options_flow(monkeypatch, provider="ezviz", ready=True):
    env = framework(monkeypatch)
    module = env.load("options_flow")
    readiness = {"ready": ready, "reason": "ready" if ready else "network_mount_missing"}
    monkeypatch.setattr(module, "storage_readiness", lambda mount: readiness)
    flow = module.VistodaOptionsFlow()
    flow.config_entry, flow.hass = entry(provider), env.hass
    return flow


async def test_event_archive_options_are_saved(monkeypatch):
    flow = options_flow(monkeypatch)
    result = await flow.async_step_init(
        {"backup_storage": "family_archive", "event_archive": True, "event_retention_days": 30}
    )
    assert result["type"] == "create_entry"
    assert result["data"]["event_archive"] is True
    assert result["data"]["event_retention_days"] == 30


async def test_options_reject_retention_between_one_and_six(monkeypatch):
    flow = options_flow(monkeypatch)
    for days in (1, 6):
        result = await flow.async_step_init(
            {
                "backup_storage": "family_archive",
                "event_archive": True,
                "event_retention_days": days,
            }
        )
        assert result["errors"] == {"base": "invalid_retention"}


async def test_enabling_needs_a_ready_mount(monkeypatch):
    flow = options_flow(monkeypatch, ready=False)
    result = await flow.async_step_init(
        {"backup_storage": "family_archive", "event_archive": True, "event_retention_days": 0}
    )
    assert result["errors"] == {"base": "network_mount_missing"}
    disabled = await flow.async_step_init(
        {"backup_storage": "family_archive", "event_archive": False, "event_retention_days": 0}
    )
    assert disabled["type"] == "create_entry"
    assert disabled["data"]["event_archive"] is False


async def test_blink_entries_ignore_event_options(monkeypatch):
    flow = options_flow(monkeypatch, provider="blink")
    result = await flow.async_step_init(
        {"backup_storage": "family_archive", "event_archive": True, "event_retention_days": 3}
    )
    assert result["type"] == "create_entry"
    assert "event_archive" not in result["data"]

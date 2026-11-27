"""Missing Python modules are installed through Home Assistant, and their absence is survivable."""

import logging
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.media_bridge import required_modules, ts_remux
from custom_components.media_bridge.recording_mp4 import convert


def hass_with_executor():
    async def run(function, *args):
        return function(*args)

    return SimpleNamespace(async_add_executor_job=run)


def fake_requirements(monkeypatch, installer):
    module = ModuleType("homeassistant.requirements")
    module.async_process_requirements = installer
    monkeypatch.setitem(sys.modules, module.__name__, module)


async def test_nothing_is_installed_when_everything_is_there(monkeypatch):
    installer = AsyncMock()
    fake_requirements(monkeypatch, installer)
    monkeypatch.setattr(required_modules, "missing_modules", lambda: [])
    assert await required_modules.async_ensure_modules(hass_with_executor()) == []
    installer.assert_not_awaited()


async def test_a_missing_module_is_installed_by_home_assistant(monkeypatch, caplog):
    still = iter([["av"], []])  # Missing before the install, present after it.
    monkeypatch.setattr(required_modules, "missing_modules", lambda: next(still))
    installer = AsyncMock()
    fake_requirements(monkeypatch, installer)
    hass = hass_with_executor()
    with caplog.at_level(logging.INFO):
        assert await required_modules.async_ensure_modules(hass) == []
    installer.assert_awaited_once_with(hass, "media_bridge", ["av"])
    assert "installed av" in caplog.text


async def test_a_failed_install_is_reported_and_never_raises(monkeypatch, caplog):
    monkeypatch.setattr(required_modules, "missing_modules", lambda: ["av"])
    fake_requirements(monkeypatch, AsyncMock(side_effect=RuntimeError("no network")))
    with caplog.at_level(logging.WARNING):
        assert await required_modules.async_ensure_modules(hass_with_executor()) == ["av"]
    assert "could not install av (no network)" in caplog.text


def test_the_real_check_sees_what_is_installed_and_what_is_not(monkeypatch):
    pytest.importorskip("av")
    assert required_modules.missing_modules() == []
    monkeypatch.setattr(required_modules.importlib.util, "find_spec", lambda name: None)
    assert required_modules.missing_modules() == ["av"]


def test_without_pyav_conversion_is_a_clean_refusal_and_backups_keep_the_ts(monkeypatch):
    monkeypatch.setitem(sys.modules, "av", None)  # `import av` now raises ImportError.
    with pytest.raises(ValueError, match="not installed"):
        ts_remux.ts_to_mp4(b"G" * 188)
    assert convert(b"G" * 188) is None

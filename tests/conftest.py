"""Load pure client modules without importing Home Assistant runtime modules."""

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "media_bridge"

custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
media_bridge = ModuleType("custom_components.media_bridge")
media_bridge.__path__ = [str(PACKAGE)]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.media_bridge", media_bridge)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_outage_clocks():
    """Outage clocks are process-wide by design; every test starts without an outage."""
    from custom_components.media_bridge import outage

    outage._CLOCKS.clear()
    yield
    outage._CLOCKS.clear()

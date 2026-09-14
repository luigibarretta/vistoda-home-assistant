"""Native account association must be exact and metadata must be allowlisted."""

import ast
from pathlib import Path
from types import SimpleNamespace as NS  # noqa: N814

SOURCE = Path("custom_components/media_bridge/ezviz_panel_metadata.py")


def metadata(native_entries, source="serial:1"):
    registry = NS(
        entities={
            "alarm": NS(
                config_entry_id="native", device_id=None, disabled_by=None,
                entity_id="alarm_control_panel.fixture", name=None, original_name="Alarm",
                original_device_class=None,
            ),
            "battery": NS(
                config_entry_id="native", device_id="device", disabled_by=None,
                entity_id="sensor.fixture_battery", name=None, original_name="Battery",
                original_device_class="battery",
            ),
            "audio": NS(
                config_entry_id="native", device_id="device", disabled_by=None,
                entity_id="switch.fixture_audio", name=None, original_name="Audio",
                original_device_class=None,
            ),
        }
    )
    lookups = []

    def find(identifier, entry_id):
        lookups.append((identifier, entry_id))
        return NS(id="device", area_id="hall")

    namespace = {
        "CONF_EZVIZ_SOURCE_ID": "ezviz_source_id",
        "valid_source_id": lambda value: value == "serial:1",
        "er": NS(async_get=lambda _: registry),
        "dr": NS(async_get=lambda _: NS(async_get_device_by_identifier=find)),
        "ar": NS(async_get=lambda _: NS(async_get_area=lambda _: NS(name="HA hall"))),
    }
    tree = ast.parse(SOURCE.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
    states = {
        "sensor.fixture_battery": NS(attributes={"friendly_name": "Camera battery", "device_class": "battery"}),
        "switch.fixture_audio": NS(attributes={"friendly_name": "Camera audio"}),
    }
    hass = NS(config_entries=NS(async_entries=lambda _: native_entries), states=NS(get=states.get))
    result = namespace["panel_metadata"](hass, NS(data={"ezviz_source_id": source}))
    return result, lookups


def native(name="Native camera"):
    return NS(
        entry_id="native",
        runtime_data=NS(
            data={"serial": {"name": name, "token": "do-not-expose", "password": "private"}}
        ),
    )


def test_exact_binding_exposes_native_name_account_alarm_and_labeled_ha_area():
    result, lookups = metadata([native()])
    assert result == {
        "device_name": "Native camera",
        "alarm_entity_id": "alarm_control_panel.fixture",
        "alarm_scope": "account",
        "native_entities": [
            {"entity_id": "sensor.fixture_battery", "domain": "sensor", "name": "Camera battery", "device_class": "battery"},
            {"entity_id": "switch.fixture_audio", "domain": "switch", "name": "Camera audio", "device_class": None},
        ],
        "battery_entity_id": "sensor.fixture_battery",
        "room_name": "HA hall",
        "room_source": "home_assistant",
    }
    assert lookups == [(("ezviz", "serial"), "native")]


def test_missing_or_ambiguous_binding_never_guesses_account_by_name():
    assert metadata([native()], "another:1")[0] == {}
    assert metadata([native(), native()])[0] == {}
    assert metadata([])[0] == {}

"""Battery level (app 0.10+) and charging state (app 0.13+) of one EZVIZ camera."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .ezviz_controls import BATTERY_SUFFIX, CHARGING_SUFFIX, controls_of
from .ezviz_identity import device_info, entity_prefix


class EzvizBatterySensor(CoordinatorEntity, SensorEntity):
    """Created only once the app reports a battery; work mode stays an attribute."""

    _attr_has_entity_name = True
    _attr_translation_key = "ezviz_battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entity_prefix(entry)}{BATTERY_SUFFIX}"
        self._attr_device_info = device_info(entry)

    @property
    def _controls(self):
        return controls_of(self.coordinator.data)

    @property
    def available(self) -> bool:
        controls = self._controls
        return (
            self.coordinator.last_update_success
            and controls is not None
            and controls.battery_percent is not None
        )

    @property
    def native_value(self) -> int | None:
        controls = self._controls
        return controls.battery_percent if controls else None

    @property
    def extra_state_attributes(self) -> dict:
        controls = self._controls
        return {"work_mode": controls.battery_work_mode if controls else None}


class EzvizChargingSensor(CoordinatorEntity, BinarySensorEntity):
    """Charging state; created only once the app reports one (0.13+)."""

    _attr_has_entity_name = True
    _attr_translation_key = "ezviz_charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entity_prefix(entry)}{CHARGING_SUFFIX}"
        self._attr_device_info = device_info(entry)

    @property
    def _controls(self):
        return controls_of(self.coordinator.data)

    @property
    def available(self) -> bool:
        controls = self._controls
        return (
            self.coordinator.last_update_success
            and controls is not None
            and controls.battery_charging is not None
        )

    @property
    def is_on(self) -> bool | None:
        controls = self._controls
        return controls.battery_charging if controls else None

    @property
    def extra_state_attributes(self) -> dict:
        controls = self._controls
        return {
            "power_source": controls.battery_power_source if controls else None,
            "power_status": controls.battery_power_status if controls else None,
        }


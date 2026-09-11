"""Bounded Ring status and control client contract."""

from urllib.parse import quote

from .models import parse_ring_status


class RingControlClientMixin:
    """Consume the private Ring control endpoints."""

    async def ring_status(self, alias: str):
        """Return native Ring Intercom battery, connectivity and levels."""
        payload = await self._json("GET", f"/v1/devices/{quote(alias, safe='')}/status")
        return parse_ring_status(payload)

    async def unlock_ring(self, alias: str, *, expected_device_id: str) -> None:
        """Issue one native unlock request without retries in Home Assistant."""
        await self._empty(
            "POST",
            f"/v1/devices/{quote(alias, safe='')}/unlock",
            json={"expected_device_id": expected_device_id},
        )

    async def set_ring_volume(
        self, alias: str, setting: str, value: int, *, expected_device_id: str
    ) -> None:
        """Set exactly one bounded native volume."""
        if setting not in {"doorbell_volume", "mic_volume", "voice_volume"}:
            raise ValueError("unknown Ring volume")
        await self._empty(
            "PATCH",
            f"/v1/devices/{quote(alias, safe='')}/settings",
            json={setting: value, "expected_device_id": expected_device_id},
        )

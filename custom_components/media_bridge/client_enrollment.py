"""Provider enrollment calls shared by managed Vistoda apps."""

from typing import Any
from urllib.parse import quote

from .client_helpers import parse_enrollment
from .errors import CannotConnectError
from .managed_devices import SAFE_ALIAS
from .models import Enrollment
from .ring_binding import valid_device_id


class EnrollmentClientMixin:
    """Keep two-step enrollment mechanics out of the media client."""

    async def ring_intercoms(self) -> list[dict]:
        """Return bounded physical identities and provider-verified routable aliases."""
        raw = (await self._json("GET", "/v1/intercoms")).get("intercoms")
        if not isinstance(raw, list) or len(raw) > 64:
            raise CannotConnectError
        result, identifiers, aliases = [], set(), set()
        for item in raw:
            if not isinstance(item, dict) or not valid_device_id(item.get("device_id")):
                raise CannotConnectError
            identifier = item["device_id"]
            name, location, alias = item.get("name"), item.get("location_name"), item.get("alias")
            if (
                identifier in identifiers
                or not isinstance(name, str)
                or not 1 <= len(name) <= 256
                or (location is not None and (not isinstance(location, str) or len(location) > 256))
                or (
                    alias is not None
                    and (
                        not isinstance(alias, str)
                        or not SAFE_ALIAS.fullmatch(alias)
                        or alias in aliases
                    )
                )
            ):
                raise CannotConnectError
            result.append(
                {"device_id": identifier, "name": name, "location_name": location, "alias": alias}
            )
            identifiers.add(identifier)
            if alias is not None:
                aliases.add(alias)
        return result

    async def start_ring_enrollment(self, email: str, password: str) -> Enrollment:
        return await self._start_enrollment({"email": email, "password": password})

    async def start_ezviz_enrollment(
        self, account: str, password: str, api_region: str
    ) -> Enrollment:
        return await self._start_enrollment(
            {"account": account, "password": password, "api_region": api_region}
        )

    async def verify_enrollment(self, enrollment_id: str, code: str) -> None:
        payload = await self._json(
            "POST", f"/v1/enrollments/{quote(enrollment_id, safe='')}", json={"code": code}
        )
        if payload.get("status") != "complete":
            raise CannotConnectError

    async def cancel_enrollment(self, enrollment_id: str) -> None:
        response = await self._request("DELETE", f"/v1/enrollments/{quote(enrollment_id, safe='')}")
        async with response:
            await self._bounded(response, 64 * 1024)
            if response.status not in (204, 404):
                self._raise_status(response.status)

    async def _start_enrollment(self, payload: dict[str, Any]) -> Enrollment:
        return parse_enrollment(await self._json("POST", "/v1/enrollments", json=payload))

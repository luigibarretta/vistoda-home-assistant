"""Provider enrollment calls shared by managed Vistoda apps."""

from typing import Any
from urllib.parse import quote

from .client_helpers import parse_enrollment
from .errors import CannotConnectError
from .models import Enrollment


class EnrollmentClientMixin:
    """Keep two-step enrollment mechanics out of the media client."""

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

"""Python modules Vistoda needs beyond Home Assistant's own, installed on demand.

Today that is one: `av` (PyAV), which converts Blink recordings to MP4. Home Assistant's `stream`
component (a dependency of this integration) already requires it, so this is a safety net rather
than the normal path. It is deliberately *not* a manifest requirement: a failed install of a
manifest requirement stops the whole integration from loading, while here it only turns off the
MP4 conversion (recordings stay as TS and are not playable in the browser).
"""

import importlib
import importlib.util
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
# Import name → requirement. Home Assistant's constraints pick the version.
REQUIRED_MODULES = {"av": "av"}


def missing_modules() -> list[str]:
    """Requirements whose module cannot be imported."""
    return [
        requirement
        for name, requirement in REQUIRED_MODULES.items()
        if importlib.util.find_spec(name) is None
    ]


async def async_ensure_modules(hass) -> list[str]:
    """Install what is missing with Home Assistant's own requirements manager.

    Returns the requirements that are still missing afterwards; never raises, so a machine
    without network or without pip access keeps working without the MP4 conversion.
    """
    missing = await hass.async_add_executor_job(missing_modules)
    if not missing:
        return []
    from homeassistant.requirements import async_process_requirements

    _LOGGER.info("Vistoda needs %s; asking Home Assistant to install it", ", ".join(missing))
    try:
        await async_process_requirements(hass, DOMAIN, missing)
    except Exception as error:  # RequirementsNotFound, no network, pip disabled…
        _LOGGER.warning(
            "Vistoda could not install %s (%s): Blink recordings stay as TS and cannot be "
            "played in the browser until it is installed",
            ", ".join(missing),
            error,
        )
        return await hass.async_add_executor_job(missing_modules)
    importlib.invalidate_caches()
    still_missing = await hass.async_add_executor_job(missing_modules)
    if still_missing:
        _LOGGER.warning("Vistoda still lacks %s after installing", ", ".join(still_missing))
    else:
        _LOGGER.info("Vistoda installed %s", ", ".join(missing))
    return still_missing

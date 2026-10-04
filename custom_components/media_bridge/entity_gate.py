"""Add entities only once an optional provider feature has been reported."""

from collections.abc import Callable, Iterable

from homeassistant.core import callback


def async_add_when_supported(
    entry,
    coordinator,
    supported: Callable[[object], bool],
    build: Callable[[], Iterable],
    async_add_entities,
) -> None:
    """Older engines lack the feature: create nothing until a poll reports it."""
    if supported(coordinator.data):
        async_add_entities(list(build()))
        return
    remove = None

    @callback
    def _check() -> None:
        nonlocal remove
        if remove is not None and supported(coordinator.data):
            remove()
            remove = None
            async_add_entities(list(build()))

    remove = coordinator.async_add_listener(_check)
    entry.async_on_unload(lambda: remove() if remove is not None else None)

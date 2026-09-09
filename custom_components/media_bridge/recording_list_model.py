"""Validated persistent model for user-defined Ring recording lists."""

from uuid import uuid4

MAX_LISTS_PER_ENTRY = 64
MAX_RECORDINGS_PER_LIST = 4096
MAX_NAME_LENGTH = 64
MAX_RECORDING_ID_LENGTH = 64


class RecordingListError(ValueError):
    """Describe one bounded list validation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_list_name(name: str) -> str:
    """Normalize a visible list name without accepting empty input."""
    normalized = " ".join(name.split())
    if not normalized or len(normalized) > MAX_NAME_LENGTH:
        raise RecordingListError("invalid_name")
    return normalized


class RecordingListData:
    """Own the serializable many-to-many list membership state."""

    def __init__(self, data: object) -> None:
        raw_entries = data.get("entries", {}) if isinstance(data, dict) else {}
        entries = {}
        if isinstance(raw_entries, dict):
            for entry_id, raw_lists in raw_entries.items():
                if isinstance(entry_id, str):
                    entries[entry_id] = self._clean_lists(raw_lists)
        self.data = {"entries": entries}
        self.dirty = self.data != data

    def snapshot(
        self, entry_id: str, valid_recording_ids: set[str] | None = None
    ) -> tuple[list[dict], bool]:
        """Return one entry and optionally prune orphan memberships."""
        lists = self._entry(entry_id)
        changed = False
        if valid_recording_ids is not None:
            for item in lists:
                valid = [value for value in item["recording_ids"] if value in valid_recording_ids]
                if valid != item["recording_ids"]:
                    item["recording_ids"] = valid
                    changed = True
        changed = changed or self.dirty
        self.dirty = False
        return self._public(lists), changed

    def create(self, entry_id: str, name: str) -> tuple[list[dict], str]:
        """Create a uniquely named list for one config entry."""
        lists = self._entry(entry_id)
        normalized = normalize_list_name(name)
        if len(lists) >= MAX_LISTS_PER_ENTRY:
            raise RecordingListError("list_limit")
        if any(item["name"].casefold() == normalized.casefold() for item in lists):
            raise RecordingListError("duplicate_name")
        list_id = uuid4().hex
        lists.append({"list_id": list_id, "name": normalized, "recording_ids": []})
        return self._public(lists), list_id

    def delete(self, entry_id: str, list_id: str) -> tuple[list[dict], bool]:
        """Delete one list without deleting any recording."""
        lists = self._entry(entry_id)
        remaining = [item for item in lists if item["list_id"] != list_id]
        changed = len(remaining) != len(lists)
        if changed:
            self.data["entries"][entry_id] = remaining
        return self._public(remaining), changed

    def update(self, entry_id: str, list_id: str, name: str) -> tuple[list[dict], bool]:
        """Rename one list while preserving its recording memberships."""
        lists = self._entry(entry_id)
        item = next((value for value in lists if value["list_id"] == list_id), None)
        if item is None:
            raise RecordingListError("list_not_found")
        normalized = normalize_list_name(name)
        if any(
            value["list_id"] != list_id and value["name"].casefold() == normalized.casefold()
            for value in lists
        ):
            raise RecordingListError("duplicate_name")
        if item["name"] == normalized:
            return self._public(lists), False
        item["name"] = normalized
        return self._public(lists), True

    def set_membership(
        self, entry_id: str, list_id: str, recording_id: str, included: bool
    ) -> tuple[list[dict], bool]:
        """Add or remove one recording from one list idempotently."""
        if not recording_id or len(recording_id) > MAX_RECORDING_ID_LENGTH:
            raise RecordingListError("invalid_recording")
        lists = self._entry(entry_id)
        item = next((value for value in lists if value["list_id"] == list_id), None)
        if item is None:
            raise RecordingListError("list_not_found")
        members = item["recording_ids"]
        present = recording_id in members
        if included and not present:
            if len(members) >= MAX_RECORDINGS_PER_LIST:
                raise RecordingListError("membership_limit")
            members.append(recording_id)
            return self._public(lists), True
        if not included and present:
            members.remove(recording_id)
            return self._public(lists), True
        return self._public(lists), False

    def remove_recordings(self, entry_id: str, recording_ids: set[str]) -> bool:
        """Remove deleted recordings from every list in one write."""
        changed = False
        for item in self._entry(entry_id):
            members = [value for value in item["recording_ids"] if value not in recording_ids]
            if members != item["recording_ids"]:
                item["recording_ids"] = members
                changed = True
        return changed

    def _entry(self, entry_id: str) -> list[dict]:
        return self.data["entries"].setdefault(entry_id, [])

    @staticmethod
    def _public(lists: list[dict]) -> list[dict]:
        return [{**item, "recording_ids": list(item["recording_ids"])} for item in lists]

    @staticmethod
    def _clean_lists(raw_lists: object) -> list[dict]:
        if not isinstance(raw_lists, list):
            return []
        cleaned = []
        seen_ids = set()
        seen_names = set()
        for raw in raw_lists[:MAX_LISTS_PER_ENTRY]:
            if not isinstance(raw, dict):
                continue
            list_id = raw.get("list_id")
            try:
                name = normalize_list_name(raw.get("name", ""))
            except RecordingListError:
                continue
            if not isinstance(list_id, str) or not list_id or len(list_id) > 64:
                continue
            if list_id in seen_ids or name.casefold() in seen_names:
                continue
            raw_members = raw.get("recording_ids", [])
            members = []
            if isinstance(raw_members, list):
                for value in raw_members:
                    if (
                        isinstance(value, str)
                        and 0 < len(value) <= MAX_RECORDING_ID_LENGTH
                        and value not in members
                    ):
                        members.append(value)
                    if len(members) == MAX_RECORDINGS_PER_LIST:
                        break
            cleaned.append({"list_id": list_id, "name": name, "recording_ids": members})
            seen_ids.add(list_id)
            seen_names.add(name.casefold())
        return cleaned

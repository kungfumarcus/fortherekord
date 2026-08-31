"""
Query and smart-playlist criteria validation.

Field/operator pairs follow specs/McpServer.md. Rekordbox smart-list XML
cannot store location or missing; those are search-only.
"""

from typing import Dict, FrozenSet, Optional

from .domain import Condition, Criteria
from .errors import ValidationError

TEXT_OPS: FrozenSet[str] = frozenset(
    {"is", "is_not", "contains", "not_contains", "starts_with", "ends_with"}
)
NUMBER_OPS: FrozenSet[str] = frozenset({"is", "is_not", "greater", "less", "between"})
DATE_OPS: FrozenSet[str] = NUMBER_OPS | frozenset({"in_last", "not_in_last"})
TAG_OPS: FrozenSet[str] = frozenset({"contains", "not_contains"})
FLAG_OPS: FrozenSet[str] = frozenset({"is"})
ID_OPS: FrozenSet[str] = frozenset({"is", "is_not"})
MEMBERSHIP_OPS: FrozenSet[str] = frozenset({"contains", "not_contains"})

TRACK_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = {
    "title": TEXT_OPS,
    "artist": TEXT_OPS,
    "album": TEXT_OPS,
    "album_artist": TEXT_OPS,
    "original_artist": TEXT_OPS,
    "remixer": TEXT_OPS,
    "composer": TEXT_OPS,
    "genre": TEXT_OPS,
    "label": TEXT_OPS,
    "comments": TEXT_OPS,
    "key": TEXT_OPS,
    "filename": TEXT_OPS,
    "tags": TAG_OPS,
    "bpm": NUMBER_OPS,
    "rating": NUMBER_OPS,
    "duration": NUMBER_OPS,
    "year": NUMBER_OPS,
    "play_count": NUMBER_OPS,
    "bitrate": NUMBER_OPS,
    "file_type": TEXT_OPS,
    "date_added": DATE_OPS,
    "date_created": DATE_OPS,
    "date_released": DATE_OPS,
    "color": frozenset({"is", "is_not"}),
    "location": frozenset({"is", "is_not", "contains", "starts_with"}),
    "missing": FLAG_OPS,
}

SMART_PERSIST_FIELDS: Dict[str, FrozenSet[str]] = {
    key: ops
    for key, ops in TRACK_SEARCH_FIELDS.items()
    if key not in {"location", "missing", "bitrate", "file_type"}
}

FOLDER_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = {
    "id": ID_OPS,
    "name": TEXT_OPS,
    "path": TEXT_OPS,
    "parent": ID_OPS,
    "position": NUMBER_OPS,
}

PLAYLIST_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = {
    "id": ID_OPS,
    "name": TEXT_OPS,
    "path": TEXT_OPS,
    "folder": ID_OPS,
    "position": NUMBER_OPS,
    "track": MEMBERSHIP_OPS,
}

SMART_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = {
    "id": ID_OPS,
    "name": TEXT_OPS,
    "path": TEXT_OPS,
    "folder": ID_OPS,
    "position": NUMBER_OPS,
}

HISTORY_FOLDER_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = FOLDER_SEARCH_FIELDS

HISTORY_SESSION_SEARCH_FIELDS: Dict[str, FrozenSet[str]] = {
    **PLAYLIST_SEARCH_FIELDS,
    "date": DATE_OPS,
}

PERIOD_UNITS: FrozenSet[str] = frozenset({"day", "week"})


def criteria_from_dict(payload: Dict[str, object]) -> Criteria:
    """Build Criteria from a JSON-like dict."""
    match = payload.get("match", "all")
    raw_conditions = payload.get("conditions")
    if not isinstance(raw_conditions, list):
        raise ValidationError("criteria.conditions must be a list")
    conditions = []
    for item in raw_conditions:
        if not isinstance(item, dict):
            raise ValidationError("each condition must be an object")
        if "field" not in item or "operator" not in item:
            raise ValidationError("condition requires field and operator")
        conditions.append(
            Condition(
                field=str(item["field"]),
                operator=str(item["operator"]),
                value=item.get("value"),
            )
        )
    return Criteria(match=str(match), conditions=conditions)


def validate_criteria(
    criteria: Criteria, allowed: Optional[Dict[str, FrozenSet[str]]] = None
) -> None:
    """Reject empty lists, bad match, month periods, and illegal pairs."""
    fields = allowed if allowed is not None else TRACK_SEARCH_FIELDS
    if criteria.match not in {"all", "any"}:
        raise ValidationError("match must be 'all' or 'any'")
    if not criteria.conditions:
        raise ValidationError("criteria requires at least one condition")
    for condition in criteria.conditions:
        _validate_condition(condition, fields)


def _validate_condition(condition: Condition, fields: Dict[str, FrozenSet[str]]) -> None:
    if condition.field not in fields:
        raise ValidationError(f"unknown field '{condition.field}'")
    legal = fields[condition.field]
    if condition.operator not in legal:
        raise ValidationError(
            f"operator '{condition.operator}' is not valid for '{condition.field}'"
        )
    if condition.operator == "between":
        if not isinstance(condition.value, dict):
            raise ValidationError("between requires {min, max}")
        if "min" not in condition.value or "max" not in condition.value:
            raise ValidationError("between requires {min, max}")
    if condition.operator in {"in_last", "not_in_last"}:
        _validate_period(condition.value)


def _validate_period(value: object) -> None:
    if not isinstance(value, dict):
        raise ValidationError("in_last requires {amount, unit}")
    if "amount" not in value or "unit" not in value:
        raise ValidationError("in_last requires {amount, unit}")
    unit = str(value["unit"])
    if unit == "month":
        raise ValidationError("month is not supported for in_last")
    if unit not in PERIOD_UNITS:
        raise ValidationError("unit must be 'day' or 'week'")


def criteria_to_dict(criteria: Criteria) -> Dict[str, object]:
    """Serialize criteria for diffs and MCP responses."""
    return {
        "match": criteria.match,
        "conditions": [
            {"field": c.field, "operator": c.operator, "value": c.value}
            for c in criteria.conditions
        ],
    }


def validate_smart_playlist_criteria(criteria: Criteria) -> None:
    """Criteria written to Rekordbox cannot use search-only fields."""
    validate_criteria(criteria, SMART_PERSIST_FIELDS)

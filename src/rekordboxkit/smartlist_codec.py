"""Convert domain Criteria to and from pyrekordbox SmartList XML."""

from typing import Any, Callable, Optional, Tuple

from pyrekordbox.db6.smartlist import LogicalOperator, SmartList

from .criteria import validate_smart_playlist_criteria
from .domain import Condition, Criteria
from .errors import ValidationError

FIELD_TO_PROPERTY = {
    "title": "name",
    "artist": "artist",
    "album": "album",
    "album_artist": "albumArtist",
    "original_artist": "originalArtist",
    "remixer": "remixedBy",
    "composer": "producer",
    "genre": "genre",
    "label": "label",
    "comments": "comments",
    "key": "key",
    "filename": "fileName",
    "tags": "myTag",
    "bpm": "bpm",
    "rating": "rating",
    "duration": "duration",
    "year": "year",
    "play_count": "counter",
    "date_added": "stockDate",
    "date_created": "dateCreated",
    "date_released": "dateReleased",
    "color": "grouping",
}

PROPERTY_TO_FIELD = {value: key for key, value in FIELD_TO_PROPERTY.items()}

OP_TO_INT = {
    "is": 1,
    "is_not": 2,
    "greater": 3,
    "less": 4,
    "between": 5,
    "in_last": 6,
    "not_in_last": 7,
    "contains": 8,
    "not_contains": 9,
    "starts_with": 10,
    "ends_with": 11,
}

INT_TO_OP = {value: key for key, value in OP_TO_INT.items()}


def criteria_to_smartlist(
    criteria: Criteria,
    playlist_id: str,
    tag_id_for_name: Callable[[str], str],
    color_id_for_name: Callable[[str], str],
) -> SmartList:
    """Build a pyrekordbox SmartList from domain criteria."""
    validate_smart_playlist_criteria(criteria)
    logical = LogicalOperator.ALL if criteria.match == "all" else LogicalOperator.ANY
    smart = SmartList(logical_operator=int(logical))
    smart.playlist_id = playlist_id
    for condition in criteria.conditions:
        prop = FIELD_TO_PROPERTY.get(condition.field)
        if not prop:
            raise ValidationError(
                f"field '{condition.field}' cannot be saved as smart playlist criteria"
            )
        left, right, unit = _encode_value(condition, tag_id_for_name, color_id_for_name)
        smart.add_condition(prop, OP_TO_INT[condition.operator], left, right, unit)
    return smart


def smartlist_to_criteria(
    xml: Optional[str],
    tag_name_for_id: Callable[[str], str],
    color_name_for_id: Callable[[str], str],
) -> Optional[Criteria]:
    """Parse SmartList XML into domain Criteria."""
    if not xml:
        return None
    smart = SmartList()
    smart.parse(xml)
    match = "all" if int(smart.logical_operator) == int(LogicalOperator.ALL) else "any"
    conditions = []
    for raw in smart.conditions:
        field = PROPERTY_TO_FIELD.get(raw.property)
        if not field:
            continue
        operator = INT_TO_OP.get(int(raw.operator))
        if not operator:
            continue
        value = _decode_value(field, operator, raw, tag_name_for_id, color_name_for_id)
        conditions.append(Condition(field=field, operator=operator, value=value))
    if not conditions:
        return None
    return Criteria(match=match, conditions=conditions)


def _encode_value(
    condition: Condition,
    tag_id_for_name: Callable[[str], str],
    color_id_for_name: Callable[[str], str],
) -> Tuple[str, str, str]:
    if condition.operator == "between" and isinstance(condition.value, dict):
        return str(condition.value["min"]), str(condition.value["max"]), ""
    if condition.operator in {"in_last", "not_in_last"} and isinstance(condition.value, dict):
        unit = str(condition.value["unit"])
        return str(condition.value["amount"]), "", unit
    value = condition.value
    if condition.field == "tags":
        return str(tag_id_for_name(str(value))), "", ""
    if condition.field == "color":
        return str(color_id_for_name(str(value))), "", ""
    return str(value if value is not None else ""), "", ""


def _decode_value(
    field: str,
    operator: str,
    raw: Any,
    tag_name_for_id: Callable[[str], str],
    color_name_for_id: Callable[[str], str],
) -> Any:
    if operator == "between":
        return {"min": _maybe_number(raw.value_left), "max": _maybe_number(raw.value_right)}
    if operator in {"in_last", "not_in_last"}:
        return {"amount": int(raw.value_left), "unit": raw.unit or "day"}
    left = raw.value_left
    if field == "tags":
        return tag_name_for_id(str(left))
    if field == "color":
        return color_name_for_id(str(left))
    return _maybe_number(left)


def _maybe_number(value: Any) -> Any:
    if value is None or value == "":
        return ""
    text = str(value)
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text

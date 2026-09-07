"""Validate the bundled schema subset without installed Python packages.

The source schemas remain Draft 2020-12. Their current validation keywords are
compatible with Draft 7; new keywords must be reviewed instead of silently ignored.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import json
import math
import re

from vendor import fastjsonschema


class InvalidSchemaData(ValueError):
    def __init__(self, stage, path, message):
        self.path = tuple(path)
        pointer = "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in path)
        super().__init__(f"{stage} schema at {pointer}: {message}")


class InvalidSchema(ValueError):
    pass


_DATE_TIME = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-]([0-9]{2}):([0-9]{2}))")


def date_time(value):
    """RFC 3339 calendar/time/offset checks; fractional seconds are not truncated.

    Like jsonschema's optional RFC 3339 checker, leap-second spelling is rejected.
    Unlike its permissive regex terminator, this checks the entire string.
    """
    if not isinstance(value, str):
        return True  # JSON Schema formats only constrain strings.
    match = _DATE_TIME.fullmatch(value)
    if not match:
        return False
    try:
        datetime(*(int(v) for v in match.groups()[:6]))
        return match[7] is None or (int(match[7]) < 24 and int(match[8]) < 60)
    except ValueError:
        return False


_MAPS = {"properties", "$defs"}
_LISTS = {"allOf", "anyOf", "oneOf"}
_SINGLES = {"items", "not", "if", "then", "else", "additionalProperties"}
_KEYWORDS = _MAPS | _LISTS | _SINGLES | {
    "$schema", "$id", "$ref", "title", "description", "type", "enum", "const",
    "required", "minLength", "maxLength", "minItems", "maxItems", "minimum",
    "maximum", "pattern", "format", "uniqueItems"}
_TYPES = {"null", "boolean", "object", "array", "number", "integer", "string"}


def _check_contract(contract):
    patterns, refs = set(), []

    def fail(location, message):
        raise InvalidSchema(f"Schema definition at {location or '/'}: {message}")

    def walk(node, location=""):
        if isinstance(node, bool):
            return
        if not isinstance(node, dict):
            fail(location, "expected a schema object or boolean")
        unknown = node.keys() - _KEYWORDS
        if unknown:
            fail(location, f"unsupported keywords: {', '.join(sorted(unknown))}")
        if "$schema" in node and node["$schema"] != "https://json-schema.org/draft/2020-12/schema":
            fail(location, "expected the bundled Draft 2020-12 dialect")
        if "$id" in node and (location or not isinstance(node["$id"], str)):
            fail(location, "only a root string $id is supported")
        if "$ref" in node:
            ref = node["$ref"]
            if len(node) != 1 or not isinstance(ref, str) or not ref.startswith("#/$defs/"):
                fail(location, "use a local $defs reference without sibling keywords")
            refs.append((ref, location))
        for key, value in node.items():
            child = f"{location}/{key}"
            if key in _MAPS:
                if not isinstance(value, dict):
                    fail(child, "expected a map of schemas")
                for name, schema in value.items():
                    walk(schema, f"{child}/{name}")
            elif key in _LISTS:
                if not isinstance(value, list) or not value:
                    fail(child, "expected a nonempty list of schemas")
                for index, schema in enumerate(value):
                    walk(schema, f"{child}/{index}")
            elif key in _SINGLES:
                walk(value, child)
            elif key == "type":
                types = value if isinstance(value, list) else [value]
                if (not types or any(not isinstance(t, str) or t not in _TYPES for t in types)
                        or len(types) != len(set(types))):
                    fail(child, "expected distinct JSON types")
            elif key == "required":
                if (not isinstance(value, list) or any(not isinstance(v, str) for v in value)
                        or len(value) != len(set(value))):
                    fail(child, "expected distinct property names")
            elif key in {"minLength", "maxLength", "minItems", "maxItems"}:
                if type(value) is not int or value < 0:
                    fail(child, "expected a nonnegative integer")
            elif key in {"minimum", "maximum"}:
                if type(value) not in (int, float) or not math.isfinite(value):
                    fail(child, "expected a finite number")
            elif key == "enum" and (not isinstance(value, list) or not value):
                fail(child, "expected a nonempty list")
            elif key == "uniqueItems" and type(value) is not bool:
                fail(child, "expected a boolean")
            elif key == "format" and value != "date-time":
                fail(child, "only date-time is supported")
            elif key == "pattern":
                try:
                    re.compile(value)
                except (TypeError, re.error) as error:
                    fail(child, str(error))
                patterns.add(value)
            elif key in {"title", "description"} and not isinstance(value, str):
                fail(child, "expected a string")

    walk(contract)
    for ref, location in refs:
        target = contract
        try:
            for key in ref[2:].split("/"):
                target = target[key.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            fail(location, f"unresolved reference: {ref}")
    return patterns


@lru_cache(maxsize=16)
def _compiled(serialized, formats):
    contract = json.loads(serialized)
    patterns = _check_contract(contract)
    # Select an explicit compatible dialect; do not rely on upstream's fallback
    # for an unrecognized $schema. Local $defs JSON pointers remain unchanged.
    if isinstance(contract, dict):
        contract["$schema"] = "http://json-schema.org/draft-07/schema#"
    try:
        compiled = fastjsonschema.compile(contract, use_default=False, use_formats=formats,
                                          formats={"date-time": date_time}, fast_fail=False)
    except (fastjsonschema.JsonSchemaDefinitionException, TypeError, KeyError, ValueError) as error:
        raise InvalidSchema(f"Cannot compile bundled schema: {error}") from error
    # Pinned fastjsonschema rewrites $ to \Z. Restore jsonschema/Python regex
    # semantics in this compiled function only, without patching vendor globals.
    compiled.func.__globals__["REGEX_PATTERNS"].update({p: re.compile(p) for p in patterns})
    return compiled


def check_schema(contract):
    _compiled(json.dumps(contract, sort_keys=True), True)


def _path(error, data):
    result = []
    for part in error.path[1:]:  # upstream paths start with the synthetic "data" root
        key = int(part) if isinstance(data, list) else part
        result.append(key)
        data = data[key]
    return tuple(result)


def validate(data, contract, stage="internal", *, formats=True):
    compiled = _compiled(json.dumps(contract, sort_keys=True), formats)
    try:
        compiled(data)
    except (fastjsonschema.JsonSchemaValueException, fastjsonschema.JsonSchemaValuesException) as error:
        errors = getattr(error, "errors", [error])
        first = min(errors, key=lambda e: str(list(_path(e, data))))
        raise InvalidSchemaData(stage, _path(first, data), first.message) from None
    return data

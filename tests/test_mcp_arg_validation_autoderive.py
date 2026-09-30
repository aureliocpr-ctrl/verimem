"""§305 — auto-derived lenient input validation for ALL MCP tools.

Pre-§305 only the ~15 hand-tuned schemas in `_SCHEMAS_BY_TOOL` validated their
arguments; the other ~210 tools accepted anything. This wires a LENIENT
(type/enum, null-tolerant) schema auto-derived from every tool's own
`inputSchema`, so gross type/enum mistakes are caught. Since #146 it also keeps
the `required` fields the tool publishes: the schema a client reads from
`list_tools()` is the schema the door enforces.
"""
from __future__ import annotations

import pytest

from verimem import mcp_server as m

# ---------- _derive_lenient_schema (unit) -------------------------------


def test_derive_keeps_required_type_and_enum() -> None:
    """Dal T184 lo schema derivato TIENE `required`: il client legge da
    `list_tools()` i campi obbligatori, e la porta li deve far rispettare.
    Prima li lasciava cadere «per non rifiutare mai una chiamata che il
    gestore avrebbe accettato» — e il gestore accettava perche' leggeva quei
    campi con un ripiego vuoto, fino a scrivere un fatto la cui proposizione
    era la stringa 'None'. Un `required` che nomina un campo non dichiarato e'
    un refuso dello schema: si scarta invece di rifiutare ogni chiamata."""
    src = {
        "type": "object",
        "required": ["x", "fantasma"],
        "properties": {
            "x": {"type": "string", "minLength": 3, "description": "d"},
            "mode": {"type": "string", "enum": ["a", "b"]},
            "n": {"type": "integer", "minimum": 1},
        },
    }
    d = m._derive_lenient_schema(src)
    assert d is not None
    assert d["required"] == ["x"]
    assert d["additionalProperties"] is True
    # type widened with null so an explicit-null optional never false-rejects
    assert d["properties"]["x"]["type"] == ["string", "null"]
    assert d["properties"]["n"]["type"] == ["integer", "null"]
    # strict constraints dropped (lenient by design)
    assert "minLength" not in d["properties"]["x"]
    assert "minimum" not in d["properties"]["n"]
    # enum kept
    assert d["properties"]["mode"]["enum"] == ["a", "b"]


def test_derive_keeps_a_required_field_that_has_no_type_or_enum() -> None:
    """Un campo obbligatorio senza `type` ne' `enum` resta obbligatorio.

    Lo schema derivato teneva `required` solo fra le proprieta' con un tipo o
    un enum: un campo obbligatorio dichiarato senza tipo usciva dallo schema
    della porta, e una chiamata che non lo porta passava. La sonda del 30/09
    ne conta 0 su 123 tool, ma il primo tool che ne pubblica uno nascerebbe
    col difetto che #146 cura. Qui si misura la funzione che costruisce lo
    schema, anche nel caso in cui l'unico campo dichiarato non ha tipo."""
    d = m._derive_lenient_schema({
        "type": "object",
        "required": ["x", "y"],
        "properties": {
            "x": {"type": "string"},
            "y": {"description": "qualunque valore"},
        },
    })
    assert d is not None
    assert d["required"] == ["x", "y"]
    solo = m._derive_lenient_schema({
        "type": "object",
        "required": ["y"],
        "properties": {"y": {"description": "qualunque valore"}},
    })
    assert solo is not None, "l'unico campo e' obbligatorio: lo schema serve"
    assert solo["required"] == ["y"]


def test_derive_returns_none_when_nothing_to_validate() -> None:
    assert m._derive_lenient_schema({"type": "object", "properties": {}}) is None
    assert m._derive_lenient_schema({"type": "string"}) is None
    assert m._derive_lenient_schema(None) is None
    # property with no usable type/enum → skipped → None
    assert m._derive_lenient_schema(
        {"type": "object", "properties": {"x": {"description": "d"}}}
    ) is None


# ---------- _ensure_derived_schemas (coverage + manual precedence) ------


@pytest.mark.asyncio
async def test_derived_covers_most_tools_and_manual_wins() -> None:
    await m._ensure_derived_schemas()
    # The vast majority of the ~228 tools now have at least a lenient schema.
    assert len(m._DERIVED_SCHEMAS) > 100
    # Manual schemas take precedence: a manually-schema'd tool is NOT shadowed
    # by a derived one (so its `required` etc still apply).
    assert "hippo_recall" in m._SCHEMAS_BY_TOOL
    assert "hippo_recall" not in m._DERIVED_SCHEMAS


# ---------- validation wired through _validate_input --------------------


@pytest.mark.asyncio
async def test_autoderived_rejects_bad_type() -> None:
    await m._ensure_derived_schemas()
    target = None
    for tname, sch in m._DERIVED_SCHEMAS.items():
        # un tool con campi obbligatori rifiuterebbe `{pk: 7}` per quelli:
        # qui si misura il TIPO, quindi si sceglie un tool senza `required`
        if sch.get("required"):
            continue
        for pk, pv in sch["properties"].items():
            ty = pv.get("type")
            if isinstance(ty, list) and "integer" in ty:
                target = (tname, pk)
                break
        if target:
            break
    assert target, "expected ≥1 auto-derived tool with an integer field"
    tname, pk = target
    # wrong type rejected …
    assert m._validate_input(tname, {pk: "not-an-integer"})
    # … correct type accepted …
    assert m._validate_input(tname, {pk: 7}) == ""
    # … explicit null tolerated (optional-safe) …
    assert m._validate_input(tname, {pk: None}) == ""
    # … and an UNDECLARED extra field is allowed (additionalProperties).
    assert m._validate_input(tname, {"___extra___": "whatever"}) == ""


@pytest.mark.asyncio
async def test_autoderived_rejects_bad_enum() -> None:
    await m._ensure_derived_schemas()
    target = None
    for tname, sch in m._DERIVED_SCHEMAS.items():
        if sch.get("required"):  # come sopra: qui si misura l'enum
            continue
        for pk, pv in sch["properties"].items():
            if isinstance(pv.get("enum"), list) and pv["enum"]:
                target = (tname, pk, pv["enum"])
                break
        if target:
            break
    if target is None:
        pytest.skip("no auto-derived tool exposes an enum field")
    tname, pk, enum = target
    assert m._validate_input(tname, {pk: "__not_a_valid_enum_value__"})
    assert m._validate_input(tname, {pk: enum[0]}) == ""

"""Native Hermes plugin: typed tools plus namespaced specialist workflows."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from . import core, artifacts


def schema(name, description, properties, required=()):
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": list(required), "additionalProperties": False}}


STRING = {"type": "string"}
TOOLS = [
    (core.capabilities, schema("engineering_status", "Inspect workbench capabilities and optional libraries. Does not probe live CAD, email or Hermes services.", {})),
    (core.plan, schema("engineering_plan", "Plan software, office or MEP work with evidence gates. This does not execute the plan. Load the returned namespaced specialist skill.", {
        "domain": {"type": "string", "enum": list(core.DOMAINS)}, "objective": STRING}, ("domain", "objective"))),
    (core.inspect_repo, schema("engineering_repo_inspect", "Static bounded inventory of known repository manifests in HERMES_WORKBENCH_ROOT. Reads no secrets and executes no code.", {"path": STRING})),
    (core.calculate, schema("engineering_mep_calculate", "Run a preliminary SI-unit MEP formula with explicit design basis. Not equipment sizing, code compliance or construction approval. Inputs must match the operation exactly.", {
        "operation": {"type": "string", "enum": list(core.CALCULATIONS)},
        "design_basis": STRING,
        "inputs": {"type": "object", "properties": {key: {"type": "number", "description": "Strict SI quantity; unit is encoded in the field name"} for entry in core.CALCULATIONS.values() for key in entry[0]}, "additionalProperties": False}}, ("operation", "inputs", "design_basis"))),
    (core.boq, schema("engineering_boq", "Check BOQ decimal arithmetic and duplicate IDs from supplied quantities/prices; does not verify scope, units, source prices, taxes or code compliance.", {
        "currency": STRING, "items": {"type": "array", "minItems": 1, "maxItems": 1000, "items": {
            "type": "object", "properties": {key: ({"type": ["string", "number"]} if key in ("quantity", "unit_price") else STRING) for key in ("id", "description", "unit", "quantity", "unit_price", "source")},
            "required": ["id", "description", "unit", "quantity", "unit_price", "source"], "additionalProperties": False}}}, ("currency", "items"))),
    (artifacts.export, schema("engineering_export", "Create a NEW draft artifact and hash/provenance manifest inside the authorized workspace. Formats MD/CSV/DOCX/XLSX/PPTX/PDF. PDF/PPTX tables are unsupported. Unicode PDF needs operator-configured TTF. No email, upload or overwrite. Visual review remains required.", {
        "format": {"type": "string", "enum": sorted(artifacts.FORMATS)}, "title": STRING,
        "sections": {"type": "array", "maxItems": 100, "items": {"type": "object", "properties": {"heading": STRING, "body": STRING}, "required": ["heading", "body"], "additionalProperties": False}},
        "columns": {"type": "array", "maxItems": 30, "items": STRING},
        "rows": {"type": "array", "maxItems": 1000, "items": {"type": "array", "maxItems": 30, "items": {"type": ["string", "number", "boolean", "null"]}}},
        "sources": {"type": "array", "minItems": 1, "maxItems": 100, "items": STRING}}, ("format", "title", "sources"))),
]


def handler(function, specification):
    def invoke(args, **kwargs):
        try:
            if not isinstance(args, dict):
                raise ValueError("Arguments must be an object")
            params = specification["parameters"]
            if set(args) - set(params["properties"]) or set(params["required"]) - set(args):
                raise ValueError("Unknown or missing tool arguments")
            if len(json.dumps(args, allow_nan=False)) > 400000:
                raise ValueError("Tool input exceeds size limit")
            result = function(args)
            return json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
            return json.dumps({"ok": False, "error": str(exc), "type": "validation_error"})
        except Exception:
            # Do not expose credentials, provider responses, or arbitrary exception objects.
            logging.getLogger(__name__).warning("Workbench operation failed: %s", specification["name"])
            return json.dumps({"ok": False, "error": "Operation failed; check dependencies, workspace permissions and operator logs", "type": "operation_error"})
    return invoke


HANDLERS = {spec["name"]: handler(fn, spec) for fn, spec in TOOLS}


def register(ctx):
    for _, spec in TOOLS:
        ctx.register_tool(name=spec["name"], toolset="engineering_workbench", schema=spec, handler=HANDLERS[spec["name"]])
    for path in sorted((Path(__file__).parent / "skills").glob("*/SKILL.md")):
        ctx.register_skill(path.parent.name, path)

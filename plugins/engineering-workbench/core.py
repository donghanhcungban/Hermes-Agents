"""Deterministic helpers. No model calls, subprocesses, network, or design sign-off."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

VERSION = "0.1.0"
DOMAINS = {
    "software": {
        "steps": ["Inspect repository and instructions", "Reproduce and add regression test", "Implement on an isolated branch/worktree", "Run tests, lint, build and security checks", "Review diff independently", "Open PR with evidence; do not infer merge/deploy"],
        "deliverables": ["patch", "test results", "review findings", "rollback instructions"],
        "approval": ["merge", "production deployment", "migration", "secret access"],
    },
    "office": {
        "steps": ["Identify source, audience, privacy and output format", "Extract and reconcile data; do not run macros", "Draft document or workbook", "Validate numbers and source references", "Render and visually inspect", "Deliver artifact; sending/sharing is a separate approval"],
        "deliverables": ["editable artifact", "source references", "validation evidence"],
        "approval": ["send email", "external sharing", "overwrite originals", "financial commitment"],
    },
    "mep": {
        "steps": ["Record project, jurisdiction, standards editions and design basis", "Check source revisions, units and missing inputs", "Run deterministic preliminary calculations", "Coordinate systems and quantities", "Independent qualified-engineer review", "Issue draft only until authorized approval"],
        "deliverables": ["design basis", "calculation record", "BOQ", "coordination issues", "review status"],
        "approval": ["live CAD/BIM write", "equipment selection", "construction issue", "life-safety approval"],
    },
}


def text(value, name, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name}: expected non-empty text up to {limit} characters")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError(f"{name}: control characters are not allowed")
    return value.strip()


def number(value, name, positive=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a JSON number")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{name}: out of range") from None
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"{name}: expected a finite {'positive' if positive else 'non-negative'} number")
    return result


def workspace():
    raw = os.environ.get("HERMES_WORKBENCH_ROOT", "")
    if not raw:
        raise ValueError("Set HERMES_WORKBENCH_ROOT to a dedicated authorized workspace")
    root = Path(raw).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("HERMES_WORKBENCH_ROOT must be an existing absolute directory")
    return root.resolve()


def inside(relative="."):
    root = workspace()
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Use a workspace-relative path")
    candidate = root / relative
    if ".." in Path(relative).parts:
        raise ValueError("Parent traversal is not allowed")
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlinks are not allowed in workspace paths")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Path is outside the authorized workspace")
    return resolved


def capabilities(args):
    return {
        "version": VERSION,
        "implemented": ["workflow planning (not execution)", "static repository inventory", "five SI preliminary calculations", "BOQ arithmetic", "office artifact export"],
        "optional_libraries": {m: importlib.util.find_spec(m) is not None for m in ("docx", "openpyxl", "pptx", "reportlab")},
        "workspace_configured": bool(os.environ.get("HERMES_WORKBENCH_ROOT")),
        "not_implemented": ["Revit/AutoCAD live adapter", "IFC clash detection", "email/calendar adapters", "autonomous merge/deploy", "regulatory compliance certification"],
        "host_connections": "not probed; an installed library is not a live integration",
    }


def plan(args):
    domain = args.get("domain")
    if domain not in DOMAINS:
        raise ValueError("domain must be software, office or mep")
    return {"status": "planned_not_executed", "domain": domain,
            "objective": text(args.get("objective"), "objective"),
            **DOMAINS[domain], "skill": f"engineering-workbench:{domain}",
            "parallelism": "Delegate only disjoint file ownership; one integrator. Use Hermes native delegation if available.",
            "evidence_rule": "Never label planned, mocked or skipped work as executed, passed, merged or deployed."}


def inspect_repo(args):
    root = inside(args.get("path", "."))
    if not root.is_dir():
        raise ValueError("Repository path must be a directory")
    manifests = ["pyproject.toml", "requirements.txt", "package.json", "Cargo.toml", "go.mod", "pom.xml", "Dockerfile"]
    def present(name, file_only=False):
        candidate = root
        for part in Path(name).parts:
            candidate = candidate / part
            if candidate.is_symlink():
                return False
        return candidate.is_file() if file_only else candidate.exists()
    files = [name for name in manifests if present(name, file_only=True)]
    signals = [name for name in ("AGENTS.md", "README.md", "tests", "test", ".github/workflows", "SECURITY.md") if present(name)]
    return {"path": str(root.relative_to(workspace())), "manifests": files, "signals": signals,
            "status": "static_inventory_only", "tests_executed": False,
            "next": "Use Hermes native file/terminal tools in a sandbox to inspect content, git status and actual test commands. Do not run untrusted install hooks automatically."}


CALCULATIONS = {
    "three_phase_current": (("power_W", "line_voltage_V", "power_factor"), "I = P / (sqrt(3) * V_LL * PF)", "A", "Balanced sinusoidal three-phase active electrical input power; excludes harmonics, inrush, cable sizing and protection coordination."),
    "sensible_airflow": (("heat_W", "density_kg_m3", "specific_heat_J_kgK", "delta_T_K"), "Qv = heat / (density * specific_heat * delta_T)", "m3/s", "Sensible heat only, constant properties; excludes latent load and ventilation/code minimums."),
    "water_flow": (("heat_W", "density_kg_m3", "specific_heat_J_kgK", "delta_T_K"), "Qv = heat / (density * specific_heat * delta_T)", "m3/s", "Single-phase steady heat transport; use fluid properties at design temperature; excludes pipe sizing."),
    "circular_velocity": (("flow_m3_s", "diameter_m"), "v = 4 * Qv / (pi * D^2)", "m/s", "Full circular cross-section using internal diameter; not a partially full drainage calculation."),
    "darcy_pressure_loss": (("darcy_factor", "length_m", "diameter_m", "density_kg_m3", "velocity_m_s"), "dp = f_D * (L/D) * density * v^2 / 2", "Pa", "Darcy, not Fanning friction factor; straight fully developed flow; excludes fittings, elevation and transient effects."),
}


def calculate(args):
    operation = args.get("operation")
    if operation not in CALCULATIONS:
        raise ValueError("Unsupported calculation")
    keys, formula, unit, limitation = CALCULATIONS[operation]
    values = args.get("inputs")
    if not isinstance(values, dict) or set(values) != set(keys):
        raise ValueError("inputs must contain exactly: " + ", ".join(keys))
    basis = text(args.get("design_basis"), "design_basis", 4000)
    v = {key: number(values[key], key) for key in keys}
    if operation == "three_phase_current":
        if v["power_factor"] > 1:
            raise ValueError("power_factor must be in (0, 1]")
        result = v["power_W"] / (math.sqrt(3) * v["line_voltage_V"] * v["power_factor"])
    elif operation in ("sensible_airflow", "water_flow"):
        result = v["heat_W"] / (v["density_kg_m3"] * v["specific_heat_J_kgK"] * v["delta_T_K"])
    elif operation == "circular_velocity":
        result = 4 * v["flow_m3_s"] / (math.pi * v["diameter_m"] ** 2)
    else:
        if v["darcy_factor"] > 1:
            raise ValueError("darcy_factor outside supported range (0, 1]")
        result = v["darcy_factor"] * v["length_m"] / v["diameter_m"] * v["density_kg_m3"] * v["velocity_m_s"] ** 2 / 2
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Calculation overflow/underflow; review the inputs")
    return {"operation": operation, "inputs": values, "formula": formula, "value": result,
            "unit": unit, "design_basis": basis, "status": "preliminary_not_for_construction",
            "review_required": True, "limitations": limitation, "standards_verified": False}


def amount(value, name):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{name}: expected decimal text or number")
    raw = str(value)
    if len(raw) > 40:
        raise ValueError(f"{name}: number too long")
    try:
        out = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"{name}: invalid decimal") from None
    if not out.is_finite() or out < 0 or out > Decimal("1e15") or not -9 <= out.as_tuple().exponent <= 15:
        raise ValueError(f"{name}: outside supported non-negative decimal range")
    return out


def boq(args):
    rows = args.get("items")
    currency = text(args.get("currency"), "currency", 3)
    if not currency.isascii() or not currency.isalpha() or len(currency) != 3 or currency != currency.upper():
        raise ValueError("currency must be a three-letter uppercase code; no conversion is performed")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError("items must contain 1..1000 rows")
    seen, result, total = set(), [], Decimal(0)
    with localcontext() as context:
        context.prec = 64
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "description", "unit", "quantity", "unit_price", "source"}:
                raise ValueError("Each BOQ row needs exactly id, description, unit, quantity, unit_price, source")
            key = text(row["id"], "id", 100)
            if key in seen:
                raise ValueError("Duplicate BOQ id: " + key)
            seen.add(key)
            quantity, price = amount(row["quantity"], "quantity"), amount(row["unit_price"], "unit_price")
            cost = quantity * price
            total += cost
            result.append({"id": key, "description": text(row["description"], "description"),
                           "unit": text(row["unit"], "unit", 40), "quantity": str(quantity),
                           "unit_price": str(price), "line_total": str(cost), "source": text(row["source"], "source")})
    return {"items": result, "subtotal": str(total), "currency": currency,
            "status": "arithmetic_checked_only", "excludes": ["tax", "wastage", "escalation", "scope completeness", "quantity/unit/source verification"],
            "review_required": True}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

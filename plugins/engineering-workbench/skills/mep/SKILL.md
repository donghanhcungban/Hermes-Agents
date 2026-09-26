---
name: mep
description: Preliminary MEP calculations, quantity reconciliation and review-first CAD/BIM planning.
---

# MEP specialist on Hermes

Call `engineering_status` and `engineering_plan(domain="mep", objective=...)`.
Do not equate language-model knowledge with a verified engineering design.

## Design basis first

Record project/site, jurisdiction, building use, design stage, drawing/model
revision, client requirements, applicable standard names/editions and authoritative
sources. Identify missing dimensions, loads, diversity, climate and equipment data.
Never fabricate a code clause or assume a standard edition is current. Obtain
licensed standards through authorized sources; no copyrighted standard is bundled.

Use SI quantities with explicit field names. Convert kW to W and mm to m before
calling tools and show the conversion. `engineering_mep_calculate` requires a
non-empty `design_basis` and these exact operation inputs:

| Operation | Required input fields | Output | Scope |
|---|---|---|---|
| three_phase_current | power_W, line_voltage_V, power_factor | A | Balanced sinusoidal electrical active input power |
| sensible_airflow | heat_W, density_kg_m3, specific_heat_J_kgK, delta_T_K | m3/s | Sensible heat transport only |
| water_flow | heat_W, density_kg_m3, specific_heat_J_kgK, delta_T_K | m3/s | Single-phase steady heat transport |
| circular_velocity | flow_m3_s, diameter_m | m/s | Full pipe/duct, internal diameter |
| darcy_pressure_loss | darcy_factor, length_m, diameter_m, density_kg_m3, velocity_m_s | Pa | Straight-run loss, Darcy not Fanning factor |

All inputs must be finite and strictly positive. Fluid density, specific heat and
friction factor are user/project inputs, not hidden defaults. Electrical input
power is not motor shaft output: handle verified efficiency separately. Darcy
loss excludes fittings, elevation and transients. Airflow excludes latent loads
and minimum ventilation requirements. None of these functions chooses breakers,
cables, pumps, fans, fire-protection equipment or certifies code compliance.

Check units, order of magnitude and at least one independently worked case.
Retain tool inputs, formula, output and limitations. Every calculation returns
`preliminary_not_for_construction`, `standards_verified: false` and a review flag.
A second LLM is not a substitute for independent qualified-engineer verification.

## Quantities and artifacts

Use `engineering_boq` only to check decimal arithmetic and duplicate item IDs.
Every line requires id, description, unit, quantity, unit_price and source. Prefer
quantity/price decimal strings. Keep source drawing/model revision and measurement
rules in the source reference. Reconcile units/scope separately. Export schedules,
BOQ and calculation reports through `engineering_export`, keeping draft status.

## CAD/BIM boundary

This release has **no live Revit/AutoCAD adapter or IFC clash detector**. Existing
Autodesk guidance in the repository is not an installed or connected add-in.
Before any future adapter is used, verify exact host product, version, update,
SDK/.NET runtime and license, then probe health and a real read-only query.
Revit 2025/2026 originally use .NET 8 rather than a universal net48 target;
some updates transition to .NET 10. Every host/update needs its own current
official compatibility check, including supported SDK and dependency versions.

Use Revit ExternalEvent/valid API context and transactions, or the host-supported
AutoCAD document lock/command context. Future writes must bind an authenticated,
expiring, single-use approval to the exact document revision, preview and operations;
reject stale previews. Back up originals and test on a disposable model. A JSON
field saying `approved: true` is not authorization. Life-safety calculations,
equipment selection and issued-for-construction packages require responsible
qualified review and explicit project authorization.

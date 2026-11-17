# Editable design sources

`source/edit_table_up/` is the authoritative current assembly STEP in mm; `source/print/` contains the manufacturing orientations and STL meshes. Source STEP display names are English and stable component IDs remain unchanged. The owner-edited `slider_upper_jaw` geometry is authoritative and may be changed only on owner instruction.

The v3.4-alu10 revision relabels source STEP files in place, revises `column_lower` and the four base bolts, and adds the aluminum plate, eight wire thread inserts and twelve top washers. The regular build copies the source files into the delivery; there is one active set of part STEP files. The machining plate has a separately documented translated datum, rather than different geometry.

`scripts/derive_column_lower_b.py` derives option B once from the v3.2 STEP in the recorded Git baseline, or from an explicit input path. It extends the flange 6 mm downward and cuts four diameter10.4 flat counterbores 6 mm deep. The revised flange is Z10.75..24.75. Print orientation is flange down, pure translation (45,55,-10.75), re-zeroed to the bed. The build does not derive it again.

`scripts/update_alu10_sources.py --baseline-ref COMMIT` reproduces the complete source revision and updates provenance. Use the baseline commit recorded in `source/revision_validation.json`, not a later revision's HEAD. The record includes name-token-only byte proofs and measured solid count, volume, bounds and face count against v3.2 for every protected STEP. It explicitly lists the 34 retained upper bodies and owner-edited slider. The five other print STLs are byte-identical. All six print transforms are registered by actual geometry; obsolete manifest transforms are preserved in the revision record for review.

`source/manifest.json` describes the active v3.4-alu10 design. Obsolete printed-base, 8 mm aluminum-concept and heat-set-base parameters are marked under `parameters.historical_v3_2`, rather than silently discarded. `design/PROVENANCE.json` contains current hashes and keeps the complete v3.2 provenance under `previous`.

Tabletop Z0, nominal compressed anti-slip offset0.75 without a pad CAD body, aluminum plate Z0.75..10.75, and flange seat Z10.75 define the assembly. All geometry above the flange and the controller table-from-pad transform stay unchanged. Aluminum alloy, temper and finish are left to the buyer/supplier.

Controller reference geometry retains BatonyRobson's CC BY 4.0; original fixture work remains MIT by 5o1. STEP snapshots do not claim original parametric feature history. Historical validation files remain history and do not certify the current physical joint.

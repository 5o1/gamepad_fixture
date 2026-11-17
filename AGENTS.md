# Scope

Maintain this independent gamepad fixture project. Source STEP inputs live in
`design/source`; generated delivery packages belong in ignored `build/` and
GitHub Releases. Keep public README links pointed at Release downloads.

Current design uses a 10 mm aluminum base with wire thread inserts, a revised
`column_lower` (option B, derived by script into the source), six PETG prints, and the accepted
upper assembly. Part display names are English with original IDs kept. The
panels beside the inner column are "gusset plates" (斜板), never "ears".
The owner-edited slider geometry is authoritative and may be changed only on owner instruction.
The build copies the English source STEP files; it does not derive the column again.

Use millimetres for CAD. Read actual exported solids when checking dimensions.
Distinguish nominal geometry/static calculations from physical strength tests.
Controller reference CAD and textured renders retain BatonyRobson's CC BY4.0;
original fixture work is MIT by5o1. Preserve these notices in release bundles.

Use the approved upstream Blender/Cycles scene for controller appearance. Never
replace its PBR materials with a plain preview while calling it the approved
render. Inspect rendered images before publication.

Do not add parent-workspace paths, remote profiles, credentials or private logs.

# One fixture palette

`config/colors.json` defines the six printed-part colors and their unchanged per-part assignments. The printing color CSV/PDF, visual URDF and rendering scripts consume the same palette. HEX/RGB values are sRGB display references; confirm actual PETG supplier swatches before production.

The current English delivery uses `01_printed/print_colors.csv` and `.pdf`. Production STL files are in mm. The column sleeve is described as having **clevis lugs**; panels beside the inner column are **gusset plates**.

`05_simulation_and_rendering/URDF/fixture.urdf` and `meshes/` form a fixed visual assembly with 60 part links, one root and 60 fixed joints. Meshes and translations are in meters; do not print these meshes. RGBA uses normalized sRGB from the palette. No collision geometry, inertias, masses or articulated adjustment behavior is supplied.

Purchased parts are gray in the overview and URDF. The mounted and base presentation views use the opaque aluminum material in `presentation_materials.aluminum`: color #bfc5cb, roughness0.32, metallic0.8, opacity1. This is a presentation default, not a production alloy, temper or finish specification. The approved controller PBR materials, UV maps and Boiler Room illumination remain authoritative. Lighting and color management can change visible colors; palette numbers govern.

No aluminum images have been rendered for this revision. The repository's existing images and recorded rendering checks describe the previous acrylic design. Rebuild meshes and references before a separate rendering task; inspect the resulting images before publication.

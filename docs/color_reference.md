# One fixture palette

`config/colors.json` is the source of truth for all six printed-part colors.
Change that file, then rebuild the delivery and render images using the same file.

## Printing centre

`01_打印件/print_colors.csv` lists the STL filename, quantity, PETG, English color
name and sRGB HEX/RGB. `print_colors.pdf` and `.png` provide six labeled swatches.
The existing printing list also includes the color name and HEX reference.

HEX is a display reference, not a filament SKU or a calibrated physical target.
The print centre should select an available PETG swatch and confirm its supplier
color code before production. STL geometry does not carry this order information.

## URDF rendering reference

`05_simulation_and_rendering/URDF/fixture.urdf` and `meshes/` form a self-contained
fixed visual assembly: 56 part links plus a root, and 56 fixed joints. Meshes
and link translations are in metres. Its material RGBA is normalized sRGB from
the same palette. Keep the mesh directory with the URDF. A ROS 2 package-URI
variant and package metadata are included as `fixture_ros.urdf`.

This reference freezes the current assembly. It supplies no collision geometry,
inertias, masses or articulated height/tilt behavior. Do not treat it as a
validated dynamics model or send its metre-scale meshes for printing.

## Presentation rendering

The overview and mounted image use identical printed-part base colors and
roughness. Purchased parts use gray in the overview/URDF, while the mounted view
retains realistic metal and clear-acrylic surfaces. The controller retains the
approved upstream PBR materials, UV maps and Boiler Room illumination.
Different renderer lights and transfer functions can change apparent color;
the palette numbers are authoritative. Hole highlight colors are annotations,
not material/filament requests.

URDF material and mesh interpretation follows the ROS URDF visual model and
[the yourdfpy loader API](https://yourdfpy.readthedocs.io/en/latest/api/yourdfpy.html).

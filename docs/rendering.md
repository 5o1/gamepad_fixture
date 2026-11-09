# Reproducible rendering reference

The overview and mounted image read the same six printed-part base colors from
[`config/colors.json`](../config/colors.json). The print order, swatch sheet and
URDF are generated from that same file; the image legend also reads it.

## Controller appearance

The mounted view opens the approved Blender 4.5.9/Cycles scene from
[xbox_gamepad_physics](https://github.com/5o1/xbox_gamepad_physics). It retains the
16 evaluated controller meshes, original PBR material/UV/image data, Boiler Room
HDR illumination at strength 1.0 and Standard/None/Exposure 0/Gamma 1 color
management. Fixture CAD, a floor and a presentation camera are added. The
controller is not replaced by a flat-color STL preview.

Printed parts use the shared palette in both views. Purchased parts are uniform
gray in the overview and URDF. In the mounted view, steel and clear acrylic keep
their presentation surface properties, defined separately in the same config.
Hole colors are semitransparent annotations, not requests to dye the acrylic.

## Render the reference

Download and extract `render_inputs_v3.3.0.zip` from the Release. It includes the
approved packed scene, fixture mesh arrays, part placement, palette and scripts.

```sh
/path/to/blender --background INPUTS/approved.blend --threads 8 \
  --python-exit-code 1 --python INPUTS/render_scene.py \
  -- INPUTS 3 --palette INPUTS/colors.json
python INPUTS/compose_renders.py 3 INPUTS --palette INPUTS/colors.json
```

To update only the mounted view, append `--only mounted` to the Blender command.
For a changed project palette, pass the repository's `config/colors.json` to
both commands, and regenerate the printing/URDF references with
`python scripts/build.py`. Re-render the images after changing colors; rebuilding
CAD alone does not run Blender.

The recorded reference uses CPU, 64 samples and denoising. The input scene and
controller references retain CC BY 4.0; the packed HDR is CC0. See
[notices](../THIRD_PARTY_NOTICES.md). The technical acrylic view uses illustrative
transparency and disjoint blue/orange hole volumes, not an optical or stress
simulation.

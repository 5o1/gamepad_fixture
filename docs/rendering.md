# Rendering

The controller-mounted view opens the approved Blender4.5.9/Cycles scene from [xbox_gamepad_physics](https://github.com/5o1/xbox_gamepad_physics), retaining its sixteen evaluated controller meshes, original PBR material/UV/image data, Boiler Room HDR illumination at strength1.0, and Standard/None/Exposure0/Gamma1 color management. Fixture CAD, presentation floor and camera are added. Rendering uses CPU, not a reconstructed flat-colored controller.

The technical overview assigns one color to each of six printed parts and a unified gray to purchased parts. The acrylic manufacturing perspective uses illustrative transparency and blue/orange disjoint hole volumes; it is not an optical simulation or a stress plot.

Three image-review rounds are recorded for the published images. Render inputs are provided with the Release, including the approved scene and scripts, under the notices included in the archive.

```sh
/path/to/blender --background approved.blend --threads 8 \
  --python-exit-code 1 --python render_blender.py -- /path/to/render-inputs 3
```

For the repository compositor, use `python scripts/compose_renders.py 3 /path/to/render-inputs` after rendering.

The original approved scene and controller references remain CC BY4.0; the packed HDR is CC0. See [notices](../THIRD_PARTY_NOTICES.md).

The v3.2.1 image update redraws titles, the part legend and hole descriptions in English. The reviewed Cycles render pixels, CAD geometry, controller materials and lighting are unchanged.

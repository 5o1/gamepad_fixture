# Reproducible rendering reference

The build generates revised fixture meshes, part placement, English legends and the shared palette under `build/alu10/render_inputs/`, and packages them as `render_inputs_v3.4.0.zip`. It does not run Blender or reuse historical acrylic images as aluminum evidence.

The approved upstream Blender 4.5.9/Cycles packed scene is not stored in this repository. Supply its unchanged `approved.blend` from the existing published rendering inputs. Its recorded SHA-256 is `1ff81e02d4d41dc22e59f14b181d2119851e913c3c955628f74f3d2a0aaa210b`. The prior scene record remains history.

The mounted view evaluates the 16 original controller meshes at frame0, retains their PBR/UV/image data and uses the unchanged source table-from-pad transform with the 153 mm width-derived scale. Keep Boiler Room HDR strength1.0, Standard/None/Exposure0/Gamma1 color management, CPU, 64 samples and denoising for final quality. Only fixture geometry, presentation camera and floor are added.

The six PETG colors and assignments are unchanged. Purchased parts are gray in the overview/URDF. The mounted and base views use an opaque aluminum presentation material from `config/colors.json`; aluminum alloy, temper and finish remain unspecified. Geometry and IDs come from the current build. No transparent acrylic replacement is used.

From the extracted revised inputs with the approved scene supplied:

```sh
/path/to/blender --background approved.blend --threads 32 \
  --python-exit-code 1 --python render_scene.py \
  -- . 3 --palette colors.json
python compose_renders.py 3 . --palette colors.json
```

The script fixes rendering at 32 CPU threads (increased from eight), verifies Blender 4.5.9 and the approved scene hash, checks for 16 controller parts, and asserts that visible geometry fits inside the camera frame. Round 3 uses 2000 × 2000 pixels for assembly views and 2000 × 1440 for the base, with 64 samples and denoising. Each view's camera, projection bounds and render time are written to `round3/record.json`.

The base view adds eight solid, opaque Ø10 mm visual discs using the existing palette entries: blue for the four active column mounts at Y −14 / −46 mm, and orange for the four spare rear-shift positions at Y −78 / −110 mm. These are presentation annotations within 0.08 mm above the plate's top face, not paint, hole diameters or manufactured geometry. All eight positions have the same M5×0.8, 1.5D tangless wire thread insert specification. The composed legend identifies position roles, provides the common insert specification, and states that the drawings and STEP govern. The assembly views hide these markers.

Append `--only mounted` or `--only base` to render one view. Composition uses DejaVu Sans and accepts the same `--only` option; without it, all three views are composed. For a base-only revision, append `--only base` to both commands to preserve accepted assembly images. If that font is unavailable on the rendering machine, copy the raw PNGs locally and compose with the same command and palette. For an existing input ZIP, copy the current `scripts/render_scene.py`, `scripts/compose_renders.py` and `config/colors.json` into its extracted directory before rendering; the CAD payload and meshes do not change. Inspect every composed image before publication.

The v3.4-alu10 README images were rendered and visually inspected. See [the new rendering record](validation/alu10-render-record.json) for settings, camera bounds, timing and raw/composed PNG hashes. The thick flange and recessed heads are visible; the recessed three-washer stacks cannot be counted reliably from these assembly views. Exported-solid unit tests separately verify the four counterbores and three washers beneath each bolt head. This is CAD and rendering evidence, not a physical strength test.

Controller references and packed scene retain BatonyRobson's CC BY 4.0; Boiler Room by Poly Haven is CC0. Original fixture work is MIT by 5o1; preserve the third-party notices in redistributed render inputs.

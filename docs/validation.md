# Validation scope

The current v3.4-alu10 build writes its evidence to `build/alu10/validation/gates.json`, `final_review.json` and `IMPLEMENTATION_REPORT.md`. It validates nominal exported CAD geometry, document contents and package consistency. It does not certify physical strength or provide an approved M5 assembly torque.

The six critical gates cover one valid derived column with analytic volume and ten unchanged upper sections; 34 geometry-identical source STEP bodies with name-only diffs against the recorded Git baseline and five byte-identical print STLs; geometrically registered orientations for all six prints; no penetrating intersections in the revised base joint; unchanged controller frame and a measured flange/plate contact; and a 9 mm plate negative control that must fail seating. The owner-edited upper jaw slider geometry and M6 teardrop holes remain unchanged. The column revision lives in source and is not derived again by the build. The assembly has 60 solids: six printed and 54 purchased bodies. Controller surfaces are additional references and are not counted as solids.

The drawing and STEP plate use different documented origins: machining X0..240/Y0..130/Z0..10, assembly X-120..120/Y-130..0/Z0.75..10.75. STEP holes use nominal installed insert envelopes diameter6.04; production requires drilling5.2 then M5x0.8 STI tapping through. Eight 7.5 mm tangless inserts are recessed0.4 from the top. Supplier confirmation of STI tolerances, gauges and installation is required. Aluminum alloy, temper and finish are left to the buyer/supplier.

`scripts/bolt_strength.py` screens nominal static axial/shear stress in steel bolts at the current flange seat Z10.75, using assumed loads, preload and amplification. It does not certify insert pullout, aluminum thread capacity, PETG preload/creep, fatigue, clamps or the overall joint. No physical printing, machining, strength, dimensional repeatability, torque or robot/world calibration test has been performed for this revision.

The package scanner decodes STEP Unicode escapes, scans text and filenames for CJK characters, and extracts PDF text. Source STEP files have English names; the same files are copied to the build and package. Name-only changes are proven by comparing all non-name bytes and measuring solid count, volume, bounds and face count against the recorded v3.2 Git version. The revised column and four base bolts are explicit geometry changes. Six print colors are unchanged. URDF and render mesh bounds are checked against CAD; URDF is a fixed visual model without collision or inertia parameters. No Blender run or new image acceptance is included.

Files under `docs/validation/` remain immutable historical evidence for earlier designs and are not an aluminum10 pass record. Existing media show the earlier acrylic design. The prior accepted local spring-contact limitations remain unresolved; changing the base does not certify the upper assembly.

```sh
python scripts/build.py
python scripts/validate.py --out build/alu10
python -m unittest discover -s tests
```

The measured minimum distance from each bolt axis to the gusset plates is 6.00 mm, so the Ø10.4 counterbore leaves 0.8 mm.

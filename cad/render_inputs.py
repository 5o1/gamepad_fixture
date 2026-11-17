"""Prepare revised fixture arrays for the approved scene; never run Blender."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import trimesh


def make(out, source):
    out, source = Path(out), Path(source)
    m=json.loads((out/'manifest.json').read_text())
    folder=out/'render_inputs';folder.mkdir(exist_ok=True)
    arrays={}
    for row in json.loads((out/'simulation_reference/parts.json').read_text()):
        n=row['part_id'];mesh=trimesh.load(out/'simulation_reference'/row['stl'],force='mesh',process=False)
        arrays[n+'_v']=mesh.vertices+np.array(row['origin_m'])
        arrays[n+'_f']=mesh.faces
    np.savez_compressed(folder/'meshes.npz',**arrays)
    width=json.loads((source/'manifest.json').read_text())['parameters']['measured']['width']
    payload=dict(parts=[dict(name=r['name'],printed=r['is_printed']) for r in m['parts']],
        board=m['board'],table_from_pad_mm=m['table_from_pad_mm'],controller_width_mm=width,
        design_revision=m['design_revision'])
    (folder/'payload.json').write_text(json.dumps(payload,indent=2)+'\n')
    repo=Path(__file__).resolve().parents[1]
    for n in ('render_scene.py','compose_renders.py'):shutil.copyfile(repo/'scripts'/n,folder/n)
    shutil.copyfile(repo/'config/colors.json',folder/'colors.json')
    for n in ('LICENSE','THIRD_PARTY_NOTICES.md'):shutil.copyfile(repo/n,folder/n)
    approved=json.loads((repo/'docs/validation/palette-render-record.json').read_text())['scene_sha256']
    (folder/'README.md').write_text(f'''# Rendering inputs for v3.4-alu10

This bundle contains the revised fixture meshes, placement, palette and scripts. No Blender render has been run for this revision. Old acrylic images are not included.

Supply the unchanged approved upstream `approved.blend` from the existing rendering Release bundle in this directory. Its recorded SHA-256 is `{approved}`. The packed scene is not present in this repository and is not included here. Retain its controller PBR materials, UVs, maps and Boiler Room environment.

The script evaluates frame 0 and applies the source table-from-pad transform and width-derived 153 mm scale. It leaves controller materials unchanged. The base uses an opaque aluminum presentation material; this does not specify a production alloy, temper or finish.

```sh
/path/to/blender --background approved.blend --threads 8 --python-exit-code 1 --python render_scene.py -- . 3 --palette colors.json
python compose_renders.py 3 . --palette colors.json
```

Inspect every rendered image before publication. The scripts have been syntax checked; scene execution and image acceptance remain for the separate rendering task.
''')
    return folder

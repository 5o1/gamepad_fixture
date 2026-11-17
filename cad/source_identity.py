"""Name-only STEP edits and reproducible geometry comparison against Git history."""
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from build123d import import_step
from OCP.gp import gp_Trsf
from build123d import Location
from geometry import bounds
from column_lower_b import require, volume
from part_names import label

TOKENS = re.compile(rb"'(?:''|[^'])*'")
ALLOWED_NAME_ENTITIES = {'FILE_NAME','PRODUCT','NEXT_ASSEMBLY_USAGE_OCCURRENCE'}


def git_bytes(root, ref, relative):
    return subprocess.check_output(['git','show',f'{ref}:{relative}'],cwd=root)


def decode_token(token):
    text=token[1:-1].decode('utf-8').replace("''", "'")
    text=re.sub(r'[\r\n]+[ \t]*','',text)
    return re.sub(r'\\X2\\([0-9A-Fa-f]+)\\X0\\',lambda m:bytes.fromhex(m.group(1)).decode('utf-16-be'),text)


def english_labels(data):
    def replace(match):
        text=decode_token(match.group())
        identifier=re.search(r'\[([A-Za-z0-9_+\-]+)\]',text)
        if not identifier:return match.group()
        return ("'"+label(identifier.group(1)).replace("'","''")+"'").encode('ascii')
    return TOKENS.sub(replace,data)


def geometry(shape):
    return dict(solid_count=len(shape.solids()),volume_mm3=shape.volume,
                bounds_mm=bounds(shape),face_count=len(shape.faces()))


def read_bytes(data):
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'input.step';path.write_bytes(data)
        return import_step(path)


def prove_name_only(before, after):
    a,b=list(TOKENS.finditer(before)),list(TOKENS.finditer(after))
    require(len(a)==len(b) and TOKENS.sub(b"'<string>'",before)==TOKENS.sub(b"'<string>'",after),
            'C2: non-string STEP bytes changed')
    changes=[]
    for old,new in zip(a,b):
        if old.group()==new.group():continue
        previous=before[before.rfind(b';',0,old.start())+1:old.start()]
        entity=re.search(rb'(?:#\d+\s*=\s*)?([A-Z][A-Z_0-9]+)\s*\(',previous)
        kind=entity.group(1).decode() if entity else 'UNKNOWN'
        require(kind in ALLOWED_NAME_ENTITIES and re.search(r'\[[A-Za-z0-9_+\-]+\]',decode_token(old.group())),
                f'C2: changed token is not a recognized STEP name: {kind}')
        changes.append(dict(entity=kind,old_token_sha256=hashlib.sha256(old.group()).hexdigest(),new_name=decode_token(new.group())))
    return changes


def prove_geometry(before_shape, after_shape, name):
    a,b=geometry(before_shape),geometry(after_shape)
    dv=abs(a['volume_mm3']-b['volume_mm3'])
    db=float(np.max(abs(np.array(a['bounds_mm'])-np.array(b['bounds_mm']))))
    require(a['solid_count']==b['solid_count'] and a['face_count']==b['face_count'] and dv<=1e-6 and db<=1e-6,
            f'C2: geometry changed: {name}; volume error={dv}, bounds error={db}')
    return dict(baseline=a,current=b,volume_error_mm3=dv,bounds_error_mm=db)


def location(matrix):
    tr=gp_Trsf();tr.SetValues(*np.array(matrix)[:3].flatten().tolist())
    return Location(tr)


def location_matrix(loc):
    transform=loc.wrapped.Transformation()
    matrix=np.eye(4)
    for i in range(3):
        for j in range(4):matrix[i,j]=transform.Value(i+1,j+1)
    return matrix


def feature_error(a,b):
    from build123d import CenterOf
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial import cKDTree
    require(len(a.faces())==len(b.faces()) and len(a.edges())==len(b.edges()), 'C3: topology counts differ')
    def faces(shape):
        return np.array([[f.area,*f.center(CenterOf.MASS),*np.array(bounds(f)).flatten()] for f in shape.faces()])
    x,y=faces(a),faces(b)
    cost=abs(x[:,None]-y[None,:]).max(2);i,j=linear_sum_assignment(cost)
    face_error=float(cost[i,j].max())
    def points(shape):
        return np.array([list(e.position_at(t)) for e in shape.edges() for t in (0,.25,.5,.75,1)])
    x,y=points(a),points(b)
    edge_error=float(max(cKDTree(x).query(y)[0].max(),cKDTree(y).query(x)[0].max()))
    return face_error,edge_error,len(x)


def registration(table, printable, rotations, name):
    # Native placements are a candidate only: actual geometry independently accepts them.
    native=printable.location*table.location.inverse()
    candidates=[(location_matrix(native),native)]
    for rotation in rotations:
        matrix=np.eye(4);matrix[:3,:3]=rotation
        candidate=table.moved(location(matrix))
        matrix[:3,3]=np.array(bounds(printable))[0]-np.array(bounds(candidate))[0]
        candidates.append((matrix,location(matrix)))
    for matrix,pose in candidates:
        candidate=table.moved(pose)
        error=float(np.max(abs(np.array(bounds(candidate))-np.array(bounds(printable)))))
        dv=abs(candidate.volume-printable.volume)
        if error>1e-4 or dv>1e-6:continue
        if len(candidate.faces())!=len(printable.faces()) or len(candidate.edges())!=len(printable.edges()):continue
        face_error,edge_error,samples=feature_error(candidate,printable)
        if face_error<=1e-6 and edge_error<=1e-6:
            common=volume(candidate & printable)
            return dict(matrix=matrix.tolist(),bounds_error_mm=error,volume_error_mm3=dv,
                face_metric_error=face_error,edge_sample_error_mm=edge_error,edge_samples=samples,
                boolean_common_volume_mm3=common,boolean_diagnostic_reliable=abs(common-printable.volume)<=1e-3,
                method='Native-location candidate verified by bounds, volume, face counts/areas/centroids/bounds and bidirectional five-point-per-edge samples')
    require(False,f'C3: cannot geometrically register {name}')

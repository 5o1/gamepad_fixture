"""Auditable static bolt-body screening, not joint qualification or FEA.
Run python scripts/bolt_strength.py. Does not modify source CAD.
"""
import hashlib,itertools,json,math
from pathlib import Path
import numpy as np
import trimesh
from build123d import import_step

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'design/source'
OUT=ROOT/'build/bolt_strength';OUT.mkdir(parents=True,exist_ok=True)
m=json.loads((SRC/'manifest.json').read_text())
T=np.asarray(m['v3_2_table_from_pad'])
xy=[];hashes={}
for i in range(4):
 p=SRC/'edit_table_up'/f'hardware_base_M5_{i}.step'
 s=import_step(p).solids()[0]
 b=s.bounding_box();c=np.asarray([(b.min.X+b.max.X)/2,(b.min.Y+b.max.Y)/2,(b.min.Z+b.max.Z)/2,1.])
 xy.append(c[:2]);hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
xy=np.asarray(xy);centre=xy.mean(0);offset=xy-centre
sx=float((offset[:,0]**2).sum());sy=float((offset[:,1]**2).sum());J=sx+sy
p=SRC/'reference/controller_table_up.stl';controller=trimesh.load(p,force='mesh',process=False)
hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
# Global geometry checks are identity checks of measured inputs, not load tests.
assert np.allclose(np.sort(np.unique(offset[:,0])),[-35,35])
assert np.allclose(np.sort(np.unique(offset[:,1])),[-16,16])
lo,hi=controller.bounds
base_top=16.75
rbox=np.array([lo-[*centre,base_top],hi-[*centre,base_top]])
rbox[:,2]+=30 # Highest height, +30mm, explicit common worst-case envelope.
corners=np.array(list(itertools.product(*zip(*rbox))))
At=14.2;Ashear=math.pi*4.0**2/4
proof_N=8230.;ultimate_N=11350.;proof_MPa=proof_N/At
cases=[]
# Same 16mm thickness for all three options isolates material choice. The 8mm
# aluminum option only translates the assembled parts; lever arm over the
# flange remains unchanged. It does NOT lower the above-flange force lever.
variants=[('printed_PETG_16',16,'existing heat-set joint'),
          ('cast_PMMA_16',16,'concept: through-bolt/nut; fastener length and counterbore not yet designed'),
          ('aluminum_6061_8',8,'concept: tapped blind holes; old M5x12 has nominal4mm entry, not qualified')]
for name,t,note in variants:
 # All upper bodies translate t-16 in table coordinates. Both force point and
 # interface translate equally, so rbox is identical: no artificial advantage.
 normal_coefficients=[]
 shear_coefficients=[]
 for r in corners:
  for x,y in offset:
   c=np.array([-r[2]*x/sx,-r[2]*y/sy,.25+r[1]*y/sy+r[0]*x/sx])
   normal_coefficients.append(dict(value=float(np.linalg.norm(c)),r=r.tolist(),bolt=[float(x),float(y)],direction=(c/np.linalg.norm(c)).tolist()))
   # Direct shear + elastic bolt-group torsional shear; no friction credited.
   Mz=np.array([-r[1],r[0],0.])
   A=np.array([[.25,0,0],[0,.25,0]])+np.outer([-y/J,x/J],Mz)
   shear_coefficients.append(float(np.linalg.svd(A,compute_uv=False)[0]))
 cn=max(normal_coefficients,key=lambda v:v['value']);cs=max(shear_coefficients)
 for F in (20.,50.,100.):
  for preload in (0.,1000.,3000.):
   for amplification in (1.,3.,6.):
    # 3x and 6x are sensitivity scenarios, not verified physical upper bounds.
    ext=cn['value']*F*amplification
    shear=cs*F*(2 if amplification==6 else 1)
    tension=preload+ext
    sigma=tension/At;tau=shear/Ashear;vm=math.sqrt(sigma*sigma+3*tau*tau)
    cases.append(dict(variant=name,force_N=F,assumed_preload_each_N=preload,
      assumed_tension_amplification=amplification,external_tension_each_N=ext,
      shear_each_N=shear,total_tension_each_N=tension,equivalent_stress_MPa=vm,
      proof_stress_ratio=proof_MPa/vm,below_static_proof_comparison=vm<proof_MPa))

# Bounded coefficient validation: all corners, all bolts, representative unit
# loads must reproduce moment/force equilibrium in the signed elastic group.
equilibrium_error=0.
for r in corners:
 for F in np.eye(3):
  moment=np.cross(r,F)
  n=F[2]/4+moment[0]*offset[:,1]/sy-moment[1]*offset[:,0]/sx
  v=np.tile(F[:2]/4,(4,1))+np.c_[-offset[:,1],offset[:,0]]*moment[2]/J
  actual=np.array([n.sum(),(offset[:,1]*n).sum(),-(offset[:,0]*n).sum(),v[:,0].sum(),v[:,1].sum(),(offset[:,0]*v[:,1]-offset[:,1]*v[:,0]).sum()])
  expected=np.r_[F[2],moment[:2],F[:2],moment[2]]
  equilibrium_error=max(equilibrium_error,float(abs(actual-expected).max()))
assert equilibrium_error<1e-8
result=dict(executed=True,method='Python closed-form elastic bolt group; nominal axial and shear stress; no FEA or physical loading',
 source_sha256=hashes,bolt_centres_table_mm=xy.tolist(),bolt_group_centre_table_mm=centre.tolist(),
 spacing_mm=dict(left_right=70,front_back=32),relative_force_box_highest_mm=rbox.tolist(),
 nominal_thread='M5x0.8',assumed_property_class='8.8; NOT previously specified or verified as purchased',
 stress_area_mm2=At,assumed_shear_core_diameter_mm=4.,shear_area_mm2=Ashear,
 proof_load_N=proof_N,minimum_tensile_fracture_load_N=ultimate_N,
 maximum_elastic_tension_per_force=cn,maximum_elastic_shear_per_force=cs,
 variants=[dict(name=n,thickness_mm=t,note=note) for n,t,note in variants],
 force_cases_are_assumptions=True,assumed_preload_is_not_tightening_instruction=True,
 results=cases,equilibrium_residual_max_N_or_Nmm=equilibrium_error,
 all_three_variants_identical_bolt_body_results=True,
 limitations=['Single quasi-static force within axis-aligned controller envelope, highest height, default45deg tilt; not arbitrary tilt or pure external applied torque.',
 'Unknown operating forces and self-weight resultants must be added;20/50/100N are screening scenarios, not measured operating limits.',
 'Elastic distribution assumes intact seated flange;1/3/6 multipliers are sensitivity inputs, not a certified bound on prying or failed supports.',
 'Preloads0/1000/3000N are assumptions. No approved assembly torque, clamp force, residual tightening torsion, transverse bolt bending, fatigue, impact, defects or corrosion are modelled.',
 'No pass decision for female threads, heat-set inserts, acrylic counterbores, printed flange, base plate or desk clamps. No overall joint certification.'],
 sources=[dict(title='Bossard: metric screw mechanical properties, ISO898-1',url='https://assets.eu.ctfassets.net/0vp0u5uh75zd/1VPwGxSRcAQdDRArMtTqeY/8fe01cf6ef692e134b45f895fb69fe97/012_016_Screws_property_class46_Fastening_EN_01_2025.pdf',used='M5 stress area14.2mm2; class8.8 proof8230N, minimum tensile11350N')])
(OUT/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
for F in (20.,50.,100.):
 row=next(v for v in cases if v['variant']==variants[0][0] and v['force_N']==F and v['assumed_preload_each_N']==3000 and v['assumed_tension_amplification']==6)
 print(json.dumps(row,ensure_ascii=False))
print('same results all3 variants; equilibrium residual',equilibrium_error,'; coefficient',cn['value'],'; shear',cs)

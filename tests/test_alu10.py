"""Acceptance checks read actual exported solids, never source constants alone."""
import csv
import json
import sys
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from base_review import cylinders, seat_check, solid
from base_plate import make_plate
from column_lower_b import GateFailure
from delivery import PACKAGE_NAME, scan_english
from geometry import bounds
from part_names import export_named_step


class AluminumRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/'build/alu10'
        if not (cls.out/'manifest.json').exists():raise RuntimeError('Run scripts/build.py before the exported-geometry tests')
        cls.m=json.loads((cls.out/'manifest.json').read_text())
        cls.base=solid(cls.out/'edit_table_up/base_aluminum.step')
        cls.lower=solid(cls.out/'edit_table_up/column_lower.step')

    def test_plate_and_flange_seat(self):
        self.assertLess(np.max(abs(np.array(bounds(self.base))-[[-120,-130,.75],[120,0,10.75]])),1e-6)
        seat=seat_check(self.base,self.lower)
        self.assertAlmostEqual(seat['plate_top_z_mm'],10.75,places=6)
        self.assertGreater(seat['contact_area_mm2'],4385)
        holes=cylinders(self.base)
        self.assertEqual(len(holes),8)
        for h in holes:
            self.assertAlmostEqual(h['radius_mm']*2,6.04,places=6)
            np.testing.assert_allclose(np.array(h['bounds_mm'])[:,2],[.75,10.75],atol=1e-6,rtol=0)

    def test_counterbore_depth_diameter(self):
        holes=[c for c in cylinders(self.lower) if abs(c['radius_mm']-5.2)<1e-6]
        self.assertEqual(len(holes),4)
        self.assertEqual(sorted((round(h['axis_origin_mm'][0]),round(h['axis_origin_mm'][1])) for h in holes),[(-35,-46),(-35,-14),(35,-46),(35,-14)])
        for h in holes:np.testing.assert_allclose(np.array(h['bounds_mm'])[:,2],[18.75,24.75],atol=1e-6,rtol=0)
        np.testing.assert_allclose(np.array(bounds(self.lower))[:,2],[10.75,86.75],atol=1e-6,rtol=0)

    def test_bolt_insert_and_washer_z(self):
        for i in range(4):
            bolt=solid(self.out/'edit_table_up'/f'hardware_base_M5_{i}.step')
            np.testing.assert_allclose(np.array(bounds(bolt))[:,2],[1.75,26.75],atol=1e-6,rtol=0)
            head=[c for c in cylinders(bolt) if abs(c['radius_mm']-4.25)<1e-6]
            np.testing.assert_allclose(np.array(head[0]['bounds_mm'])[:,2],[21.75,26.75],atol=1e-6,rtol=0)
            for j in range(3):
                washer=solid(self.out/'edit_table_up'/f'hardware_base_top_washer_{i}_{j}.step')
                np.testing.assert_allclose(np.array(bounds(washer))[:,2],[18.75+j,19.75+j],atol=1e-6,rtol=0)
        for i in range(8):
            insert=solid(self.out/'edit_table_up'/f'hardware_base_insert_{i}.step')
            np.testing.assert_allclose(np.array(bounds(insert))[:,2],[2.85,10.35],atol=1e-6,rtol=0)

    def test_geometry_identity_including_owner_slider(self):
        names=[r['part'] for r in self.m['unchanged_sources']]
        self.assertEqual(len(names),34);self.assertIn('slider_upper_jaw',names)
        from source_identity import geometry
        for r in self.m['unchanged_sources']:
            current=geometry(solid(self.out/'edit_table_up'/f"{r['part']}.step"));baseline=r['baseline']
            self.assertEqual(current['solid_count'],baseline['solid_count'])
            self.assertEqual(current['face_count'],baseline['face_count'])
            self.assertLessEqual(abs(current['volume_mm3']-baseline['volume_mm3']),1e-6)
            np.testing.assert_allclose(current['bounds_mm'],baseline['bounds_mm'],atol=1e-6,rtol=0)
        revision=json.loads((ROOT/'design/source/revision_validation.json').read_text())
        import hashlib
        for row in revision['STL_checks']:
            if row['file'].endswith('/column_lower.stl'):continue
            self.assertEqual(hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest(),row['sha256'])
        for r in self.m['parts']:
            n=r['name']
            self.assertEqual((ROOT/'design/source/edit_table_up'/f'{n}.step').read_bytes(),(self.out/'edit_table_up'/f'{n}.step').read_bytes())
            if r['is_printed']:
                for ext in ('.step','.stl'):
                    self.assertEqual((ROOT/'design/source/print'/(n+ext)).read_bytes(),(self.out/'print'/(n+ext)).read_bytes())

    def test_package_has_no_CJK_including_STEP_escapes(self):
        self.assertTrue(scan_english(self.out/PACKAGE_NAME)['pass_'])

    def test_negative_control_plate_9_fails_contact(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plate_9.step';export_named_step(make_plate(9),path)
            with self.assertRaisesRegex(GateFailure,r'plate top Z=9.750000, flange bottom Z=10.750000, gap=1.000000 mm'):
                seat_check(solid(path),self.lower)


if __name__=='__main__':unittest.main()

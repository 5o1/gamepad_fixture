"""Regression for OCCT's wrapped/escaped Unicode assembly labels."""
import importlib.util,re,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('part_names',ROOT/'cad/part_names.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class StepNames(unittest.TestCase):
 def test_wrapped_identifier_preserves_geometry_records(self):
  label='底座螺母厚平垫 M5 1 [hardware_base_bottom_washer_0]'
  bad="'broken_[hardware_base_bottom_\nwasher_0]'"
  tail="\n#20=CARTESIAN_POINT('',(1.,2.,3.));\n"
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'part.step';p.write_text('#10=PRODUCT('+bad+','+bad+",'',());"+tail)
   module.repair_step_names(p,[label]);data=p.read_bytes()
   self.assertIn(label.encode('utf-16-be').hex().upper().encode(),data);self.assertTrue(data.endswith(tail.encode()))
 def test_complete_step_unicode_escape_is_canonical(self):
  label='套筒（叉形耳板） [column_sleeve]';wrong='bad [column_sleeve]'
  token='\\X2\\'+wrong.encode('utf-16-be').hex().upper()+'\\X0\\'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'part.step';p.write_text("#1=PRODUCT('"+token+"','','',());")
   module.repair_step_names(p,[label]);self.assertIn(label.encode('utf-16-be').hex().upper(),p.read_text())
if __name__=='__main__':unittest.main()

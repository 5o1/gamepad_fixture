"""Write option B from a v3.2 STEP path or recorded Git baseline, never during a build."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from column_lower_b import derive
from source_identity import git_bytes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-step',type=Path)
    p.add_argument('--print-step',type=Path)
    p.add_argument('--baseline-ref',default='HEAD')
    p.add_argument('--out',type=Path,default=ROOT/'design/source')
    a=p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        baseline=Path(folder)
        for name in ('edit_table_up','print'):(baseline/name).mkdir()
        table=a.source_step.read_bytes() if a.source_step else git_bytes(ROOT,a.baseline_ref,'design/source/edit_table_up/column_lower.step')
        printing=a.print_step.read_bytes() if a.print_step else git_bytes(ROOT,a.baseline_ref,'design/source/print/column_lower.step')
        (baseline/'edit_table_up/column_lower.step').write_bytes(table)
        (baseline/'print/column_lower.step').write_bytes(printing)
        for name in ('edit_table_up','print'):(a.out/name).mkdir(parents=True,exist_ok=True)
        _,record=derive(baseline,a.out)
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()

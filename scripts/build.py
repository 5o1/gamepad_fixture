"""Rebuild the aluminum machining/printing delivery from authoritative English CAD inputs."""
import argparse
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from base_plate import make
from base_paper import make as paper
from delivery import package
from visual_reference import make as visual_reference
from printing_colors import make as print_colors
from render_inputs import make as render_inputs


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=ROOT/'design/source')
    p.add_argument('--out',type=Path,default=ROOT/'build/alu10')
    a=p.parse_args()
    make(a.source,a.out)
    paper(a.out)
    visual_reference(a.out)
    print_colors(a.out)
    from reference_validation import check
    check(a.out)
    render_inputs(a.out,a.source)
    subprocess.run([sys.executable,str(ROOT/'scripts/bolt_strength.py'),'--out',str(a.out/'bolt_strength')],check=True)
    folder=package(a.out)
    print('Delivery:',folder)


if __name__=='__main__':main()

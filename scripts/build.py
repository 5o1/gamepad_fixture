"""Rebuild the machining/printing delivery from this repository's CAD inputs."""
import argparse,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from acrylic_base import make
from acrylic_paper import make as paper
from acrylic_review import review
from acrylic_delivery import package
from visual_reference import make as visual_reference

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'design/source');p.add_argument('--out',type=Path,default=ROOT/'build/acrylic16');a=p.parse_args()
 make(a.source,a.out)
 for name,target in [('acrylic','acrylic_perspective'),('mounted','assembly_with_controller')]:
  src=ROOT/'docs/media'/(name+'.png')
  if src.exists():shutil.copyfile(src,a.out/(target+'.png'))
 paper(a.out);review(a.out,a.source);visual_reference(a.out);folder=package(a.out)
 print('Delivery:',folder)

if __name__=='__main__':main()

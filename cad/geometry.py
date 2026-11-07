"""Shared solid construction helpers; dimensions are millimetres."""
import math
import numpy as np
from build123d import Box,Cylinder,Face,Wire,Location,extrude

def box(x0,x1,y0,y1,z0,z1):
 return Box(x1-x0,y1-y0,z1-z0).moved(Location(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)))

def cyl(radius,length,center,axis='z'):
 return Cylinder(radius,length).moved(Location(center,{'x':(0,90,0),'y':(90,0,0),'z':(0,0,0)}[axis]))

def prism(points,direction):
 return extrude(Face(Wire.make_polygon(points,close=True)),amount=float(np.linalg.norm(direction)),dir=tuple(np.asarray(direction)/np.linalg.norm(direction)))

def hex_prism(af,length,center,axis='z'):
 r=af/math.sqrt(3);s=prism([(r*math.cos(k*math.pi/3),r*math.sin(k*math.pi/3),-length/2) for k in range(6)],(0,0,length))
 return s.moved(Location(center,{'x':(0,90,0),'y':(90,0,0),'z':(0,0,0)}[axis]))

def bounds(shape):
 b=shape.bounding_box();return [[b.min.X,b.min.Y,b.min.Z],[b.max.X,b.max.Y,b.max.Z]]

"""Derive option B from a recorded v3.2 column and register its real print frame."""
import hashlib
import math
import numpy as np
from build123d import Compound, Location, Plane, import_step, export_stl
from geometry import bounds, box, cyl
from part_names import export_named_step, label


class GateFailure(RuntimeError):
    """A critical design acceptance failure; do not continue packaging."""


def require(condition, message):
    if not condition:
        raise GateFailure(message)


def volume(shape):
    return shape.volume if shape else 0.0


def section_area(shape, z):
    return Compound(children=list(shape.intersect(Plane(origin=(0, 0, z))))).area


def register(source):
    source_shape = import_step(source / 'edit_table_up/column_lower.step').solids()[0]
    print_shape = import_step(source / 'print/column_lower.step').solids()[0]
    a, b = np.array(bounds(source_shape)), np.array(bounds(print_shape))
    translation = b[0] - a[0]
    candidate = source_shape.moved(Location(tuple(translation)))
    error = float(np.max(abs(np.array(bounds(candidate)) - b)))
    delta = abs(candidate.volume - print_shape.volume)
    symmetric = volume(candidate - print_shape) + volume(print_shape - candidate)
    require(error <= 1e-4 and delta <= 1e-6 and symmetric <= 1e-6,
            f'C3: print registration failed: bounds={error}, volume={delta}, symmetric difference={symmetric}')
    transform = np.eye(4)
    transform[:3, 3] = translation
    return source_shape, dict(matrix=transform.tolist(), bounds_error_mm=error,
                             volume_error_mm3=delta, symmetric_difference_mm3=symmetric,
                             method='Translation fitted to bounds; full bidirectional Boolean feature comparison')


def derive(source, out):
    original, registration = register(source)
    revised = original + box(-45, 45, -55, -5, 10.75, 16.75)
    for x in (-35, 35):
        for y in (-14, -46):
            revised -= cyl(2.75, 6, (x, y, 13.75))
            revised -= cyl(5.2, 6, (x, y, 21.75))
    revised.label = label('column_lower')
    export_named_step(revised, out / 'edit_table_up/column_lower.step')
    # Read the exported solid for acceptance, not just the in-memory construction.
    revised = import_step(out / 'edit_table_up/column_lower.step').solids()[0]
    expected = original.volume + 90*50*6 - 4*math.pi*2.75**2*6 - 4*math.pi*(5.2**2-2.75**2)*6
    error = abs(revised.volume - expected)
    require(revised.is_valid and len(revised.solids()) == 1 and error <= 1e-3,
            f'C1: invalid column or analytic volume mismatch: {error} mm^3')
    sections = [dict(z_mm=float(z), source_area_mm2=section_area(original, z),
                     revised_area_mm2=section_area(revised, z)) for z in np.linspace(24.8, 86.7, 10)]
    above = box(-100, 100, -100, 100, 24.75, 100)
    missing = volume((original - revised) & above)
    added = volume((revised - original) & above)
    require(missing <= 1e-6 and added <= 1e-6 and all(abs(r['source_area_mm2']-r['revised_area_mm2']) <= 1e-6 for r in sections),
            f'C1: upper geometry changed: missing={missing}, added={added}')
    translation = np.array(registration['matrix'])[:3, 3]
    # The same registered axes with a 6 mm bed re-zero preserve apex +Z.
    translation[2] += 6
    printable = revised.moved(Location(tuple(translation)))
    printable.label = label('column_lower')
    export_named_step(printable, out / 'print/column_lower.step')
    export_stl(printable, out / 'print/column_lower.stl', tolerance=.04)
    return revised, dict(rev='v3.4-B', source_sha256=hashlib.sha256((source/'edit_table_up/column_lower.step').read_bytes()).hexdigest(),
        operations=['Union box X -45..45, Y -55..-5, Z 10.75..16.75',
                    'Extend four diameter 5.5 holes through Z 10.75..16.75',
                    'Cut four diameter 10.4 flat counterbores Z 18.75..24.75'],
        source_volume_mm3=original.volume, expected_volume_mm3=expected, exported_volume_mm3=revised.volume,
        volume_error_mm3=error, bounds_mm=bounds(revised), sections=sections,
        source_minus_revised_above_flange_mm3=missing, revised_minus_source_above_flange_mm3=added,
        registered_source_print_transform=registration,
        revised_print_translation_mm=translation.tolist(),
        print_note='Axes unchanged; bed origin reset by +6 mm Z after flange extension. Counterbores open upward, floor at print Z 8; no counterbore roof bridging. Confirm toolpath and floor quality in slicer; no physical print test.')

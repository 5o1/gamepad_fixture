"""English CAD display names preserve stable part IDs."""
from pathlib import Path
import re

NAMES = {
    'base_printed': 'Base plate (retired printed snapshot)',
    'base_aluminum': 'Base plate (10 mm aluminum)',
    'column_lower': 'Column base (flange, gusset plates, inner column)',
    'column_sleeve': 'Column sleeve (clevis lugs)',
    'cradle_lower_jaw': 'Cradle (back support, lower jaw, integrated guide cap)',
    'slider_upper_jaw': 'Upper jaw slider',
    'hirth_fixed': 'Fixed Hirth disc',
    'hirth_moving': 'Moving Hirth disc',
    'pad_back': 'Back support pad',
    'pad_lower_jaw': 'Lower jaw pad',
    'pad_upper_jaw': 'Upper jaw pad',
    'hardware_M8_sliding_sleeve': 'Pivot sliding steel sleeve',
    'hardware_M8_axis_bolt': 'Pivot bolt M8x100',
    'hardware_M8_hub_washer': 'Cradle hub washer M8',
    'hardware_M8_star_knob_envelope': 'Through-thread star knob M8 (purchase envelope)',
    'hardware_M6_height_bolt': 'Height-lock bolt M6x70',
    'hardware_M6_locknut': 'Height-lock nut M6',
    'guide_pin_coupon': 'Guide pin fit coupon',
    'controller_reference_SURFACE': 'Controller reference surface (do not print)',
}


def label(part):
    if part in NAMES:
        title = NAMES[part]
    elif part.startswith('guide_rod_'):
        title = 'Steel guide rod ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_compression_spring_'):
        title = 'Compression spring ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_M8_washer_'):
        title = 'Pivot washer M8 ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_M6_washer_'):
        title = 'Height-lock washer M6 ' + ('left' if part.endswith('_-1') else 'right')
    elif part.startswith('hardware_base_M5_'):
        title = 'Column mounting bolt M5x20 ISO 4762 class 8.8 ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_base_top_washer_'):
        title = 'Column mounting washer M5 ISO 7089 ' + part.removeprefix('hardware_base_top_washer_')
    elif part.startswith('hardware_base_insert_'):
        title = 'Wire thread insert M5x0.8 1.5D tangless ' + part.rsplit('_', 1)[1]
    elif part.startswith(('hardware_fixed_ring_', 'hardware_moving_ring_')):
        ring = 'Fixed Hirth disc' if part.startswith('hardware_fixed_ring_') else 'Moving Hirth disc'
        fastener = 'nut M3' if '_nut_' in part else 'bolt M3'
        title = f'{ring} {fastener} {part.rsplit("_", 1)[1]} deg'
    else:
        title = part
    return f'{title} [{part}]'


def repair_step_names(path,labels):
    """Use STEP Unicode escapes for labels passed through OCCT's8-bit ctor.

    Only complete quoted label tokens are replaced. Geometry entities and
    numeric coordinates are untouched; no shared Python package is patched.
    """
    path=Path(path);data=path.read_bytes();direct={};by_id={}
    for name in set(labels):
        if not name:continue
        # ASCII labels are written literally; OCCT's nested re-import can
        # still replace their spaces/brackets with underscores, which the
        # stable-ID fallback below restores.
        escaped=(name.replace("'","''").encode('ascii') if name.isascii() else
            ('\\X2\\'+name.encode('utf-16-be').hex().upper()+'\\X0\\').encode('ascii'))
        identifier=re.search(r'\[[A-Za-z0-9_+-]+\]',name)
        if identifier:by_id[identifier.group().encode('ascii')]=escaped
        for wrong in (name,name.encode('utf-8').decode('latin-1')):
            direct[wrong.replace("'","''").encode('utf-8')]=escaped
    def replace(match):
        content=match.group(1);replacement=direct.get(content)
        # OCCT may wrap long label tokens inside their stable identifier.
        searchable=re.sub(rb'[\r\n]+[ \t]*',b'',content)
        # Nested STEP exports can escape the complete label, including its
        # ASCII stable ID. Decode only string escapes for ID matching; never
        # reinterpret geometric records or depend on damaged display text.
        if b'\\X2\\' in searchable:
            try:
                searchable=re.sub(rb'\\X2\\([0-9A-Fa-f]+)\\X0\\',
                    lambda q:bytes.fromhex(q.group(1).decode('ascii')).decode('utf-16-be').encode('utf-8'),searchable)
            except (UnicodeError,ValueError):
                searchable=content
        if replacement is None and b'[' in searchable:
            replacement=next((value for key,value in by_id.items() if key in searchable),None)
        return b"'"+replacement+b"'" if replacement is not None else match.group()
    path.write_bytes(re.sub(rb"'((?:''|[^'])*)'",replace,data))


def export_named_step(shape,path,**kwargs):
    from build123d import export_step
    result=export_step(shape,path,**kwargs)
    labels=[];pending=[shape]
    while pending:
        node=pending.pop();labels.append(node.label);pending.extend(getattr(node,'children',[]))
    repair_step_names(path,labels)
    return result

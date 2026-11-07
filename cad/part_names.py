"""CAD labels retain the part IDs and terminology used in the Fusion review."""
from pathlib import Path
import re

NAMES = {
    'base_printed': '底板',
    'column_lower': '立柱底座（法兰、斜板、内立柱）',
    'column_sleeve': '套筒（叉形耳板）',
    'cradle_lower_jaw': '托架（背托、下夹爪、一体导轨盖）',
    'slider_upper_jaw': '上夹爪滑块',
    'hirth_fixed': '固定齿盘',
    'hirth_moving': '转动齿盘',
    'pad_back': '背托软垫',
    'pad_lower_jaw': '下夹爪软垫',
    'pad_upper_jaw': '上夹爪软垫',
    'hardware_M8_sliding_sleeve': '转轴滑动钢套管',
    'hardware_M8_axis_bolt': '转轴螺栓 M8×100',
    'hardware_M8_hub_washer': '托架凸台大垫圈 M8',
    'hardware_M8_star_knob_envelope': '标准星形把手 M8（采购包络）',
    'hardware_M6_height_bolt': '调高螺栓 M6×70',
    'hardware_M6_locknut': '调高防松螺母 M6',
    'guide_pin_coupon': '钢销配合小样',
}


def label(part):
    if part in NAMES:
        title = NAMES[part]
    elif part.startswith('guide_rod_'):
        title = '钢销导杆 ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_compression_spring_'):
        title = '压簧 ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_M8_washer_'):
        title = '转轴大垫圈 M8 ' + part.rsplit('_', 1)[1]
    elif part.startswith('hardware_M6_washer_'):
        title = '调高大垫圈 M6 ' + ('左' if part.endswith('_-1') else '右')
    elif part.startswith('hardware_base_M5_'):
        title = '立柱底座固定螺丝 M5 ' + str(int(part.rsplit('_', 1)[1]) + 1)
    elif part.startswith(('hardware_fixed_ring_', 'hardware_moving_ring_')):
        ring = '固定齿盘' if part.startswith('hardware_fixed_ring_') else '转动齿盘'
        fastener = '螺母 M3' if '_nut_' in part else '螺丝 M3'
        title = f'{ring}{fastener} {part.rsplit("_", 1)[1]}°'
    else:
        # Historical coupons and optional parts already have stable public IDs.
        title = part
    return f'{title} [{part}]'


def repair_step_names(path,labels):
    """Use STEP Unicode escapes for labels passed through OCCT's8-bit ctor.

    Only complete quoted label tokens are replaced. Geometry entities and
    numeric coordinates are untouched; no shared Python package is patched.
    """
    path=Path(path);data=path.read_bytes();direct={};by_id={}
    for name in set(labels):
        if not name or name.isascii():continue
        escaped=('\\X2\\'+name.encode('utf-16-be').hex().upper()+'\\X0\\').encode('ascii')
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

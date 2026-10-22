import json
import math
import struct
from startup_support import require

def validate_scene(directory):
    path = directory / 'scene-report.json'
    require(path.is_file(), 'Original worker did not save a scene report')
    value = json.loads(path.read_text())
    require(value.get('status') == 'READY', 'Original scene report is not READY')
    require(len(value.get('drive', [])) == 14 and all((math.isfinite(x) for x in value['drive'])), 'Invalid drive-state evidence')
    require(len(value.get('measured_arm', [])) == 12 and all((math.isfinite(x) for x in value['measured_arm'])), 'Invalid measured-joint evidence')
    for name in ('head_camera', 'left_camera', 'right_camera'):
        image = (directory / f'{name}-start.png').read_bytes()
        require(image[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', image[16:24]) == (320, 240), 'Invalid camera PNG: ' + name)
    return value

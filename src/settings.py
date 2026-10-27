import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROFILES={'stable':512,'low':256,'minimum':128}
def load():
    path=ROOT/'settings.json'
    data=json.loads(path.read_text()) if path.exists() else {'profile':'stable','gain_db':0}
    if not isinstance(data,dict):
        raise ValueError('settings must be a JSON object')
    profile=data.get('profile','stable')
    gain=data.get('gain_db',0)
    if profile not in PROFILES or type(gain) not in (int,float) or not -12<=gain<=18:
        raise ValueError('profile must be stable/low/minimum and gain_db must be -12..18')
    return {'profile':profile,'gain_db':float(gain),'target':PROFILES[profile]}

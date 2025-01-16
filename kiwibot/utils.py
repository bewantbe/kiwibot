import time
from datetime import datetime

def GetISOTimestamp(t = None):
    """return string like '2025-01-14T07:03:43.273',
    used for timestamp in metadata"""
    if t is None:
        t = time.time()
    #ms = int((t - int(t)) * 1000)
    #return time.strftime('%Y-%m-%dT%H:%M:%S.', time.localtime(t)) + f"{ms:03d}"
    return datetime.fromtimestamp(t).isoformat(timespec='milliseconds')

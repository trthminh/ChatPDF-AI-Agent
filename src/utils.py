from datetime import datetime
from zoneinfo import ZoneInfo
def get_current_hcm_time_iso() -> str:
    hcm_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now_hcm = datetime.now(hcm_tz)
    print(f"Current HCM time: {now_hcm.isoformat()}")
    return now_hcm.isoformat()
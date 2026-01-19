from datetime import datetime, timezone
from zoneinfo import ZoneInfo

hkTime = datetime.now(ZoneInfo('Asia/Macau'))
hkDate, hkTime = str(hkTime).split(".")[0].split(" ")
hkTime = hkTime.split(":")[0:2]
hkDate = hkDate.split("-")[1:3]
print(hkTime)
print(hkDate)
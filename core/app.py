from version import VERSION
from updater import check_update

print("XDTool modules started")
print("Version:", VERSION)

latest = check_update()

if latest != VERSION:
    print("[WARNING] Nueva versión disponible:", latest)
else:
    print("[CHECK-IN] You are fully updated")
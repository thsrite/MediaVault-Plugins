"""A dependency-free runner: consume one JSON request and return one JSON result."""

import json
import sys


request = json.loads(sys.stdin.readline())
if request.get("type") == "action" and request.get("action") == "preview":
    result = {"event_type": "action.preview", "payload": request.get("payload", {})}
elif request.get("type") == "event":
    result = {
        "event_id": request.get("event_id"),
        "event_type": request.get("event_type"),
        "source": request.get("source"),
        "payload_keys": sorted((request.get("payload") or {}).keys()),
    }
elif request.get("type") == "schedule" and request.get("task_id") == "hourly_check":
    result = {"task_id": request["task_id"], "status": "checked"}
else:
    print(json.dumps({"ok": False, "error": "unsupported request"}))
    raise SystemExit(2)

print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))

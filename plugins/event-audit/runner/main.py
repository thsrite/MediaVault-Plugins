"""A dependency-free runner: consume one JSON request and return one JSON result."""

import json
import sys


request = json.loads(sys.stdin.readline())
logs = []


def log(level, message, **fields):
    """协议日志：只返回 JSON，宿主负责格式化、脱敏和落盘。"""
    logs.append({"level": level, "message": message, "fields": fields})


if request.get("type") == "action" and request.get("action") == "preview":
    result = {"event_type": "action.preview", "payload": request.get("payload", {})}
    log("info", "预览 action 已执行")
elif request.get("type") == "event":
    result = {
        "event_id": request.get("event_id"),
        "event_type": request.get("event_type"),
        "source": request.get("source"),
        "payload_keys": sorted((request.get("payload") or {}).keys()),
    }
    log("info", "事件已接收", event_type=request.get("event_type"))
elif request.get("type") == "schedule" and request.get("task_id") == "hourly_check":
    result = {"task_id": request["task_id"], "status": "checked"}
    log("info", "定时任务已执行", task_id=request["task_id"])
else:
    print(json.dumps({"ok": False, "error": "unsupported request"}))
    raise SystemExit(2)

print(json.dumps({"ok": True, "result": result, "logs": logs}, ensure_ascii=False))

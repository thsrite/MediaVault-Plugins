import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "event-audit"
MANIFEST = json.loads((PLUGIN_ROOT / "mv-plugin.json").read_text(encoding="utf-8"))


def run_plugin(request):
    return subprocess.run(
        ["python3", MANIFEST["entrypoint"]],
        cwd=PLUGIN_ROOT,
        input=json.dumps(request, ensure_ascii=False) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )


class ProtocolTests(unittest.TestCase):
    def test_manifest_declares_all_public_events_and_boundaries(self):
        self.assertEqual(MANIFEST["manifest_version"], 1)
        self.assertEqual(MANIFEST["runtime"], "python3-stdlib")
        self.assertEqual(len(MANIFEST["events"]), 16)
        self.assertEqual(MANIFEST.get("permissions", []), [])
        self.assertEqual(MANIFEST["entrypoint"], "runner/main.py")
        self.assertEqual(MANIFEST["ui"]["schema"]["type"], "form")
        self.assertEqual(MANIFEST["ui"]["schema"]["components"][0]["bind"], "label")

    def test_event_request_returns_event_identity_without_mv_dependency(self):
        process = run_plugin({
            "protocol_version": 1,
            "type": "event",
            "event_id": "event-1",
            "event_type": "media.uploaded",
            "source": "monitor",
            "payload": {"file_name": "电影.mkv"},
        })
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["event_id"], "event-1")
        self.assertEqual(response["result"]["event_type"], "media.uploaded")
        self.assertEqual(response["logs"][0]["level"], "info")
        self.assertEqual(response["logs"][0]["fields"]["event_type"], "media.uploaded")

    def test_action_request_returns_payload(self):
        process = run_plugin({
            "protocol_version": 1,
            "type": "action",
            "request_id": "request-1",
            "action": "preview",
            "payload": {"sample": True},
        })
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["payload"]["sample"])

    def test_schedule_request_returns_task_status(self):
        process = run_plugin({
            "protocol_version": 1,
            "type": "schedule",
            "task_id": "hourly_check",
        })
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"], {"task_id": "hourly_check", "status": "checked"})

    def test_unknown_request_fails_closed(self):
        process = run_plugin({"protocol_version": 1, "type": "unknown"})
        self.assertNotEqual(process.returncode, 0)
        response = json.loads(process.stdout)
        self.assertFalse(response["ok"])


if __name__ == "__main__":
    unittest.main()

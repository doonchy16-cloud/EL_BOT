import json
import tempfile
import unittest
from pathlib import Path

from Engines.cluster.control_plane import CoordinatorControlPlane
from Engines.cluster.coordinator import WorkerSession, _validate_round_frame
from Engines.ui.aio_dashboard import APP_TITLE, APP_VERSION, build_frame, strip_ansi


class DummyConn:
    def shutdown(self, *args, **kwargs):
        pass

    def close(self):
        pass


def make_session(node_id, session_id, hostname, speed=3.0, assigned_steps=250):
    session = WorkerSession(conn=DummyConn(), addr=("192.168.1.2", 1234), max_payload=1024)
    session.cluster_id = "quotesnap-main"
    session.session_id = session_id
    session.epoch = 8
    session.node_id = node_id
    session.hostname = hostname
    session.transport = "LAN"
    session.software_version = "3.4.2"
    session.remote_steps_per_second = speed
    session.state = "TRAINING"
    session.active_round_id = "BASE-000067500-000018"
    session.local_window_step = 70
    session.assigned_steps = assigned_steps
    session.assigned_examples = assigned_steps * 128
    session.round_total_steps = 750
    session.round_total_examples = 96000
    session.canonical_step = 67500
    return session


class V342StatusAndUITests(unittest.TestCase):
    def test_coordinator_snapshot_keeps_sessions_per_worker(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {
                "cluster_id": "quotesnap-main",
                "tcp_port": 48571,
                "udp_discovery_port": 0,
                "expected_worker_count": 2,
                "session_freshness_seconds": 30,
            }
            cp = CoordinatorControlPlane(cfg, {}, "3.4.2", Path(td), hostname="DESKTOP-V9SCI9V")
            cp.epoch = 8
            cp.coordinator_instance_id = "coord-1234567890"
            cp._registry.admit(make_session("doonchyscomputi", "main-session", "MAIN", 3.3, 329))
            cp._registry.admit(make_session("msi", "msi-session", "MSI", 3.1, 284))
            snap = cp.snapshot()
            self.assertEqual(snap["coordinator_instance_id"], "coord-1234567890")
            self.assertNotIn("session_id", snap)
            self.assertNotIn("peer", snap)
            self.assertNotIn("worker_hostname", snap)
            self.assertEqual(snap["expected_worker_count"], 2)
            self.assertEqual({w["session_id"] for w in snap["workers"]}, {"main-session", "msi-session"})
            self.assertTrue(snap["cluster_sync"]["sessions_unique"])
            self.assertTrue(snap["cluster_sync"]["epoch_match"])
            self.assertTrue(snap["cluster_sync"]["cluster_match"])
            self.assertTrue(snap["cluster_sync"]["software_match"])

    def test_distinct_worker_sessions_are_valid_and_cross_session_is_rejected(self):
        main = make_session("doonchyscomputi", "main-session", "MAIN")
        msi = make_session("msi", "msi-session", "MSI")
        for session in (main, msi):
            _validate_round_frame(
                session,
                {"cluster_id": "quotesnap-main", "epoch": 8, "session_id": session.session_id, "round_id": "R"},
                cluster_id="quotesnap-main",
                round_id="R",
            )
        with self.assertRaisesRegex(Exception, "session mismatch"):
            _validate_round_frame(
                msi,
                {"cluster_id": "quotesnap-main", "epoch": 8, "session_id": "main-session", "round_id": "R"},
                cluster_id="quotesnap-main",
                round_id="R",
            )

    def test_coordinator_overview_is_cluster_first(self):
        state = {
            "stage": "BASE", "status": "TRAINING", "stage_step": 67500,
            "stage_examples": 8640000, "stage_target_examples": 1000000000,
            "loss": 0.073427, "steps_per_second": 1.22, "effective_batch": 128,
            "local_window_step": 31,
        }
        cluster = {
            "role": "COORDINATOR", "control_state": "ROUND_TRAINING",
            "cluster_id": "quotesnap-main", "coordinator_instance_id": "coord-1234567890",
            "epoch": 8, "round": "BASE-000067500-000018", "canonical_step": 67500,
            "fallback": False, "configured_primary": "DESKTOP_v9sci9v",
            "local_hostname": "DESKTOP-V9SCI9V", "authority_match": True,
            "expected_role": "COORDINATOR", "expected_worker_count": 2,
            "transport_summary": "LAN", "adaptive_round_balancing": True,
            "round_total_steps": 750, "round_total_examples": 96000,
            "coordinator": {"assigned_steps": 137, "local_window_step": 31, "steps_per_second": 1.22},
            "cluster_sync": {
                "status": "VERIFIED", "workers_active": 2, "workers_expected": 2,
                "sessions_unique": True, "epoch_match": True, "round_match": True,
                "canonical_match": True, "software_match": True,
            },
            "workers": [
                {"hostname": "MAIN", "node_id": "doonchyscomputi", "session_id": "main-session", "state": "TRAINING", "transport": "LAN", "peer": "192.168.1.174:1", "local_window_step": 70, "assigned_steps": 329, "steps_per_second": 3.3, "last_heartbeat_age_seconds": 0.6},
                {"hostname": "MSI", "node_id": "msi", "session_id": "msi-session", "state": "TRAINING", "transport": "LAN", "peer": "192.168.1.6:1", "local_window_step": 70, "assigned_steps": 284, "steps_per_second": 3.1, "last_heartbeat_age_seconds": 0.7},
            ],
        }
        text = strip_ansi(build_frame(state, {}, cluster, {"free_gb": 400}, "x.log"))
        self.assertIn("V3.4.2", text)
        self.assertIn("Coordinator ID", text)
        self.assertIn("CLUSTER SYNC", text)
        self.assertIn("VERIFIED", text)
        self.assertIn("137 steps", text)
        self.assertIn("329 steps", text)
        self.assertIn("284 steps", text)
        self.assertNotIn("Authority match:", text)
        self.assertNotIn("Remote speed", text)

    def test_worker_overview_is_assignment_first(self):
        state = {
            "stage": "BASE", "status": "TRAINING", "stage_step": 67500,
            "stage_examples": 8640000, "stage_target_examples": 1000000000,
            "loss": 0.073427, "steps_per_second": 3.3188, "effective_batch": 128,
            "local_window_step": 150, "local_window_examples": 19200,
            "local_window_target_examples": 42112,
        }
        cluster = {
            "role": "WORKER", "control_state": "TRAINING", "cluster_id": "quotesnap-main",
            "coordinator_hostname": "DESKTOP-V9SCI9V", "coordinator_instance_id": "coord-1234567890",
            "epoch": 8, "worker_session_id": "main-session", "session_id": "main-session",
            "round": "BASE-000067500-000018", "canonical_step": 67500,
            "assignment_steps": 329, "assignment_examples": 42112,
            "round_total_steps": 750, "round_total_examples": 96000,
            "local_window_step": 150, "fallback": False, "transport": "LAN",
            "peer": "192.168.1.110", "configured_primary": "DESKTOP_v9sci9v",
            "local_hostname": "DOONCHYSCOMPUTI", "node_id": "doonchyscomputi",
            "authority_match": False, "expected_role": "WORKER",
        }
        text = strip_ansi(build_frame(
            state,
            {"name": "RTX 5070", "used": "4049", "total": "8151", "util": "95", "temp": "76", "power": "61.4"},
            cluster,
            {"free_gb": 1726},
            "x.log",
        ))
        self.assertIn("CURRENT ASSIGNMENT", text)
        self.assertIn("329 steps", text)
        self.assertIn("150 / 329", text)
        self.assertIn("My session", text)
        self.assertIn("main-session", text)
        self.assertNotIn("Authority match: NO", text)
        self.assertIn("Coordinator", text)
        self.assertIn("DESKTOP-V9SCI9V", text)
        self.assertIn("43.9%", text)

    def test_software_and_protocol_identity(self):
        self.assertEqual(APP_VERSION, "3.4.2")
        self.assertIn("V3.4.2", APP_TITLE)
        root = Path(__file__).resolve().parents[2]
        aio = json.loads((root / "Config" / "aio.json").read_text(encoding="utf-8"))
        cluster = json.loads((root / "Config" / "cluster.json").read_text(encoding="utf-8"))
        self.assertEqual(aio["version"], "3.4.2")
        self.assertEqual(cluster["version"], "3.4")
        self.assertEqual(cluster["software_version"], "3.4.2")
        self.assertEqual(cluster["expected_worker_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

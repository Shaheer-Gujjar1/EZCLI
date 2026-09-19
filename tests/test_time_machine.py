"""Tests for Time Machine (ez time-machine) native snapshot engine, CLI, and elevation."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ezcli_app.time_machine.snapshot_engine import (
    SnapshotMetadata,
    format_snapshot_id,
    format_human_size,
    list_local_snapshots,
    get_latest_snapshot,
    create_snapshot,
    simulate_restore,
    restore_snapshot,
    delete_snapshot,
    get_storage_stats,
)
from ezcli_app.time_machine.time_machine_cli import (
    print_snapshots_table,
    run_cli_time_machine,
)


class TestTimeMachineEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.snapshots_dir = Path(self.temp_dir.name) / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_human_size(self):
        self.assertEqual(format_human_size(0), "0 B")
        self.assertEqual(format_human_size(500), "500 B")
        self.assertEqual(format_human_size(1024), "1.0 KB")
        self.assertEqual(format_human_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_human_size(1024 * 1024 * 1024), "1.0 GB")

    def test_format_snapshot_id(self):
        snap_id = format_snapshot_id()
        self.assertRegex(snap_id, r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

    def test_get_storage_stats(self):
        stats = get_storage_stats(Path(self.temp_dir.name))
        self.assertIn("avail_bytes", stats)
        self.assertIn("total_bytes", stats)
        self.assertIn("used_percent", stats)
        self.assertGreater(stats["total_bytes"], 0)

    def test_create_and_list_snapshots(self):
        # Create fake source structure for test
        with tempfile.TemporaryDirectory() as src_dir:
            src_path = Path(src_dir)
            (src_path / "test.conf").write_text("setting=1")

            orig_exists = os.path.exists
            with patch("os.path.exists", side_effect=lambda p: True if p in ("/etc", "/usr/local") else orig_exists(p)):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                    ok, meta, err = create_snapshot(
                        comment="Initial system state",
                        profile="config",
                        snapshots_dir=self.snapshots_dir,
                    )
                    self.assertTrue(ok, f"Error creating snapshot: {err}")
                    self.assertIsNotNone(meta)
                    self.assertEqual(meta.comment, "Initial system state")
                    self.assertEqual(meta.profile, "config")


            # Check snapshot listed
            snaps = list_local_snapshots(self.snapshots_dir)
            self.assertEqual(len(snaps), 1)
            self.assertEqual(snaps[0].id, meta.id)
            self.assertEqual(snaps[0].comment, "Initial system state")

            latest = get_latest_snapshot(self.snapshots_dir)
            self.assertIsNotNone(latest)
            self.assertEqual(latest.id, meta.id)

    def test_delete_snapshot(self):
        # Create dummy snapshot
        snap_id = "2026-09-19_12-00-00"
        snap_dir = self.snapshots_dir / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "id": snap_id,
            "created_at": "2026-09-19 12:00:00",
            "timestamp": 1700000000.0,
            "comment": "To be deleted",
            "profile": "config",
            "size_bytes": 1024,
            "distro": "Linux",
            "kernel": "6.6.0",
            "packages_count": 100,
            "status": "complete",
        }
        with open(snap_dir / "snapshot.json", "w") as f:
            json.dump(meta, f)

        self.assertEqual(len(list_local_snapshots(self.snapshots_dir)), 1)
        ok, msg = delete_snapshot(snap_id, snapshots_dir=self.snapshots_dir)
        self.assertTrue(ok)
        self.assertEqual(len(list_local_snapshots(self.snapshots_dir)), 0)

        # Deleting non-existent snapshot
        ok_fail, msg_fail = delete_snapshot("fake_id", snapshots_dir=self.snapshots_dir)
        self.assertFalse(ok_fail)

    def test_simulate_restore_missing_snapshot(self):
        res = simulate_restore("non_existent_snapshot", snapshots_dir=self.snapshots_dir)
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"].lower())

    def test_restore_snapshot_missing(self):
        ok, err = restore_snapshot("non_existent_snapshot", snapshots_dir=self.snapshots_dir)
        self.assertFalse(ok)
        self.assertIn("not found", err.lower())


class TestTimeMachineCLI(unittest.TestCase):
    @patch("ezcli_app.time_machine.time_machine_cli.list_local_snapshots", return_value=[])
    def test_print_snapshots_table_empty(self, mock_list):
        from rich.console import Console
        c = Console(record=True)
        print_snapshots_table(console=c)
        out = c.export_text()
        self.assertIn("Time Machine", out)
        self.assertIn("No system restore points found", out)

    @patch("ezcli_app.time_machine.time_machine_cli.list_local_snapshots")
    def test_print_snapshots_table_with_items(self, mock_list):
        from rich.console import Console
        mock_list.return_value = [
            SnapshotMetadata(
                id="2026-09-19_10-00-00",
                created_at="2026-09-19 10:00:00",
                timestamp=1700000000.0,
                comment="Pre-driver update",
                profile="config",
                size_bytes=10485760,
                distro="Deepin 25",
                kernel="6.6.0",
                packages_count=1200,
            )
        ]
        c = Console(record=True, width=120)
        print_snapshots_table(console=c)
        out = c.export_text()
        self.assertIn("2026-09-19_10-00-00", out)
        self.assertIn("Pre-driver", out)
        self.assertIn("CONFIG", out)



    def test_path_arguments_rejected(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli_time_machine(raw_args=["/var/log"])
        self.assertEqual(ctx.exception.code, 1)

        with self.assertRaises(SystemExit) as ctx2:
            run_cli_time_machine(raw_args=["some_folder"])
        self.assertEqual(ctx2.exception.code, 1)

    @patch("ezcli_app.elevation.elevated_tm_create")
    def test_cli_create_direct(self, mock_create):
        mock_create.return_value = (True, {"id": "2026-09-19_11-11-11", "size_bytes": 1000, "profile": "config"}, "")
        from rich.console import Console
        c = Console(record=True)
        run_cli_time_machine(raw_args=["create", "Test CLI snapshot"], console=c)
        out = c.export_text()
        self.assertIn("Restore point created successfully", out)
        self.assertIn("2026-09-19_11-11-11", out)
        mock_create.assert_called_once()

    @patch("ezcli_app.time_machine.time_machine_cli.print_snapshots_table")
    def test_cli_list_dispatch(self, mock_print):
        run_cli_time_machine(raw_args=["list"])
        mock_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()

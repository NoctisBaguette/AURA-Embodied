import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "m9_vulkan_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("vulkan_diagnostic", SOURCE)
DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTIC)


class VulkanDiagnosticGuards(unittest.TestCase):
    def test_only_standard_library_imports_no_simulator_or_loader_execution(self):
        tree = ast.parse(SOURCE.read_text())
        allowed = {"argparse", "datetime", "hashlib", "importlib", "json", "os",
                   "pathlib", "shutil", "subprocess", "sys"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] in allowed for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module.split(".")[0], allowed)
        self.assertNotIn("vulkaninfo", SOURCE.read_text())
        self.assertNotIn("ctypes", SOURCE.read_text())

    def test_override_files_and_xdg_paths_retained_even_when_override_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "data/vulkan/icd.d"
            directory.mkdir(parents=True)
            actual = directory / "actual.json"
            actual.write_text('{}')
            missing = root / "missing.json"
            found = DIAGNOSTIC.manifest_files({"XDG_DATA_HOME": str(root / "data"),
                "VK_DRIVER_FILES": str(missing)}, root, root)
            self.assertIn(actual, found)
            self.assertIn(missing, found)
            self.assertEqual(DIAGNOSTIC.read_file(missing)["state"], "unreadable")

    def test_missing_and_timed_out_external_tools_reported_not_installed(self):
        with patch.object(DIAGNOSTIC.shutil, "which", return_value=None):
            self.assertEqual(DIAGNOSTIC.command(["missing"])["state"], "not_installed")
        with patch.object(DIAGNOSTIC.shutil, "which", return_value="/usr/bin/readelf"), \
             patch.object(DIAGNOSTIC.subprocess, "run", side_effect=subprocess.TimeoutExpired("readelf", 15)):
            self.assertEqual(DIAGNOSTIC.command(["readelf", "-d", "file"])["state"], "timeout")

    def test_report_uses_environment_allowlist_and_handles_malformed_icd(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "driver.json"
            manifest.write_text('[1, 2]')
            with patch.dict(DIAGNOSTIC.os.environ, {"UNRELATED_SECRET": "must_not_appear"}), \
                 patch.object(DIAGNOSTIC, "manifest_files", return_value=[manifest]), \
                 patch.object(DIAGNOSTIC, "command", return_value={"state": "not_installed"}), \
                 patch.object(DIAGNOSTIC.metadata, "version", side_effect=DIAGNOSTIC.metadata.PackageNotFoundError("test-package")), \
                 patch.object(DIAGNOSTIC.metadata, "distribution", side_effect=DIAGNOSTIC.metadata.PackageNotFoundError("sapien")):
                encoded = json.dumps(DIAGNOSTIC.inspect(), allow_nan=False)
            self.assertNotIn("must_not_appear", encoded)
            self.assertIn('"library_path": null', encoded)

    def test_existing_output_is_not_overwritten_or_inspected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "inventory.json"
            target.write_text("preserve")
            with patch.object(DIAGNOSTIC.sys, "argv", [str(SOURCE), "--output", str(target)]), \
                 patch.object(DIAGNOSTIC, "inspect") as inspect:
                with self.assertRaises(FileExistsError):
                    DIAGNOSTIC.main()
            inspect.assert_not_called()
            self.assertEqual(target.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()

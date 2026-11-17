"""Offline checks for raw-data preservation and interrupted-download handling."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.download_data import WORKBOOK, download


def archive_bytes(payload=b"synthetic workbook bytes for transfer tests only"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(WORKBOOK, payload)
    return stream.getvalue()


class DownloadTests(unittest.TestCase):
    def test_archive_extracts_records_hashes_and_reruns_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "online_retail.zip").write_bytes(archive_bytes())
            with patch("scripts.download_data.urllib.request.urlopen", side_effect=AssertionError("Network must not be used")):
                metadata = download(output)
                second_run = download(output)
            self.assertEqual(metadata, second_run)
            self.assertTrue((output / WORKBOOK).is_file())
            stored = json.loads((output / "source_metadata.json").read_text())
            self.assertEqual(len(stored["files"]), 2)
            self.assertTrue(all(len(record["sha256"]) == 64 for record in stored["files"]))

    def test_workbook_changed_after_registration_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "online_retail.zip").write_bytes(archive_bytes())
            download(output)
            (output / WORKBOOK).write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "Raw data changed"):
                download(output)
            self.assertEqual((output / WORKBOOK).read_bytes(), b"changed")

    def test_unregistered_conflicting_workbook_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "online_retail.zip").write_bytes(archive_bytes())
            (output / WORKBOOK).write_bytes(b"keep this existing file")
            with self.assertRaisesRegex(RuntimeError, "not overwritten"):
                download(output)
            self.assertEqual((output / WORKBOOK).read_bytes(), b"keep this existing file")

    def test_invalid_download_is_removed_and_not_registered(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("scripts.download_data.urllib.request.urlopen", return_value=io.BytesIO(b"<html>server error</html>")):
                with self.assertRaisesRegex(RuntimeError, "valid ZIP"):
                    download(output)
            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

"""Download the official UCI archive without modifying existing raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
WORKBOOK = "Online Retail.xlsx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "online_retail.zip"
    workbook_path = output_dir / WORKBOOK
    metadata_path = output_dir / "source_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for record in metadata["files"]:
            path = output_dir / record["name"]
            if not path.is_file() or sha256(path) != record["sha256"]:
                raise RuntimeError(f"Raw data changed or missing: {path}. Restore it before rerunning.")
        return metadata

    if not archive_path.exists():
        temporary = output_dir / "online_retail.zip.download"
        request = urllib.request.Request(URL, headers={"User-Agent": "DataMiningCourseProject/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as target:
                shutil.copyfileobj(response, target)
            if not zipfile.is_zipfile(temporary):
                raise RuntimeError("The server did not return a valid ZIP archive.")
            temporary.replace(archive_path)
        finally:
            temporary.unlink(missing_ok=True)

    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist() if Path(m.filename).name == WORKBOOK]
        if len(members) != 1:
            raise RuntimeError("The official archive must contain exactly one expected workbook.")
        member = members[0]
        if workbook_path.exists():
            with archive.open(member) as source:
                archived_hash = hashlib.file_digest(source, "sha256").hexdigest()
            if archived_hash != sha256(workbook_path):
                raise RuntimeError("Existing raw workbook differs from the official archive; it was not overwritten.")
        else:
            temporary_workbook = output_dir / (WORKBOOK + ".download")
            try:
                with archive.open(member) as source, temporary_workbook.open("wb") as target:
                    shutil.copyfileobj(source, target)
                temporary_workbook.replace(workbook_path)
            finally:
                temporary_workbook.unlink(missing_ok=True)

    metadata = {
        "dataset": "UCI Online Retail",
        "dataset_id": 352,
        "landing_page": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "download_url": URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "license": "CC BY 4.0",
        "citation": "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33",
        "files": [
            {"name": p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in (archive_path, workbook_path)
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    try:
        metadata = download(args.output_dir.resolve())
    except (OSError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Download could not finish: {error}\nRaw files were not overwritten. Check network access and retry.\n")
    print(json.dumps({"dataset": metadata["dataset"], "output_dir": str(args.output_dir.resolve()), "files": metadata["files"]}, indent=2))


if __name__ == "__main__":
    main()

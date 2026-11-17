"""Record the actual Python environment without claiming packages are installed."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ["pandas", "numpy", "scikit-learn", "mlxtend", "matplotlib", "seaborn", "openpyxl"]


def main() -> None:
    packages = {}
    for package in PACKAGES:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    weka_jar = Path(os.environ.get("WEKA_JAR", "D:/Weka-3-8-7/weka.jar"))
    java_executable = Path(os.environ.get("JAVA_EXE", "D:/java 25/bin/java.exe"))
    python_model_ready = all(packages[name] is not None for name in ["pandas", "numpy", "scikit-learn", "mlxtend"])
    weka_model_ready = weka_jar.is_file() and java_executable.is_file()
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
        "ready": all(value is not None for value in packages.values()),
        "raw_audit_ready": all(packages[name] is not None for name in ["pandas", "numpy", "openpyxl"]),
        "sklearn_mlxtend_ready": python_model_ready,
        "weka_modeling_ready": weka_model_ready,
        "modeling_ready": python_model_ready or weka_model_ready,
        "modeling_backend_used": "Weka 3.8.7 Java bridge" if weka_model_ready else None,
    }
    output = ROOT / "results" / "tables" / "environment.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

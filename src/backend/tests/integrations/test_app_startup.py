import os
from pathlib import Path
import subprocess
import sys


def test_worker_imports_do_not_replace_prepared_examples(tmp_path):
    app_dir = Path(__file__).resolve().parents[2] / "app"
    examples = tmp_path / "examples"
    env = {
        **os.environ,
        "ACC_EXAMPLES_DIR": str(examples),
        "ACC_DATA_DIR": str(tmp_path / "data"),
        "ACC_LOG_DIR": str(tmp_path / "logs"),
    }

    subprocess.run([sys.executable, "main.py"], cwd=app_dir, env=env, check=True, timeout=30)
    assert (examples / "phenols" / "propofol.fw2.cif").is_file()
    marker = examples / "already-prepared"
    marker.write_text("shared example directory")

    subprocess.run(
        [sys.executable, "-c", "import main; main.create_app()"],
        cwd=app_dir, env=env, check=True, timeout=30,
    )

    assert marker.read_text() == "shared example directory"

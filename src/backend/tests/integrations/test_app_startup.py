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

    # Computations that a former process did not finish, of a guest and of a user, and
    # a finished one.
    data = tmp_path / "data"
    interrupted = [
        data / "guest" / "computations" / "comp-1" / "charges",
        data / "user" / "user-1" / "computations" / "comp-2" / "charges",
    ]
    finished = data / "guest" / "computations" / "comp-3" / "charges"
    for charges in (*interrupted, finished):
        charges.mkdir(parents=True)
    for charges in interrupted:
        (charges / ".calculating").write_text("")
    (finished / ".completed").write_text("")

    subprocess.run(
        [sys.executable, "-c", "import main; main.create_app()"],
        cwd=app_dir, env=env, check=True, timeout=30,
    )

    assert marker.read_text() == "shared example directory"
    for charges in interrupted:
        assert not (charges / ".calculating").exists()
        assert "interrupted" in (charges / ".failed").read_text()
    assert sorted(p.name for p in finished.iterdir()) == [".completed"]

# tests/test_quickstart_scripts.py

from pathlib import Path
import pytest


def _project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists() or (parent / "README.md").exists():
            return parent
    return Path.cwd()


def test_windows_bootstrap_script_exists_and_has_core_commands():
    """
    Ensure scripts/bootstrap_windows.ps1 exists and contains the expected
    core commands for venv setup and CLI usage.
    """
    root = _project_root()
    script = root / "scripts" / "bootstrap_windows.ps1"

    if not script.exists():
        pytest.skip("bootstrap_windows.ps1 not present; skipping Windows bootstrap test")

    text = script.read_text(encoding="utf-8").lower()

    assert "py -m venv .venv" in text
    assert ".\\.venv\\scripts\\activate.ps1" in text
    assert "pip install" in text
    assert "lattice-base-init" in text
    assert "lattice-base-validate" in text
    assert "lattice-base-test --complete" in text
    assert "lattice-base-mermaid" in text


def test_unix_bootstrap_script_exists_and_has_core_commands():
    """
    Ensure scripts/bootstrap_unix.sh exists and contains the expected
    core commands for venv setup and CLI usage.
    """
    root = _project_root()
    script = root / "scripts" / "bootstrap_unix.sh"

    if not script.exists():
        pytest.skip("bootstrap_unix.sh not present; skipping Unix bootstrap test")

    text = script.read_text(encoding="utf-8").lower()

    assert "python3 -m venv .venv" in text
    assert "source .venv/bin/activate" in text
    assert "pip install" in text
    assert "lattice-base-init" in text
    assert "lattice-base-validate" in text
    assert "lattice-base-test --complete" in text
    assert "lattice-base-mermaid" in text

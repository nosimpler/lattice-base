# tests/test_docs.py

from pathlib import Path
import pytest


def _project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists() or (parent / "README.md").exists():
            return parent
    return Path.cwd()


def _read_readme() -> str:
    root = _project_root()
    readme = root / "README.md"
    if not readme.exists():
        pytest.skip("README.md not present; doc tests cannot run")
    return readme.read_text(encoding="utf-8")


def test_readme_mentions_cli_tools():
    """
    lb-dx-readme:
    README.md should exist and mention the core CLI tools by name.
    """
    text = _read_readme()

    expected = [
        "lattice-base-init",
        "lattice-base-next",
        "lattice-base-validate",
        "lattice-base-test",
        "lattice-base-mermaid",
    ]
    for token in expected:
        assert token in text, f"Expected README.md to mention {token!r}"


def test_windows_quickstart_snippet_present():
    """
    lb-dx-quickstart-windows:
    README should include a Windows / PowerShell quickstart with venv and CLI usage.
    """
    text = _read_readme().lower()

    assert "windows" in text or "powershell" in text, "Expected README to mention Windows or PowerShell"

    # venv creation on Windows
    assert "py -m venv .venv" in text, "Expected Windows quickstart to use 'py -m venv .venv'"
    assert ".\\.venv\\scripts\\activate.ps1" in text, "Expected Windows quickstart to show Activate.ps1"

    # some lattice-base CLI usage
    assert "lattice-base-init" in text, "Expected Windows quickstart to show lattice-base-init"
    assert "lattice-base-next" in text, "Expected Windows quickstart to show lattice-base-next"
    assert "lattice-base-validate" in text, "Expected Windows quickstart to show lattice-base-validate"
    assert "lattice-base-test --complete" in text, "Expected Windows quickstart to show lattice-base-test --complete"
    assert "lattice-base-mermaid" in text, "Expected Windows quickstart to show lattice-base-mermaid"


def test_linux_quickstart_snippet_present():
    """
    lb-dx-quickstart-linux:
    README should include a Linux/macOS quickstart with venv and CLI usage.
    """
    text = _read_readme().lower()

    assert "linux" in text or "macos" in text, "Expected README to mention Linux or macOS"

    # venv creation on Linux/macOS
    assert "python3 -m venv .venv" in text, "Expected Linux quickstart to use 'python3 -m venv .venv'"
    assert "source .venv/bin/activate" in text, "Expected Linux quickstart to show 'source .venv/bin/activate'"

    # some lattice-base CLI usage
    assert "lattice-base-init" in text, "Expected Linux quickstart to show lattice-base-init"
    assert "lattice-base-next" in text, "Expected Linux quickstart to show lattice-base-next"
    assert "lattice-base-validate" in text, "Expected Linux quickstart to show lattice-base-validate"
    assert "lattice-base-test --complete" in text, "Expected Linux quickstart to show lattice-base-test --complete"
    assert "lattice-base-mermaid" in text, "Expected Linux quickstart to show lattice-base-mermaid"

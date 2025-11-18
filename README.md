# lattice-base

A lightweight, testable project-lattice framework for organizing and validating development tasks, dependencies, and tests.  
Developed and maintained by **Robert Law <nosimpler@gmail.com>**.  
Licensed under **LGPL-3.0**.

---

## 🧩 Overview

`lattice-base` provides a minimal YAML-backed project lattice model.  
It lets you treat a software or research project as a directed acyclic graph (DAG) of tasks — each with dependencies, tests, and states.

**Key features:**
- Tasks form a dependency lattice.
- `lattice-base-test --complete` runs all testable tasks, updating statuses.
- `lattice-base-mermaid` generates live diagrams (for GitHub or CI visibility).
- Designed for modular integration with higher-level orchestration tools.

---

## ⚙️ Quickstart (for your project)

### Linux / macOS

```bash
# From your project repo root
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install git+https://github.com/nosimpler/lattice-base.git

# Initialize, validate, and test
lattice-base-init --repo . --id myproj --name "My Project"
lattice-base-next --repo .
lattice-base-validate --repo .
lattice-base-test --complete
lattice-base-mermaid --repo . > lattice.mmd
```

### Windows (PowerShell)

```powershell
# From your project repo root
py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install git+https://github.com/nosimpler/lattice-base.git

# Initialize, validate, and test
lattice-base-init --repo . --id myproj --name "My Project"
lattice-base-next --repo .
lattice-base-validate --repo .
lattice-base-test --complete
lattice-base-mermaid --repo . > lattice.mmd
```

> ⚠️ **Troubleshooting (Windows execution policy)**  
> If PowerShell refuses to run the activation script due to execution policy, temporarily relax it for this session only:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
> ```

---

## ⚡️ Optional Bootstrap Scripts

If you prefer a single command to set everything up, you can use the provided bootstrap scripts:

### Windows

```powershell
# From your project repo root (only do this if you trust the script)
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_windows.ps1
```

### Linux / macOS

```bash
bash scripts/bootstrap_unix.sh
```

Both scripts will:
- Create a venv
- Install `lattice-base`
- Initialize and validate a lattice
- Run `lattice-base-test --complete`
- Generate a `lattice.mmd` diagram

---

## 🧠 Developing lattice-base itself

If you want to work on lattice-base itself:

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .[dev]

pytest
lattice-base-test --complete
```

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e .[dev]

pytest
lattice-base-test --complete
```

---

## 📈 Example: lattice-base project lattice

```mermaid
%%{init: {'theme': 'default', 'themeVariables': { 'fontSize': '18px' }, 'flowchart': { 'width':100, wrap': 'true', curve': 'linear', 'nodeSpacing': 100, 'rankSpacing': 120 }}}%%
graph TD
  epic-core["Core lattice model & I/O"]
  lb-core-model("Pydantic lattice model")
  lb-core-io("YAML load/save helpers")
  lb-core-validation("Basic validation semantics")
  epic-graph["Graph reasoning & analysis"]
  lb-graph-ready("Ready task computation")
  lb-graph-toposort("Topological sort <br> & cycle detection")
  epic-cli["CLI suite"]
  lb-cli-init("lattice-base-init")
  lb-cli-next("lattice-base-next")
  lb-cli-validate("lattice-base-validate")
  lb-cli-mermaid("lattice-base-mermaid")
  lb-cli-test("lattice-base-test CLI")
  epic-dx["Documentation & DX"]
  lb-dx-readme("Core README & examples")
  lb-dx-quickstart-windows("Windows quickstart")
  lb-dx-quickstart-linux("Linux/macOS quickstart")
  lb-dx-bootstrap-scripts("Bootstrap scripts for user repos")
  epic-future["Future features & lattice semantics"]
  lb-completion-enforcement("Distinguished completion <br> node enforcement")
  lb-code-markers("Code-block markers by task id")
  lb-bug-localization("Bug localization <br> via task markers")
  complete-lattice-base-v0((("lattice-base v0 completion")))
  lb-core-model --> lb-core-io
  lb-core-model --> lb-core-validation
  lb-core-io --> lb-core-validation
  lb-core-model --> lb-graph-ready
  lb-core-model --> lb-graph-toposort
  lb-core-model --> lb-cli-init
  lb-core-io --> lb-cli-init
  lb-core-model --> lb-cli-next
  lb-graph-ready --> lb-cli-next
  lb-core-validation --> lb-cli-validate
  lb-graph-toposort --> lb-cli-validate
  lb-core-model --> lb-cli-mermaid
  lb-graph-ready --> lb-cli-mermaid
  lb-core-model --> lb-cli-test
  lb-core-io --> lb-cli-test
  lb-cli-init --> lb-dx-readme
  lb-cli-next --> lb-dx-readme
  lb-cli-validate --> lb-dx-readme
  lb-cli-mermaid --> lb-dx-readme
  lb-dx-readme --> lb-dx-quickstart-windows
  lb-dx-readme --> lb-dx-quickstart-linux
  lb-dx-readme --> lb-dx-bootstrap-scripts
  lb-dx-quickstart-windows --> lb-dx-bootstrap-scripts
  lb-dx-quickstart-linux --> lb-dx-bootstrap-scripts
  lb-core-model --> lb-completion-enforcement
  lb-cli-validate --> lb-completion-enforcement
  lb-core-model --> lb-code-markers
  lb-code-markers --> lb-bug-localization
  lb-core-model --> complete-lattice-base-v0
  lb-core-io --> complete-lattice-base-v0
  lb-core-validation --> complete-lattice-base-v0
  lb-graph-ready --> complete-lattice-base-v0
  lb-graph-toposort --> complete-lattice-base-v0
  lb-cli-init --> complete-lattice-base-v0
  lb-cli-next --> complete-lattice-base-v0
  lb-cli-validate --> complete-lattice-base-v0
  lb-cli-mermaid --> complete-lattice-base-v0
  lb-dx-readme --> complete-lattice-base-v0

%% status-based styling (optional, adjust in your docs if desired)
classDef done fill:#bbf,stroke:#000;
classDef inprogress fill:#ffd,stroke:#000;
classDef planned fill:#dfd,stroke:#000;
classDef blocked fill:#fbb,stroke:#000;
class lb-core-model done;
class lb-core-io done;
class lb-core-validation done;
class lb-graph-ready done;
class lb-graph-toposort done;
class lb-cli-init done;
class lb-cli-next done;
class lb-cli-validate done;
class lb-cli-mermaid done;
class lb-cli-test done;
class lb-dx-readme done;
class lb-dx-quickstart-windows done;
class lb-dx-quickstart-linux done;
class lb-dx-bootstrap-scripts done;
class complete-lattice-base-v0 done;
```



You can generate this diagram automatically for your project:
```bash
lattice-base-mermaid --repo . > lattice.mmd
```

---

## 🧪 Testing

Run all tests:

```bash
pytest
lattice-base-test --complete
```

The latter will execute all CLI-defined task tests from your `project.yaml` and mark tasks as done or revert them as needed.

---

For full details of the lattice YAML format, see [docs/spec.md](docs/spec.md).

---

_LGPL-3.0 © 2025 Robert Law <nosimpler@gmail.com>_

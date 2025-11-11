param(
    [string]$ProjectId = "myproj",
    [string]$ProjectName = "My Project"
)

# Create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install "lattice-base @ git+https://github.com/your-user/lattice-base.git"

# Initialize a new lattice for this repo
lattice-base-init --repo . --id $ProjectId --name $ProjectName

# Sanity check the lattice and reconcile test status
lattice-base-validate --repo .
lattice-base-test --complete

# Emit a Mermaid diagram of the lattice
lattice-base-mermaid --repo . > lattice.mmd

#!/bin/zsh
# macOS launcher for the Route Checker (double-click in Finder to run).
# Equivalent of Start.bat / "Route Checker starten.lnk", which are Windows-only
# (a .bat needs cmd.exe, a .lnk is a Windows shortcut binary - neither works on macOS).

cd "$(dirname "$0")"

VENV_DIR=".venv"

# Set up a local virtual environment on first run. This is needed because macOS's
# Homebrew Python refuses global "pip install" (PEP 668, "externally-managed-environment").
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "Setting up Python environment (first run only) ..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python3" -c "import pandas, shapely" >/dev/null 2>&1; then
    echo "Installing required Python packages (pandas, shapely) ..."
    "$VENV_DIR/bin/pip" install --quiet pandas shapely
    echo
fi

"$VENV_DIR/bin/python3" main.py

echo
read "?Press Enter to close this window..."

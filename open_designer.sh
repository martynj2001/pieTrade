#!/usr/bin/env bash
# Opens Qt Designer (PySide6) for the pyTrade project using its Anaconda environment.
# Works from a terminal AND from a desktop launcher (no terminal).

# If started with "sh open_designer.sh", re-run under bash.
if [ -z "$BASH_VERSION" ]; then
    exec bash "$0" "$@"
fi

# ---- EDIT THIS: the name of your conda environment ----------------------
CONDA_ENV="piTrade"
# --------------------------------------------------------------------------

PROJECT_DIR="/home/martyn/pieTrade"
UI_FILE="$PROJECT_DIR/pyTrade_GUI_v2.ui"
LOG_FILE="/tmp/pyTrade_designer.log"

# Record everything to a log so desktop launches can be diagnosed
exec >>"$LOG_FILE" 2>&1
echo "=== $(date) : starting ==="

fail() {
    echo "ERROR: $1"
    # No terminal on a desktop launch, so show a pop-up instead
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "pyTrade Designer failed" "$1 (see $LOG_FILE)"
    fi
    exit 1
}

cd "$PROJECT_DIR" || fail "Cannot find $PROJECT_DIR"

# Find the conda environment folder directly - no 'conda activate' needed
ENV_DIR=""
for base in "$HOME/anaconda3" "$HOME/miniconda3" "$HOME/miniforge3" \
            "$HOME/mambaforge" "/opt/anaconda3" "/opt/miniconda3" "/opt/conda"; do
    if [ -d "$base/envs/$CONDA_ENV" ]; then
        ENV_DIR="$base/envs/$CONDA_ENV"
        break
    fi
done
[ -n "$ENV_DIR" ] || fail "Conda environment '$CONDA_ENV' not found"

# Equivalent of activating the environment
export CONDA_PREFIX="$ENV_DIR"
export CONDA_DEFAULT_ENV="$CONDA_ENV"
export PATH="$ENV_DIR/bin:$PATH"

echo "Using Python: $(which python)"

DESIGNER="$ENV_DIR/bin/pyside6-designer"
[ -x "$DESIGNER" ] || fail "pyside6-designer not found in '$CONDA_ENV' (pip install PySide6)"

if [ -f "$UI_FILE" ]; then
    echo "Opening $UI_FILE"
    nohup "$DESIGNER" "$UI_FILE" >>"$LOG_FILE" 2>&1 &
else
    echo "UI file not found - opening Designer empty"
    nohup "$DESIGNER" >>"$LOG_FILE" 2>&1 &
fi
echo "Designer launched (pid $!)"
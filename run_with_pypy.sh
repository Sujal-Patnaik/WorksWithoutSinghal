#!/usr/bin/env sh
set -eu

ACTION="all"
SKIP_INSTALL=0
PYPY_EXE="${PYPY_EXE:-}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        build|run|all|test|tune|compare|plot)
            ACTION="$1"
            ;;
        --skip-install)
            SKIP_INSTALL=1
            ;;
        --pypy-exe)
            shift
            if [ "$#" -eq 0 ]; then
                echo "ERROR: --pypy-exe requires a value" >&2
                exit 1
            fi
            PYPY_EXE="$1"
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            echo "Usage: ./run_with_pypy.sh [build|run|all|test|tune|compare|plot] [--skip-install] [--pypy-exe PATH]" >&2
            exit 1
            ;;
    esac
    shift
done

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="$REPO_ROOT/.venv-pypy"

resolve_pypy_exe() {
    if [ -n "$PYPY_EXE" ]; then
        if [ -x "$PYPY_EXE" ]; then
            printf '%s\n' "$PYPY_EXE"
            return
        fi
        echo "ERROR: Provided PyPy executable is not executable: $PYPY_EXE" >&2
        exit 1
    fi

    if command -v pypy3 >/dev/null 2>&1; then
        command -v pypy3
        return
    fi
    if command -v pypy >/dev/null 2>&1; then
        command -v pypy
        return
    fi

    echo "ERROR: Could not find pypy3/pypy. Set PYPY_EXE or install PyPy." >&2
    exit 1
}

resolve_venv_pypy() {
    if [ -x "$VENV_DIR/bin/pypy3" ]; then
        printf '%s\n' "$VENV_DIR/bin/pypy3"
        return
    fi
    if [ -x "$VENV_DIR/bin/pypy" ]; then
        printf '%s\n' "$VENV_DIR/bin/pypy"
        return
    fi
    if [ -x "$VENV_DIR/Scripts/pypy3.exe" ]; then
        printf '%s\n' "$VENV_DIR/Scripts/pypy3.exe"
        return
    fi
    if [ -x "$VENV_DIR/Scripts/pypy.exe" ]; then
        printf '%s\n' "$VENV_DIR/Scripts/pypy.exe"
        return
    fi

    echo "ERROR: Could not find PyPy inside $VENV_DIR. Rebuild with PyPy." >&2
    exit 1
}

cd "$REPO_ROOT"

echo "[INFO] Repository root: $REPO_ROOT"
echo "[INFO] Action:          $ACTION"

if [ "$ACTION" = "build" ] || [ "$ACTION" = "all" ]; then
    HOST_PYPY=$(resolve_pypy_exe)

    if [ ! -d "$VENV_DIR" ]; then
        echo "[BUILD] Creating PyPy virtual environment at $VENV_DIR"
        "$HOST_PYPY" -m venv "$VENV_DIR"
    else
        echo "[BUILD] Reusing existing PyPy virtual environment at $VENV_DIR"
    fi

    VENV_PYPY=$(resolve_venv_pypy)

    if [ "$SKIP_INSTALL" -eq 0 ]; then
        echo "[BUILD] Upgrading pip tooling"
        "$VENV_PYPY" -m pip install --upgrade pip setuptools wheel

        if [ -f "$REPO_ROOT/requirements.txt" ]; then
            echo "[BUILD] Installing dependencies from requirements.txt"
            "$VENV_PYPY" -m pip install -r "$REPO_ROOT/requirements.txt"
        else
            echo "[BUILD] No requirements.txt found; skipping dependency install"
        fi
    else
        echo "[BUILD] Skip install enabled; skipping package installation"
    fi
fi

if [ "$ACTION" = "run" ] || [ "$ACTION" = "all" ] || [ "$ACTION" = "test" ] || [ "$ACTION" = "tune" ] || [ "$ACTION" = "compare" ] || [ "$ACTION" = "plot" ]; then
    if [ ! -d "$VENV_DIR" ]; then
        echo "ERROR: Virtual environment not found at $VENV_DIR. Run build or all first." >&2
        exit 1
    fi

    VENV_PYPY=$(resolve_venv_pypy)

    case "$ACTION" in
        run|all)
            echo "[RUN] Executing main.py"
            "$VENV_PYPY" "$REPO_ROOT/main.py"
            ;;
        test)
            echo "[TEST] Executing test_operators.py"
            "$VENV_PYPY" "$REPO_ROOT/test_operators.py"
            ;;
        tune)
            echo "[TUNE] Executing tune.py"
            "$VENV_PYPY" "$REPO_ROOT/tune.py"
            ;;
        compare)
            echo "[COMPARE] Executing experiments/compare_policies.py"
            "$VENV_PYPY" "$REPO_ROOT/experiments/compare_policies.py" --pypy-exe "$VENV_PYPY"
            ;;
        plot)
            echo "[PLOT] Executing experiments/plot_comparison.py"
            "$VENV_PYPY" "$REPO_ROOT/experiments/plot_comparison.py"
            ;;
    esac
fi

echo "[DONE] Completed action '$ACTION'."

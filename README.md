PyPy-only workflow

Environment policy
- Single virtual environment: `.venv-pypy`
- Runtime/interpreter target: PyPy only

Quick start

macOS/Linux
1. Build env + install deps
	`./run_with_pypy.sh build`
2. Run solver
	`./run_with_pypy.sh run`
3. Run tests
	`./run_with_pypy.sh test`
4. Tune
	`./run_with_pypy.sh tune`
5. Compare policies
	`./run_with_pypy.sh compare`
6. Plot comparison outputs
	`./run_with_pypy.sh plot`

Windows PowerShell
1. Build env + install deps
	`./run_with_pypy.ps1 -Action build`
2. Run solver
	`./run_with_pypy.ps1 -Action run`
3. Run tests
	`./run_with_pypy.ps1 -Action test`
4. Tune
	`./run_with_pypy.ps1 -Action tune`
5. Compare policies
	`./run_with_pypy.ps1 -Action compare`
6. Plot comparison outputs
	`./run_with_pypy.ps1 -Action plot`

If PyPy is not on PATH, pass an explicit executable path:
- macOS/Linux: `./run_with_pypy.sh build --pypy-exe /path/to/pypy3`
- Windows: `./run_with_pypy.ps1 -Action build -PyPyExe C:\path\to\pypy3.exe`

Compact benchmark (completed)

This project was benchmarked with a compact, reproducible setup for Roulette vs RL (bandit):

`./.venv-pypy/bin/python experiments/compare_policies.py --pypy-exe ./.venv-pypy/bin/pypy3 --instances-folder pdp_200 --max-instances 1 --seeds 3 --seed-start 41 --iterations 200 --stage1-iterations 200 --log-iterations --output-root results/comparison_pypy_rl_small`

Plot command used:

`./.venv-pypy/bin/python experiments/plot_comparison.py --output-root results/comparison_pypy_rl_small`

Quantitative results

Source: `results/comparison_pypy_rl_small/summary_aggregated.csv`

| Policy | Runs | Mean Distance | Std Distance | Mean Vehicles | Mean Global Cost | Mean Exec Time (s) |
|---|---:|---:|---:|---:|---:|---:|
| roulette | 3 | 2704.57 | 0.00 | 20 | 2704.57 | 5.5533 |
| bandit (RL) | 3 | 2704.57 | 0.00 | 20 | 2704.57 | 5.7133 |

Distance winner summary (`results/comparison_pypy_rl_small/distance_wins.csv`):
- roulette wins: 0
- bandit wins: 0
- ties: 1

Qualitative analysis
- For this compact setting and tested instance (`LC1_2_1.txt`), Roulette and Bandit converge to the exact same final solution quality.
- Variance is zero for distance across the tested seeds in both policies.
- Bandit shows a small runtime overhead (about 0.16s on average in this run), likely due to policy bookkeeping/exploration logic, while not improving final distance in this specific scenario.
- No unassigned requests in final reported runs.

Generated artifacts
- Raw run rows: `results/comparison_pypy_rl_small/summary_raw.csv`
- Aggregated metrics: `results/comparison_pypy_rl_small/summary_aggregated.csv`
- Distance wins: `results/comparison_pypy_rl_small/distance_wins.csv`
- Boxplot: `results/comparison_pypy_rl_small/plots/boxplot_final_distance.png`
- Wins bar chart: `results/comparison_pypy_rl_small/plots/wins_bar.png`
- Convergence curve: `results/comparison_pypy_rl_small/plots/convergence_LC1_2_1.png`

Troubleshooting

1) VS Code error: "The argument 'file' cannot be empty"
- Root cause: Python extension tried to run `-m pip list` with an invalid/empty interpreter path (common after stale or cross-OS virtual environments).
- Fix used in this repo:
  - Recreate/use native macOS `.venv-pypy`
  - Set absolute interpreter in `.vscode/settings.json`:
    - `"python.defaultInterpreterPath": "/Users/mac/Coding/Projects/WorksWithoutSinghal/.venv-pypy/bin/python"`
  - Keep `python.terminal.activateEnvironment` enabled
  - Reload VS Code window after updating interpreter

2) Repeated "command is waiting for input" notifications during long runs
- In this workload, this can be a false-positive from terminal notifications while the process is still printing logs.
- Mitigation:
  - Run one long compare command at a time (foreground)
  - Avoid launching duplicate background compares
  - Kill stale terminals if duplicated notifications continue


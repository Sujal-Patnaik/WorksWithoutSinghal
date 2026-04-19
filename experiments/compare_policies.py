import argparse
import csv
import glob
import os
import re
import subprocess
from statistics import mean, pstdev


RESULT_PATTERNS = {
    "instance": re.compile(r"^File Tested:\s*(.+)$"),
    "policy": re.compile(r"^Policy Mode:\s*(.+)$"),
    "seed": re.compile(r"^Seed:\s*(\d+)$"),
    "exec_time": re.compile(r"^Total Execution Time:\s*([0-9.]+)"),
    "vehicles": re.compile(r"^Vehicles Used:\s*([0-9]+)"),
    "distance": re.compile(r"^Total Distance:\s*([0-9.]+)"),
    "unassigned": re.compile(r"^Unassigned Requests:\s*([0-9]+)"),
    "global_cost": re.compile(r"^Global Cost:\s*([0-9.]+)"),
}


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_default_pypy_exe():
    candidates = [
        os.path.join(REPO_ROOT, ".venv-pypy", "bin", "pypy3"),
        os.path.join(REPO_ROOT, ".venv-pypy", "bin", "pypy"),
        os.path.join(REPO_ROOT, ".venv-pypy", "Scripts", "pypy3.exe"),
        os.path.join(REPO_ROOT, ".venv-pypy", "Scripts", "pypy.exe"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "Could not find PyPy in .venv-pypy. Build it first with run_with_pypy.sh/ps1."
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Run roulette vs bandit ALNS comparisons")
    parser.add_argument("--instances-folder", default="pdp_200")
    parser.add_argument("--max-instances", type=int, default=20)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--output-root", default=os.path.join("results", "comparison_runs"))
    parser.add_argument("--pypy-exe", default=None)
    parser.add_argument("--log-iterations", action="store_true")
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--stage1-iterations", type=int, default=3000)
    parser.add_argument("--bandit-alpha", type=float, default=0.8)
    parser.add_argument("--bandit-epsilon", type=float, default=0.05)
    return parser.parse_args()


def run_command(cmd):
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def run_experiments(args):
    policies = ["roulette", "bandit"]
    os.makedirs(args.output_root, exist_ok=True)
    main_script = os.path.join(REPO_ROOT, "main.py")

    for policy in policies:
        for run_idx in range(args.seeds):
            seed = args.seed_start + run_idx
            run_output = os.path.join(args.output_root, policy, f"seed_{seed}")
            os.makedirs(run_output, exist_ok=True)

            cmd = [
                args.pypy_exe,
                main_script,
                "--policy",
                policy,
                "--seed",
                str(seed),
                "--instances-folder",
                args.instances_folder,
                "--max-instances",
                str(args.max_instances),
                "--output-folder",
                run_output,
                "--iterations",
                str(args.iterations),
                "--stage1-iterations",
                str(args.stage1_iterations),
                "--bandit-alpha",
                str(args.bandit_alpha),
                "--bandit-epsilon",
                str(args.bandit_epsilon),
            ]
            if args.log_iterations:
                cmd.append("--log-iterations")

            run_command(cmd)


def parse_result_file(path):
    parsed = {
        "instance": None,
        "policy": None,
        "seed": None,
        "exec_time": None,
        "vehicles": None,
        "distance": None,
        "unassigned": None,
        "global_cost": None,
    }

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            for key, pattern in RESULT_PATTERNS.items():
                match = pattern.match(line)
                if not match:
                    continue
                value = match.group(1)
                if key in ("seed", "vehicles", "unassigned"):
                    parsed[key] = int(value)
                elif key in ("distance", "global_cost", "exec_time"):
                    parsed[key] = float(value)
                else:
                    parsed[key] = value
    return parsed


def collect_rows(output_root):
    rows = []
    txt_files = glob.glob(os.path.join(output_root, "**", "*_results.txt"), recursive=True)
    for txt in txt_files:
        data = parse_result_file(txt)
        if not data["instance"]:
            continue
        rows.append(data)
    return rows


def write_summary(rows, output_root):
    summary_path = os.path.join(output_root, "summary_raw.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "policy",
            "seed",
            "instance",
            "distance",
            "vehicles",
            "global_cost",
            "unassigned",
            "exec_time",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})

    grouped = {}
    for row in rows:
        key = (row["policy"], row["instance"])
        grouped.setdefault(key, []).append(row)

    agg_path = os.path.join(output_root, "summary_aggregated.csv")
    with open(agg_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "policy",
            "instance",
            "runs",
            "mean_distance",
            "std_distance",
            "mean_vehicles",
            "mean_global_cost",
            "mean_exec_time",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (policy, instance), values in sorted(grouped.items()):
            distances = [v["distance"] for v in values]
            vehicles = [v["vehicles"] for v in values]
            costs = [v["global_cost"] for v in values]
            runtimes = [v["exec_time"] for v in values]
            writer.writerow(
                {
                    "policy": policy,
                    "instance": instance,
                    "runs": len(values),
                    "mean_distance": mean(distances),
                    "std_distance": pstdev(distances) if len(distances) > 1 else 0.0,
                    "mean_vehicles": mean(vehicles),
                    "mean_global_cost": mean(costs),
                    "mean_exec_time": mean(runtimes),
                }
            )

    return summary_path, agg_path


def write_win_table(rows, output_root):
    by_instance = {}
    for row in rows:
        by_instance.setdefault(row["instance"], {}).setdefault(row["policy"], []).append(row["distance"])

    out_path = os.path.join(output_root, "distance_wins.csv")
    wins = {"roulette": 0, "bandit": 0, "tie": 0}

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["instance", "roulette_mean_distance", "bandit_mean_distance", "winner"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for instance in sorted(by_instance.keys()):
            roulette_vals = by_instance[instance].get("roulette", [])
            bandit_vals = by_instance[instance].get("bandit", [])
            if not roulette_vals or not bandit_vals:
                continue
            r_mean = mean(roulette_vals)
            b_mean = mean(bandit_vals)

            if abs(r_mean - b_mean) < 1e-9:
                winner = "tie"
            elif r_mean < b_mean:
                winner = "roulette"
            else:
                winner = "bandit"
            wins[winner] += 1

            writer.writerow(
                {
                    "instance": instance,
                    "roulette_mean_distance": r_mean,
                    "bandit_mean_distance": b_mean,
                    "winner": winner,
                }
            )

    print("Distance win summary:", wins)
    return out_path


def main():
    args = parse_args()
    if args.pypy_exe is None:
        args.pypy_exe = resolve_default_pypy_exe()
    run_experiments(args)

    rows = collect_rows(args.output_root)
    summary_path, agg_path = write_summary(rows, args.output_root)
    wins_path = write_win_table(rows, args.output_root)

    print("Wrote:", summary_path)
    print("Wrote:", agg_path)
    print("Wrote:", wins_path)


if __name__ == "__main__":
    main()

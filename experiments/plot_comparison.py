import argparse
import csv
import glob
import os
from collections import defaultdict
from statistics import mean


def parse_args():
    parser = argparse.ArgumentParser(description="Create comparison graphs from experiment outputs")
    parser.add_argument("--output-root", default=os.path.join("results", "comparison_runs"))
    parser.add_argument("--instance", default=None, help="Instance filename for convergence plot, e.g., LC1_2_1.txt")
    return parser.parse_args()


def load_summary_raw(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["distance"] = float(row["distance"])
            rows.append(row)
    return rows


def plot_boxplot_distance(rows, plot_dir):
    import matplotlib.pyplot as plt

    by_policy = defaultdict(list)
    for row in rows:
        by_policy[row["policy"]].append(row["distance"])

    policies = sorted(by_policy.keys())
    data = [by_policy[p] for p in policies]

    plt.figure(figsize=(8, 5))
    plt.boxplot(data, tick_labels=policies)
    plt.ylabel("Final Distance")
    plt.title("Final Distance Distribution by Policy")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    out = os.path.join(plot_dir, "boxplot_final_distance.png")
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def plot_wins(output_root, plot_dir):
    import matplotlib.pyplot as plt

    path = os.path.join(output_root, "distance_wins.csv")
    counts = {"roulette": 0, "bandit": 0, "tie": 0}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counts[row["winner"]] += 1

    labels = ["roulette", "bandit", "tie"]
    values = [counts[l] for l in labels]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color=["#4e79a7", "#f28e2b", "#9d9d9d"])
    plt.ylabel("Number of Instances")
    plt.title("Win/Tie/Loss by Mean Distance")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    out = os.path.join(plot_dir, "wins_bar.png")
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def choose_instance(output_root, requested_instance):
    if requested_instance:
        return requested_instance
    paths = glob.glob(os.path.join(output_root, "**", "*_iterations.csv"), recursive=True)
    if not paths:
        return None
    base = os.path.basename(paths[0])
    # expected format: INSTANCE_policy_seedX_iterations.csv
    parts = base.split("_")
    if len(parts) < 4:
        return None
    return "_".join(parts[0:3]) + ".txt"


def parse_iteration_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("stage") != "stage2":
                continue
            rows.append(
                {
                    "iteration": int(row["iteration"]),
                    "best_distance": float(row["best_distance"]),
                }
            )
    return rows


def collect_curves(output_root, policy, instance):
    curves = []
    instance_base = instance.replace(".txt", "")
    pattern = os.path.join(output_root, policy, "seed_*", f"{instance_base}_{policy}_seed*_iterations.csv")
    for path in glob.glob(pattern):
        curve_rows = parse_iteration_csv(path)
        if curve_rows:
            curves.append(curve_rows)

    if curves:
        return curves

    # Fallback: search all iteration logs and keep those starting with the instance base.
    fallback_pattern = os.path.join(output_root, policy, "seed_*", "*_iterations.csv")
    for path in glob.glob(fallback_pattern):
        if not os.path.basename(path).startswith(instance_base + "_"):
            continue
        curve_rows = parse_iteration_csv(path)
        if curve_rows:
            curves.append(curve_rows)
    return curves


def average_curve(curves):
    if not curves:
        return [], []
    by_iter = defaultdict(list)
    for curve in curves:
        for row in curve:
            by_iter[row["iteration"]].append(row["best_distance"])

    xs = sorted(by_iter.keys())
    ys = [mean(by_iter[x]) for x in xs]
    return xs, ys


def plot_convergence(output_root, plot_dir, instance):
    import matplotlib.pyplot as plt

    roulette_curves = collect_curves(output_root, "roulette", instance)
    bandit_curves = collect_curves(output_root, "bandit", instance)
    if not roulette_curves and not bandit_curves:
        return None

    rx, ry = average_curve(roulette_curves)
    bx, by = average_curve(bandit_curves)

    plt.figure(figsize=(9, 5))
    if rx:
        plt.plot(rx, ry, label="roulette", linewidth=2)
    if bx:
        plt.plot(bx, by, label="bandit", linewidth=2)
    plt.xlabel("Iteration")
    plt.ylabel("Best Distance (Stage 2)")
    plt.title(f"Convergence Comparison - {instance}")
    plt.legend()
    plt.grid(alpha=0.3, linestyle="--")

    out = os.path.join(plot_dir, f"convergence_{instance.replace('.txt', '')}.png")
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def main():
    args = parse_args()

    try:
        import matplotlib  # noqa: F401
    except Exception:
        print("matplotlib is required. Install it in .venv-pypy (for example via run_with_pypy.sh/ps1 build).")
        return

    summary_raw = os.path.join(args.output_root, "summary_raw.csv")
    if not os.path.exists(summary_raw):
        print("summary_raw.csv not found. Run experiments/compare_policies.py first.")
        return

    rows = load_summary_raw(summary_raw)

    plot_dir = os.path.join(args.output_root, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    out1 = plot_boxplot_distance(rows, plot_dir)
    out2 = plot_wins(args.output_root, plot_dir)

    instance = choose_instance(args.output_root, args.instance)
    out3 = None
    if instance:
        out3 = plot_convergence(args.output_root, plot_dir, instance)

    print("Wrote:", out1)
    print("Wrote:", out2)
    if out3:
        print("Wrote:", out3)


if __name__ == "__main__":
    main()

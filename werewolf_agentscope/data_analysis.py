"""
data_analysis.py – Phân tích dữ liệu game như một hệ thống dữ liệu.

Phương pháp:
  1. Game log → Dataset (tabular, mỗi round = 1 record)
  2. Feature engineering từ hành vi agent
  3. Correlation: hành vi nào liên quan đến kết cục đúng?
  4. Feature importance: đặc trưng nào dự đoán vote đúng tốt nhất?

Gắn với môn Nền tảng Dữ liệu:
  - ETL: Extract (JSON) → Transform (feature) → Load (analysis)
  - Descriptive statistics
  - Correlation analysis (Pearson / Point-biserial)
  - Simple feature ranking
"""

import json
import os
import math
from glob import glob
from collections import defaultdict

LOG_DIR = os.path.join(os.path.dirname(__file__), "data", "logs")


# ══════════════════════════════════════════════════════════════════════
# 1. ETL – Extract Transform Load
# ══════════════════════════════════════════════════════════════════════
def extract_games(log_dir: str = LOG_DIR) -> list[dict]:
    """Extract: đọc tất cả file game_*.json."""
    files = sorted(glob(os.path.join(log_dir, "game_*.json")))
    games = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            games.append(json.load(fp))
    return games


def transform_to_dataset(games: list[dict]) -> list[dict]:
    """
    Transform: mỗi round → 1 record với các features:

    Features (X):
      - n_accusers       : số người bị tố cáo trong thảo luận
      - vote_consensus   : mức độ đồng thuận vote (max_votes / total_voters)
      - night_kill_exist : đêm đó có ai chết không (0/1)
      - seer_checked     : đêm đó Seer có check không (0/1)
      - doctor_saved     : đêm đó Doctor có cứu không (0/1)

    Label (y):
      - correct_vote     : vote ngày đó có loại đúng Ma Sói không (0/1)
      - result_villager  : ván đó dân có thắng không (0/1)
    """
    dataset = []
    for game in games:
        result = game.get("result", "unknown")
        result_villager = 1 if result == "villager" else 0

        for r in game.get("rounds", []):
            night = r.get("night", {})
            day   = r.get("day", {})
            if not day:
                continue

            # Features từ đêm
            night_kill_exist = 1 if night.get("killed") else 0
            seer_checked     = 1 if night.get("seer_check") else 0
            doctor_saved     = 1 if night.get("doctor_save") else 0

            # Features từ ngày
            ballots    = day.get("ballots", {})
            tally      = day.get("tally", {})
            n_voters   = len(ballots)
            max_votes  = max(tally.values()) if tally else 0
            vote_consensus = round(max_votes / n_voters, 3) if n_voters else 0

            # Số unique targets bị vote (đa dạng vs tập trung)
            unique_targets = len(set(ballots.values()))
            vote_diversity = round(unique_targets / n_voters, 3) if n_voters else 0

            # Labels
            correct_vote = 1 if day.get("correct_vote") else 0

            dataset.append({
                # Metadata
                "game_id":         game.get("game_id", ""),
                "round":           r.get("round", 0),
                # Features
                "night_kill":      night_kill_exist,
                "seer_checked":    seer_checked,
                "doctor_saved":    doctor_saved,
                "vote_consensus":  vote_consensus,
                "vote_diversity":  vote_diversity,
                "n_voters":        n_voters,
                # Labels
                "correct_vote":    correct_vote,
                "result_villager": result_villager,
            })

    return dataset


# ══════════════════════════════════════════════════════════════════════
# 2. Descriptive Statistics
# ══════════════════════════════════════════════════════════════════════
def describe(dataset: list[dict], col: str) -> dict:
    """Tính thống kê mô tả cho một cột số."""
    vals = [r[col] for r in dataset if col in r]
    if not vals:
        return {}
    n    = len(vals)
    mean = sum(vals) / n
    var  = sum((v - mean) ** 2 for v in vals) / n
    std  = math.sqrt(var)
    return {
        "n":    n,
        "mean": round(mean, 4),
        "std":  round(std, 4),
        "min":  min(vals),
        "max":  max(vals),
    }


# ══════════════════════════════════════════════════════════════════════
# 3. Correlation Analysis
# ══════════════════════════════════════════════════════════════════════
def pearson_correlation(x: list[float], y: list[float]) -> float:
    """Tính hệ số tương quan Pearson giữa 2 biến."""
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num    = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den_x  = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y  = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 4)


def compute_correlations(dataset: list[dict]) -> dict:
    """
    Tính correlation của từng feature với correct_vote và result_villager.
    Kết quả dùng để chọn feature quan trọng.
    """
    features = ["night_kill", "seer_checked", "doctor_saved",
                "vote_consensus", "vote_diversity"]
    targets  = ["correct_vote", "result_villager"]
    corrs    = {}

    for feat in features:
        corrs[feat] = {}
        x = [r[feat] for r in dataset]
        for tgt in targets:
            y = [r[tgt] for r in dataset]
            corrs[feat][tgt] = pearson_correlation(x, y)

    return corrs


# ══════════════════════════════════════════════════════════════════════
# 4. Feature Importance (Information Gain đơn giản)
# ══════════════════════════════════════════════════════════════════════
def entropy(labels: list[int]) -> float:
    """Tính entropy của một tập nhãn nhị phân."""
    n = len(labels)
    if n == 0:
        return 0.0
    p = sum(labels) / n
    if p == 0 or p == 1:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def information_gain(dataset: list[dict], feature: str, target: str) -> float:
    """
    Tính Information Gain của feature đối với target (binary).
    IG = H(parent) - weighted H(children)
    Dùng median làm ngưỡng phân chia.
    """
    parent_labels = [r[target] for r in dataset]
    h_parent = entropy(parent_labels)

    vals = sorted(set(r[feature] for r in dataset))
    if len(vals) < 2:
        return 0.0

    # Ngưỡng = median
    threshold = vals[len(vals) // 2]
    left  = [r[target] for r in dataset if r[feature] <= threshold]
    right = [r[target] for r in dataset if r[feature] >  threshold]
    n     = len(dataset)

    h_children = (
        len(left)  / n * entropy(left)  +
        len(right) / n * entropy(right)
    )
    return round(h_parent - h_children, 4)


def feature_importance(dataset: list[dict], target: str = "correct_vote") -> dict:
    """Xếp hạng feature theo Information Gain."""
    features = ["night_kill", "seer_checked", "doctor_saved",
                "vote_consensus", "vote_diversity"]
    ig = {f: information_gain(dataset, f, target) for f in features}
    return dict(sorted(ig.items(), key=lambda x: -x[1]))


# ══════════════════════════════════════════════════════════════════════
# 5. In báo cáo đầy đủ
# ══════════════════════════════════════════════════════════════════════
def _bar(val: float, max_val: float = 1.0, width: int = 20) -> str:
    filled = int(abs(val) / max(abs(max_val), 1e-9) * width)
    sign   = "+" if val >= 0 else "-"
    return sign + "#" * filled + "." * (width - filled)


def print_analysis(games: list[dict]) -> None:
    if not games:
        print("[DataAnalysis] Chua co du lieu. Chay run_game() truoc.")
        return

    dataset = transform_to_dataset(games)
    n_records = len(dataset)
    n_games   = len(games)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  PHAN TICH DU LIEU GAME  |  {n_games} van  |  {n_records} records")
    print(sep)

    # ── ETL summary ───────────────────────────────────────────────────
    print(f"\n[ETL] Game log -> Dataset")
    print(f"  Input : {n_games} file JSON tu data/logs/")
    print(f"  Output: {n_records} records (moi round = 1 record)")
    print(f"  Fields: night_kill, seer_checked, doctor_saved, "
          f"vote_consensus, vote_diversity")

    # ── Descriptive stats ─────────────────────────────────────────────
    print(f"\n[1] THONG KE MO TA (Descriptive Statistics)")
    print(f"  {'Feature':<20} {'Mean':>8} {'Std':>8} {'Min':>6} {'Max':>6}")
    print(f"  {'-'*52}")
    for col in ["vote_consensus", "vote_diversity", "night_kill",
                "seer_checked", "correct_vote", "result_villager"]:
        d = describe(dataset, col)
        if d:
            print(f"  {col:<20} {d['mean']:>8.3f} {d['std']:>8.3f} "
                  f"{d['min']:>6} {d['max']:>6}")

    # ── Correlation ───────────────────────────────────────────────────
    print(f"\n[2] CORRELATION (Pearson) voi correct_vote va result_villager")
    corrs = compute_correlations(dataset)
    print(f"  {'Feature':<20} {'vs correct_vote':>18} {'vs result_villager':>20}")
    print(f"  {'-'*60}")
    for feat, vals in corrs.items():
        cv  = vals.get("correct_vote", 0)
        rv  = vals.get("result_villager", 0)
        bar = _bar(cv, max_val=0.5)
        print(f"  {feat:<20} {cv:>+8.4f} {bar}  {rv:>+8.4f}")

    print(f"\n  Giai thich: r > 0.2 la tuong quan co y nghia thuc te")

    # ── Feature Importance ────────────────────────────────────────────
    print(f"\n[3] FEATURE IMPORTANCE (Information Gain voi correct_vote)")
    fi = feature_importance(dataset, "correct_vote")
    max_ig = max(fi.values()) if fi else 1.0
    print(f"  {'Feature':<20} {'IG':>8}  {'Bar':>22}")
    print(f"  {'-'*55}")
    for feat, ig in fi.items():
        bar = "#" * int(ig / max(max_ig, 1e-9) * 20)
        print(f"  {feat:<20} {ig:>8.4f}  [{bar:<20}]")

    # ── Cross-tab: night_kill vs correct_vote ─────────────────────────
    print(f"\n[4] CROSS-TAB: co nguoi chet dem (night_kill) vs vote dung")
    for nk in [0, 1]:
        subset = [r for r in dataset if r["night_kill"] == nk]
        if not subset:
            continue
        cv_rate = sum(r["correct_vote"] for r in subset) / len(subset) * 100
        label = "Co nguoi chet" if nk else "Dem yen binh"
        print(f"  {label:<20}: vote dung {cv_rate:.1f}%  (n={len(subset)})")

    print(f"\n[5] NHAN XET TONG HOP")
    # Tự sinh nhận xét từ data
    corrs_cv = {f: corrs[f]["correct_vote"] for f in corrs}
    best_feat = max(corrs_cv, key=lambda f: abs(corrs_cv[f]))
    best_r    = corrs_cv[best_feat]
    print(f"  > Feature tuong quan manh nhat voi vote dung: "
          f"'{best_feat}' (r={best_r:+.4f})")

    fi_best = list(fi.keys())[0]
    print(f"  > Feature co Information Gain cao nhat: '{fi_best}' (IG={fi[fi_best]:.4f})")

    vil_win_rate = sum(r["result_villager"] for r in dataset) / n_records * 100
    cv_rate_all  = sum(r["correct_vote"] for r in dataset) / n_records * 100
    print(f"  > Ti le dan thang tren tap du lieu: {vil_win_rate:.1f}%")
    print(f"  > Ti le vote dung tren tap du lieu: {cv_rate_all:.1f}%")
    print(f"\n{sep}\n")


if __name__ == "__main__":
    games = extract_games()
    print(f"[DataAnalysis] Doc {len(games)} van tu {LOG_DIR}")
    print_analysis(games)

"""
experiment.py – Thực nghiệm khoa học so sánh 3 loại agent.

Ba chế độ:
  "random"     – RandomAgent    : quyết định hoàn toàn ngẫu nhiên (baseline)
  "rule_based" – RuleBasedAgent : heuristic cứng, belief đơn giản
  "belief"     – BeliefAgent    : BeliefModel 3 chiều + SocialReasoning (hệ thống đề xuất)

Chỉ số so sánh:
  1. Tỉ lệ thắng của dân làng (%)
  2. Số vòng trung bình mỗi ván
  3. Hiệu quả bỏ phiếu – vote đúng Ma Sói (%)
  4. Tỉ lệ cứu thành công của Bác Sĩ (%)
  5. Độ chính xác Tiên Tri tìm Ma Sói (%)
"""

import random
import io
import contextlib
import sys
import os
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))

from agents.random_agent     import RandomAgent
from agents.rule_based_agent import RuleBasedAgent
from agents.werewolf_agent   import WerewolfAgent
from agents.seer_agent       import SeerAgent
from agents.doctor_agent     import DoctorAgent
from agents.villager_agent   import VillagerAgent
from game.game_state  import GameState
from game.game_master import GameMaster
from game.logger      import GameLogger

# ── Cấu hình thực nghiệm ──────────────────────────────────────────────
EXP_CONFIG = {
    "num_players":    8,
    "num_werewolves": 2,
    "player_names":   ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Henry"],
    "n_games":        50,    # số ván mỗi chế độ
    "max_rounds":     10,
}


# ══════════════════════════════════════════════════════════════════════
# Factory: tạo agents theo mode
# ══════════════════════════════════════════════════════════════════════
def build_agents(names: list[str], assignment: dict[str, str], mode: str) -> dict:
    """
    mode: "random" | "rule_based" | "belief"
    Trả về dict {name: agent}.
    """
    wolf_names = [n for n, r in assignment.items() if r == "werewolf"]
    agents = {}

    for name, role in assignment.items():
        teammates = [w for w in wolf_names if w != name] if role == "werewolf" else []

        if mode == "random":
            agents[name] = RandomAgent(name, role, teammates)

        elif mode == "rule_based":
            agents[name] = RuleBasedAgent(name, role, teammates)

        else:  # "belief" – hệ thống đề xuất
            if role == "werewolf":
                agents[name] = WerewolfAgent(name, teammates)
            elif role == "seer":
                agents[name] = SeerAgent(name)
            elif role == "doctor":
                agents[name] = DoctorAgent(name)
            else:
                agents[name] = VillagerAgent(name)

    for agent in agents.values():
        agent.init_belief(names)

    return agents


# ══════════════════════════════════════════════════════════════════════
# Chạy 1 ván game
# ══════════════════════════════════════════════════════════════════════
def run_one_game(seed: int, mode: str, cfg: dict) -> dict:
    """
    Chạy 1 ván và trả về dict kết quả (không lưu file JSON).
    """
    random.seed(seed)
    names = cfg["player_names"][:cfg["num_players"]]
    n_wolves = cfg["num_werewolves"]

    roles = (
        ["werewolf"] * n_wolves + ["seer"] + ["doctor"]
        + ["villager"] * (len(names) - n_wolves - 2)
    )
    random.shuffle(roles)
    assignment = dict(zip(names, roles))

    agents = build_agents(names, assignment, mode)
    state  = GameState(players=names)
    gm     = GameMaster(agents, state)

    night_logs = []
    day_logs   = []
    winner     = None

    gm.announce_roles()

    for _ in range(cfg["max_rounds"]):
        state.next_round()
        night_log = gm.night_phase()
        night_logs.append(night_log)
        winner = gm.check_end()
        if winner:
            break
        day_log = gm.day_phase()
        day_logs.append(day_log)
        winner = gm.check_end()
        if winner:
            break

    if winner is None:
        winner = "draw"

    return {
        "mode":        mode,
        "seed":        seed,
        "result":      winner,
        "rounds":      state.round - 1,   # round thực tế đã chơi
        "night_logs":  night_logs,
        "day_logs":    day_logs,
    }


# ══════════════════════════════════════════════════════════════════════
# Tính metrics từ danh sách game results
# ══════════════════════════════════════════════════════════════════════
def compute_metrics(results: list[dict]) -> dict:
    total = len(results)
    if total == 0:
        return {}

    villager_wins = sum(1 for r in results if r["result"] == "villager")
    rounds_list   = [r["rounds"] for r in results]

    # Vote accuracy
    correct_votes = sum(
        1 for r in results
        for dl in r["day_logs"]
        if dl.get("day", {}).get("correct_vote") is True
    )
    total_votes = sum(len(r["day_logs"]) for r in results)

    # Doctor save rate
    saves_success = sum(
        1 for r in results
        for nl in r["night_logs"]
        if nl.get("night", {}).get("wolf_target") and
           nl["night"].get("wolf_target") == nl["night"].get("doctor_save")
    )
    total_nights_with_save = sum(
        1 for r in results
        for nl in r["night_logs"]
        if nl.get("night", {}).get("doctor_save") is not None
    )

    # Seer accuracy
    seer_wolf_found = sum(
        1 for r in results
        for nl in r["night_logs"]
        for t, res in nl.get("night", {}).get("seer_check", {}).items()
        if res == "werewolf"
    )
    seer_total_checks = sum(
        1 for r in results
        for nl in r["night_logs"]
        if nl.get("night", {}).get("seer_check")
    )

    return {
        "total_games":     total,
        "villager_wins":   villager_wins,
        "villager_pct":    round(villager_wins / total * 100, 1),
        "avg_rounds":      round(sum(rounds_list) / total, 2),
        "min_rounds":      min(rounds_list),
        "max_rounds":      max(rounds_list),
        "vote_accuracy":   round(correct_votes / total_votes * 100, 1) if total_votes else 0,
        "doctor_save_pct": round(saves_success / total_nights_with_save * 100, 1)
                           if total_nights_with_save else 0,
        "seer_accuracy":   round(seer_wolf_found / seer_total_checks * 100, 1)
                           if seer_total_checks else 0,
    }


# ══════════════════════════════════════════════════════════════════════
# In bảng so sánh khoa học
# ══════════════════════════════════════════════════════════════════════
def print_comparison(all_metrics: dict[str, dict], n_games: int) -> None:
    modes  = ["random", "rule_based", "belief"]
    labels = {
        "random":     "Random (Baseline)",
        "rule_based": "Rule-Based",
        "belief":     "Belief+Social (Proposed)",
    }

    sep = "=" * 68
    print(f"\n{sep}")
    print(f"  BANG SO SANH THUC NGHIEM  ({n_games} van / che do)")
    print(sep)

    # Header
    print(f"{'Chi so':<30} {'Random':>12} {'Rule-Based':>12} {'Belief+SR':>12}")
    print("-" * 68)

    metrics_rows = [
        ("Ti le dan thang (%)",        "villager_pct"),
        ("So vong trung binh",          "avg_rounds"),
        ("Min / Max vong",              None),
        ("Vote dung Ma Soi (%)",        "vote_accuracy"),
        ("Bac Si cuu thanh cong (%)",   "doctor_save_pct"),
        ("Tien Tri tim Ma Soi (%)",     "seer_accuracy"),
    ]

    for label, key in metrics_rows:
        if key is None:
            # Min/Max đặc biệt
            vals = []
            for m in modes:
                mt = all_metrics.get(m, {})
                vals.append(f"{mt.get('min_rounds','?')}/{mt.get('max_rounds','?')}")
            print(f"  {label:<28} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12}")
        else:
            vals = [str(all_metrics.get(m, {}).get(key, "N/A")) for m in modes]
            # Đánh dấu giá trị tốt nhất
            try:
                floats = [float(v) for v in vals]
                # Villager win, vote accuracy, save, seer → cao hơn = tốt hơn
                # Avg rounds → không có hướng rõ ràng
                best_idx = floats.index(max(floats))
                vals[best_idx] = f"[{vals[best_idx]}]"  # đánh dấu winner
            except Exception:
                pass
            print(f"  {label:<28} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12}")

    print(sep)
    print("  [X] = gia tri tot nhat trong hang")
    print(sep)

    # Nhận xét tự động
    print("\n  NHAN XET:")
    r = all_metrics.get("random", {})
    rb = all_metrics.get("rule_based", {})
    b = all_metrics.get("belief", {})

    if b.get("villager_pct", 0) > rb.get("villager_pct", 0) > r.get("villager_pct", 0):
        print("  > Belief+Social > Rule-Based > Random (thu tu dung nhu ly thuyet)")
    elif b.get("villager_pct", 0) > r.get("villager_pct", 0):
        print("  > Belief+Social vuot qua Random baseline")

    if b.get("vote_accuracy", 0) > r.get("vote_accuracy", 0):
        diff = round(b["vote_accuracy"] - r["vote_accuracy"], 1)
        print(f"  > Vote accuracy: Belief+Social cao hon Random {diff}%")

    if b.get("avg_rounds", 0) > r.get("avg_rounds", 0):
        print(f"  > Game dai hon ({b['avg_rounds']} vs {r['avg_rounds']} vong) "
              f"= dan lang chong cu tot hon")
    print()


# ══════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════
def run_experiment(cfg: dict = None) -> dict[str, dict]:
    cfg = cfg or EXP_CONFIG
    n   = cfg["n_games"]
    modes = ["random", "rule_based", "belief"]

    all_results: dict[str, list] = {m: [] for m in modes}
    all_metrics: dict[str, dict] = {}

    for mode in modes:
        print(f"\n[Experiment] Chay {n} van – che do: {mode.upper()} ...")
        for i in range(n):
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                result = run_one_game(seed=i * 97 + 13, mode=mode, cfg=cfg)
            all_results[mode].append(result)

        metrics = compute_metrics(all_results[mode])
        all_metrics[mode] = metrics
        c = Counter(r["result"] for r in all_results[mode])
        print(f"  Dan: {c['villager']}  |  Ma Soi: {c['werewolf']}  |  Hoa: {c.get('draw',0)}")

    print_comparison(all_metrics, n)
    return all_metrics


if __name__ == "__main__":
    run_experiment()

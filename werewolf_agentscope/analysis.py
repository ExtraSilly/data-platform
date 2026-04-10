"""
analysis.py – Phân tích hậu game từ các file JSON đã lưu.

Các chỉ số phân tích:
  1. Tỉ lệ thắng theo phe (Ma Sói vs Dân)
  2. Số vòng trung bình mỗi ván
  3. Độ chính xác của Tiên Tri (seer_check đúng bao nhiêu %)
  4. Hiệu quả bỏ phiếu (vote đúng Ma Sói bao nhiêu %)
  5. Tỉ lệ cứu thành công của Bác Sĩ
  6. Phân phối người bị giết theo vai trò

📌 Dùng chính file JSON từ logger.py – chứng minh "data-driven".
"""

import json
import os
from glob import glob
from collections import defaultdict, Counter

LOG_DIR = os.path.join(os.path.dirname(__file__), "data", "logs")


# ══════════════════════════════════════════════════════════════════════
# Đọc dữ liệu
# ══════════════════════════════════════════════════════════════════════
def load_games(log_dir: str = LOG_DIR) -> list[dict]:
    """Đọc tất cả file game_*.json trong thư mục logs."""
    pattern = os.path.join(log_dir, "game_*.json")
    files = sorted(glob(pattern))
    games = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            games.append(json.load(fp))
    return games


# ══════════════════════════════════════════════════════════════════════
# 1. Tỉ lệ thắng theo phe
# ══════════════════════════════════════════════════════════════════════
def win_rate(games: list[dict]) -> dict:
    """
    Đếm số ván thắng của mỗi phe.
    Output: {"villager": int, "werewolf": int, "draw": int, "total": int}
    """
    counter = Counter(g["result"] for g in games)
    total = len(games)
    return {
        "villager":      counter.get("villager", 0),
        "werewolf":      counter.get("werewolf", 0),
        "draw":          counter.get("draw", 0),
        "total":         total,
        "villager_pct":  round(counter.get("villager", 0) / total * 100, 1) if total else 0,
        "werewolf_pct":  round(counter.get("werewolf", 0) / total * 100, 1) if total else 0,
    }


# ══════════════════════════════════════════════════════════════════════
# 2. Số vòng trung bình
# ══════════════════════════════════════════════════════════════════════
def avg_rounds(games: list[dict]) -> dict:
    """Tính số vòng trung bình, min, max."""
    counts = [g["summary"]["total_rounds"] for g in games]
    if not counts:
        return {"avg": 0, "min": 0, "max": 0}
    return {
        "avg": round(sum(counts) / len(counts), 2),
        "min": min(counts),
        "max": max(counts),
        "all": counts,
    }


# ══════════════════════════════════════════════════════════════════════
# 3. Độ chính xác của Tiên Tri
# ══════════════════════════════════════════════════════════════════════
def seer_accuracy(games: list[dict]) -> dict:
    """
    Đếm tổng số lần Tiên Tri kiểm tra:
      - check_werewolf: số lần check đúng (tìm ra Ma Sói)
      - check_villager: số lần check dân thường
    Accuracy = check_werewolf / total_checks * 100
    (Ghi chú: accuracy ở đây = tỉ lệ check trúng Ma Sói, phản ánh chiến lược)
    """
    total_checks = 0
    wolf_checks = 0
    villager_checks = 0

    for g in games:
        for r in g.get("rounds", []):
            seer_check = r.get("night", {}).get("seer_check", {})
            for target, result in seer_check.items():
                total_checks += 1
                if result == "werewolf":
                    wolf_checks += 1
                else:
                    villager_checks += 1

    accuracy = round(wolf_checks / total_checks * 100, 1) if total_checks else 0
    return {
        "total_checks":    total_checks,
        "wolf_found":      wolf_checks,
        "villager_checked": villager_checks,
        "accuracy_pct":    accuracy,   # % check trúng Ma Sói
    }


# ══════════════════════════════════════════════════════════════════════
# 4. Hiệu quả bỏ phiếu (vote đúng Ma Sói)
# ══════════════════════════════════════════════════════════════════════
def vote_accuracy(games: list[dict]) -> dict:
    """
    correct_vote = True  → bỏ phiếu loại đúng Ma Sói
    correct_vote = False → loại nhầm dân thường
    """
    correct = sum(
        1 for g in games
        for r in g.get("rounds", [])
        if r.get("day", {}).get("correct_vote") is True
    )
    wrong = sum(
        1 for g in games
        for r in g.get("rounds", [])
        if r.get("day", {}).get("correct_vote") is False
        and r.get("day", {})
    )
    total = correct + wrong
    return {
        "correct_votes":  correct,
        "wrong_votes":    wrong,
        "total_votes":    total,
        "accuracy_pct":   round(correct / total * 100, 1) if total else 0,
    }


# ══════════════════════════════════════════════════════════════════════
# 5. Tỉ lệ cứu thành công của Bác Sĩ
# ══════════════════════════════════════════════════════════════════════
def doctor_save_rate(games: list[dict]) -> dict:
    """
    Đêm nào có doctor_save VÀ wolf_target == doctor_save → cứu thành công
    Đêm nào có doctor_save VÀ killed != None → cứu thất bại
    """
    success = 0
    fail = 0
    no_action = 0

    for g in games:
        for r in g.get("rounds", []):
            night = r.get("night", {})
            wolf_target  = night.get("wolf_target")
            doctor_save  = night.get("doctor_save")
            killed       = night.get("killed")

            if not doctor_save:
                no_action += 1
            elif wolf_target == doctor_save:
                success += 1   # cứu đúng người bị nhắm
            else:
                fail += 1      # cứu nhầm người khác

    total_saves = success + fail
    return {
        "save_success":   success,
        "save_fail":      fail,
        "no_save":        no_action,
        "success_rate":   round(success / total_saves * 100, 1) if total_saves else 0,
    }


# ══════════════════════════════════════════════════════════════════════
# 6. Phân phối vai trò bị loại
# ══════════════════════════════════════════════════════════════════════
def elimination_breakdown(games: list[dict]) -> dict:
    """Đếm tổng số người bị loại theo từng vai trò (đêm + ngày)."""
    night_kills: Counter = Counter()
    day_hangs:   Counter = Counter()

    for g in games:
        # Lấy role map từ config + alive/dead (không có trong JSON → ước tính)
        for r in g.get("rounds", []):
            night = r.get("night", {})
            day   = r.get("day", {})

            # Đêm: chỉ biết tên, không biết role → ghi "unknown"
            if night.get("killed"):
                night_kills["(night_victim)"] += 1

            # Ngày: biết role
            hanged_role = day.get("hanged_role")
            if hanged_role:
                day_hangs[hanged_role] += 1

    return {
        "killed_night": dict(night_kills),
        "hanged_day":   dict(day_hangs),
    }


# ══════════════════════════════════════════════════════════════════════
# In báo cáo tổng hợp
# ══════════════════════════════════════════════════════════════════════
def print_report(games: list[dict]) -> None:
    if not games:
        print("[Analysis] Chua co du lieu. Chay run_game() truoc.")
        return

    wr   = win_rate(games)
    ar   = avg_rounds(games)
    sa   = seer_accuracy(games)
    va   = vote_accuracy(games)
    dr   = doctor_save_rate(games)
    eb   = elimination_breakdown(games)

    sep = "=" * 52

    print(f"\n{sep}")
    print(f"  PHAN TICH HAU GAME  ({wr['total']} van choi)")
    print(sep)

    # 1. Tỉ lệ thắng
    print(f"\n[1] TI LE THANG THEO PHE")
    print(f"  Dan lang  : {wr['villager']:>3} van  ({wr['villager_pct']}%)")
    bar_v = "#" * wr["villager"]
    bar_w = "#" * wr["werewolf"]
    print(f"  Ma Soi    : {wr['werewolf']:>3} van  ({wr['werewolf_pct']}%)")
    print(f"  Hoa       : {wr['draw']:>3} van")
    print(f"  [{bar_v}{'.'*(wr['total']-wr['villager'])}] Dan")
    print(f"  [{bar_w}{'.'*(wr['total']-wr['werewolf'])}] Ma Soi")

    # 2. Số vòng
    print(f"\n[2] SO VONG MOI VAN")
    print(f"  Trung binh: {ar['avg']}")
    print(f"  Ngan nhat : {ar['min']}  |  Dai nhat: {ar['max']}")

    # 3. Tiên Tri
    print(f"\n[3] DO CHINH XAC TIEN TRI")
    print(f"  Tong luot kiem tra : {sa['total_checks']}")
    print(f"  Tim ra Ma Soi      : {sa['wolf_found']}  ({sa['accuracy_pct']}%)")
    print(f"  Kiem tra dan thuong: {sa['villager_checked']}")

    # 4. Vote
    print(f"\n[4] HIEU QUA BO PHIEU CONG DONG")
    print(f"  Tong luot bo phieu : {va['total_votes']}")
    print(f"  Vote dung Ma Soi   : {va['correct_votes']}  ({va['accuracy_pct']}%)")
    print(f"  Vote sai (loai dan): {va['wrong_votes']}")

    # 5. Bác Sĩ
    print(f"\n[5] TI LE CUU THANH CONG BAC SI")
    print(f"  Cuu dung nguoi bi nham : {dr['save_success']}  ({dr['success_rate']}%)")
    print(f"  Cuu sai nguoi khac     : {dr['save_fail']}")
    print(f"  Dem khong hanh dong    : {dr['no_save']}")

    # 6. Phân phối loại
    print(f"\n[6] PHAN PHOI VAI BI LOAI (NGAY)")
    if eb["hanged_day"]:
        for role, count in sorted(eb["hanged_day"].items(), key=lambda x: -x[1]):
            bar = "#" * count
            print(f"  {role:12}: {bar} ({count})")
    else:
        print("  (chua co du lieu)")

    print(f"\n{sep}\n")


# ══════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    games = load_games()
    print(f"[Analysis] Da doc {len(games)} van choi tu {LOG_DIR}")
    print_report(games)

"""
GameLogger – lưu log mỗi ván game ra file JSON.

Cấu trúc log:
  {
    "game_id": "game_20260408_153012",
    "config": { ... },
    "result": "villager" | "werewolf",
    "rounds": [
      {
        "round": 1,
        "night": { "wolf_target", "doctor_save", "seer_check", "killed" },
        "day":   { "ballots", "tally", "hanged", "hanged_role", "correct_vote" }
      },
      ...
    ],
    "summary": {
      "total_rounds": 3,
      "total_killed_night": 2,
      "total_hanged_day": 2,
      "correct_votes": 1,
      "wrong_votes": 1
    }
  }

Mỗi ván game = 1 file JSON riêng biệt.
"""

import json
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")


class GameLogger:
    """Thu thập và xuất log từng vòng ra file JSON."""

    def __init__(self, config: dict):
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.game_id = f"game_{timestamp}"
        self.config = config
        self.rounds: list[dict] = []     # mỗi phần tử = 1 round record
        self._current: dict = {}         # record đang xây dựng

    # ── Bắt đầu một round mới ────────────────────────────────────────
    def start_round(self, round_num: int) -> None:
        """Khởi tạo record rỗng cho round mới."""
        self._current = {"round": round_num, "night": {}, "day": {}}

    # ── Ghi kết quả đêm ──────────────────────────────────────────────
    def log_night(self, night_log: dict) -> None:
        """
        night_log có cấu trúc:
          { "round": int, "night": { wolf_target, doctor_save, seer_check, killed } }
        """
        self._current["night"] = night_log.get("night", night_log)

    # ── Ghi kết quả ngày ─────────────────────────────────────────────
    def log_day(self, day_log: dict) -> None:
        """
        day_log có cấu trúc:
          { "round": int, "day": { ballots, tally, hanged, hanged_role, correct_vote } }
        """
        self._current["day"] = day_log.get("day", day_log)

    # ── Kết thúc round, đẩy vào danh sách ───────────────────────────
    def end_round(self) -> None:
        """Lưu record round hiện tại vào danh sách rounds."""
        if self._current:
            self.rounds.append(dict(self._current))
            self._current = {}

    # ── Lưu toàn bộ game ra file ─────────────────────────────────────
    def save(self, result: str, alive: list[str], dead: list[str]) -> str:
        """
        Xuất file JSON đầy đủ sau khi game kết thúc.
        Trả về đường dẫn file đã lưu.
        """
        summary = self._build_summary(result)

        output = {
            "game_id":  self.game_id,
            "config":   self.config,
            "result":   result,          # "villager" | "werewolf" | "draw"
            "alive":    alive,
            "dead":     dead,
            "rounds":   self.rounds,
            "summary":  summary,
        }

        filename = f"{self.game_id}.json"
        filepath = os.path.join(LOG_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n[Logger] Game log da luu: {filepath}")
        self._print_summary(summary, result)
        return filepath

    # ── Tính tóm tắt thống kê ─────────────────────────────────────────
    def _build_summary(self, result: str) -> dict:
        """Tổng hợp thống kê từ tất cả rounds."""
        total_killed_night = sum(
            1 for r in self.rounds
            if r.get("night", {}).get("killed") is not None
        )
        total_hanged_day = sum(
            1 for r in self.rounds
            if r.get("day", {}).get("hanged") is not None
        )
        correct_votes = sum(
            1 for r in self.rounds
            if r.get("day", {}).get("correct_vote") is True
        )
        wrong_votes = sum(
            1 for r in self.rounds
            if r.get("day", {}).get("correct_vote") is False
            and r.get("day", {})  # có pha ngày
        )
        wolf_kills = [
            r["night"]["killed"]
            for r in self.rounds
            if r.get("night", {}).get("killed")
        ]
        hanged_list = [
            {"name": r["day"]["hanged"], "role": r["day"]["hanged_role"]}
            for r in self.rounds
            if r.get("day", {}).get("hanged")
        ]

        return {
            "total_rounds":       len(self.rounds),
            "total_killed_night": total_killed_night,
            "total_hanged_day":   total_hanged_day,
            "correct_votes":      correct_votes,
            "wrong_votes":        wrong_votes,
            "wolf_kills":         wolf_kills,
            "hanged_list":        hanged_list,
            "winner":             result,
        }

    def _print_summary(self, summary: dict, result: str) -> None:
        """In bảng tóm tắt ra console."""
        print("\n" + "=" * 50)
        print("  THONG KE VAN CHOI")
        print("=" * 50)
        print(f"  Ket qua       : {'DAN THANG' if result == 'villager' else 'MA SOI THANG' if result == 'werewolf' else 'HOA'}")
        print(f"  So vong       : {summary['total_rounds']}")
        print(f"  Chet dem      : {summary['total_killed_night']} nguoi  -> {summary['wolf_kills']}")
        print(f"  Treo co ngay  : {summary['total_hanged_day']} nguoi")
        print(f"  Vote dung     : {summary['correct_votes']} lan")
        print(f"  Vote sai      : {summary['wrong_votes']} lan")
        if summary['hanged_list']:
            print(f"  Nguoi bi treo :")
            for h in summary['hanged_list']:
                mark = "X" if h['role'] == 'werewolf' else "?"
                print(f"    [{mark}] {h['name']} ({h['role']})")
        print("=" * 50)

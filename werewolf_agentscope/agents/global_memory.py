"""
GlobalMemory – bộ nhớ liên ván (cross-game learning).

Agent không học trong 1 game, mà học GIỮA nhiều game.

Lưu thống kê hành vi từ tất cả ván đã chơi:
  - behavior_stats[role][behavior] = {count, correct, total}
  - Pattern: Ma Sói hay làm gì → điều chỉnh belief weight
  - Học: α, β, γ trong BeliefModel nên được bao nhiêu?

Persistence: lưu/đọc từ data/global_memory.json
"""

import json
import os
from collections import defaultdict

MEMORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "global_memory.json"
)


class GlobalMemory:
    """Singleton bộ nhớ toàn cục – chia sẻ giữa tất cả agent qua nhiều ván."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ── Pattern: hành vi theo vai trò ────────────────────────────
        # behavior_stats[role][behavior] = {"accused_wolf": int, "accused_vil": int}
        self.behavior_stats: dict = {
            "werewolf": defaultdict(lambda: {"accused_wolf": 0, "accused_vil": 0, "total": 0}),
            "villager": defaultdict(lambda: {"accused_wolf": 0, "accused_vil": 0, "total": 0}),
            "seer":     defaultdict(lambda: {"accused_wolf": 0, "accused_vil": 0, "total": 0}),
            "doctor":   defaultdict(lambda: {"accused_wolf": 0, "accused_vil": 0, "total": 0}),
        }

        # ── Hiệu quả vote theo vai trò ───────────────────────────────
        # vote_accuracy[role] = {"correct": int, "total": int}
        self.vote_accuracy: dict = {
            r: {"correct": 0, "total": 0}
            for r in ["werewolf", "villager", "seer", "doctor"]
        }

        # ── Belief weight tự học ──────────────────────────────────────
        # Trọng số α, β, γ khởi đầu từ lý thuyết, được điều chỉnh theo data
        self.learned_weights: dict = {
            "alpha": 0.40,   # vote behavior
            "beta":  0.35,   # speech behavior
            "gamma": 0.25,   # seer oracle
        }

        # ── Số ván đã học ────────────────────────────────────────────
        self.games_played: int = 0
        self.villager_wins: int = 0

        # Load từ file nếu có
        self._load()

    # ── Persistence ──────────────────────────────────────────────────
    def _load(self) -> None:
        """Đọc global memory từ file JSON."""
        if not os.path.exists(MEMORY_PATH):
            return
        try:
            with open(MEMORY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self.games_played    = data.get("games_played", 0)
            self.villager_wins   = data.get("villager_wins", 0)
            self.learned_weights = data.get("learned_weights", self.learned_weights)
            self.vote_accuracy   = data.get("vote_accuracy", self.vote_accuracy)
            # behavior_stats cần convert lại defaultdict
            raw = data.get("behavior_stats", {})
            for role, behaviors in raw.items():
                if role in self.behavior_stats:
                    for beh, stats in behaviors.items():
                        self.behavior_stats[role][beh] = stats
        except Exception:
            pass  # file hỏng → dùng mặc định

    def save(self) -> None:
        """Ghi global memory ra file JSON."""
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        data = {
            "games_played":    self.games_played,
            "villager_wins":   self.villager_wins,
            "learned_weights": self.learned_weights,
            "vote_accuracy":   self.vote_accuracy,
            "behavior_stats":  {
                role: dict(behaviors)
                for role, behaviors in self.behavior_stats.items()
            },
        }
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Update sau mỗi ván ───────────────────────────────────────────
    def update_from_game(self, game_log: dict, role_map: dict[str, str]) -> None:
        """
        Học từ 1 ván vừa kết thúc.

        game_log: dict từ GameLogger (có "rounds", "result")
        role_map: {name: role} – ai đóng vai gì trong ván này
        """
        self.games_played += 1
        result = game_log.get("result", "unknown")
        if result == "villager":
            self.villager_wins += 1

        # ── Học vote accuracy theo vai trò ────────────────────────────
        for r in game_log.get("rounds", []):
            day = r.get("day", {})
            hanged      = day.get("hanged")
            hanged_role = day.get("hanged_role")
            ballots     = day.get("ballots", {})
            correct_target = hanged if hanged_role == "werewolf" else None

            for voter, target in ballots.items():
                voter_role = role_map.get(voter, "villager")
                if voter_role in self.vote_accuracy:
                    self.vote_accuracy[voter_role]["total"] += 1
                    if correct_target and target == correct_target:
                        self.vote_accuracy[voter_role]["correct"] += 1

        # ── Học behavior pattern: ai hay đổ nghi vào Ma Sói vs Dân ───
        wolf_names = {n for n, r in role_map.items() if r == "werewolf"}
        for r in game_log.get("rounds", []):
            day = r.get("day", {})
            ballots = day.get("ballots", {})
            for voter, target in ballots.items():
                voter_role = role_map.get(voter, "villager")
                behavior   = "vote_wolf" if target in wolf_names else "vote_vil"
                if voter_role in self.behavior_stats:
                    self.behavior_stats[voter_role][behavior]["total"] += 1
                    if target in wolf_names:
                        self.behavior_stats[voter_role][behavior]["accused_wolf"] += 1
                    else:
                        self.behavior_stats[voter_role][behavior]["accused_vil"] += 1

        # ── Cập nhật learned_weights dựa trên hiệu quả ───────────────
        self._update_weights()
        self.save()

    # ── Điều chỉnh trọng số BeliefModel theo data ────────────────────
    def _update_weights(self) -> None:
        """
        Logic học trọng số:
        - Nếu dân thắng nhiều: giữ nguyên
        - Nếu vote accuracy của seer cao: tăng gamma (tin Seer hơn)
        - Nếu vote accuracy dân thấp: tăng alpha (tin hành vi vote hơn)
        """
        if self.games_played < 5:
            return   # cần tối thiểu 5 ván để học

        villager_win_rate = self.villager_wins / self.games_played

        # Seer vote accuracy
        seer_va = self.vote_accuracy.get("seer", {})
        seer_acc = (seer_va.get("correct", 0) / seer_va.get("total", 1)
                    if seer_va.get("total", 0) > 0 else 0.33)

        # Villager vote accuracy
        vil_va = self.vote_accuracy.get("villager", {})
        vil_acc = (vil_va.get("correct", 0) / vil_va.get("total", 1)
                   if vil_va.get("total", 0) > 0 else 0.33)

        # Điều chỉnh gamma: nếu seer chính xác cao → tăng gamma
        gamma_new = min(0.45, max(0.15, 0.25 + (seer_acc - 0.33) * 0.5))
        # Điều chỉnh alpha: nếu villager vote accuracy cao → tăng alpha
        alpha_new = min(0.50, max(0.25, 0.40 + (vil_acc - 0.33) * 0.3))
        # beta = 1 - alpha - gamma
        beta_new  = max(0.10, 1.0 - alpha_new - gamma_new)

        self.learned_weights = {
            "alpha": round(alpha_new, 3),
            "beta":  round(beta_new, 3),
            "gamma": round(gamma_new, 3),
        }

    # ── Query: lấy thông tin để agent dùng ───────────────────────────
    def get_weights(self) -> dict:
        """Trả về α, β, γ đã học để BeliefModel dùng."""
        return dict(self.learned_weights)

    def get_role_vote_accuracy(self, role: str) -> float:
        """Tỉ lệ vote đúng của vai trò này trong lịch sử."""
        va = self.vote_accuracy.get(role, {})
        total = va.get("total", 0)
        return va.get("correct", 0) / total if total > 0 else 0.33

    def win_rate(self) -> float:
        """Tỉ lệ dân thắng tổng thể."""
        return self.villager_wins / self.games_played if self.games_played > 0 else 0.0

    def summary(self) -> str:
        """In tóm tắt bộ nhớ toàn cục."""
        lines = [
            "\n=== GLOBAL MEMORY (Cross-game Learning) ===",
            f"  Tong van da hoc : {self.games_played}",
            f"  Ti le dan thang : {self.win_rate()*100:.1f}%",
            f"  Learned weights : α={self.learned_weights['alpha']} "
            f"β={self.learned_weights['beta']} γ={self.learned_weights['gamma']}",
            "  Vote accuracy theo vai:",
        ]
        for role, va in self.vote_accuracy.items():
            total = va.get("total", 0)
            if total > 0:
                acc = va["correct"] / total * 100
                lines.append(f"    {role:10}: {acc:.1f}%  ({va['correct']}/{total})")
        lines.append("=" * 44)
        return "\n".join(lines)


# Singleton accessor
def get_global_memory() -> GlobalMemory:
    return GlobalMemory()

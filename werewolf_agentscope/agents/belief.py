"""
BeliefModel – mô hình niềm tin nâng cấp.

Belief(player) = α · vote_behavior
               + β · speech_behavior
               + γ · seer_result

Tách thành 2 chiều:
  suspicion_score  [0,1] – càng cao càng nghi là Ma Sói
  trust_score      [0,1] – càng cao càng tin là Dân (do Seer xác nhận)

Final belief = clamp(suspicion_score - trust_score * 0.5 + 0.5, 0, 1)
"""

from dataclasses import dataclass, field

# Trọng số mặc định – được GlobalMemory ghi đè sau khi học đủ dữ liệu
ALPHA = 0.40   # vote behavior
BETA  = 0.35   # speech/social behavior
GAMMA = 0.25   # seer oracle result


def _get_learned_weights() -> tuple[float, float, float]:
    """Lấy trọng số đã học từ GlobalMemory nếu có đủ dữ liệu."""
    try:
        from .global_memory import get_global_memory
        gm = get_global_memory()
        if gm.games_played >= 5:
            w = gm.get_weights()
            return w["alpha"], w["beta"], w["gamma"]
    except Exception:
        pass
    return ALPHA, BETA, GAMMA


@dataclass
class PlayerBelief:
    """Niềm tin của một agent về một người chơi cụ thể."""

    name: str

    # ── Chiều 1: Suspicion (nghi ngờ) ───────────────────────────────
    suspicion_score: float = 0.5       # khởi tạo trung tính

    # ── Chiều 2: Trust (tin tưởng, do bằng chứng tích cực) ──────────
    trust_score: float = 0.0           # mặc định chưa có bằng chứng

    # ── Nguồn dữ liệu cấu thành belief ─────────────────────────────
    vote_evidence:   list[float] = field(default_factory=list)   # α
    speech_evidence: list[float] = field(default_factory=list)   # β
    seer_confirmed:  str | None  = None  # "werewolf"|"villager"|None (γ)

    @property
    def final_belief(self) -> float:
        """
        Tổng hợp belief từ 3 nguồn với trọng số α, β, γ.
        Output trong [0, 1]: 1.0 = chắc chắn Ma Sói.
        """
        # Vote component
        vote_score = (
            sum(self.vote_evidence) / len(self.vote_evidence)
            if self.vote_evidence else 0.5
        )

        # Speech component
        speech_score = (
            sum(self.speech_evidence) / len(self.speech_evidence)
            if self.speech_evidence else 0.5
        )

        # Seer oracle component (γ) – mạnh nhất khi có
        if self.seer_confirmed == "werewolf":
            seer_score = 1.0
        elif self.seer_confirmed == "villager":
            seer_score = 0.0
        else:
            seer_score = 0.5   # chưa biết

        alpha, beta, gamma = _get_learned_weights()
        weighted = (
            alpha * vote_score
            + beta  * speech_score
            + gamma * seer_score
        )

        # Áp dụng trust: nếu tin tưởng mạnh → kéo xuống
        result = weighted - self.trust_score * 0.3
        return max(0.0, min(1.0, result))

    def add_vote_evidence(self, delta: float) -> None:
        """Thêm bằng chứng từ hành vi bỏ phiếu (α)."""
        self.vote_evidence.append(max(0.0, min(1.0, delta)))

    def add_speech_evidence(self, delta: float) -> None:
        """Thêm bằng chứng từ lời nói / hành vi xã hội (β)."""
        self.speech_evidence.append(max(0.0, min(1.0, delta)))

    def set_seer_result(self, result: str) -> None:
        """Ghi nhận kết quả Tiên Tri (γ) – ghi đè nếu có."""
        self.seer_confirmed = result
        if result == "villager":
            self.trust_score = 1.0
        elif result == "werewolf":
            self.suspicion_score = 1.0


class BeliefModel:
    """
    Bộ niềm tin đầy đủ của một agent về tất cả người chơi khác.
    Thay thế dict belief đơn giản trong BaseAgent.
    """

    def __init__(self, owner: str, players: list[str]):
        self.owner = owner
        self.beliefs: dict[str, PlayerBelief] = {
            p: PlayerBelief(name=p)
            for p in players if p != owner
        }

    def get(self, name: str) -> float:
        """Trả về final_belief của player (tương thích với API cũ)."""
        if name not in self.beliefs:
            return 0.5
        return self.beliefs[name].final_belief

    def update_vote(self, target: str, delta: float) -> None:
        if target in self.beliefs:
            self.beliefs[target].add_vote_evidence(
                self.beliefs[target].suspicion_score + delta
            )

    def update_speech(self, target: str, delta: float) -> None:
        if target in self.beliefs:
            self.beliefs[target].add_speech_evidence(
                self.beliefs[target].suspicion_score + delta
            )

    def set_seer(self, target: str, result: str) -> None:
        if target in self.beliefs:
            self.beliefs[target].set_seer_result(result)

    def most_suspected(self, candidates: list[str]) -> str:
        pool = [p for p in candidates if p in self.beliefs]
        if not pool:
            return candidates[0]
        return max(pool, key=lambda p: self.beliefs[p].final_belief)

    def summary(self) -> str:
        lines = [f"BeliefModel({self.owner}):"]
        for name, b in sorted(self.beliefs.items(),
                               key=lambda x: -x[1].final_belief):
            seer = f" [SEER:{b.seer_confirmed}]" if b.seer_confirmed else ""
            lines.append(
                f"  {name:10} belief={b.final_belief:.2f}  "
                f"sus={b.suspicion_score:.2f} trust={b.trust_score:.2f}{seer}"
            )
        return "\n".join(lines)

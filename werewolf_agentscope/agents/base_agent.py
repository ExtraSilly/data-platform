"""
BaseAgent – lớp cha trừu tượng cho mọi agent trong trò chơi Ma Sói.

Triết lý thiết kế:
  "Mỗi agent có bộ nhớ và niềm tin riêng, đảm bảo tính tự chủ của tác tử."

Ba thành phần bắt buộc:
  1. memory          – lịch sử quan sát (riêng tư)
  2. belief          – BeliefModel 3 chiều: vote · speech · seer  (riêng tư)
  3. decide          – abstract, mỗi vai tự định nghĩa hành vi

Nâng cấp so với phiên bản cơ bản:
  - BeliefModel: α·vote + β·speech + γ·seer (có trọng số)
  - SocialReasoning: phát hiện leader / contrarian / silent
"""

from .belief import BeliefModel
from .social_reasoning import SocialReasoning


class BaseAgent:
    """Lớp cha trừu tượng – tất cả agent kế thừa từ đây."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.is_alive = True

        # ── 1. MEMORY ────────────────────────────────────────────────
        self.memory: list[dict] = []

        # ── 2. BELIEF (nâng cấp: BeliefModel 3 chiều) ────────────────
        # Vẫn giữ self.belief dict để tương thích ngược với code cũ
        self.belief: dict[str, float] = {}
        self._belief_model: BeliefModel | None = None   # khởi tạo sau

        # ── 3. SOCIAL REASONING ───────────────────────────────────────
        self._social: SocialReasoning = SocialReasoning(name)
        # Đếm số lần mỗi người phát biểu (feed vào silence detector)
        self._speech_counts: dict[str, int] = {}

    # ── INIT ─────────────────────────────────────────────────────────
    def init_belief(self, players: list[str]) -> None:
        """Khởi tạo BeliefModel và dict belief tương thích ngược."""
        self._belief_model = BeliefModel(self.name, players)
        self.belief = {p: 0.5 for p in players if p != self.name}

    def _sync_belief(self) -> None:
        """Đồng bộ self.belief từ BeliefModel sau mỗi cập nhật.
        Không overwrite các giá trị đã được Seer xác nhận (0.0 hoặc 1.0)."""
        if self._belief_model:
            for p in self.belief:
                pb = self._belief_model.beliefs.get(p)
                # Nếu Seer đã xác nhận → giữ nguyên giá trị tuyệt đối
                if pb and pb.seer_confirmed is not None:
                    self.belief[p] = 1.0 if pb.seer_confirmed == "werewolf" else 0.05
                else:
                    self.belief[p] = self._belief_model.get(p)

    # ── OBSERVE ──────────────────────────────────────────────────────
    def observe(self, game_state) -> None:
        """Quan sát game_state, lưu vào memory, cập nhật social signals."""
        for e in game_state.events:
            if e["round"] == game_state.round and e not in self.memory:
                self.memory.append(e)

                # Ghi nhận accusations trong thảo luận
                if e.get("type") == "discuss":
                    msg = e.get("msg", "")
                    src = e.get("source", "")
                    if src and src != self.name:
                        self._speech_counts[src] = self._speech_counts.get(src, 0) + 1
                        # Phát hiện ai bị nhắc tên → ghi nhận accusation
                        for candidate in self.belief:
                            if candidate in msg and candidate != src:
                                self._social.record_accusation(src, candidate)

    # ── MEMORY helpers ───────────────────────────────────────────────
    def remember(self, round_num: int, event: str, source: str = "system") -> None:
        self.memory.append({"round": round_num, "source": source, "event": event})

    def recall(self, last_n: int = 5) -> list[dict]:
        return self.memory[-last_n:]

    # ── BELIEF helpers (tương thích ngược + nâng cấp) ─────────────────
    def update_belief(self, target: str, delta: float) -> None:
        """Cập nhật belief đơn giản (tương thích ngược với code cũ)."""
        if target in self.belief:
            self.belief[target] = max(0.0, min(1.0, self.belief[target] + delta))
        if self._belief_model and target in self._belief_model.beliefs:
            self._belief_model.update_speech(target, delta)

    def update_vote_belief(self, target: str, delta: float) -> None:
        """Cập nhật belief từ hành vi vote (α component)."""
        if self._belief_model:
            self._belief_model.update_vote(target, delta)
            self._sync_belief()

    def update_speech_belief(self, target: str, delta: float) -> None:
        """Cập nhật belief từ lời nói / social (β component)."""
        # Cập nhật cả dict đơn giản để tương thích
        if target in self.belief:
            self.belief[target] = max(0.0, min(1.0, self.belief[target] + delta))
        if self._belief_model:
            self._belief_model.update_speech(target, delta)
            self._sync_belief()

    def update_seer_belief(self, target: str, result: str) -> None:
        """Cập nhật belief từ kết quả Tiên Tri (γ component)."""
        if self._belief_model:
            self._belief_model.set_seer(target, result)
            self._sync_belief()

    def apply_social_reasoning(self, alive: list[str]) -> None:
        """
        Chạy SocialReasoning và feed kết quả vào BeliefModel (β).
        Gọi trước khi vote để có belief chính xác nhất.
        """
        deltas = self._social.analyze(alive, self._speech_counts)
        for p, delta in deltas.items():
            if delta != 0.0:
                self.update_speech_belief(p, delta)

    def record_vote_round(self, round_num: int, ballots: dict[str, str]) -> None:
        """Ghi nhận kết quả vote cho SocialReasoning."""
        self._social.record_votes(round_num, ballots)

    def most_suspected(self, candidates: list[str] | None = None) -> str:
        """Trả về người bị nghi ngờ nhất (dùng BeliefModel nếu có)."""
        pool = candidates if candidates is not None else list(self.belief.keys())
        pool = [p for p in pool if p in self.belief]
        if not pool:
            raise ValueError(f"{self.name}: Khong co ung vien hop le.")
        if self._belief_model:
            return self._belief_model.most_suspected(pool)
        return max(pool, key=lambda p: self.belief[p])

    # ── DECIDE (abstract) ─────────────────────────────────────────────
    def decide(self, game_state) -> dict:
        """Quyết định hành động – subclass BẮT BUỘC override."""
        raise NotImplementedError(
            f"{self.__class__.__name__} chua implement decide()."
        )

    # ── Convenience wrappers ──────────────────────────────────────────
    def night_action(self, game_state) -> dict:
        return {"action": "none", "target": None}

    def discuss(self, game_state) -> str:
        return f"{self.name} im lang."

    def vote(self, candidates: list[str]) -> str:
        # Áp dụng social reasoning trước khi vote
        self.apply_social_reasoning(candidates)
        return self.most_suspected(candidates)

    # ── Debug ─────────────────────────────────────────────────────────
    def status(self) -> str:
        lines = [
            f"[{self.name} | {self.role} | {'alive' if self.is_alive else 'dead'}]",
            f"  Memory ({len(self.memory)} entries):",
        ]
        for entry in self.recall(last_n=3):
            src = entry.get("source") or entry.get("type", "?")
            msg = entry.get("event") or entry.get("msg", "")
            lines.append(f"    R{entry['round']} [{src}] {msg}")
        if self._belief_model:
            lines.append(self._belief_model.summary())
        else:
            lines.append(f"  Belief: {self.belief}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        status = "alive" if self.is_alive else "dead"
        return f"<{self.__class__.__name__} name={self.name!r} role={self.role!r} {status}>"

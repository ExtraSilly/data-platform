"""
SocialReasoning – phân tích hành vi xã hội từ memory.

Phát hiện 3 pattern:
  1. LEADER     – hay dẫn dắt vote (đề xuất target, người theo)
  2. CONTRARIAN – hay vote ngược số đông (có thể đang bảo vệ Ma Sói)
  3. SILENT     – im lặng bất thường (ít phát biểu)

Output: điểm suspicion_delta cho từng người → feed vào BeliefModel (β).

Gắn khái niệm: Social Dynamics trong Multi-Agent System.
"""

from collections import defaultdict, Counter


class SocialReasoning:
    """
    Phân tích hành vi xã hội từ lịch sử events.
    Được tích hợp vào BaseAgent để cập nhật BeliefModel.
    """

    def __init__(self, observer: str):
        self.observer = observer
        # Lịch sử ai đề xuất ai trong thảo luận
        self.accusations: list[tuple[str, str]] = []    # (accuser, accused)
        # Lịch sử vote: round → {voter: target}
        self.vote_history: dict[int, dict[str, str]] = {}

    # ── Thu thập dữ liệu ─────────────────────────────────────────────
    def record_accusation(self, accuser: str, accused: str) -> None:
        """Ghi lại ai đổ nghi ngờ lên ai trong thảo luận."""
        self.accusations.append((accuser, accused))

    def record_votes(self, round_num: int, ballots: dict[str, str]) -> None:
        """Ghi lại kết quả vote của một vòng."""
        self.vote_history[round_num] = dict(ballots)

    # ── Phân tích leader ─────────────────────────────────────────────
    def detect_leaders(self, alive: list[str]) -> dict[str, float]:
        """
        Leader = người đề xuất target mà NGƯỜI KHÁC THEO.
        Cách tính: đếm số lần accusation của p trùng với
                   người bị đa số vote cuối vòng.
        Suspicion delta: leader → +0.12 (có thể đang dẫn dắt sai)
        """
        scores: dict[str, float] = {p: 0.0 for p in alive}

        for round_num, ballots in self.vote_history.items():
            if not ballots:
                continue
            # Xác định target đa số vòng này
            tally = Counter(ballots.values())
            majority_target = tally.most_common(1)[0][0]
            majority_count = tally.most_common(1)[0][1]
            total_voters = len(ballots)

            # Ai đã đề xuất majority_target trong accusations?
            round_accs = [
                (acc, acd) for acc, acd in self.accusations
                if acd == majority_target
            ]
            for accuser, _ in round_accs:
                if accuser in scores:
                    # Dẫn dắt thành công (>50% theo) → nghi ngờ hơn
                    follow_ratio = majority_count / total_voters
                    scores[accuser] += 0.12 * follow_ratio

        return scores

    # ── Phân tích contrarian ─────────────────────────────────────────
    def detect_contrarians(self, alive: list[str]) -> dict[str, float]:
        """
        Contrarian = hay vote ngược số đông.
        Nếu vote ngược đa số → +0.08 (có thể đang bảo vệ Ma Sói)
        Nếu vote đúng đa số  → -0.05 (hành vi bình thường)
        """
        scores: dict[str, float] = {p: 0.0 for p in alive}

        for round_num, ballots in self.vote_history.items():
            if not ballots:
                continue
            tally = Counter(ballots.values())
            majority_target, majority_count = tally.most_common(1)[0]

            for voter, target in ballots.items():
                if voter not in scores:
                    continue
                if target != majority_target:
                    scores[voter] += 0.08   # vote ngược → nghi ngờ
                else:
                    scores[voter] -= 0.03   # vote theo đa số → tin tưởng hơn

        return scores

    # ── Phân tích silence ────────────────────────────────────────────
    def detect_silent(self, alive: list[str],
                      speech_counts: dict[str, int]) -> dict[str, float]:
        """
        Silent = ít phát biểu hơn mức trung bình đáng kể.
        Im lặng bất thường → +0.06 suspicion.
        """
        scores: dict[str, float] = {p: 0.0 for p in alive}
        if not speech_counts:
            return scores

        avg = sum(speech_counts.values()) / max(len(speech_counts), 1)
        for p in alive:
            count = speech_counts.get(p, 0)
            if count < avg * 0.5:
                scores[p] = +0.06   # nói ít hơn 50% trung bình → nghi ngờ
            elif count > avg * 1.5:
                scores[p] = -0.02   # nói nhiều nhưng bình thường

        return scores

    # ── Phát hiện accusation phối hợp (dấu hiệu Ma Sói đồng thuận) ────
    def detect_coordinated_attack(self, alive: list[str]) -> dict[str, float]:
        """
        Nếu 2+ người cùng đổ nghi lên 1 mục tiêu trong cùng 1 round
        → những người đổ nghi đó tăng suspicion (có thể đang phối hợp).

        Delta: +0.15 cho mỗi kẻ đồng loạt đổ nghi vào cùng 1 người.
        """
        scores: dict[str, float] = {p: 0.0 for p in alive}

        # Đếm số lần mỗi (accuser, accused) xuất hiện
        from collections import Counter
        accused_counts: Counter = Counter(accused for _, accused in self.accusations)

        # Tìm nạn nhân bị đổ nghi nhiều nhất (≥ 2 người)
        coordinated_targets = {
            accused for accused, count in accused_counts.items()
            if count >= 2
        }

        for target in coordinated_targets:
            # Ai đã đổ nghi lên target?
            attackers = [acc for acc, acd in self.accusations if acd == target]
            count = len(set(attackers))
            for attacker in set(attackers):
                if attacker in scores:
                    scores[attacker] += 0.15 * count  # phối hợp → nghi ngờ hơn

        return scores

    # ── Tổng hợp tất cả signals ──────────────────────────────────────
    def analyze(self, alive: list[str],
                speech_counts: dict[str, int] | None = None) -> dict[str, float]:
        """
        Chạy tất cả detector và tổng hợp điểm suspicion_delta.
        Trả về: {name: delta} để feed vào BeliefModel.update_speech()
        """
        leaders      = self.detect_leaders(alive)
        contrarians  = self.detect_contrarians(alive)
        silent       = self.detect_silent(alive, speech_counts or {})
        coordinated  = self.detect_coordinated_attack(alive)

        combined: dict[str, float] = {}
        for p in alive:
            delta = (
                leaders.get(p, 0.0)
                + contrarians.get(p, 0.0)
                + silent.get(p, 0.0)
                + coordinated.get(p, 0.0)   # ← signal mạnh nhất
            )
            combined[p] = round(delta, 3)

        return combined

    def report(self, alive: list[str],
               speech_counts: dict[str, int] | None = None) -> str:
        """In báo cáo social reasoning (dùng cho debug/báo cáo)."""
        scores = self.analyze(alive, speech_counts)
        leaders = self.detect_leaders(alive)
        contrarians = self.detect_contrarians(alive)

        lines = [f"\n[SocialReasoning by {self.observer}]"]
        for p in sorted(scores, key=lambda x: -scores[x]):
            l = f"+{leaders.get(p,0):.2f}(lead)"
            c = f"+{contrarians.get(p,0):.2f}(contra)"
            total = scores[p]
            lines.append(f"  {p:10} delta={total:+.3f}  [{l} {c}]")
        return "\n".join(lines)

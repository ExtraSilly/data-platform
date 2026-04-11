"""
GameMaster – người cầm luật, điều phối toàn bộ game.

📌 GameMaster KHÔNG có trí tuệ:
  - Không có memory, belief, hay strategy
  - Chỉ gọi agent.decide() và áp dụng kết quả theo luật
  - Là "trọng tài" trung lập biết vai trò tất cả mọi người

Ba nhiệm vụ chính:
  1. assign_roles()   – gán vai ngẫu nhiên cho agents
  2. night_phase()    – thu thập wolf_target / doctor_save / seer_info và giải quyết
  3. day_phase()      – cho tất cả thảo luận, sau đó bỏ phiếu loại người
"""

from agents.seer_agent import SeerAgent
from .game_state import GameState


class GameMaster:
    """Trọng tài trung lập – không phải AI agent."""

    def __init__(self, agents: dict, state: GameState):
        # agents: {name: BaseAgent}  – GameMaster biết TẤT CẢ vai trò
        self.agents = agents
        self.state = state

    # ══════════════════════════════════════════════════════════════════
    # 1. GÁN VAI (assign_roles)
    # ══════════════════════════════════════════════════════════════════
    def announce_roles(self) -> None:
        """
        Thông báo bí mật cho từng agent biết vai trò của mình.
        (Trong thực tế: chỉ agent biết vai của bản thân)
        """
        self.state.add_event("system", "\n[GameMaster] Tro choi bat dau. Vai tro da duoc phan cong.")
        for name, agent in self.agents.items():
            self.state.add_event(
                "system",
                f"[GameMaster -> {name}] Ban la: {agent.role.upper()}"
            )

    # ══════════════════════════════════════════════════════════════════
    # 2. PHA ĐÊM (night_phase)
    # ══════════════════════════════════════════════════════════════════
    def night_phase(self) -> dict:
        """
        Trình tự bắt buộc:
          1. Werewolf chọn mục tiêu giết
          2. Doctor bảo vệ một người
          3. Seer kiểm tra một người
          4. Xử lý chết / sống (_resolve_night)

        Trả về night_log – dict có cấu trúc chuẩn để lưu file.
        """
        s = self.state
        s.set_phase("night")
        s.add_event("system", f"\n{'='*50}")
        s.add_event("system", f"  DEM {s.round}")
        s.add_event("system", f"{'='*50}")

        wolf_target: str | None = None
        doctor_save: str | None = None
        seer_check:  dict       = {}    # {tên: "werewolf"|"villager"}

        # ── BƯỚC 1: Werewolf chọn mục tiêu ───────────────────────────
        for name, agent in self.agents.items():
            if agent.is_alive and agent.role == "werewolf":
                result = agent.night_action(s)
                if result["action"] == "kill" and result["target"]:
                    wolf_target = result["target"]
        if wolf_target:
            s.add_event("kill", f"[Dem] Ma Soi nham vao: {wolf_target} (an)")

        # ── BƯỚC 2: Doctor bảo vệ ─────────────────────────────────────
        for name, agent in self.agents.items():
            if agent.is_alive and agent.role == "doctor":
                result = agent.night_action(s)
                if result["action"] == "save" and result["target"]:
                    doctor_save = result["target"]
        if doctor_save:
            s.add_event("save", f"[Dem] Bac Si bao ve: {doctor_save} (an)")

        # ── BƯỚC 3: Seer kiểm tra ─────────────────────────────────────
        for name, agent in self.agents.items():
            if agent.is_alive and agent.role == "seer":
                result = agent.night_action(s)
                if result["action"] == "check" and result["target"]:
                    target_name = result["target"]
                    target_role = self.agents[target_name].role
                    check_result = "werewolf" if target_role == "werewolf" else "villager"
                    seer_check[target_name] = check_result
                    # Cập nhật state
                    s.seer_target = target_name
                    s.seer_result = check_result
                    # Trả kết quả bí mật cho Seer
                    if isinstance(agent, SeerAgent):
                        agent.receive_check_result(target_name, check_result, s.round)
                    s.add_event("check", f"[Dem] Tien Tri kiem tra {target_name} -> {check_result} (an)")

        # Ghi vào state
        s.night_kill = wolf_target
        s.night_save = doctor_save

        # ── BƯỚC 4: Xử lý chết / sống ────────────────────────────────
        killed = self._resolve_night(wolf_target, doctor_save)

        # ── Structured log (chuẩn JSON) ───────────────────────────────
        night_log = {
            "round":  s.round,
            "night": {
                "wolf_target": wolf_target,
                "doctor_save": doctor_save,
                "seer_check":  seer_check,
                "killed":      killed,       # None nếu được cứu / đêm yên
            },
        }
        s.add_event("system", f"[Log dem {s.round}] {night_log}")
        s.night_log = night_log   # lưu vào state để engine xuất file
        return night_log

    def _resolve_night(self, wolf_target: str | None, doctor_save: str | None) -> str | None:
        """
        Luật áp dụng theo thứ tự ưu tiên:
          wolf_target != doctor_save → nạn nhân chết  → trả về tên nạn nhân
          wolf_target == doctor_save → được cứu        → trả về None
          không có wolf_target       → đêm yên bình   → trả về None
        """
        s = self.state

        if wolf_target and wolf_target != doctor_save:
            self.agents[wolf_target].is_alive = False
            s.eliminate(wolf_target)
            s.add_event("kill", f"\n[Sang] {wolf_target} da bi giet trong dem.")
            for agent in self.agents.values():
                if agent.is_alive:
                    agent.remember(s.round, f"{wolf_target} bi giet trong dem.")
                    agent.update_belief(wolf_target, -0.5)
            return wolf_target   # ← tên người bị giết

        elif wolf_target and wolf_target == doctor_save:
            s.add_event("save", f"\n[Sang] Mot nguoi bi tan cong nhung da duoc cuu song!")
            for agent in self.agents.values():
                if agent.is_alive:
                    agent.remember(s.round, "Co nguoi bi tan cong nhung duoc cuu.")
            return None

        else:
            s.add_event("system", f"\n[Sang] Dem yen binh, khong ai bi giet.")
            for agent in self.agents.values():
                if agent.is_alive:
                    agent.remember(s.round, "Dem qua khong ai chet.")
            return None

    # ══════════════════════════════════════════════════════════════════
    # 3. PHA NGÀY (day_phase)
    # ══════════════════════════════════════════════════════════════════
    def day_phase(self) -> dict:
        """
        Trình tự bắt buộc:
          1. Công bố người chết đêm qua
          2. Mỗi agent phát biểu một lượt (discuss)
          3. Mỗi agent vote đúng 1 lần – GameMaster tổng hợp
          4. Treo cổ người nhiều phiếu nhất

        Trả về day_log – dict có cấu trúc chuẩn.
        """
        s = self.state
        self._announce_deaths()
        self._discussion()
        day_log = self._vote()
        return day_log

    # ── BƯỚC 1: Công bố người chết ────────────────────────────────────
    def _announce_deaths(self) -> None:
        """
        GameMaster công bố công khai ai đã chết đêm qua.
        Tất cả agent nghe và cập nhật memory.
        """
        s = self.state
        s.set_phase("day")
        s.add_event("system", f"\n{'='*50}")
        s.add_event("system", f"  NGAY {s.round} - BUOI SANG")
        s.add_event("system", f"{'='*50}")

        if s.night_kill and s.night_kill in s.dead:
            # Có người chết đêm qua
            s.add_event(
                "system",
                f"[GameMaster] Dem qua, {s.night_kill} da bi Ma Soi giet. "
                f"Hom nay lang can tim ra ke pham toi."
            )
        elif s.night_kill and s.night_kill not in s.dead:
            # Bị tấn công nhưng được cứu
            s.add_event(
                "system",
                "[GameMaster] Dem qua co nguoi bi tan cong nhung may man thoat chet. "
                "Lang van day du nguoi."
            )
        else:
            s.add_event("system", "[GameMaster] Mot dem binh yen. Khong ai bi thuong.")

        s.add_event("system", f"Nguoi con song ({len(s.alive)}): {', '.join(s.alive)}")

    # ── BƯỚC 2: Thảo luận ─────────────────────────────────────────────
    def _discussion(self) -> None:
        """
        Mỗi agent còn sống phát biểu đúng 1 lần theo thứ tự vòng tròn.
        Các agent khác nghe → cập nhật memory + belief.
        """
        s = self.state
        s.add_event("system", f"\n--- THAO LUAN ---")

        for name in list(s.alive):
            statement = self.agents[name].speak(s)   # LLM-powered, fallback rule-based
            s.add_event("discuss", f"  {statement}")

            # Broadcast: tất cả agent còn sống nghe phát biểu này
            for other_name, other_agent in self.agents.items():
                if not other_agent.is_alive or other_name == name:
                    continue
                other_agent.remember(s.round, statement, source=name)
                other_agent._social.record_accusation.__doc__  # ensure exists

                # Chỉ lấy phần câu nói gốc của speaker (trước dấu " – ")
                # để tránh đếm nội dung echo từ agent khác
                own_words = statement.split(" – ")[0] if " – " in statement else statement

                for candidate in s.alive:
                    if candidate in own_words and candidate != name:
                        other_agent.update_speech_belief(candidate, +0.12)
                        other_agent._social.record_accusation(name, candidate)

    # ── BƯỚC 3 + 4: Vote + Treo cổ ────────────────────────────────────
    def _vote(self) -> dict:
        """
        Quy tắc vote:
          - Mỗi agent vote đúng 1 lần
          - Không được tự vote cho bản thân
          - GameMaster tổng hợp phiếu (tally)
          - Người nhiều phiếu nhất bị treo cổ (tie → người đầu danh sách)
          - Vai trò lộ công khai sau khi bị loại
        """
        s = self.state
        s.set_phase("vote")
        s.add_event("system", f"\n--- BO PHIEU ---")

        # Đảm bảo mỗi agent vote đúng 1 lần
        ballots: dict[str, str] = {}    # {voter: target}
        tally:   dict[str, int] = {p: 0 for p in s.alive}

        for name in list(s.alive):
            if name in ballots:
                continue    # guard: không vote 2 lần

            candidates = [p for p in s.alive if p != name]
            # Apply social reasoning trước khi vote → belief chính xác nhất
            self.agents[name].apply_social_reasoning(candidates)
            chosen = self.agents[name].vote(candidates)

            # Validate: phải vote cho người còn sống, không phải bản thân
            if chosen not in candidates:
                chosen = candidates[0]

            ballots[name] = chosen
            tally[chosen] = tally.get(chosen, 0) + 1
            s.add_event("vote", f"  {name:10} bo phieu: {chosen}")

        # GameMaster tổng hợp
        s.vote_tally = tally
        s.add_event("system", f"\n  [Tong hop phieu bau]")
        for player, count in sorted(tally.items(), key=lambda x: -x[1]):
            bar = "#" * count
            s.add_event("system", f"    {player:10} {bar} ({count})")

        # Xác định người bị treo cổ
        max_votes = max(tally.values())
        top = [p for p, v in tally.items() if v == max_votes]
        hanged = top[0]   # tie-break: người đứng đầu danh sách alive

        # Treo cổ
        self.agents[hanged].is_alive = False
        hanged_role = self.agents[hanged].role
        s.eliminate(hanged)
        s.voted_out = hanged

        s.add_event(
            "vote",
            f"\n  [GameMaster] QUYET DINH: {hanged} bi treo co "
            f"({max_votes} phieu) – vai that: {hanged_role.upper()}"
        )

        # Broadcast ballots: tất cả agent học được vote history
        wrong_voters   = [v for v, t in ballots.items() if t != hanged and v in s.alive]
        correct_voters = [v for v, t in ballots.items() if t == hanged and v in s.alive]

        for agent in self.agents.values():
            if not agent.is_alive:
                continue
            agent.remember(s.round, f"{hanged} bi treo co, vai that: {hanged_role}.")
            # Feed vote history vào SocialReasoning
            agent.record_vote_round(s.round, ballots)

            if hanged_role == "werewolf":
                for v in correct_voters:
                    agent.update_vote_belief(v, -0.1)   # vote đúng → tin hơn
            else:
                for v in wrong_voters:
                    agent.update_vote_belief(v, +0.08)  # vote sai → nghi hơn

        # Structured day log
        day_log = {
            "round":  s.round,
            "day": {
                "ballots":      ballots,
                "tally":        tally,
                "hanged":       hanged,
                "hanged_role":  hanged_role,
                "correct_vote": hanged_role == "werewolf",
            },
        }
        s.add_event("system", f"[Log ngay {s.round}] {day_log}")
        return day_log

    # ══════════════════════════════════════════════════════════════════
    # 4. ĐIỀU KIỆN THẮNG / THUA
    # ══════════════════════════════════════════════════════════════════
    def check_end(self) -> str | None:
        """
        Kiểm tra sau MỖI hành động loại người (đêm hoặc ngày).

        Điều kiện kết thúc:
          wolves == 0              → DÂN THẮNG  (đã diệt hết Ma Sói)
          wolves >= villagers      → MA SÓI THẮNG (số lượng áp đảo)

        Trả về:
          "villager"  – dân làng thắng
          "werewolf"  – ma sói thắng
          None        – chưa kết thúc, game tiếp tục
        """
        alive = self.state.alive

        wolves    = [n for n in alive if self.agents[n].role == "werewolf"]
        villagers = [n for n in alive if self.agents[n].role != "werewolf"]

        # ── Điều kiện 1: Dân thắng ────────────────────────────────────
        if len(wolves) == 0:
            self._announce_end("villager", wolves, villagers)
            return "villager"

        # ── Điều kiện 2: Ma Sói thắng ─────────────────────────────────
        if len(wolves) >= len(villagers):
            self._announce_end("werewolf", wolves, villagers)
            return "werewolf"

        # ── Chưa kết thúc ─────────────────────────────────────────────
        return None

    def _announce_end(self, winner: str, wolves: list, villagers: list) -> None:
        """In thông báo kết thúc game kèm thống kê."""
        s = self.state
        s.add_event("system", f"\n{'*'*50}")
        if winner == "villager":
            s.add_event("system", "  KET QUA: DAN LANG CHIEN THANG!")
            s.add_event("system", f"  Da tieu diet het {len(s.dead)} nguoi (trong do co Ma Soi).")
        else:
            s.add_event("system", "  KET QUA: MA SOI CHIEN THANG!")
            s.add_event("system", f"  Ma Soi con lai: {', '.join(wolves)}")
            s.add_event("system", f"  Dan con lai:    {', '.join(villagers)}")
        s.add_event("system", f"  Sau {s.round} vong (round bi loai tinh tu 2).")
        s.add_event("system", f"{'*'*50}")

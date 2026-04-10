"""
GameState – trạng thái toàn cục của toàn bộ hệ thống.

Ba trường cốt lõi (ghi vào báo cáo):
  - round  : theo dõi tiến trình game (vòng mấy)
  - phase  : kiểm soát hành động hợp lệ (chỉ đúng pha mới được hành động)
  - events : log & phân tích hành vi agent sau game
"""


class GameState:
    """Dữ liệu chung được chia sẻ qua toàn bộ hệ thống agent."""

    # Thứ tự các pha trong một vòng
    PHASES = ["night", "day", "vote"]

    def __init__(self, players: list[str]):
        # --- 3 trường cốt lõi ---
        self.round: int = 1
        self.phase: str = "night"
        self.events: list[dict] = []        # {"round", "phase", "type", "msg"}

        # --- Danh sách người chơi ---
        self.alive: list[str] = list(players)
        self.dead: list[str] = []

        # --- Kết quả trong round hiện tại ---
        self.night_kill: str | None = None   # mục tiêu Ma Sói
        self.night_save: str | None = None   # mục tiêu Bác Sĩ
        self.seer_target: str | None = None  # mục tiêu Tiên Tri
        self.seer_result: str | None = None  # "werewolf" | "villager"
        self.vote_tally: dict[str, int] = {}
        self.voted_out: str | None = None

        # Structured night log (reset mỗi round)
        self.night_log: dict = {}

    # ------------------------------------------------------------------
    # Events / logging
    # ------------------------------------------------------------------
    def add_event(self, event_type: str, msg: str):
        """
        Ghi một sự kiện vào events (log chính thức) và in ra console.
        event_type: "kill" | "save" | "check" | "discuss" | "vote" | "system"
        """
        entry = {
            "round": self.round,
            "phase": self.phase,
            "type": event_type,
            "msg": msg,
        }
        self.events.append(entry)
        print(msg)

    # ------------------------------------------------------------------
    # Phase control
    # ------------------------------------------------------------------
    def set_phase(self, phase: str):
        """Chuyển pha, chỉ cho phép các giá trị hợp lệ."""
        if phase not in self.PHASES:
            raise ValueError(f"Phase không hợp lệ: {phase!r}. Chọn trong {self.PHASES}")
        self.phase = phase

    # ------------------------------------------------------------------
    # Player management
    # ------------------------------------------------------------------
    def eliminate(self, name: str):
        """Loại một người chơi ra khỏi danh sách alive → dead."""
        if name in self.alive:
            self.alive.remove(name)
            self.dead.append(name)

    # ------------------------------------------------------------------
    # Round transition
    # ------------------------------------------------------------------
    def next_round(self):
        """Chuyển sang round tiếp theo, reset kết quả đêm/ngày."""
        self.round += 1
        self.phase = "night"
        self.night_kill = None
        self.night_save = None
        self.seer_target = None
        self.seer_result = None
        self.vote_tally = {}
        self.voted_out = None

    # ------------------------------------------------------------------
    # In trạng thái (📌 yêu cầu: in được state mỗi vòng)
    # ------------------------------------------------------------------
    def print_state(self):
        """In snapshot trạng thái hiện tại – gọi cuối mỗi vòng."""
        sep = "-" * 40
        print(f"\n{sep}")
        print(f"  STATE | Round {self.round} | Phase: {self.phase.upper()}")
        print(sep)
        print(f"  Alive ({len(self.alive)}): {', '.join(self.alive) if self.alive else '(none)'}")
        print(f"  Dead  ({len(self.dead)}):  {', '.join(self.dead) if self.dead else '(none)'}")
        print(f"  Events this round:")
        round_events = [e for e in self.events if e["round"] == self.round]
        if round_events:
            for e in round_events:
                print(f"    [{e['type']:8}] {e['msg']}")
        else:
            print("    (chua co su kien)")
        print(sep)

    def __repr__(self):
        return (
            f"GameState(round={self.round}, phase={self.phase!r}, "
            f"alive={self.alive}, dead={self.dead})"
        )

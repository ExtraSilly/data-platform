"""GameEngine – khởi tạo và chạy toàn bộ vòng lặp game."""

import random
from agents.werewolf_agent   import WerewolfAgent
from agents.seer_agent       import SeerAgent
from agents.doctor_agent     import DoctorAgent
from agents.villager_agent   import VillagerAgent
from agents.global_memory    import get_global_memory
from .game_state  import GameState
from .game_master import GameMaster
from .logger      import GameLogger


DEFAULT_CONFIG = {
    "num_players": 8,
    "num_werewolves": 2,
    "player_names": ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Henry"],
}
# Tỉ lệ cân bằng: 8 người, 2 wolves
# Sau đêm: 2:5 → vote đúng: 1:5 (dân thắng lợi lớn)
#                 vote sai: 2:4 (dân vẫn còn lợi thế)
# Cần ≥ 3 vòng để wolves có thể thắng → đủ thời gian cho Seer hoạt động


def setup_game(config: dict = None) -> tuple[dict, GameState]:
    """Khởi tạo agents và GameState."""
    cfg = config or DEFAULT_CONFIG
    names: list[str] = cfg["player_names"][: cfg["num_players"]]
    num_wolves: int = cfg["num_werewolves"]

    roles = (
        ["werewolf"] * num_wolves
        + ["seer"]
        + ["doctor"]
        + ["villager"] * (len(names) - num_wolves - 2)
    )
    random.shuffle(roles)
    assignment = dict(zip(names, roles))
    wolf_names = [n for n, r in assignment.items() if r == "werewolf"]

    agents: dict = {}
    for name, role in assignment.items():
        if role == "werewolf":
            teammates = [w for w in wolf_names if w != name]
            agents[name] = WerewolfAgent(name, teammates=teammates)
        elif role == "seer":
            agents[name] = SeerAgent(name)
        elif role == "doctor":
            agents[name] = DoctorAgent(name)
        else:
            agents[name] = VillagerAgent(name)

    for agent in agents.values():
        agent.init_belief(names)

    # Khởi tạo GameState với 3 trường cốt lõi: round, phase, events
    state = GameState(players=names)
    # Lưu role_map vào state để engine dùng sau game
    state.role_map = assignment

    print("\n" + "=" * 50)
    print("  KHOI DAU TRAN DAU")
    print("=" * 50)
    print(f"Nguoi choi: {', '.join(names)}")
    print("Phan vai (bi mat):")
    for name, role in assignment.items():
        print(f"  {name:10} -> {role}")
    # Hiển thị trọng số đã học từ GlobalMemory
    gm_mem = get_global_memory()
    if gm_mem.games_played >= 5:
        w = gm_mem.get_weights()
        print(f"  [Cross-game learning] α={w['alpha']} β={w['beta']} γ={w['gamma']} "
              f"(tu {gm_mem.games_played} van)")
    print("=" * 50)

    # In state ban đầu
    state.print_state()

    return agents, state


def run_game(config: dict = None, max_rounds: int = 10):
    """Vòng lặp chính: Night → Day → Vote → check end → log → print_state."""
    cfg = config or DEFAULT_CONFIG
    agents, state = setup_game(cfg)
    gm = GameMaster(agents, state)
    logger = GameLogger(cfg)
    winner = None

    # GameMaster thông báo vai trò bí mật cho từng agent
    gm.announce_roles()

    for _ in range(max_rounds):
        state.next_round()
        logger.start_round(state.round)   # bắt đầu record mới

        # ── Đêm ──────────────────────────────────────────────────────
        night_log = gm.night_phase()
        logger.log_night(night_log)       # ghi record đêm

        winner = gm.check_end()
        if winner:
            logger.end_round()
            break

        # ── Ngày ─────────────────────────────────────────────────────
        day_log = gm.day_phase()
        logger.log_day(day_log)           # ghi record ngày

        winner = gm.check_end()
        logger.end_round()                # hoàn tất record round này

        # In state sau mỗi vòng
        state.print_state()

        if winner:
            break

    # Hết số vòng mà chưa ai thắng
    if winner is None:
        print("\n" + "=" * 50)
        print("  KET QUA: HOA (het so vong toi da)")
        print("=" * 50)
        winner = "draw"

    print(f"Nguoi song sot: {', '.join(state.alive)}")

    # Lưu log ra file JSON
    game_log = logger.save(winner, state.alive, state.dead)

    # ── Cross-game learning: cập nhật GlobalMemory ────────────────────
    role_map = getattr(state, "role_map", {})
    if role_map:
        gm_mem = get_global_memory()
        gm_mem.update_from_game(
            {"result": winner, "rounds": logger.rounds},
            role_map,
        )
        if gm_mem.games_played % 5 == 0:   # in tóm tắt mỗi 5 ván
            print(gm_mem.summary())

    return state

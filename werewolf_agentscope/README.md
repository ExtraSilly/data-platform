# Ma Sói – AgentScope Multi-Agent Simulation

Mô phỏng trò chơi Ma Sói bằng hệ thống AI đa tác tử với BeliefModel, SocialReasoning và cross-game learning.

## Cấu trúc

```
werewolf_agentscope/
├── run_game.py              # Entry point: chạy 1 ván game
├── analysis.py              # Phân tích 6 chỉ số từ log JSON
├── experiment.py            # So sánh 3 loại agent (50 ván/chế độ)
├── data_analysis.py         # ETL + Pearson correlation + Information Gain
├── agents/
│   ├── base_agent.py        # Lớp cha: Memory + BeliefModel + SocialReasoning
│   ├── belief.py            # BeliefModel 3 chiều với trọng số α/β/γ
│   ├── social_reasoning.py  # 4 pattern: leader/contrarian/silent/coordinated
│   ├── global_memory.py     # Cross-game learning singleton
│   ├── werewolf_agent.py    # AI Ma Sói
│   ├── seer_agent.py        # AI Tiên Tri (3-tier disclosure)
│   ├── doctor_agent.py      # AI Bác Sĩ
│   ├── villager_agent.py    # AI Dân Thường
│   ├── random_agent.py      # Baseline ngẫu nhiên
│   └── rule_based_agent.py  # Heuristic cứng
├── game/
│   ├── game_engine.py       # Vòng lặp chính
│   ├── game_master.py       # Trọng tài trung lập
│   ├── game_state.py        # Trạng thái toàn cục
│   └── logger.py            # Ghi log JSON
└── data/
    ├── logs/                # game_*.json (gitignored)
    └── global_memory.json   # Trọng số α/β/γ học từ nhiều ván
```

## Chạy game

```bash
# Chạy 1 ván game
python -X utf8 run_game.py

# Phân tích toàn bộ log
python -X utf8 analysis.py

# So sánh 3 loại agent
python -X utf8 experiment.py

# ETL + Correlation + Feature Importance
python -X utf8 data_analysis.py
```

## Luật chơi

| Yếu tố | Giá trị |
|---|---|
| Số người | 8 (2 wolves, 1 seer, 1 doctor, 4 villagers) |
| Pha chơi | Đêm → Ngày (thảo luận) → Bỏ phiếu |
| Dân thắng | Diệt hết Ma Sói |
| Ma Sói thắng | wolves ≥ dân còn sống |

## Thiết kế AI Agent

Mỗi agent có **3 thành phần bắt buộc**:

1. **Memory** – `self.memory`: danh sách quan sát theo round
2. **BeliefModel** – `α×vote + β×speech + γ×seer − trust×0.3`
3. **Decision Policy** – `decide(phase)` trừu tượng, từng vai hiện thực riêng

## Kết quả thực nghiệm (150 ván)

| Loại agent | Dân thắng | Vote đúng | Bác Sĩ cứu đúng |
|---|---|---|---|
| Random (baseline) | 10% | 22.4% | 24.1% |
| Rule-Based | **52%** | 38.6% | 28.5% |
| Belief+SR | 32% | **41.2%** | **33.9%** |

# Ma Sói – AgentScope Multi-Agent Simulation

Mô phỏng trò chơi Ma Sói bằng hệ thống AI đa tác tử.

## Cấu trúc

```
werewolf_agentscope/
├── agents/
│   ├── base_agent.py        # Lớp cha: Memory + Belief + Policy
│   ├── werewolf_agent.py    # Vai Ma Sói
│   ├── seer_agent.py        # Vai Tiên Tri
│   ├── doctor_agent.py      # Vai Bác Sĩ
│   └── villager_agent.py    # Vai Dân Thường
├── game/
│   ├── game_state.py        # Trạng thái toàn cục
│   ├── game_master.py       # Điều phối Night/Day/Vote
│   └── game_engine.py       # Vòng lặp game chính
├── data/logs/               # Log ván chơi
├── run_game.py              # Entry point
└── README.md
```

## Chạy game

```bash
python run_game.py
```

## Luật chơi

| Yếu tố       | Giá trị                        |
|--------------|-------------------------------|
| Số người     | 6–8                           |
| Ma Sói       | 2                             |
| Tiên Tri     | 1 (kiểm tra vai ban đêm)      |
| Bác Sĩ       | 1 (cứu người ban đêm)         |
| Dân Thường   | số còn lại                    |
| Pha chơi     | Đêm → Ngày (thảo luận) → Bỏ phiếu |
| Điều kiện thắng | Dân: diệt hết Ma Sói / Ma Sói: bằng hoặc hơn số Dân |

## Thiết kế AI Agent

Mỗi agent có **3 thành phần bắt buộc**:

1. **Memory** – `self.memory`: danh sách quan sát theo round  
2. **Belief** – `self.belief`: điểm nghi ngờ 0.0–1.0 cho từng người  
3. **Decision Policy** – `night_action()`, `discuss()`, `vote()` theo vai trò

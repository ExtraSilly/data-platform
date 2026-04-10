# Ma Sói – AI Đa Tác Tử (Werewolf Multi-Agent System)

> Mô phỏng trò chơi Ma Sói bằng hệ thống AI đa tác tử có BeliefModel, SocialReasoning và cross-game learning.  
> Đồ án môn **Nền Tảng Dữ Liệu**.

---

## Tổng quan

Dự án xây dựng một hệ thống **Multi-Agent System (MAS)** mô phỏng trò chơi Ma Sói, trong đó mỗi agent (người chơi AI) hoạt động độc lập với:

- **Memory** – ghi nhớ quan sát theo từng round
- **BeliefModel** – mô hình niềm tin 3 chiều (vote / speech / seer oracle)
- **SocialReasoning** – phân tích hành vi xã hội (leader, contrarian, silence, coordinated attack)
- **Decision Policy** – chiến lược riêng theo vai trò

Hệ thống cũng có **cross-game learning**: trọng số BeliefModel được điều chỉnh tự động sau mỗi ván qua `GlobalMemory`.

---

## Cấu trúc dự án

```
werewolf_agentscope/
├── run_game.py              # Entry point: chạy 1 ván game
├── analysis.py              # Phân tích 6 chỉ số từ log JSON
├── experiment.py            # So sánh khoa học 3 loại agent (150 ván)
├── data_analysis.py         # ETL + Pearson correlation + Information Gain
│
├── agents/
│   ├── base_agent.py        # Lớp cha trừu tượng (Memory + Belief + Policy)
│   ├── belief.py            # BeliefModel 3 chiều với trọng số α/β/γ
│   ├── social_reasoning.py  # Phân tích hành vi xã hội (4 pattern)
│   ├── global_memory.py     # Cross-game learning singleton
│   ├── werewolf_agent.py    # AI Ma Sói
│   ├── seer_agent.py        # AI Tiên Tri (private oracle, 3-tier disclosure)
│   ├── doctor_agent.py      # AI Bác Sĩ
│   ├── villager_agent.py    # AI Dân Thường
│   ├── random_agent.py      # Baseline: quyết định ngẫu nhiên
│   └── rule_based_agent.py  # Heuristic cứng, không BeliefModel
│
├── game/
│   ├── game_engine.py       # Vòng lặp chính + tích hợp GlobalMemory
│   ├── game_master.py       # Trọng tài trung lập (không có AI)
│   ├── game_state.py        # Trạng thái toàn cục (round/phase/events)
│   └── logger.py            # Ghi log JSON mỗi ván
│
└── data/
    ├── logs/                # game_*.json (gitignored)
    └── global_memory.json   # Trọng số học được từ nhiều ván
```

---

## Cài đặt

```bash
# Clone repo
git clone https://github.com/ExtraSilly/data-platform.git
cd data-platform/werewolf_agentscope

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Cài dependencies
pip install -r requirements.txt
```

---

## Cách chạy

```bash
cd werewolf_agentscope

# Chạy 1 ván game (in log + lưu JSON)
python -X utf8 run_game.py

# Phân tích toàn bộ ván đã chạy (6 chỉ số thống kê)
python -X utf8 analysis.py

# Thực nghiệm khoa học: so sánh 3 loại agent (50 ván/chế độ)
python -X utf8 experiment.py

# ETL + Pearson correlation + Information Gain
python -X utf8 data_analysis.py
```

> **Lưu ý Windows:** cần flag `-X utf8` để hiển thị tiếng Việt đúng encoding.

---

## Luật chơi

| Yếu tố | Giá trị |
|---|---|
| Số người chơi | 8 |
| Ma Sói | 2 |
| Tiên Tri | 1 (kiểm tra vai ban đêm) |
| Bác Sĩ | 1 (cứu người ban đêm) |
| Dân Thường | 4 |
| Pha chơi | Đêm → Ngày (thảo luận) → Bỏ phiếu |
| Dân thắng | Diệt hết Ma Sói |
| Ma Sói thắng | Số wolves ≥ số dân còn sống |

**Thứ tự đêm:** Werewolf chọn giết → Doctor cứu → Seer kiểm tra → Resolve

---

## Thiết kế AI

### BeliefModel – Mô hình niềm tin 3 chiều

```
Belief(player) = α × vote_score + β × speech_score + γ × seer_score − trust × 0.3
```

| Chiều | Trọng số mặc định | Ý nghĩa |
|---|---|---|
| α | 0.40 | Hành vi bỏ phiếu |
| β | 0.35 | Hành vi phát biểu / cáo buộc |
| γ | 0.25 | Kết quả oracle của Tiên Tri |

Sau 5+ ván, trọng số tự động điều chỉnh từ `GlobalMemory`.

### SocialReasoning – 4 Pattern phát hiện

| Pattern | Logic | Tác động |
|---|---|---|
| Leader | Đề xuất target được đa số follow | +0.12 × follow_ratio |
| Contrarian | Vote ngược số đông liên tục | +0.08 |
| Silent | Phát biểu < 50% mức trung bình | +0.06 |
| Coordinated Attack | 2+ người cùng đổ nghi 1 target | +0.15 × count |

### Chiến lược từng vai

- **Ma Sói**: Giết người ảnh hưởng cao nhưng chưa bị nghi (`influence×0.6 + (1−suspicion)×0.4`)
- **Tiên Tri**: Oracle riêng tư, tiết lộ theo 3 mức tùy tình huống (nguy cấp / bình thường / ẩn)
- **Bác Sĩ**: Threat score đa chiều, không cứu cùng 1 người 2 đêm liên tiếp
- **Dân Thường**: Tích lũy bằng chứng từ memory, apply SocialReasoning trước vote

---

## Kết quả thực nghiệm

### So sánh 3 loại agent (50 ván/chế độ)

| Chỉ số | Random | Rule-Based | Belief+SR |
|---|---|---|---|
| Tỉ lệ dân thắng | 10% | **52%** | 32% |
| Vote đúng Ma Sói | 22.4% | 38.6% | **41.2%** |
| Bác Sĩ cứu đúng | 24.1% | 28.5% | **33.9%** |

**Nhận xét:** Rule-Based thắng nhiều hơn nhờ logic Seer đơn giản và quyết đoán. Belief+SR có vote accuracy và doctor save rate tốt nhất – ưu thế trong game dài hơn.

### Phân tích dữ liệu (Pearson Correlation)

| Feature | r với correct_vote |
|---|---|
| `vote_consensus` | **−0.324** (tương quan mạnh nhất) |
| `vote_diversity` | +0.21 |
| `seer_checked` | +0.15 |

**Phát hiện:** Khi cả làng vote cùng 1 người với sự đồng thuận cao, thường là Ma Sói đang thao túng dư luận.

---

## Báo cáo

Xem [report.md](report.md) để có báo cáo tiến độ đầy đủ gồm kiến trúc hệ thống, kết quả thực nghiệm, phân tích dữ liệu và các vấn đề kỹ thuật đã giải quyết.

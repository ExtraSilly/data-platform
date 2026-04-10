# BÁO CÁO TIẾN ĐỘ DỰ ÁN
## Ứng dụng AI Đa Tác Tử – Mô Phỏng Trò Chơi Ma Sói (Werewolf)
### Môn: Nền Tảng Dữ Liệu

**Ngày cập nhật:** 10/04/2026  
**Trạng thái tổng thể:** Hoàn thành – Có dữ liệu thực nghiệm đầy đủ 3 chế độ agent

---

## 1. TỔNG QUAN TIẾN ĐỘ

| Hạng mục | Bước | Trạng thái |
|---|---|---|
| Cấu trúc project & file skeleton | Bước 3 | Hoàn thành |
| GameState – trạng thái game | Bước 4 | Hoàn thành |
| BaseAgent – khung chung | Bước 5 | Hoàn thành |
| WerewolfAgent | Bước 6 | Hoàn thành |
| SeerAgent | Bước 7 | Hoàn thành |
| DoctorAgent | Bước 8 | Hoàn thành |
| VillagerAgent | Bước 9 | Hoàn thành |
| GameMaster – trọng tài | Bước 10 | Hoàn thành |
| Pha Đêm (Night Phase) | Bước 11 | Hoàn thành |
| Pha Ngày & bỏ phiếu (Day Phase) | Bước 12 | Hoàn thành |
| Điều kiện thắng – kết thúc game | Bước 13 | Hoàn thành |
| Logging JSON | Bước 14 | Hoàn thành |
| Phân tích hậu game (analysis.py) | Bước 15 | Hoàn thành |
| BeliefModel nâng cấp 3 chiều | Nâng cao 1.1 | Hoàn thành |
| SocialReasoning 4 pattern | Nâng cao 1.2 | Hoàn thành |
| Seer/Doctor chiến lược | Nâng cao 1.3 | Hoàn thành |
| So sánh 3 loại agent (experiment.py) | Nâng cao 2.1 | Hoàn thành |
| Cross-game learning (GlobalMemory) | Nâng cao 2.2 | Hoàn thành |
| ETL + phân tích dữ liệu (data_analysis.py) | Nâng cao 2.3 | Hoàn thành |

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Cấu trúc Source Code

```
werewolf_agentscope/
├── run_game.py              # Entry point: chạy 1 ván game đầy đủ
├── analysis.py              # Phân tích 6 chỉ số từ file JSON đã lưu
├── experiment.py            # So sánh khoa học 3 chế độ agent (50 ván/chế độ)
├── data_analysis.py         # ETL pipeline + Pearson correlation + Information Gain
│
├── agents/
│   ├── base_agent.py        # Lớp cha trừu tượng (memory + belief + social)
│   ├── belief.py            # BeliefModel 3 chiều có trọng số α/β/γ
│   ├── social_reasoning.py  # Phân tích hành vi xã hội (4 detector pattern)
│   ├── global_memory.py     # Cross-game learning singleton
│   ├── werewolf_agent.py    # AI Ma Sói – chiến lược giết + ngụy trang
│   ├── seer_agent.py        # AI Tiên Tri – oracle riêng tư, 3-tier tiết lộ
│   ├── doctor_agent.py      # AI Bác Sĩ – bảo vệ chiến lược
│   ├── villager_agent.py    # AI Dân Thường – suy luận từ quan sát
│   ├── random_agent.py      # Baseline: quyết định hoàn toàn ngẫu nhiên
│   └── rule_based_agent.py  # Heuristic cứng, không có BeliefModel
│
├── game/
│   ├── game_engine.py       # Vòng lặp chính + tích hợp GlobalMemory
│   ├── game_master.py       # Trọng tài trung lập (không có AI)
│   ├── game_state.py        # Trạng thái game toàn cục (round/phase/events)
│   └── logger.py            # Ghi log JSON với timestamp microsecond
│
└── data/
    ├── logs/                # game_*.json – mỗi ván 1 file
    └── global_memory.json   # Trọng số α/β/γ học từ nhiều ván
```

### 2.2. Sơ đồ luồng dữ liệu

```
┌─────────────────────────────────────────────────────────────┐
│                     run_game.py / experiment.py              │
└─────────────────────┬───────────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │  GameEngine    │  setup_game() → run_game()
              └───────┬────────┘
                      │ gọi
         ┌────────────▼────────────┐
         │       GameMaster        │  điều phối pha game
         └────┬───────┬────────────┘
              │       │
     ┌────────▼──┐ ┌──▼──────────┐
     │  Night    │ │  Day Phase  │
     │  Phase    │ │ Discuss+Vote│
     └────┬──────┘ └──┬──────────┘
          │            │
     ┌────▼────────────▼────────────────────────────────────┐
     │              Agents (Belief + SocialReasoning)        │
     │   Wolf | Seer | Doctor | Villager | Random | RuleBased│
     └────────────────────┬─────────────────────────────────┘
                          │ sau ván
              ┌───────────▼───────────┐
              │     GameLogger        │  → game_*.json
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │    GlobalMemory       │  học α/β/γ
              └───────────┬───────────┘
                          │
     ┌────────────────────▼──────────────────────────────────┐
     │   data_analysis.py: ETL → Correlation → Feature Rank  │
     └───────────────────────────────────────────────────────┘
```

---

## 3. CHI TIẾT CÁC THÀNH PHẦN

### 3.1. BaseAgent – Nền tảng tác tử

```python
# ba thành phần cốt lõi của mỗi agent
self.memory        = []           # danh sách sự kiện quan sát
self.belief        = {}           # dict belief đơn giản (tương thích ngược)
self._belief_model = BeliefModel  # model 3 chiều đầy đủ
self._social       = SocialReasoning  # tích hợp phân tích hành vi
```

- `observe(event)`: lưu sự kiện công khai vào memory
- `remember(event)`: lưu sự kiện riêng tư (vd: Seer check result)
- `recall(last_n)`: đọc n sự kiện gần nhất
- `_sync_belief()`: đồng bộ BeliefModel → dict belief; bảo vệ kết quả Seer khỏi bị ghi đè
- `apply_social_reasoning()`: cập nhật belief từ SocialReasoning trước mỗi vote
- `decide()`: **abstract** – mỗi agent type hiện thực riêng

### 3.2. BeliefModel – Mô hình niềm tin 3 chiều

**Công thức:**
```
Belief(player) = α × vote_score + β × speech_score + γ × seer_score − trust_score × 0.3
```

| Chiều | Trọng số mặc định | Nguồn bằng chứng |
|---|---|---|
| α (vote behavior) | 0.40 | Ai bỏ phiếu chống ai |
| β (speech behavior) | 0.35 | Ai cáo buộc ai trong thảo luận |
| γ (seer oracle) | 0.25 | Kết quả kiểm tra của Tiên Tri |

Sau 5+ ván, trọng số được **GlobalMemory điều chỉnh tự động** dựa trên dữ liệu thực nghiệm.

### 3.3. SocialReasoning – Phân tích hành vi xã hội

| Pattern | Logic | Tác động belief |
|---|---|---|
| `detect_leaders` | Ai đề xuất target được đa số follow | +0.12 × follow_ratio |
| `detect_contrarians` | Ai vote ngược số đông liên tục | +0.08 |
| `detect_silent` | Ai phát biểu < 50% mức trung bình | +0.06 |
| `detect_coordinated_attack` | 2+ người cùng đổ nghi 1 target | +0.15 × count (từng kẻ tấn công) |

**Tại sao coordinated_attack quan trọng:** Ma Sói (2 người) thường ngầm thống nhất vote cùng người → cả 2 đều bị đánh dấu nghi ngờ +0.30, giúp dân làng phát hiện.

### 3.4. Chiến lược từng Agent

**WerewolfAgent**
- Đêm: `kill_score(t) = influence(t) × 0.6 + (1 − suspicion(t)) × 0.4`
  - Ưu tiên người có ảnh hưởng cao (Seer, người uy tín) nhưng chưa bị nghi
  - Không bao giờ nhắm đồng đội
- Ngày: đổ nghi sang người có belief cao nhất trong dân làng

**SeerAgent** – 3-tier tiết lộ:
1. **Nguy cấp** (≤4 sống hoặc biết ≥30% còn sống là sói): khai thẳng danh tính + tên Ma Sói
2. **Có bằng chứng nhưng chưa nguy cấp**: gợi ý kín ("tôi biết ai đó không phải dân...")
3. **Chưa chắc chắn**: ẩn danh, gợi ý gián tiếp dựa trên belief

**DoctorAgent**
- Threat score: `was_targeted × 2.0 + influence × 0.7 + trust × 0.3`
- Không cứu cùng 1 người 2 đêm liên tiếp (`self.last_saved` tracking)

**VillagerAgent**
- Cập nhật belief từ memory: mention_count × 0.03, accusation_of_dead × 0.1
- Vote: `max(self.belief, key=self.belief.get)` sau khi apply SocialReasoning

### 3.5. GlobalMemory – Học liên ván

```python
# Lưu tại: data/global_memory.json
{
  "games_played": 50,
  "villager_wins": 16,
  "learned_weights": {"alpha": 0.354, "beta": 0.456, "gamma": 0.190},
  "vote_accuracy": {
    "seer":     {"correct": ..., "total": ...},
    "villager": {"correct": ..., "total": ...},
    ...
  }
}
```

**Logic cập nhật trọng số:**
- Nếu Seer vote chính xác cao → tăng γ (tin oracle hơn)
- Nếu Villager vote chính xác cao → tăng α (tin vote behavior hơn)
- β = 1 − α − γ (tự cân bằng)

---

## 4. HỆ THỐNG ETL & PHÂN TÍCH DỮ LIỆU

### 4.1. Pipeline ETL (data_analysis.py)

```
JSON Logs (game_*.json)
       │ Extract
       ▼
Đọc tất cả file game_*.json từ data/logs/
       │ Transform
       ▼
Mỗi round → 1 record (tabular)
  Features: night_kill, seer_checked, doctor_saved,
            vote_consensus, vote_diversity, n_voters
  Labels:   correct_vote, result_villager
       │ Load
       ▼
Phân tích Pearson Correlation + Information Gain
```

### 4.2. Feature Engineering

| Feature | Định nghĩa |
|---|---|
| `night_kill` | Đêm đó có người chết không (0/1) |
| `seer_checked` | Tiên Tri có kiểm tra đêm đó không (0/1) |
| `doctor_saved` | Bác Sĩ có cứu đêm đó không (0/1) |
| `vote_consensus` | max_votes / total_voters – mức độ tập trung phiếu |
| `vote_diversity` | unique_targets / total_voters – mức độ phân tán phiếu |

### 4.3. Kết quả Correlation (Pearson)

| Feature | r với correct_vote | r với result_villager |
|---|---|---|
| `vote_consensus` | **−0.324** | +0.08 |
| `vote_diversity` | +0.21 | −0.05 |
| `seer_checked` | +0.15 | +0.12 |
| `night_kill` | −0.09 | −0.07 |
| `doctor_saved` | +0.04 | +0.03 |

**Phát hiện chính:**
- `vote_consensus` cao (đồng thuận cao) **liên quan âm** với vote đúng Ma Sói
- Diễn giải: khi cả làng vote cùng 1 người với sự đồng thuận cao, thường là Ma Sói đã thành công dẫn dắt dư luận → loại oan dân
- `r > 0.2` được coi là tương quan có ý nghĩa thực tế

### 4.4. Feature Importance (Information Gain)

| Xếp hạng | Feature | IG |
|---|---|---|
| 1 | `vote_consensus` | 0.054 |
| 2 | `vote_diversity` | 0.031 |
| 3 | `seer_checked` | 0.018 |
| 4 | `night_kill` | 0.007 |
| 5 | `doctor_saved` | 0.003 |

**Kết luận:** `vote_consensus` là đặc trưng quan trọng nhất để dự đoán vote đúng – đây là tín hiệu về mức độ thao túng của Ma Sói.

---

## 5. THỰC NGHIỆM KHOA HỌC – SO SÁNH 3 LOẠI AGENT

### 5.1. Thiết kế thực nghiệm

| Thông số | Giá trị |
|---|---|
| Số ván mỗi chế độ | 50 |
| Tổng số ván | 150 |
| Cấu hình | 8 người, 2 wolves |
| Max rounds | 10 |
| Seed | Cố định (`seed = i × 97 + 13`) để tái hiện được |

**Ba chế độ agent:**
- `random` – RandomAgent: quyết định hoàn toàn ngẫu nhiên (baseline)
- `rule_based` – RuleBasedAgent: heuristic if/else, không có BeliefModel
- `belief` – Belief+SocialReasoning (hệ thống đề xuất): BeliefModel 3 chiều + SocialReasoning

### 5.2. Kết quả so sánh

| Chỉ số | Random (Baseline) | Rule-Based | Belief+SR (Đề xuất) |
|---|---|---|---|
| **Tỉ lệ dân thắng (%)** | 10.0% | **[52.0%]** | 32.0% |
| Số vòng trung bình | 2.62 | **[3.12]** | 2.94 |
| Min / Max vòng | 1/6 | 1/8 | 1/7 |
| **Vote đúng Ma Sói (%)** | 22.4% | 38.6% | **[41.2%]** |
| **Bác Sĩ cứu thành công (%)** | 24.1% | 28.5% | **[33.9%]** |
| **Tiên Tri tìm Ma Sói (%)** | 33.3% | 33.3% | 33.3% |

*([ ] = giá trị tốt nhất trong hàng)*

### 5.3. Phân tích kết quả

**Tại sao Rule-Based có win rate cao nhất (52%)?**
- RuleBasedAgent Seer có logic xác định wolf **cứng**: ngay khi tìm thấy wolf, đặt target = wolf đó và không thay đổi
- Không bị nhiễu bởi social pressure hay speech evidence phức tạp
- Heuristic đơn giản nhưng nhất quán → dân làng biết chính xác cần vote ai

**Tại sao Belief+SR có vote accuracy & doctor save rate tốt nhất?**
- BeliefModel tích lũy bằng chứng từ nhiều nguồn → vote chính xác hơn trong dài hạn
- DoctorAgent dùng threat score đa chiều → cứu đúng người bị nhắm hơn

**Tại sao Random < Belief+SR < Rule-Based về win rate?**
- Random không có chiến lược → Ma Sói dễ thắng
- Belief+SR phức tạp hơn → có thể "overthink" trong game ngắn (avg 3 vòng)
- Rule-Based đủ đơn giản và quyết đoán → hiệu quả trong game ngắn này

**Nhận xét khoa học:**
```
Random (10%) < Belief+SR (32%) < Rule-Based (52%)
```
Hệ thống đề xuất (Belief+SR) vượt qua Random baseline (+22%), nhưng rule-based đơn giản lại hiệu quả hơn trong bối cảnh game ngắn. Đây là minh chứng thực tế của bài toán **bias-variance tradeoff**: mô hình phức tạp hơn không nhất thiết tốt hơn khi dữ liệu ít (game ngắn ≤ 4 vòng).

---

## 6. CÁC VẤN ĐỀ KỸ THUẬT ĐÃ GIẢI QUYẾT

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `UnicodeEncodeError` | Windows terminal dùng cp1252, không hỗ trợ tiếng Việt | `python -X utf8` + `sys.stdout.reconfigure(encoding="utf-8")` |
| `KeyError 'source'` | Memory entries từ `observe()` dùng key `type`, không phải `source` | `.get("source") or .get("type", "?")` fallback |
| `AttributeError: alive_players` | Đổi tên field thành `alive` trong GameState | Cập nhật tất cả agent files |
| Ma Sói thắng 100% | 3 nguyên nhân: config 6 người quá ít; wolves vote cùng target; Frank echo tên người khác vào belief | Đổi sang 8 người; `detect_coordinated_attack`; tách `statement.split(" – ")[0]` |
| File log bị ghi đè | Nhiều game chạy trong cùng 1 giây | Timestamp với microsecond: `%Y%m%d_%H%M%S_%f` |
| Seer belief bị overwrite | SocialReasoning ghi đè kết quả oracle | `_sync_belief()` bảo vệ `seer_confirmed` không bị thay đổi |

### 6.1. Phân tích cân bằng game (toán học)

**Config 6 người (cũ – mất cân bằng):**
```
Bắt đầu: 2 wolves : 4 villagers
Sau đêm: 2 : 3 → check_end: 2 < 3 → tiếp tục
Vote sai: 2 : 2 → wolves ≥ villagers → MA SÓI THẮNG (chỉ 2 vòng!)
```

**Config 8 người (mới – cân bằng):**
```
Bắt đầu: 2 wolves : 6 villagers
Sau đêm 1: 2 : 5 → vote đúng: 1 : 5 (dân có lợi lớn)
Sau đêm 2: 1 : 4 → vote đúng: 0 : 4 → DÂN THẮNG
Sau đêm 2: 1 : 4 → vote sai: 1 : 3 → check: 1 < 3 → tiếp tục
```

---

## 7. KẾT QUẢ PHÂN TÍCH 60 VÁN ĐẦYTIÊN (analysis.py)

*(Dữ liệu từ 60 ván chạy với config Belief+SR – hệ thống đầy đủ)*

| Chỉ số | Giá trị |
|---|---|
| Ma Sói thắng | 48/60 (80%) |
| Dân thắng | 12/60 (20%) |
| Số vòng trung bình | 2.0 |
| Vote đúng Ma Sói | 31.7% (32/101 lượt) |
| Tiên Tri tìm đúng | 33.6% (37/110 lần check) |
| Bác Sĩ cứu đúng | 25.0% (26/104 đêm) |

---

## 8. CÁCH CHẠY HỆ THỐNG

```bash
cd werewolf_agentscope

# Chạy 1 ván game đầy đủ (in log + lưu JSON)
python -X utf8 run_game.py

# Phân tích 6 chỉ số từ tất cả ván đã lưu
python -X utf8 analysis.py

# Thực nghiệm khoa học: so sánh 3 chế độ agent (50 ván/chế độ, ~150 ván tổng)
python -X utf8 experiment.py

# Pipeline ETL + Pearson correlation + Information Gain
python -X utf8 data_analysis.py
```

**Cấu trúc dữ liệu đầu ra:**
- `data/logs/game_YYYYMMDD_HHMMSS_ffffff.json` – log từng ván
- `data/global_memory.json` – trọng số α/β/γ học từ nhiều ván

---

## 9. ĐIỂM MẠNH KỸ THUẬT

1. **Kiến trúc phân tầng rõ ràng**: Agent ↔ GameMaster ↔ GameState tách biệt hoàn toàn
2. **Information asymmetry đúng chuẩn**: Seer private oracle, Wolves biết nhau, Villagers mù hoàn toàn
3. **BeliefModel đa chiều**: Không random – tổng hợp 3 nguồn bằng chứng với trọng số học được
4. **Cross-game learning**: GlobalMemory điều chỉnh α/β/γ dựa trên hiệu quả thực nghiệm
5. **ETL pipeline hoàn chỉnh**: JSON → tabular → descriptive stats → correlation → feature importance
6. **Thực nghiệm có kiểm soát**: Seed cố định, 50 ván/chế độ, baseline rõ ràng
7. **GameMaster trung lập**: Không có AI, không có memory/belief – đảm bảo fair play

---

## 10. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

| Hạn chế | Đánh giá |
|---|---|
| Rule-Based vượt Belief+SR về win rate | Đây là kết quả khoa học hợp lệ – bias-variance tradeoff |
| Game ngắn (avg 2–3 vòng) | SocialReasoning cần ≥4 vòng để tích lũy đủ bằng chứng |
| Agent dùng rule-based, không LLM | Phù hợp với scope môn Nền tảng Dữ liệu |
| Chưa tích hợp AgentScope thật | Dùng custom Python architecture tương đương |

**Hướng mở rộng tiềm năng:**
- Kết nối Claude API / Ollama để generate ngôn ngữ tự nhiên thực sự
- Tích hợp `agentscope.agents.AgentBase` chính thức
- Thêm vai trò mới: Hunter, Witch, Mayor
- Visualization: belief heatmap, vote network graph theo từng round

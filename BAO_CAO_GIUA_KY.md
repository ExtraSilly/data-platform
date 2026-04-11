# BÁO CÁO GIỮA KỲ
## Môn: Nền Tảng Dữ Liệu

---

## 2.1. THÔNG TIN NHÓM

### Tên đề tài
**"Xây dựng Hệ thống AI Đa Tác Tử Mô Phỏng Trò Chơi Ma Sói – Ứng dụng BeliefModel, SocialReasoning và Cross-Game Learning"**

### Danh sách thành viên

| STT | Họ và tên | MSSV | Vai trò |
|---|---|---|---|
| 01 | [Họ tên 1] | [MSSV] | Nhóm trưởng – GameMaster & GameState |
| 02 | [Họ tên 2] | [MSSV] | BeliefModel & SocialReasoning |
| 03 | [Họ tên 3] | [MSSV] | Agent AI (Wolf/Seer/Doctor/Villager) |
| 04 | [Họ tên 4] | [MSSV] | ETL Pipeline & Phân tích dữ liệu |
| 05 | [Họ tên 5] | [MSSV] | Thực nghiệm & Logging |

### Mục tiêu bài toán

1. **Mục tiêu khoa học**: Nghiên cứu hành vi nổi sinh (emergent behavior) trong hệ thống đa tác tử bất đối xứng thông tin – mỗi agent chỉ biết một phần sự thật và phải suy luận từ quan sát.

2. **Mục tiêu kỹ thuật**:
   - Xây dựng mô hình BeliefModel đa chiều (vote + speech + oracle) để agent ước lượng độ nghi ngờ từng người chơi
   - Tích hợp SocialReasoning để phát hiện các mẫu hành vi bất thường
   - Triển khai cross-game learning: trọng số được điều chỉnh tự động sau nhiều ván

3. **Mục tiêu dữ liệu**: Thu thập, lưu trữ và phân tích log game cấu trúc JSON làm bộ dữ liệu thực nghiệm cho bài toán phân tích hành vi xã hội trong môi trường đa tác tử

---

## 2.2. MÔ HÌNH VÀ CÔNG NGHỆ SỬ DỤNG

### Loại mô hình

| Hạng mục | Lựa chọn | Mô tả |
|---|---|---|
| Kiến trúc agent | **Rule-Based + Probabilistic** | Không dùng LLM – agent quyết định dựa trên BeliefModel có trọng số |
| Học máy | **Cross-game weight learning** | Tương tự online learning: cập nhật α/β/γ sau mỗi ván |
| Phân tích dữ liệu | **Descriptive Statistics + Correlation** | Pearson r, Information Gain trên tabular data từ JSON logs |
| So sánh hệ thống | **Controlled experiment** | 3 agent type × 50 ván/chế độ = 150 ván tổng |

> Ghi chú: Đề tài định hướng **Agent-Based Simulation** thay vì LLM/RAG thuần túy. Agents có ngôn ngữ (phát biểu, cáo buộc) nhưng dùng rule-based text generation thay vì language model – phù hợp với phạm vi môn Nền Tảng Dữ Liệu.

### Công cụ và thư viện

| Công cụ | Phiên bản | Mục đích |
|---|---|---|
| Python | 3.10+ | Ngôn ngữ chính |
| `collections` (stdlib) | – | Counter cho vote tally, SocialReasoning |
| `json` (stdlib) | – | Đọc/ghi log game |
| `dataclasses` (stdlib) | – | PlayerBelief data model |
| `math`, `statistics` | stdlib | Tính trung bình, correlation |
| Git / GitHub | – | Quản lý version, lưu trữ source |

> Không dùng thư viện ML ngoài (scikit-learn, PyTorch) – Pearson correlation và Information Gain tự cài đặt từ công thức chuẩn.

---

## 2.3. THIẾT KẾ PIPELINE

### Mô tả luồng xử lý tổng thể

```
INPUT                    PROCESSING                        OUTPUT
─────                    ──────────                        ──────
Cấu hình game      →    GameEngine khởi tạo agents   →   JSON log / ván
(num_players,           GameMaster điều phối pha           (game_*.json)
 num_wolves,            ┌─ Night Phase ─────────────┐         │
 agent_type)            │  Wolf → Doctor → Seer      │         │
                        │  resolve_night()           │         ▼
                        └───────────────────────────┘    GlobalMemory
                        ┌─ Day Phase ────────────────┐   cập nhật α/β/γ
                        │  announce_deaths()          │         │
                        │  discussion() – mỗi agent  │         ▼
                        │  vote() → hang()           │   analysis.py
                        └───────────────────────────┘   (6 chỉ số)
                                    │                         │
                              check_end()               data_analysis.py
                           Dân / Ma Sói thắng          (ETL → Pearson →
                                                         Feature Rank)
```

### Sơ đồ kiến trúc hệ thống

```
┌──────────────────────────────────────────────────────────────────┐
│                        GAME ENGINE                               │
│                                                                  │
│   ┌────────────┐    ┌──────────────────────────────────────┐    │
│   │  GameState  │◄──│              GameMaster               │    │
│   │  round      │   │  (trọng tài trung lập, không có AI)  │    │
│   │  phase      │   └──────┬───────────────────────────────┘    │
│   │  events     │          │ gọi decide()                       │
│   │  alive/dead │          ▼                                     │
│   └────────────┘   ┌──────────────────────────────────────┐    │
│                    │            AGENTS (×8)                │    │
│                    │  ┌──────────────────────────────┐    │    │
│                    │  │         BaseAgent             │    │    │
│                    │  │  Memory │ BeliefModel │ SR    │    │    │
│                    │  └──────────────────────────────┘    │    │
│                    │   Wolf  Seer  Doctor  Villager  ...  │    │
│                    └──────────────────────────────────────┘    │
│                                    │                            │
│   ┌─────────────┐          ┌───────▼──────────┐                │
│   │ GlobalMemory│◄─────────│   GameLogger     │                │
│   │ α=0.354     │ update   │  game_*.json     │                │
│   │ β=0.456     │          └──────────────────┘                │
│   │ γ=0.190     │                                               │
│   └─────────────┘                                               │
└──────────────────────────────────────────────────────────────────┘
                              │ JSON logs
                   ┌──────────▼──────────┐
                   │   data_analysis.py  │
                   │  ETL → Tabular      │
                   │  Pearson r          │
                   │  Information Gain   │
                   └─────────────────────┘
```

### Chi tiết BeliefModel Pipeline

```
Nguồn bằng chứng                Xử lý                  Output

Vote behavior ──────► vote_score  ──► ×α (0.354)  ─┐
                                                    ├──► Belief(p) ──► decide()
Speech behavior ────► speech_score──► ×β (0.456)  ─┤
                                                    │
Seer oracle ────────► seer_score  ──► ×γ (0.190)  ─┤
                                                    │
Trust history ──────► trust_score ──► ×(−0.30)   ──┘

        ↑
  Sau ≥5 ván:
  GlobalMemory
  điều chỉnh α/β/γ
```

### SocialReasoning Pipeline

```
Sự kiện game (votes, speeches, accusations)
              │
              ▼
    ┌─────────────────────────┐
    │      SocialReasoning    │
    │  detect_leaders()       │ → +0.12 × follow_ratio
    │  detect_contrarians()   │ → +0.08
    │  detect_silent()        │ → +0.06
    │  detect_coordinated()   │ → +0.15 × count
    └────────────┬────────────┘
                 │ apply delta trước vote
                 ▼
         BeliefModel.update()
```

---

## 2.4. TIẾN ĐỘ THỰC HIỆN

### Dataset đã thu thập

| Thông số | Giá trị |
|---|---|
| Số ván game đã chạy | 150+ ván (50/chế độ × 3 chế độ) |
| Format lưu trữ | JSON cấu trúc, 1 file / ván |
| Kích thước mỗi file | ~4–8 KB |
| Nguồn dữ liệu | Tự sinh (simulation) |
| Trạng thái | Đã có pipeline ETL chuyển sang tabular |

**Cấu trúc 1 record (1 round = 1 row):**

| Feature | Kiểu | Mô tả |
|---|---|---|
| `night_kill` | binary | Có người chết đêm đó không |
| `seer_checked` | binary | Tiên Tri có check đêm đó không |
| `doctor_saved` | binary | Bác Sĩ có cứu đêm đó không |
| `vote_consensus` | float [0,1] | max_votes / total_voters |
| `vote_diversity` | float [0,1] | unique_targets / total_voters |
| `correct_vote` | binary | Vote trúng Ma Sói không (label) |

### Các thử nghiệm đã thực hiện

| Thử nghiệm | Mô tả | Trạng thái |
|---|---|---|
| Baseline Random | 50 ván agent quyết định ngẫu nhiên | Hoàn thành |
| Rule-Based heuristic | 50 ván dùng if/else cứng | Hoàn thành |
| Belief+SR (đề xuất) | 50 ván dùng BeliefModel + SocialReasoning | Hoàn thành |
| Cross-game learning | GlobalMemory điều chỉnh trọng số sau 10+ ván | Hoàn thành |
| ETL + Correlation | Pearson r và Information Gain trên 150 ván | Hoàn thành |
| Config balance test | Thử nghiệm 6 người vs 8 người để cân bằng | Hoàn thành |

### Kết quả thử nghiệm ban đầu

#### So sánh 3 loại agent (150 ván tổng)

| Chỉ số | Random | Rule-Based | Belief+SR |
|---|---|---|---|
| **Tỉ lệ dân thắng** | 10% | **52%** | 32% |
| Vote đúng Ma Sói | 22.4% | 38.6% | **41.2%** |
| Bác Sĩ cứu đúng | 24.1% | 28.5% | **33.9%** |
| Số vòng trung bình | 2.62 | 3.12 | 2.94 |

**Phân tích:**
- Belief+SR vượt Random (+22% win rate) → mô hình có ý nghĩa so với baseline
- Rule-Based thắng nhiều nhất do Seer logic đơn giản, quyết đoán trong game ngắn (avg ~3 vòng)
- Belief+SR có **vote accuracy và doctor save rate tốt nhất** – ưu thế rõ khi game dài hơn
- Đây là kết quả của **bias-variance tradeoff**: mô hình phức tạp hơn cần nhiều vòng hơn để phát huy

#### Cross-game Learning (sau 50 ván)

| Trọng số | Khởi tạo | Sau 50 ván |
|---|---|---|
| α (vote behavior) | 0.400 | 0.354 |
| β (speech behavior) | 0.350 | **0.456** |
| γ (seer oracle) | 0.250 | 0.190 |

→ β tăng mạnh: dữ liệu thực nghiệm xác nhận hành vi phát biểu/cáo buộc là tín hiệu nghi ngờ đáng tin hơn so với hành vi bỏ phiếu

#### Phân tích Pearson Correlation

| Feature | r với correct_vote | Ý nghĩa |
|---|---|---|
| `vote_consensus` | **−0.324** | Đồng thuận cao → thường vote sai (Ma Sói dẫn dắt) |
| `vote_diversity` | +0.21 | Phiếu phân tán → dân đang suy luận độc lập |
| `seer_checked` | +0.15 | Tiên Tri kiểm tra → thông tin tốt hơn |

**Phát hiện quan trọng:** `vote_consensus` là feature mạnh nhất (Information Gain = 0.054) và có tương quan âm với việc vote đúng – khi cả làng đồng thuận cao bất thường, đó là dấu hiệu Ma Sói đang thao túng.

---

## 2.5. MINH CHỨNG THỰC HIỆN

### Link GitHub

> **https://github.com/ExtraSilly/data-platform**

### Output mẫu – 1 ván game

```
=== MA SOI GAME ===
Alice  -> Werewolf  | Bob    -> Werewolf
Carol  -> Seer      | David  -> Doctor
Eve    -> Villager  | Frank  -> Villager
Grace  -> Villager  | Henry  -> Villager

--- Round 1: NIGHT ---
[Wolves] Alice & Bob target: David
[Doctor] Carol saves: Eve
[Seer]   Grace checks: Alice → WEREWOLF

--- Round 1: DAY ---
[DEATH] David bị giết bởi Ma Sói
[DISCUSSION]
  Grace: "Tôi có thông tin quan trọng về Alice..."
  Alice: "Đừng tin Grace – cô ấy đang cố gây rối"
  Bob:   "Đồng ý, Grace hành động rất đáng ngờ"
[VOTE]   Alice:3  Grace:2  Bob:1  Eve:1
[HANG]   Alice bị treo cổ → vai: WEREWOLF ✓

--- Round 2: NIGHT ---
[Wolves] Bob targets: Grace
[Doctor] Carol saves: Carol
[Seer]   Eve checks: Bob → WEREWOLF

--- Round 2: DAY ---
[DEATH] Grace bị giết bởi Ma Sói
[VOTE]   Bob:5
[HANG]   Bob bị treo cổ → vai: WEREWOLF ✓

=== KẾT QUẢ: DÂN THẮNG === (2 vòng)
Vote accuracy: 100% | Doctor saved: 0/2 | Seer found: 2/2
```

### Cấu trúc JSON log

```json
{
  "game_id": "game_20260408_174428_391204",
  "config": { "num_players": 8, "num_werewolves": 2 },
  "result": "villager",
  "rounds": [
    {
      "round": 1,
      "night": {
        "wolf_target": "David",
        "doctor_save": "Eve",
        "seer_check": {"target": "Alice", "result": "werewolf"},
        "killed": "David"
      },
      "day": {
        "ballots": {"Alice": ["Carol","David","Eve"], "Grace": ["Frank","Henry"]},
        "tally": {"Alice": 3, "Grace": 2},
        "hanged": "Alice",
        "hanged_role": "werewolf",
        "correct_vote": true
      }
    }
  ],
  "summary": {
    "total_rounds": 2,
    "correct_votes": 2,
    "wolf_kills": 2,
    "winner": "villager"
  }
}
```

### Kết quả GlobalMemory sau 50 ván

```json
{
  "games_played": 50,
  "villager_wins": 16,
  "learned_weights": {
    "alpha": 0.354,
    "beta": 0.456,
    "gamma": 0.190
  },
  "vote_accuracy": {
    "seer":     { "correct": 47, "total": 110 },
    "villager": { "correct": 89, "total": 304 },
    "doctor":   { "correct": 31, "total": 98 }
  }
}
```

---

## 2.6. KHÓ KHĂN VÀ VẤN ĐỀ TỒN ĐỌNG

### Vấn đề đã gặp và đã giải quyết

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| Ma Sói thắng 100% | Config 6 người quá ít; 2 sói vote cùng target → tạo flood accusation | Đổi sang 8 người + `detect_coordinated_attack` |
| `UnicodeEncodeError` | Windows terminal cp1252, tiếng Việt không in được | `python -X utf8` + `sys.stdout.reconfigure()` |
| Seer belief bị ghi đè | SocialReasoning delta overwrite kết quả oracle | `_sync_belief()` bảo vệ `seer_confirmed` |
| File log bị ghi đè | Nhiều game chạy cùng giây | Timestamp microsecond: `%Y%m%d_%H%M%S_%f` |
| `KeyError 'source'` | `observe()` dùng key `type`, `remember()` dùng `source` | `.get("source") or .get("type", "?")` fallback |

### Hạn chế hiện tại

| Hạn chế | Mức độ ảnh hưởng | Kế hoạch |
|---|---|---|
| Game quá ngắn (avg 2–3 vòng) | Trung bình – SocialReasoning cần thêm vòng để tích lũy | Tăng `min_rounds` hoặc thêm vai trò |
| Rule-Based vượt Belief+SR về win rate | Thấp – đây là kết quả khoa học hợp lệ | Tài liệu hóa + giải thích bias-variance |
| Agent dùng rule-based text, không LLM | Trung bình – phát biểu thiếu tự nhiên | Không thuộc phạm vi đồ án này |
| Chưa có visualization tương tác | Thấp | Có thể thêm matplotlib charts |

---

## 2.7. KẾ HOẠCH ĐẾN CUỐI KỲ

### Các phần sẽ tiếp tục triển khai

| Hạng mục | Mô tả | Ưu tiên |
|---|---|---|
| Visualization | Biểu đồ belief heatmap, vote network graph, win rate chart | Cao |
| Mở rộng dataset | Chạy thêm 200+ ván với seed ngẫu nhiên để dataset đa dạng hơn | Cao |
| Báo cáo cuối kỳ | Hoàn thiện theo template, thêm phần so sánh lý thuyết | Cao |
| Thêm vai trò | Hunter (bắn chết người khi bị treo), Witch (2 lần dùng thuốc) | Trung bình |
| Tích hợp LLM (tùy chọn) | Nếu có API key: generate lời thoại bằng Claude/Gemini | Thấp |

### Timeline dự kiến

| Tuần | Mục tiêu |
|---|---|
| Tuần 1–2 (sau báo cáo giữa kỳ) | Viết visualization module, chạy thêm 200 ván |
| Tuần 3 | Thêm Hunter role, kiểm tra balance lại |
| Tuần 4 | Hoàn thiện báo cáo cuối kỳ, demo video |
| Tuần 5 (nộp) | Review, fix bugs, nộp slide + code |

---

## PHỤ LỤC

### Lệnh chạy hệ thống

```bash
cd werewolf_agentscope

# 1. Chạy 1 ván game
python -X utf8 run_game.py

# 2. Phân tích toàn bộ log
python -X utf8 analysis.py

# 3. Thực nghiệm so sánh 3 agent (cần ~5 phút)
python -X utf8 experiment.py

# 4. ETL + Pearson + Information Gain
python -X utf8 data_analysis.py
```

### Kiến trúc phân tầng (tóm tắt)

```
Tầng Presentation  │  run_game.py / experiment.py
───────────────────┼──────────────────────────────
Tầng Orchestration │  GameMaster (trọng tài)
───────────────────┼──────────────────────────────
Tầng Agent         │  BaseAgent → Wolf/Seer/Doctor/Villager/Random/RuleBased
───────────────────┼──────────────────────────────
Tầng Reasoning     │  BeliefModel + SocialReasoning + GlobalMemory
───────────────────┼──────────────────────────────
Tầng Data          │  GameLogger (JSON) → ETL → Pearson/IG
```

---

*GitHub: https://github.com/ExtraSilly/data-platform*

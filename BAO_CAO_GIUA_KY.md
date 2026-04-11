# BÁO CÁO GIỮA KỲ
## Môn: Nền Tảng Dữ Liệu

---

## 2.1. THÔNG TIN NHÓM

### Tên đề tài
**"Xây dựng Hệ thống AI Đa Tác Tử Mô Phỏng Trò Chơi Ma Sói – Tích hợp LLM, BeliefModel và Data Pipeline Phân tích Hành vi Agent"**

### Danh sách thành viên

| STT | Họ và tên | MSSV | Vai trò |
|---|---|---|---|
| 01 | [Họ tên 1] | [MSSV] | Nhóm trưởng – GameMaster & GameState |
| 02 | [Họ tên 2] | [MSSV] | BeliefModel & SocialReasoning |
| 03 | [Họ tên 3] | [MSSV] | Agent AI (Wolf/Seer/Doctor/Villager) |
| 04 | [Họ tên 4] | [MSSV] | ETL Pipeline & Phân tích dữ liệu |
| 05 | [Họ tên 5] | [MSSV] | LLM Integration & Thực nghiệm |

### Mục tiêu bài toán

1. **Mục tiêu khoa học**: Nghiên cứu hành vi nổi sinh (emergent behavior) trong hệ thống đa tác tử bất đối xứng thông tin – mỗi agent chỉ biết một phần sự thật và phải suy luận từ quan sát, kết hợp với ngôn ngữ tự nhiên do LLM sinh ra.

2. **Mục tiêu kỹ thuật**:
   - Xây dựng BeliefModel đa chiều (vote + speech + oracle) để agent ước lượng độ nghi ngờ
   - Tích hợp SocialReasoning để phát hiện các mẫu hành vi bất thường (leader, contrarian, silence, coordinated attack)
   - Kết nối **Claude API (LLM)** để mỗi agent phát biểu bằng ngôn ngữ tự nhiên tiếng Việt, dựa trên context game state và belief riêng của từng vai
   - Triển khai cross-game learning: trọng số α/β/γ tự điều chỉnh sau nhiều ván

3. **Mục tiêu dữ liệu**: Thu thập, lưu trữ và phân tích log game cấu trúc JSON làm bộ dữ liệu thực nghiệm cho bài toán phân tích hành vi xã hội trong môi trường đa tác tử có LLM

---

## 2.2. MÔ HÌNH VÀ CÔNG NGHỆ SỬ DỤNG

### Loại mô hình

| Hạng mục | Lựa chọn | Mô tả |
|---|---|---|
| **Ngôn ngữ tự nhiên** | **LLM – Claude API** | `claude-haiku-4-5-20251001` sinh lời thoại agent trong pha thảo luận |
| Kiến trúc agent | **Rule-Based + Probabilistic** | BeliefModel có trọng số điều khiển quyết định (vote, kill, save) |
| Học máy | **Cross-game weight learning** | Online learning: cập nhật α/β/γ sau mỗi ván dựa trên accuracy |
| Phân tích dữ liệu | **Descriptive + Correlation** | Pearson r, Information Gain trên tabular data từ JSON logs |
| So sánh hệ thống | **Controlled experiment** | 3 agent type × 50 ván/chế độ = 150 ván tổng |

**Vai trò cụ thể của LLM trong hệ thống:**
- LLM **chỉ sinh ngôn ngữ** (phát biểu thảo luận) – không đưa ra quyết định game
- Quyết định game (ai để vote, ai để giết, ai để cứu) vẫn do **BeliefModel + SocialReasoning** điều khiển
- Mỗi vai nhận system prompt riêng phù hợp mục tiêu: Ma Sói → đổ nghi khéo léo; Tiên Tri → tiết lộ theo 3 tầng; Dân Thường → lập luận thuyết phục
- Có **fallback tự động** về rule-based nếu không có API key hoặc gặp lỗi

### Công cụ và thư viện

| Công cụ | Phiên bản | Mục đích |
|---|---|---|
| Python | 3.10+ | Ngôn ngữ chính |
| `anthropic` | 0.94.0 | Claude API client – sinh ngôn ngữ tự nhiên cho agent |
| `python-dotenv` | 1.0+ | Load API key từ file `.env` |
| `collections` (stdlib) | – | Counter cho vote tally, SocialReasoning |
| `json` (stdlib) | – | Đọc/ghi log game |
| `dataclasses` (stdlib) | – | PlayerBelief data model |
| `math`, `statistics` | stdlib | Pearson correlation, Information Gain |
| Git / GitHub | – | Quản lý version, lưu trữ source |

---

## 2.3. THIẾT KẾ PIPELINE

### Mô tả luồng xử lý tổng thể

```
INPUT                    PROCESSING                              OUTPUT
─────                    ──────────                              ──────
Cấu hình game      →    GameEngine khởi tạo agents         →   JSON log / ván
(num_players,           GameMaster điều phối pha                 (game_*.json)
 num_wolves,            ┌─ Night Phase ──────────────────┐           │
 agent_type,            │  Wolf → Doctor → Seer           │           │
 ANTHROPIC_API_KEY)     │  resolve_night()                │           ▼
                        └────────────────────────────────┘      GlobalMemory
                        ┌─ Day Phase ─────────────────────┐     α/β/γ update
                        │  announce_deaths()               │           │
                        │  speak() ← LLM / fallback rule  │           ▼
                        │  vote() → BeliefModel decides   │      analysis.py
                        │  hang()                         │     (6 chỉ số)
                        └────────────────────────────────┘           │
                                    │                          data_analysis.py
                              check_end()                     (ETL → Pearson →
                           Dân / Ma Sói thắng                  Feature Rank)
```

### Sơ đồ kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                           GAME ENGINE                                │
│                                                                      │
│   ┌────────────┐    ┌─────────────────────────────────────────┐    │
│   │  GameState  │◄──│               GameMaster                 │    │
│   │  round      │   │   (trọng tài trung lập, không có AI)    │    │
│   │  phase      │   └──────┬──────────────────────────────────┘    │
│   │  events     │          │ gọi speak() / vote() / night_action() │
│   │  alive/dead │          ▼                                        │
│   └────────────┘   ┌─────────────────────────────────────────┐    │
│                    │              AGENTS (×8)                  │    │
│                    │  ┌───────────────────────────────────┐   │    │
│                    │  │           BaseAgent                │   │    │
│                    │  │  Memory │ BeliefModel │ SR         │   │    │
│                    │  │         │             │            │   │    │
│                    │  │  speak()─────────────►LLMClient   │   │    │
│                    │  │    ↓ fallback          │           │   │    │
│                    │  │  discuss()         Claude API      │   │    │
│                    │  └───────────────────────────────────┘   │    │
│                    │   Wolf   Seer   Doctor   Villager   ...  │    │
│                    └─────────────────────────────────────────┘    │
│                                     │                               │
│   ┌──────────────┐          ┌───────▼───────────┐                  │
│   │ GlobalMemory │◄─────────│   GameLogger      │                  │
│   │ α=0.368      │ update   │  game_*.json      │                  │
│   │ β=0.404      │          └───────────────────┘                  │
│   │ γ=0.228      │                                                   │
│   └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
                               │ JSON logs
                    ┌──────────▼──────────┐
                    │   data_analysis.py  │
                    │  ETL → Tabular      │
                    │  Pearson r          │
                    │  Information Gain   │
                    └─────────────────────┘
```

### Chi tiết LLM Integration Pipeline

```
Game State Context                System Prompt (theo vai)
        │                                  │
        ▼                                  ▼
┌──────────────────────────────────────────────────────┐
│                   BaseAgent.speak()                   │
│                                                       │
│  _build_context():            _system_prompt():       │
│  - round, alive, dead         WerewolfAgent:          │
│  - suspicion ranking          "Bạn là MA SÓI, hãy    │
│  - 3 ký ức gần nhất           đổ nghi lên [target]"  │
│                               SeerAgent:              │
│                               "Tier 1/2/3 tiết lộ"   │
│                               DoctorAgent:            │
│                               "Không lộ vai, quan sát"│
│                               VillagerAgent:          │
│                               "Lập luận từ bằng chứng"│
└──────────────────┬───────────────────────────────────┘
                   │ gọi
        ┌──────────▼──────────┐
        │    LLMClient        │
        │  generate(sys, ctx) │──► Claude API (haiku)
        │                     │         │
        │  fallback: None     │◄── text response
        └──────────┬──────────┘
                   │ result
        ┌──────────▼──────────────────┐
        │  Có text → dùng LLM output  │
        │  None    → discuss() rule   │  ← fallback tự động
        └──────────┬──────────────────┘
                   │
        statement (ngôn ngữ tự nhiên)
                   │
        GameMaster broadcast → tất cả agent nghe
```

### Chi tiết BeliefModel Pipeline

```
Nguồn bằng chứng                Xử lý                  Output

Vote behavior ──────► vote_score  ──► ×α (0.368)  ─┐
                                                    ├──► Belief(p) ──► decide()
Speech behavior ────► speech_score──► ×β (0.404)  ─┤
                                                    │
Seer oracle ────────► seer_score  ──► ×γ (0.228)  ─┤
                                                    │
Trust history ──────► trust_score ──► ×(−0.30)   ──┘

        ↑ trọng số học tự động
  Sau ≥5 ván: GlobalMemory điều chỉnh α/β/γ
```

### SocialReasoning Pipeline

```
Phát biểu LLM / rule-based (votes, speeches, accusations)
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
         BeliefModel.update()  →  vote() quyết định
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
| **LLM Integration** | **Claude API sinh lời thoại tự nhiên, fallback rule-based** | **Hoàn thành** |

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
- Rule-Based thắng nhiều nhất do Seer logic đơn giản, quyết đoán trong game ngắn
- Belief+SR có **vote accuracy và doctor save rate tốt nhất** – ưu thế rõ khi game dài hơn
- Đây là kết quả của **bias-variance tradeoff**: mô hình phức tạp cần nhiều vòng hơn để phát huy

#### Cross-game Learning (sau 10+ ván)

| Trọng số | Khởi tạo | Sau học |
|---|---|---|
| α (vote behavior) | 0.400 | 0.368 |
| β (speech behavior) | 0.350 | 0.404 |
| γ (seer oracle) | 0.250 | 0.228 |

#### Phân tích Pearson Correlation

| Feature | r với correct_vote | Ý nghĩa |
|---|---|---|
| `vote_consensus` | **−0.324** | Đồng thuận cao → thường vote sai (Ma Sói dẫn dắt) |
| `vote_diversity` | +0.21 | Phiếu phân tán → dân đang suy luận độc lập |
| `seer_checked` | +0.15 | Tiên Tri kiểm tra → thông tin tốt hơn |

**Phát hiện:** `vote_consensus` là feature quan trọng nhất (IG=0.054), tương quan âm với vote đúng – khi cả làng đồng thuận cao bất thường là dấu hiệu Ma Sói đang thao túng.

---

## 2.5. MINH CHỨNG THỰC HIỆN

### Link GitHub

> **https://github.com/ExtraSilly/data-platform**

### Output mẫu – thảo luận với LLM (có API key)

```
--- THAO LUAN ---
  Bob: Tôi chú ý thấy Carol hầu như không lên tiếng từ đầu ván đến giờ,
       điều đó khiến tôi khá nghi ngờ về ý đồ thực sự của cô ấy.

  Carol: Tôi đã kiểm tra và có thông tin đáng tin cậy – mọi người nên
         dè chừng với Bob trong lần bỏ phiếu này.

  Eve:   Hành động của Bob trong vòng trước rất đáng chú ý, anh ta liên
         tục đổ nghi ngờ sang người khác mà không đưa ra bằng chứng cụ thể.

  Frank: Tôi đồng ý với Eve, Bob đang cố tình dẫn dắt dư luận theo hướng
         có lợi cho mình.
```

### Output mẫu – thảo luận fallback (không có API key)

```
--- THAO LUAN ---
  Bob: Toi thay Carol qua im lang, dieu do kha bat thuong.
  Carol: Toi co thong tin dang tin cay – moi nguoi hay chu y den Bob.
  Eve: Toi nghi Bob – Bob liên tục cáo buộc Carol trong vòng trước.
  Frank: Nhin lai cac dau hieu, toi cho rang Bob dang nghi ngo nhat.
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
        "wolf_target": "Dave",
        "doctor_save": "Eve",
        "seer_check": {"target": "Bob", "result": "werewolf"},
        "killed": "Dave"
      },
      "day": {
        "ballots": {"Bob": ["Carol","Dave","Eve"], "Grace": ["Frank","Henry"]},
        "tally": {"Bob": 3, "Grace": 2},
        "hanged": "Bob",
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

### GlobalMemory – trọng số học được

```json
{
  "games_played": 11,
  "learned_weights": { "alpha": 0.368, "beta": 0.404, "gamma": 0.228 },
  "vote_accuracy": {
    "seer":     { "correct": 47, "total": 110 },
    "villager": { "correct": 89, "total": 304 }
  }
}
```

---

## 2.6. KHÓ KHĂN VÀ VẤN ĐỀ TỒN ĐỌNG

### Vấn đề đã gặp và đã giải quyết

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| Ma Sói thắng 100% | Config 6 người quá ít; 2 sói vote cùng target | Đổi sang 8 người + `detect_coordinated_attack` |
| `UnicodeEncodeError` | Windows terminal cp1252, tiếng Việt không in được | `python -X utf8` + `sys.stdout.reconfigure()` |
| Seer belief bị ghi đè | SocialReasoning delta overwrite kết quả oracle | `_sync_belief()` bảo vệ `seer_confirmed` |
| File log bị ghi đè | Nhiều game chạy cùng giây | Timestamp microsecond: `%Y%m%d_%H%M%S_%f` |
| `KeyError 'source'` | `observe()` dùng key `type`, `remember()` dùng `source` | `.get("source") or .get("type", "?")` fallback |
| LLM gây crash khi không có key | `anthropic.Anthropic()` raise nếu key rỗng | Lazy init + `_available` flag + silent fallback về `discuss()` |

### Hạn chế hiện tại

| Hạn chế | Mức độ ảnh hưởng | Kế hoạch |
|---|---|---|
| Game quá ngắn (avg 2–3 vòng) | Trung bình – SocialReasoning và LLM chưa phát huy đủ | Tăng `min_rounds` hoặc thêm vai trò |
| LLM output chưa được đánh giá định lượng | Cao – chưa có metric so sánh LLM vs rule-based speech | Thêm human evaluation hoặc coherence score |
| Chi phí API mỗi ván | Thấp – Haiku rất rẻ (~$0.0001/ván) nhưng cần key | Cung cấp `.env.example`, hỗ trợ fallback |
| Chưa có visualization tương tác | Thấp | Thêm matplotlib charts cuối kỳ |

---

## 2.7. KẾ HOẠCH ĐẾN CUỐI KỲ

### Các phần sẽ tiếp tục triển khai

| Hạng mục | Mô tả | Ưu tiên |
|---|---|---|
| Đánh giá LLM speech | So sánh định lượng: LLM vs rule-based (coherence, vote influence) | **Cao** |
| Visualization | Win rate chart, belief heatmap, vote network graph | Cao |
| Mở rộng dataset | Chạy thêm 200+ ván với LLM bật để so sánh với 150 ván rule | Cao |
| Báo cáo cuối kỳ | Hoàn thiện đủ 7 mục, thêm phần so sánh LLM vs rule-based | Cao |
| Thêm vai trò | Hunter (bắn người khi bị treo), Witch (2 lần dùng thuốc) | Trung bình |

### Timeline dự kiến

| Tuần | Mục tiêu |
|---|---|
| Tuần 1 (sau báo cáo giữa kỳ) | Chạy 200 ván có LLM, thu thập dataset mới |
| Tuần 2 | Xây dựng metric đánh giá LLM speech, viết visualization module |
| Tuần 3 | Thêm Hunter role, kiểm tra balance |
| Tuần 4 | Hoàn thiện báo cáo cuối kỳ, quay demo video |
| Tuần 5 (nộp) | Review, fix bugs, nộp slide + code |

---

## PHỤ LỤC

### Lệnh chạy hệ thống

```bash
cd werewolf_agentscope

# Cài thư viện (cần cho LLM)
pip install anthropic python-dotenv

# Cấu hình API key (tùy chọn – không có vẫn chạy được)
cp ../.env.example ../.env
# Điền ANTHROPIC_API_KEY=sk-ant-... vào file .env

# 1. Chạy 1 ván game (có LLM nếu đã cấu hình key)
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
───────────────────┼──────────────────────────────────────────
Tầng Orchestration │  GameMaster (trọng tài, không có AI)
───────────────────┼──────────────────────────────────────────
Tầng Agent         │  BaseAgent → Wolf/Seer/Doctor/Villager
                   │             speak() ← LLMClient ← Claude API
───────────────────┼──────────────────────────────────────────
Tầng Reasoning     │  BeliefModel + SocialReasoning + GlobalMemory
───────────────────┼──────────────────────────────────────────
Tầng Data          │  GameLogger (JSON) → ETL → Pearson / IG
```

---

*GitHub: https://github.com/ExtraSilly/data-platform*

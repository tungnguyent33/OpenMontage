# Máy Reels: kế hoạch

Chỉ còn kế hoạch và rủi ro còn hiệu lực. Trạng thái hiện tại và việc đang dở: `docs/may-reels/TRANG-THAI.md`; quyết định đã chốt: `docs/may-reels/QUYET-DINH.md`; lịch sử từng phiên: `docs/may-reels/NHAT-KY-PHAT-TRIEN.md`. Đọc kèm `docs/may-reels/NGUYEN-TAC.md`. Tài liệu này được viết sau khi đã đọc code thật trên nhánh `kenh-vanxuan`. Chỗ nào ghi **chưa xác minh** là chưa đọc hoặc chưa chạy thử được.

**Tách ngày 2026-11-21** (không bỏ nội dung nào, số mục cũ giữ nguyên để các chỗ trỏ "KE-HOACH.md mục N / câu N" còn tìm được):

| Mục cũ | Nay ở |
|---|---|
| 1. Hiện trạng (ngày 2026-11-15) | `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-15 (1) |
| 2. Sơ đồ luồng, 3.1. Code bắt buộc gì, 5. Rủi ro | giữ ở đây |
| 3.2. Hai phương án (đã chọn phương án 2) | `QUYET-DINH.md` B1; đoạn "Ai chạy trợ lý" giữ ở đây |
| 4. Chọn pipeline `hybrid` | `QUYET-DINH.md` B2 |
| 6. Quyết định đã chốt (câu 1–19) | `QUYET-DINH.md` mục A (cùng số câu); "Việc còn chờ người dùng" ở mục C |
| 7. Kết quả test nền | `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-15 (1) |
| 8. Dựng một video từ đầu đến cuối | `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-15 (2) |
| 9. Chấm điểm theo rubric | thiết kế và kết quả: `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-16; quyết định của máy: `QUYET-DINH.md` B3 |
| 10. Kho cảnh tự nạp | `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-17, 2026-11-18, 2026-11-19 (1); quyết định: `QUYET-DINH.md` B4, B5; phát hiện còn hiệu lực: mục 5.5 bên dưới |

---

> **2026-11-20: bộ prompt C thay Prompt 5 và 5A.** Chiến lược nội dung (`docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`, chỉ trên máy) đưa vào máy qua bộ C, mục "Kế hoạch 30 ngày và cách đưa vào Máy Reels" của file chiến lược: C0 dữ liệu kênh (nhóm đối tượng, định vị, định dạng, lịch, bán hàng) — đã làm 2026-11-20; C0b học từ video mẫu (trạm phân tích); C1 sinh chủ đề theo nhóm và lịch; C2 mã theo dõi, tiêu chí "đúng đối tượng"; C3 video giọng thật của thầy; C4 mẫu trả lời Zalo, số liệu theo mã; C5 buổi xem lại hằng tuần; C6 trường nguồn trong hệ thống quản lý học viên. Prompt 5 và 5A cũ không làm nữa.

Bộ C (thứ tự chạy trong `LO-TRINH.md`, chỉ có ở máy) là kế hoạch còn lại: C2b bộ biên kịch, C1, C2, C3, C0b-2, C4, C5, rồi Prompt 7 (lịch chạy tự động). Prompt 2 (đăng bài thật) để sau.

---

## 2. Sơ đồ luồng

```
 ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌─────────────────┐   ┌──────┐   ┌─────────┐
 │ Ý tưởng  │──▶│ Sản xuất  │──▶│ Chấm điểm │──▶│ Hàng chờ duyệt  │──▶│ Đăng │──▶│ Số liệu │
 └────┬─────┘   └─────┬─────┘   └─────┬─────┘   └────────┬────────┘   └──┬───┘   └────┬────┘
      │ Sheet:        │ thiếu cảnh    │ trượt            │ Sheet:        │ dry-run     │ Sheet:
      │ tab Chủ đề    ▼               ▼ → làm lại/bỏ     │ Duyệt=Duyệt   │ mặc định    │ tab Số liệu
      │ (NGƯỜI duyệt) tab "Cần quay"                     │ (NGƯỜI duyệt)  │             │
      └───────────────────────────────────────────────────────────────────────────────────┘
```

Cổng của người: **(A)** duyệt chủ đề, trước bước Sản xuất. **(B)** duyệt video, trước bước Đăng. Ngoài hai cổng này máy không dừng hỏi ai.

### Bước 1: Ý tưởng

| | |
|---|---|
| Đầu vào | `brand/<id>/brand.json`: `chu_de[]` (`ma`, `tru_cot`, `dinh_dang`, `chu_de`, `y_chinh`, `nguon_doi_chieu`, `trend`, `da_lam`), `kenh.tru_cot_noi_dung`, `kenh.khan_gia` |
| Tái dùng | Director skill `skills/pipelines/hybrid/idea-director.md`. Schema `schemas/artifacts/brief.schema.json` và `decision_log.schema.json`. `lib/checkpoint.py` (`init_project` có tham số `series`, đặt bằng mã kênh như vx-demo-01 đã làm). |
| Viết mới | `may_reels/sheet.py`: đọc và ghi Google Sheet, khóa không cho ghi vào cột của người. `may_reels/y_tuong.py`: lấy các chủ đề chưa làm, đẩy lên tab "Chủ đề" ở trạng thái "chờ duyệt". `skills/may-reels/y-tuong.md`. |
| Cổng (A) | Chỉ những dòng có `duyet_chu_de` = `Làm` mới sang bước Sản xuất. |
| Đã làm (2026-11-15) | `may_reels/cot_sheet.py`, `may_reels/sheet.py`, `may_reels/chu_de.py`. Các lệnh `python -m may_reels sheet init` và `sheet nap-chu-de --kenh <mã>`. Hướng dẫn cài đặt: `docs/may-reels/CAI-DAT-GOOGLE.md`. |
| Lưu ý schema | `brief.target_platform` chỉ nhận `youtube`, `instagram`, `tiktok`, `linkedin`, `generic`. **Không có `facebook`.** Một video cho cả 3 nền tảng thì dùng `generic` và ghi danh sách nền tảng vào `brief.metadata` (`metadata` là object tự do, còn mức gốc của brief có `additionalProperties: false`). |
| Chưa xác minh | Cột `trend` trong brand.json đang trống ở cả 16 chủ đề. Máy chưa có nguồn nào để tự tìm chủ đề mới. |

### Bước 2: Sản xuất

Đi qua các stage của pipeline `hybrid`: `script → scene_plan → assets → edit → compose`. Lý do chọn `hybrid`: `QUYET-DINH.md` B2.

| Stage | Tái dùng (đã có) | Viết mới |
|---|---|---|
| script | `skills/pipelines/hybrid/script-director.md`, `schemas/artifacts/script.schema.json`. Mỗi `sections[]` có `text`, `start_seconds`, `end_seconds`, `delivery_cues.provider_text` (cách đọc riêng, ví dụ "150 phân khối" thay cho "150cc"), `pronunciation_guides`, `source_ref` (để gắn nguồn luật). Mẫu tham khảo: `projects/vx-demo-01/kich_ban.py`. | `may_reels/kich_ban.py`: kiểm tra trước khi ghi (cụm từ cấm, nguồn luật, số chữ hợp thời lượng theo bảng "Script Word Counts" trong `skills/creative/short-form.md`). |
| scene_plan | `skills/pipelines/hybrid/scene-director.md`, tool `frame_sampler`, `scene_detect`. | `may_reels/chon_canh.py`: chọn cảnh từ `kho_canh` theo `the`, `mo_ta`, `dia_diem`, `co_canh`, `huong`. Chỉ lấy cảnh `dung_duoc`, cắt trong `doan_dung_duoc`, kiểm lại `mat_nguoi` với `quyen_hinh`. Ý nào không có cảnh thì ghi vào tab "Cần quay". |
| assets | `skills/pipelines/hybrid/asset-director.md`, `subtitle_gen`, `audio_enhance`, `transcriber` (faster-whisper, nhận `language`). Mẫu tham khảo: `sinh_giong.py`, `nghe_lai.py`, `can_phu_de.py`, `chuan_bi_canh.py` của vx-demo-01. | Tool giọng mới `tools/audio/vieneu_tts.py` (capability `tts`, provider `vieneu`, chạy CPU), để `tts_selector` tìm thấy. `may_reels/canh.py`: cắt và chuẩn hóa cảnh về 1080×1920, 30 fps. |
| edit | `skills/pipelines/hybrid/edit-director.md`, `video_trimmer`. Lưu ý: chế độ "templated" là đúng chỗ cho làm hàng loạt (`AGENT_GUIDE.md`, mục "Composition Authoring Mode": "Right for batch output"). | Mẫu đồ họa chữ dùng chung cho kênh, đọc màu, font, logo từ `brand/<id>/`. |
| compose | `skills/pipelines/hybrid/compose-director.md`, `video_compose` (chọn Remotion, HyperFrames hoặc FFmpeg theo `edit_decisions.render_runtime`), `hyperframes_compose`, `audio_mixer`, `color_grade`. Profile trong `lib/media_profiles.py`: `youtube_shorts`, `instagram_reels`, `tiktok`. | **`lib/media_profiles.py` không có profile Facebook Reels.** Đã chốt (`QUYET-DINH.md` câu 8): Facebook dùng `instagram_reels`, không thêm profile mới. |

Tài liệu nền cho mọi stage: `skills/creative/short-form.md` (1080×1920, vùng an toàn chung 900×1400, chữ từ 42 px, −14 LUFS, đỉnh −1 dBTP, đổi hình mỗi 1–3 giây, có chữ ngay từ 0,5 giây đầu).

### Bước 3: Chấm điểm

| | |
|---|---|
| Tái dùng | `skills/meta/reviewer.md` (tối đa 2 vòng sửa, phân loại critical/suggestion/nitpick). `lib/slideshow_risk.py` `score_slideshow_risk(scenes, edit_decisions, renderer_family, render_runtime)`: điểm từ 0 đến 5, chia mức `strong` < 2, `acceptable` < 3, `revise` < 4, `fail` ≥ 4. Hàm đọc các trường `type`, `description`, `shot_language.shot_size`, `shot_language.camera_movement`, `shot_intent`, `information_role`, `narrative_role`, `hero_moment`, nên scene_plan phải điền đủ các trường này mới chấm được có nghĩa. Schema `schemas/artifacts/final_review.schema.json` bắt buộc 5 nhóm kiểm tra: `technical_probe`, `visual_spotcheck` (cần `frames_sampled` ≥ 4 theo reviewer), `audio_spotcheck`, `promise_preservation`, `subtitle_check`. Tool `visual_qa` (`review`, `probe`, `audio_levels`), `composition_validator`, `audio_probe`, `frame_sampler`. |
| Viết mới | `may_reels/cham_diem.py`, phần tất định: (1) cụm từ cấm và câu sáo trên lời đọc, chữ trên màn hình và caption; (2) ý luật nào cũng có nguồn; (3) mọi cảnh đều `dung_duoc`, nằm trong `doan_dung_duoc`, thỏa quyền hình; (4) thời lượng, khổ, fps, LUFS, đỉnh âm; (5) chữ nằm trong vùng an toàn; (6) không có tool tạo hình/video AI nào trong `asset_manifest`. Kết quả gồm điểm, lý do, và quyết định qua/làm lại/bỏ, ghi vào cột máy trên Sheet. |
| Ngưỡng | 75 điểm (`QUYET-DINH.md` câu 12). Trượt sau 2 vòng sửa vẫn vào hàng chờ, kèm cảnh báo "Dưới ngưỡng". |
| Đã làm (2026-11-16) | Xem `NHAT-KY-PHAT-TRIEN.md` mục 2026-11-16. `diem_qa` là điểm rubric nội dung (`brand/<kenh>/rubric.yaml`, `may_reels/cham_diem.py`, skill `skills/may-reels/cham-diem.md`). Điểm kỹ thuật cũ đổi tên thành `diem_ky_thuat` và chỉ là một tiêu chí. |

### Bước 4: Hàng chờ duyệt

| | |
|---|---|
| Tái dùng | `tools/publishers/export_bundle.py`: đóng gói video, phụ đề, `metadata.json`, `description.txt` vào `projects/<id>/exports/` và trả về `publish_log` có `status: "exported"`. Schema `publish_log` có trạng thái `pending_review`. |
| Viết mới | `may_reels/hang_cho.py`: đưa video đã qua chấm điểm lên tab "Hàng chờ duyệt" kèm link xem, tiêu đề, mô tả, hashtag (lấy từ `brand.json` `hashtags.facebook/tiktok/youtube`), CTA, điểm, nguồn luật. Nội dung này được chốt ở đây và không đổi lúc đăng. |
| Cổng (B) | Người xem video rồi chọn `duyet` = `Duyệt`. Người xem video qua link Google Drive (`QUYET-DINH.md` câu 3). |

### Bước 5: Đăng

| | |
|---|---|
| Tái dùng | Mẫu khai báo `BaseTool` của `export_bundle.py`. Schema `publish_log`. `.gitignore` đã có `.youtube-token.json`, cho thấy upstream đã tính đến OAuth YouTube nhưng **chưa có code**. |
| Đã làm (2026-11-15) | `tools/publishers/facebook_reels.py`, `youtube_shorts.py`, `tiktok_handoff.py` (TikTok đăng tay qua Drive). `may_reels/dang_bai.py` (lệnh `dang [--that]`), `may_reels/hang_cho.py` (lệnh `hang-cho them`). Cài đặt: `CAI-DAT-DANG-BAI.md`. **Chưa đăng thật lần nào.** |
| Kế hoạch ban đầu | `tools/publishers/youtube_shorts.py`, `tools/publishers/facebook_reels.py`, `tools/publishers/tiktok.py`. Mỗi file kế thừa `BaseTool`, `capability = "publish"`, mặc định chạy thử, import thư viện mạng bên trong hàm. `may_reels/dang.py`: đọc lại ô Duyệt ngay trước khi đăng, chống trùng theo cặp (mã video, nền tảng), ghi sổ đăng local và tab đăng trên Sheet. |
| Tài liệu API | Đã đọc ngày 2026-11-15, tóm tắt trong `docs/may-reels/API-DANG-BAI.md`. Còn chưa xác minh: Meta có cần App Review không; scope tối thiểu để đọc lại `privacyStatus`. |
| Drive | Service account không có dung lượng Drive (tài liệu Google), nên bản xem thử và thư mục TikTok dùng OAuth của người dùng (`drive.file`). |

### Bước 6: Số liệu

| | |
|---|---|
| Tái dùng | Không có gì sẵn. |
| Viết mới | `may_reels/so_lieu.py`: theo `video_id` trong sổ đăng, lấy lượt xem, thời gian xem, tương tác, rồi ghi vào tab "Số liệu". Không phải bước nào cũng cần LLM; nếu cần tóm tắt thì tách riêng khỏi đường đăng. |
| Chưa xác minh | API nào trả về số liệu nào, quyền cần cấp. |

---

## 3. Chạy pipeline không dừng hỏi người

### 3.1. Code hiện tại bắt buộc những gì

- `skills/meta/checkpoint-protocol.md`: giá trị `human_approval_default` trong manifest là **bắt buộc**. Cổng nào có giá trị `true` thì phải ghi `awaiting_human`, **kết thúc lượt**, chờ người trả lời. "Duyệt theo từng cổng": một lần "làm hết đi" không thay được các cổng sau. Muốn duyệt trước cả lượt chạy thì phải ghi một mục `decision_log` có `category: "approval_policy"`.
- `lib/checkpoint.py` `write_checkpoint()` **ép buộc bằng code**: stage nào được manifest đánh dấu duyệt mà ghi `completed` không kèm `human_approved=True` thì báo lỗi `GATE VIOLATION`. `_enforce_stage_prerequisites()` chặn tiến lên stage sau nếu stage trước chưa `completed`, hoặc đã completed mà thiếu duyệt.
- `approval_policy` **chỉ có hiệu lực ở mức hướng dẫn**: tìm trong code chỉ thấy nó nằm trong enum của `decision_log.schema.json` và trong `tests/lib/test_decision_log_approval_policy.py`. `lib/checkpoint.py` không đọc nó. Cờ `human_approved=True` do chính trợ lý truyền vào.
- Cổng của `hybrid.yaml`: `idea`, `script`, `scene_plan`, `assets` và `publish` đều có `human_approval_default: true`; `edit` và `compose` là `false`.
- `default_checkpoint_policy` có các giá trị `guided`, `manual_all`, `auto_noncreative` (`schemas/pipelines/pipeline_manifest.schema.json`). Nhưng `write_checkpoint` chỉ ghi giá trị này vào file, cổng duyệt vẫn do `human_approval_default` của từng stage quyết định. Vì vậy đổi chính sách không tắt được cổng.
- Còn các luật khác bắt hỏi người, nằm ngoài checkpoint: "Present Both Composition Runtimes (HARD RULE)", "Ask Before Major Changes", "Escalate Blockers Explicitly", "No Unilateral Substitutions" (`AGENT_GUIDE.md`), và mục chọn runtime trong `skills/pipelines/hybrid/idea-director.md`.

### 3.2. Phương án đã chọn

Phương án 2: manifest riêng `pipeline_defs/may-reels.yaml` cộng skill bọc ngoài, cổng của người chỉ ở `idea` (A) và `publish` (B). So sánh hai phương án và lý do: `QUYET-DINH.md` B1.

**Ai chạy trợ lý khi không có người ngồi:** phần sáng tạo cần trợ lý AI, Python không tự chạy director skill được. Dự kiến dùng Claude Code chế độ không tương tác (`claude -p`), gọi theo lịch bằng Windows Task Scheduler. Đã chốt (`QUYET-DINH.md` câu 10), với điều kiện phải chạy thử thật ở bước sản xuất. Cách gọi này **chưa xác minh** trên máy này.

---

## 4. Chọn pipeline: `hybrid`

Đã chốt, xem `QUYET-DINH.md` B2.

---

## 5. Rủi ro

### 5.1. Đường dẫn tuyệt đối Windows trong `brand.json`

- Các trường `nguon_kenh`, `context.*.duong_dan`, `kho_canh[].duong_dan`, `anh_that[]` và `kho_md` đều là đường dẫn tuyệt đối dạng `C:\Users\Thinkpad P15V3\Desktop\Claude code\video-agent-team-kit\...`. Riêng `assets.*` và `font.files.*` là đường dẫn tương đối trong repo, không có vấn đề.
- Hậu quả: (1) chạy trên máy khác, trong CI hoặc trên cloud thì gãy; (2) file đã commit lên repo public nên lộ tên người dùng Windows và cấu trúc thư mục; (3) tên file có dấu cách và chữ có dấu tiếng Việt dễ hỏng khi đưa vào lệnh FFmpeg, HyperFrames hay Remotion. Có thể gặp lệch chuẩn Unicode NFC/NFD (chưa xác minh trên máy này). Ngoài ra Remotion đọc file qua `remotion-composer/public/`, thư mục này bị gitignore.
- **Đã xử lý ngày 2026-11-15** (`QUYET-DINH.md` câu 18):
  - `nap_kenh.py` không còn ghi đường dẫn tuyệt đối. `kho_canh[]` chỉ còn `file_tuong_doi`. `anh_that[]` và `kho_md` là đường dẫn tương đối so với thư mục kênh. `nguon_kenh` chỉ ghi tên biến môi trường (`KENH_GOC_DIR`) và tên thư mục con.
  - File thật = `$KENH_GOC_DIR/<id>/<file_tuong_doi>`. Hàm dùng chung là `thu_muc_kenh()` trong `nap_kenh.py`.
  - Test `tests/may_reels/test_nap_kenh.py` kiểm tra brand.json đã commit không có đường dẫn tuyệt đối.
- Còn lại:
  - Lịch sử git (commit `dc52b79`, đã đẩy lên GitHub) vẫn chứa bản cũ.
  - Các script trong `projects/vx-demo-01/` (bị gitignore) đọc `k["duong_dan"]` nên sẽ gãy với brand.json mới. Các script này chưa được sửa.

### 5.2. Kho cảnh nằm ngoài repo

- Cảnh thật nằm ở `...\channels\vanxuan\canh-quay\` và `image\`, không có trong git. `ton_tai` chỉ đúng tại lúc chạy `nap_kenh.py`. File bị đổi tên hay xóa thì brand.json không biết.
- Máy phải kiểm tra lại từng file ngay trước khi dùng (có tồn tại không, và nếu có thể thì so cả kích thước hoặc hash). Lệch thì dừng và báo, không tự chọn cảnh khác.
- Kho nhỏ: 8 video và 12 ảnh dùng được. Có video chỉ 480×854 (`ghi_chu` ghi "phóng lên sẽ mềm"). Có cảnh gắn với một mùa cụ thể (băng rôn Trung thu). Có cảnh cần xử lý biển số hoặc mặt người (`can_xu_ly`). Vì vậy tab "Cần quay" sẽ được dùng thường xuyên, và chọn cảnh lặp lại giữa các video là rủi ro thật cho chất lượng.
- Quy tắc ngày trong `quyen_hinh`: file mới thêm vào kho sau `quyen_hinh.ngay` (2026-11-10) sẽ tự bị loại cho đến khi cập nhật `quyen_hinh` rồi chạy lại `nap_kenh.py`. Đây là điểm an toàn, nhưng người dùng cần biết để khỏi thắc mắc vì sao cảnh mới không được dùng.
- `lib/corpus.py` (tìm kiếm bằng vector) cần embedding CLIP `openai/clip-vit-base-patch32` (`lib/clip_embedder.py`, khoảng 350 MB, chạy CPU) và bản ghi kiểu `ClipRecord` dành cho stock. Model CLIP này huấn luyện bằng tiếng Anh, còn nhãn và mô tả trong kho là tiếng Việt. Với 24 cảnh có nhãn `the` chi tiết, khớp nhãn tất định có lẽ là đủ. Hiệu quả của CLIP với truy vấn tiếng Việt **chưa xác minh**.

### 5.3. Test của upstream có thể vỡ khi thêm tool, pipeline hoặc tài liệu mới

| Test | Vỡ khi nào |
|---|---|
| `tests/contracts/test_pipeline_catalog.py` | Lặp qua **mọi** `pipeline_defs/*.yaml`. Manifest mới phải hợp schema, thứ tự stage phải khớp `get_pipeline_stages()`, và `_stage_requires_approval()` phải trả về đúng giá trị `human_approval_default` đã khai báo. |
| `tests/contracts/test_agent_skill_pointers.py` | Lặp qua mọi tool registry tìm thấy. `agent_skills` của tool mới phải trỏ tới `.agents/skills/<tên>/SKILL.md` hoặc `.agents/skills/<tên>.md` có thật. |
| `tests/contracts/test_skill_execute_examples.py` | Quét `skills/**/*.md`, `docs/**/*.md` và `*.md` ở gốc repo, tìm mẫu `<tên>.execute({`. Tên tool chưa đăng ký hoặc khóa không có trong `input_schema` đều làm vỡ test. Skill của Máy Reels và chính hai tài liệu này phải tránh viết như vậy. |
| Mọi test gọi `registry.discover()` | `discover()` import tất cả module trong `tools/` mà không bắt lỗi. Publisher hay tool giọng mới import thư viện chưa cài ở đầu file sẽ làm vỡ toàn bộ nhóm test này. |
| `tests/contracts/test_phase0_contracts.py` (`test_discovers_concrete_tools_from_package`, `test_support_envelope`) | Tool mới thiếu trường hợp đồng hoặc `get_info()` báo lỗi. **Chưa xác minh** từng điều kiện. |
| `tests/test_preflight_capability_coverage.py` | So số provider của một số capability. Thêm provider `tts` mới **có thể** làm lệch số đếm nếu test dùng registry thật. Chưa xác minh test dùng registry thật hay registry cô lập. |
| `tests/tools/test_export_bundle.py` | Chỉ vỡ nếu sửa `export_bundle.py`. Theo nguyên tắc thì không sửa file này. |

**Kết quả chạy test nền trên máy này:** `NHAT-KY-PHAT-TRIEN.md` mục 2026-11-15 (1); mới nhất ở `TRANG-THAI.md`.

### 5.4. Rủi ro khác

- Toàn văn `context/*.md` đã tách khỏi `brand.json` sang `brand/<id>/_local/context/` (bị gitignore). Bản cũ vẫn còn trong lịch sử git.
- `brand.json` vẫn giữ `mau_tong_hop` (toàn văn `mau/TONG-HOP.md`). Mục `mau_thuan_business_vs_channel` vẫn trích một số dòng của `business.md` (hotline, website, số liệu). Hai phần này chưa được tách vì yêu cầu chỉ nói tới `context/*.md`.
- `brief.target_platform` không có `facebook`, `lib/media_profiles.py` không có profile Facebook (xem mục 2, bước 1 và bước 2).
- Đã xử lý ngày 2026-11-15: giá trị riêng của Vạn Xuân trong `nap_kenh.py` (tiền tố `vx-`, font, thư mục video) đã chuyển sang `brand/<id>/cau-hinh.yaml`. Kênh không có file này thì `brand.json` ghi `canh_bao`, máy không tự đoán giá trị.
- Giấy phép thương mại của VieNeu và PhoWhisper chưa xác minh.
- Lỗi mã hóa console: Python mặc định in bằng cp1252 trên máy này và đã báo `UnicodeEncodeError` khi in tiếng Việt. Đã xử lý bằng `PYTHONUTF8=1`, đặt qua `tools_local/py.cmd` hoặc biến môi trường (xem `HUONG-DAN-SU-DUNG.md`).

### 5.5. Phát hiện khi làm kho cảnh (2026-11-17, còn hiệu lực)

- `lib/source_media_review.review_source_media` không dùng nguyên được cho kho: hàm ghi khung hình vào ngay thư mục chứa file gốc (`.source_review_frames_<tên>`), tức thư mục mới quay; và hàm đọc khóa `text` mà `transcriber` không trả về, nên phần tóm tắt lời nói luôn rỗng. `kho nap` gọi thẳng các tool mà hàm này dùng. Không sửa file upstream.
- `audio_probe` không đo phần hình. Kích thước khung (có tính cờ xoay của điện thoại) đo bằng ffprobe như `source_media_review` và `nap_canh_quay.py`.
- GPU của máy không dùng được cho faster-whisper: thiếu `cublas64_12.dll` (CUDA 12). `transcriber` tự chuyển sang CPU int8, nên chép lời model lớn chậm.
- Hugging Face không tạo được symlink trong cache trên Windows này (`WinError 1314`), nên tải model mới bị dở (`faster-whisper-large-v3` trong cache thiếu `model.bin`). Model dùng để so sánh được tải vào thư mục thường `~/.cache/whisper-local/`.
- GPU vẫn chưa dùng được (thiếu CUDA 12). Không cần cài để dùng PhoWhisper với kho hiện tại.
- Model lớn chạy CPU tốn khoảng 3 GB bộ nhớ. `kho nap` chép lời lần lượt từng file, nên không nên chạy cùng việc nặng khác.
- **Sống chung với script cũ của bộ kit:** `scripts/nap_canh_quay.py` quét cả `canh-quay/moi-quay/`. Nếu script cũ lập index trước, `kho nap` nhận các file đó về (ghi `ngay_nap` thật, gắn nhãn) chứ không bỏ qua; cảnh đã nạp bằng `kho nap` thì script cũ giữ nguyên vì `dau` không đổi. Hướng dẫn `canh-quay/DOC-TOI.md` trong thư mục kênh gốc vẫn chỉ tới script cũ: máy không sửa file đó.

---

## 6. Quyết định đã chốt

Đã chuyển sang `QUYET-DINH.md` (câu 1–19 giữ nguyên số).

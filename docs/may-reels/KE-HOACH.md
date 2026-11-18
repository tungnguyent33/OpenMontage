# Máy Reels: kế hoạch

Đọc kèm `docs/may-reels/NGUYEN-TAC.md`. Tài liệu này được viết sau khi đã đọc code thật trên nhánh `kenh-vanxuan`. Chỗ nào ghi **chưa xác minh** là chưa đọc hoặc chưa chạy thử được.

---

## 1. Hiện trạng: những gì đã có

| Thành phần | Hiện trạng |
|---|---|
| Dữ liệu kênh | `brand/vanxuan/brand.json` do `tools_local/nap_kenh.py` sinh ra. Có 16 chủ đề (`chu_de`, 4 đã làm, 12 chưa làm), 24 cảnh trong kho (`kho_canh`, 20 dùng được: 8 video, 12 ảnh), quy tắc cấm (`cam`), quyền hình (`quyen_hinh`), CTA, hashtag theo nền tảng, màu, font, logo. |
| Dự án mẫu | `projects/vx-demo-01/` (bị gitignore, chỉ có trên máy này). Dùng pipeline `hybrid` + HyperFrames + giọng VieNeu "Hải Đăng" + PhoWhisper, chi phí 0 đ. Chỉ có checkpoint của `idea`, `script`, `scene_plan`. Thư mục `renders/` đang trống. **Chưa có bản dựng cuối nào được kiểm chứng từ đầu đến cuối.** Các bước sau `scene_plan` chạy bằng script riêng trong thư mục dự án, không ghi checkpoint. |
| Giọng đọc | `nhat-ky.md` của vx-demo-01 ghi "TTS 0/19 trong registry". VieNeu đang được gọi thẳng từ script, không phải tool của registry. |
| Publisher | Chỉ có `tools/publishers/export_bundle.py` (đóng gói tại máy, không tải lên đâu). |
| Số liệu sau khi đăng | Chưa thấy tool nào trong `tools/` lấy lượt xem hay tương tác từ các nền tảng (đã tìm "analytics", "insights", "view_count"; chỉ thấy trong tool phân tích video tham khảo). |

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

Đi qua các stage của pipeline `hybrid`: `script → scene_plan → assets → edit → compose`. Xem mục 4 về lý do chọn `hybrid`.

| Stage | Tái dùng (đã có) | Viết mới |
|---|---|---|
| script | `skills/pipelines/hybrid/script-director.md`, `schemas/artifacts/script.schema.json`. Mỗi `sections[]` có `text`, `start_seconds`, `end_seconds`, `delivery_cues.provider_text` (cách đọc riêng, ví dụ "150 phân khối" thay cho "150cc"), `pronunciation_guides`, `source_ref` (để gắn nguồn luật). Mẫu tham khảo: `projects/vx-demo-01/kich_ban.py`. | `may_reels/kich_ban.py`: kiểm tra trước khi ghi (cụm từ cấm, nguồn luật, số chữ hợp thời lượng theo bảng "Script Word Counts" trong `skills/creative/short-form.md`). |
| scene_plan | `skills/pipelines/hybrid/scene-director.md`, tool `frame_sampler`, `scene_detect`. | `may_reels/chon_canh.py`: chọn cảnh từ `kho_canh` theo `the`, `mo_ta`, `dia_diem`, `co_canh`, `huong`. Chỉ lấy cảnh `dung_duoc`, cắt trong `doan_dung_duoc`, kiểm lại `mat_nguoi` với `quyen_hinh`. Ý nào không có cảnh thì ghi vào tab "Cần quay". |
| assets | `skills/pipelines/hybrid/asset-director.md`, `subtitle_gen`, `audio_enhance`, `transcriber` (faster-whisper, nhận `language`). Mẫu tham khảo: `sinh_giong.py`, `nghe_lai.py`, `can_phu_de.py`, `chuan_bi_canh.py` của vx-demo-01. | Tool giọng mới `tools/audio/vieneu_tts.py` (capability `tts`, provider `vieneu`, chạy CPU), để `tts_selector` tìm thấy. `may_reels/canh.py`: cắt và chuẩn hóa cảnh về 1080×1920, 30 fps. |
| edit | `skills/pipelines/hybrid/edit-director.md`, `video_trimmer`. Lưu ý: chế độ "templated" là đúng chỗ cho làm hàng loạt (`AGENT_GUIDE.md`, mục "Composition Authoring Mode": "Right for batch output"). | Mẫu đồ họa chữ dùng chung cho kênh, đọc màu, font, logo từ `brand/<id>/`. |
| compose | `skills/pipelines/hybrid/compose-director.md`, `video_compose` (chọn Remotion, HyperFrames hoặc FFmpeg theo `edit_decisions.render_runtime`), `hyperframes_compose`, `audio_mixer`, `color_grade`. Profile trong `lib/media_profiles.py`: `youtube_shorts`, `instagram_reels`, `tiktok`. | **`lib/media_profiles.py` không có profile Facebook Reels.** Đã chốt (mục 6, câu 8): Facebook dùng `instagram_reels`, không thêm profile mới. |

Tài liệu nền cho mọi stage: `skills/creative/short-form.md` (1080×1920, vùng an toàn chung 900×1400, chữ từ 42 px, −14 LUFS, đỉnh −1 dBTP, đổi hình mỗi 1–3 giây, có chữ ngay từ 0,5 giây đầu).

### Bước 3: Chấm điểm

| | |
|---|---|
| Tái dùng | `skills/meta/reviewer.md` (tối đa 2 vòng sửa, phân loại critical/suggestion/nitpick). `lib/slideshow_risk.py` `score_slideshow_risk(scenes, edit_decisions, renderer_family, render_runtime)`: điểm từ 0 đến 5, chia mức `strong` < 2, `acceptable` < 3, `revise` < 4, `fail` ≥ 4. Hàm đọc các trường `type`, `description`, `shot_language.shot_size`, `shot_language.camera_movement`, `shot_intent`, `information_role`, `narrative_role`, `hero_moment`, nên scene_plan phải điền đủ các trường này mới chấm được có nghĩa. Schema `schemas/artifacts/final_review.schema.json` bắt buộc 5 nhóm kiểm tra: `technical_probe`, `visual_spotcheck` (cần `frames_sampled` ≥ 4 theo reviewer), `audio_spotcheck`, `promise_preservation`, `subtitle_check`. Tool `visual_qa` (`review`, `probe`, `audio_levels`), `composition_validator`, `audio_probe`, `frame_sampler`. |
| Viết mới | `may_reels/cham_diem.py`, phần tất định: (1) cụm từ cấm và câu sáo trên lời đọc, chữ trên màn hình và caption; (2) ý luật nào cũng có nguồn; (3) mọi cảnh đều `dung_duoc`, nằm trong `doan_dung_duoc`, thỏa quyền hình; (4) thời lượng, khổ, fps, LUFS, đỉnh âm; (5) chữ nằm trong vùng an toàn; (6) không có tool tạo hình/video AI nào trong `asset_manifest`. Kết quả gồm điểm, lý do, và quyết định qua/làm lại/bỏ, ghi vào cột máy trên Sheet. |
| Ngưỡng | 75 điểm (mục 6, câu 12). Trượt sau 2 vòng sửa vẫn vào hàng chờ, kèm cảnh báo "Dưới ngưỡng". |
| Đã làm (2026-11-16) | Xem mục 9. `diem_qa` là điểm rubric nội dung (`brand/<kenh>/rubric.yaml`, `may_reels/cham_diem.py`, skill `skills/may-reels/cham-diem.md`). Điểm kỹ thuật cũ đổi tên thành `diem_ky_thuat` và chỉ là một tiêu chí. |

### Bước 4: Hàng chờ duyệt

| | |
|---|---|
| Tái dùng | `tools/publishers/export_bundle.py`: đóng gói video, phụ đề, `metadata.json`, `description.txt` vào `projects/<id>/exports/` và trả về `publish_log` có `status: "exported"`. Schema `publish_log` có trạng thái `pending_review`. |
| Viết mới | `may_reels/hang_cho.py`: đưa video đã qua chấm điểm lên tab "Hàng chờ duyệt" kèm link xem, tiêu đề, mô tả, hashtag (lấy từ `brand.json` `hashtags.facebook/tiktok/youtube`), CTA, điểm, nguồn luật. Nội dung này được chốt ở đây và không đổi lúc đăng. |
| Cổng (B) | Người xem video rồi chọn `duyet` = `Duyệt`. Người xem video qua link Google Drive (mục 6, câu 3). |

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

### 3.2. Hai phương án

**Phương án 1: chỉ thêm skill bọc ngoài, giữ manifest `hybrid`.** Skill ghi một mục `approval_policy` dựa trên dòng Sheet đã duyệt chủ đề, rồi ghi `human_approved=True` cho cả `script`, `scene_plan`, `assets`.
- Ưu điểm: không thêm file nào vào thư mục lõi.
- Nhược điểm: người chưa hề xem kịch bản, kế hoạch cảnh hay tư liệu mà checkpoint vẫn ghi "người đã duyệt". Như vậy là dùng cờ duyệt sai nghĩa, và nhật ký kiểm tra sẽ nói sai sự thật.

**Phương án 2 (đã chọn, mục 6 câu 9): manifest riêng `pipeline_defs/may-reels.yaml` cộng skill bọc ngoài.**
- Chép cấu trúc stage của `hybrid.yaml` và trỏ `skill` của từng stage về director skill có sẵn của hybrid (`pipelines/hybrid/*-director`). Không viết director mới.
- `idea: human_approval_default: true` ứng với cổng (A) trên Sheet. `publish: true` ứng với cổng (B). `script`, `scene_plan`, `assets`, `edit`, `compose` đặt `false`.
- Thay cho cổng của người ở các stage đó là cổng tự động: reviewer + `may_reels/cham_diem.py`. Trượt thì làm lại tối đa 2 vòng (đúng `reviewer.md`), vẫn trượt thì đánh dấu "bỏ" hoặc "cần quay" trên Sheet.
- Lý do khuyên dùng: cổng duyệt vẫn được code ép đúng như upstream thiết kế, và checkpoint chỉ ghi `human_approved=True` ở đúng hai chỗ người thật sự duyệt.
- Cái giá: phải thêm file vào `pipeline_defs/`. `lib/pipeline_loader.py` chỉ đọc từ `PIPELINE_DEFS_DIR`, và `_stage_requires_approval()` gọi `load_pipeline_readonly(pipeline_type)` không kèm thư mục khác, nên manifest không đặt trong `may_reels/` được. Việc này được ghi ở "Điểm chạm upstream".

**Các luật chọn runtime và hỏi trước khi đổi**, dùng chung cho cả hai phương án: người dùng chốt một lần cho mỗi kênh (runtime, giọng, có nhạc hay không), ghi trong `brand/<id>/`. Mỗi lần chạy, máy ghi lại quyết định `render_runtime_selection` vào `decision_log` với đủ cả hai runtime trong `options_considered` và lý do "đã chốt theo cấu hình kênh". Gặp vật cản (runtime hỏng, thiếu cảnh, thiếu nguồn luật), máy không tự đổi hướng: dừng video đó và ghi lý do lên Sheet.

**Ai chạy trợ lý khi không có người ngồi:** phần sáng tạo cần trợ lý AI, Python không tự chạy director skill được. Dự kiến dùng Claude Code chế độ không tương tác (`claude -p`), gọi theo lịch bằng Windows Task Scheduler. Đã chốt (mục 6, câu 10), với điều kiện phải chạy thử thật ở bước sản xuất. Cách gọi này **chưa xác minh** trên máy này.

---

## 4. Chọn pipeline: `hybrid`

| Pipeline | Hợp với loại video nào (theo manifest) | Có khớp video "cảnh thật từ kho + đồ họa chữ" không |
|---|---|---|
| **`hybrid`** | "Source footage plus support visuals". Stage `assets` có `subtitle_gen`, `tts_selector`, `diagram_gen`. `compose` dùng `video_compose` + `hyperframes_compose` + `audio_mixer`. `stability: production`. | **Khớp.** Cảnh thật là lớp chính, đồ họa chữ, phụ đề và giọng đọc là lớp hỗ trợ. vx-demo-01 cũng đã chọn `hybrid`. Mục review_focus "Source content remains visually primary" và "Optional generated inserts do not eclipse source truth" khớp với quy tắc cấm của kênh. |
| `talking-head` | Footage có "a person speaking". Stage `script` **bắt buộc** `transcriber`, và section phải có mốc thời gian lấy từ transcript của footage. `stability: beta`. | Không khớp. Lời đọc ở đây là giọng TTS chạy theo kịch bản, không có người nói trước máy quay. Chỉ hợp nếu sau này kênh quay thầy nói trực tiếp. |
| `clip-factory` | Một nguồn dài (webinar, livestream) cắt ra nhiều clip ngắn. `script` bắt buộc `transcriber` và phải tìm ra "N candidate clips". `stability: beta`. | Không khớp. Kho có 24 cảnh ngắn (video dài nhất khoảng 31 giây), không có nguồn dài để cắt. Cái hợp với máy là ý "nhiều video một lượt", và việc đó làm ở lớp skill bọc ngoài. |

Ghi chú: `documentary-montage` (lấy cảnh từ kho stock miễn phí và kho lưu trữ mở) chưa đọc chi tiết trong phiên này. Theo mô tả trong `AGENT_GUIDE.md` thì nó dựa vào stock bên ngoài, trái với quy tắc "không stock nước ngoài".

Về runtime trong `hybrid`: manifest ghi "Hybrid typically uses render_runtime='remotion'", còn `idea-director.md` ghi "neither is an auto-default". vx-demo-01 đã dựng bằng HyperFrames (`hyperframes check` báo 0 lỗi, có ảnh xem trước). Đã chốt HyperFrames (mục 6, câu 11), với điều kiện dựng xong được một video từ đầu đến cuối.

---

## 5. Rủi ro

### 5.1. Đường dẫn tuyệt đối Windows trong `brand.json`

- Các trường `nguon_kenh`, `context.*.duong_dan`, `kho_canh[].duong_dan`, `anh_that[]` và `kho_md` đều là đường dẫn tuyệt đối dạng `C:\Users\Thinkpad P15V3\Desktop\Claude code\video-agent-team-kit\...`. Riêng `assets.*` và `font.files.*` là đường dẫn tương đối trong repo, không có vấn đề.
- Hậu quả: (1) chạy trên máy khác, trong CI hoặc trên cloud thì gãy; (2) file đã commit lên repo public nên lộ tên người dùng Windows và cấu trúc thư mục; (3) tên file có dấu cách và chữ có dấu tiếng Việt dễ hỏng khi đưa vào lệnh FFmpeg, HyperFrames hay Remotion. Có thể gặp lệch chuẩn Unicode NFC/NFD (chưa xác minh trên máy này). Ngoài ra Remotion đọc file qua `remotion-composer/public/`, thư mục này bị gitignore.
- **Đã xử lý ngày 2026-11-15** (mục 6, câu 18):
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

**Kết quả chạy test nền trên máy này:** xem mục 7.

### 5.4. Rủi ro khác

- Toàn văn `context/*.md` đã tách khỏi `brand.json` sang `brand/<id>/_local/context/` (bị gitignore). Bản cũ vẫn còn trong lịch sử git.
- `brand.json` vẫn giữ `mau_tong_hop` (toàn văn `mau/TONG-HOP.md`). Mục `mau_thuan_business_vs_channel` vẫn trích một số dòng của `business.md` (hotline, website, số liệu). Hai phần này chưa được tách vì yêu cầu chỉ nói tới `context/*.md`.
- `brief.target_platform` không có `facebook`, `lib/media_profiles.py` không có profile Facebook (xem mục 2).
- Đã xử lý ngày 2026-11-15: giá trị riêng của Vạn Xuân trong `nap_kenh.py` (tiền tố `vx-`, font, thư mục video) đã chuyển sang `brand/<id>/cau-hinh.yaml`. Kênh không có file này thì `brand.json` ghi `canh_bao`, máy không tự đoán giá trị.
- Giấy phép thương mại của VieNeu và PhoWhisper chưa xác minh.
- Lỗi mã hóa console: Python mặc định in bằng cp1252 trên máy này và đã báo `UnicodeEncodeError` khi in tiếng Việt. Đã xử lý bằng `PYTHONUTF8=1`, đặt qua `tools_local/py.cmd` hoặc biến môi trường (xem `HUONG-DAN-SU-DUNG.md`).

---

## 6. Quyết định đã chốt

Người dùng trả lời ngày 2026-11-15. Số câu giữ đúng thứ tự câu hỏi cũ. Ba câu 5, 6 và 17 có chỗ người dùng **còn để trống** trong bản trả lời. Những chỗ đó ghi **chưa chốt**, máy không tự đoán.

**Google Sheet và cách duyệt**
1. Tạo Sheet mới tên "Máy Reels" trong tài khoản Google của người dùng. Máy truy cập bằng **service account**: người dùng chia sẻ Sheet cho email của service account. File khóa để trong `secrets/` (đã gitignore), đường dẫn đọc từ `.env`.
2. Ô Duyệt là dropdown có ba giá trị: `Duyệt` / `Sửa` / `Bỏ`. Chọn `Sửa` thì đi kèm cột ghi chú của người. Mọi giá trị khác, kể cả ô trống, đều tính là **chưa duyệt**.
   **Cập nhật 2026-11-15** theo yêu cầu xây lớp nối Sheet:
   - Tab Hàng chờ: cột `duyet`, dropdown `Chờ duyệt` / `Duyệt` / `Sửa` / `Bỏ`.
   - Tab Ý tưởng: cột `duyet_chu_de`, dropdown `Chờ` / `Làm` / `Bỏ`. Cổng A mở khi chọn `Làm`.
   - Ô trống được hiểu là giá trị chờ, vì máy không ghi vào cột của người, kể cả giá trị mặc định.
   - Khóa của tab Ý tưởng là `kenh` + `ma`, không chỉ `ma`. Lý do: một Sheet dùng cho mọi kênh (câu 4), mà mã chủ đề trong `brand.json` chỉ duy nhất trong một kênh.
3. Người duyệt xem video qua **link Google Drive**. Máy tải video lên Drive rồi ghi link vào hàng chờ.
4. **Một Sheet cho mọi kênh**, có cột Kênh (mã kênh trong `brand/<id>/`).

**Đăng bài**

5. Tài khoản đăng:
   - Facebook: Fanpage `facebook.com/hoclaixephutho`. Người dùng sẽ tự tạo app Meta. Người dùng có quyền admin Fanpage hay chưa: **chưa chốt** (bản trả lời còn để trống `<có / chưa có>`).
   - YouTube: kênh nào thì **chưa chốt** (bản trả lời còn để trống `<tên hoặc link kênh>`).
   - TikTok: chưa đăng ký app. Giai đoạn đầu người dùng **đăng tay**. Máy chỉ chuẩn bị file và caption, không gọi API TikTok.
6. Đăng cùng giờ trên các nền tảng. Số video mỗi ngày cho mỗi nền tảng ghi `<1>`, nên tạm hiểu là 1 nhưng vẫn coi là **chưa chốt** (có thể là chỗ chưa điền). Giờ đăng là 11:30 hay 19:30: **chưa chốt**.
7. Chuyển sang đăng thật bằng **cờ dòng lệnh**, không bằng ô trên Sheet. Chỉ người dùng được bật cờ này. Không có cờ thì mặc định chạy thử.
8. **Một bản 9:16 dùng chung** cho cả 3 nền tảng. Facebook dùng profile `instagram_reels`. Brief ghi `target_platform = "generic"`, danh sách nền tảng ghi trong `brief.metadata`. **Không sửa** `lib/media_profiles.py`.

**Chạy không dừng**

9. Chọn **phương án 2**: manifest riêng `pipeline_defs/may-reels.yaml`. Đã ghi vào "Điểm chạm upstream" của `NGUYEN-TAC.md`.
10. Chạy `claude -p` theo lịch của Windows Task Scheduler trên chính máy này. Điều kiện: **phải chạy thử thật ở bước sản xuất** trước khi tin dùng. Sổ chi phí ghi **số lượt chạy** và **thời gian chạy** của trợ lý, không đo token.
11. Runtime là **HyperFrames**, chốt một lần trong `brand/vanxuan/`, sau đó máy không hỏi lại. Điều kiện: phải dựng xong được một video từ đầu đến cuối. **Đã đạt ngày 2026-11-15** với `projects/vx-005-a1-xe-150cc` (xem mục 8). Runtime đã ghi vào `brand/vanxuan/san-xuat.yaml`.
12. Ngưỡng **75 điểm**. Trượt sau 2 vòng sửa thì video vẫn vào hàng chờ, kèm cảnh báo "Dưới ngưỡng".

**Nội dung và quyền**

13. Trước mắt chỉ dùng **12 chủ đề chưa làm** trong `chu-de.md`. Việc máy tự đề xuất chủ đề mới để sang giai đoạn sau.
14. Với mỗi nguồn luật, lưu vào dự án: link, ngày mở, và điều khoản được dẫn. **Người duyệt chủ đề** chịu trách nhiệm xác nhận điều khoản đúng.
    **Cập nhật 2026-11-16:**
    - Người duyệt chủ đề tự tra văn bản, rồi ghi `nguon_doi_chieu` trong `chu-de.md` của kênh **đến số khoản**. Ví dụ: "Luật 36/2024/QH15, Điều 22, khoản 2, 3".
    - Chặn cứng chỉ cho phép đúng các điều, khoản đã ghi. Cách ghi liệt kê "khoản 2, 3" hoặc "khoản 2 và 3" được hiểu là cả hai khoản.
    - `nguon_luat_da_mo` trong `rubric.yaml` **giữ tắt**: máy không tự tin vào nguồn agent mở.
    - Đã áp dụng cho `giao-nhau-khong-bao-hieu` (Điều 22 khoản 2) và `vong-xuyen` (Điều 22 khoản 2, 3). Người dùng xác nhận trực tiếp với văn bản luật.

    **Cập nhật 2026-11-16 (sau đó): máy đề xuất, người xác nhận.**
    - Người duyệt không phải tự tra văn bản. Lệnh `nguon-luat` cho agent (`skills/may-reels/tra-nguon-luat.md`) mở văn bản chính thức, kiểm tra hiệu lực, rồi ghi lên tab Ý tưởng các cột của máy: `nguon_de_xuat`, `trich_nguyen_van`, `link_nguon`, `ngay_tra`, `ghi_chu_may`.
    - Người chọn `xac_nhan_nguon` (Đúng/Sai). **Người vẫn là bước quyết định.**
    - `nguon-luat ap-dung` chỉ chép những đề xuất được chọn "Đúng" vào `chu-de.md`, sao lưu trước khi sửa.
    - `nguon_luat_da_mo` **vẫn tắt**.
    - **"Tới mức khoản"** (`may_reels/nguon_luat.py`, hàm `du_muc_khoan`):
      - Mỗi lần nhắc "Điều N" phải kèm khoản, điểm hoặc mục.
      - QCVN phải có mục, phụ lục, Điều, hoặc số hiệu biển/vạch.
      - Phần không phải văn bản pháp luật (ví dụ `context/business.md`) không xét.
      - Vì vậy `a1-xe-150cc` ("Điều 57 khoản 1 điểm a và Điều 89") cũng thuộc diện phải tra, do Điều 89 chưa có khoản.
    - `san-xuat` từ chối chủ đề chưa đạt mức trên và ghi lý do vào `ghi_chu_may`. Ngoại lệ: chủ đề ghi "Không cần nguồn luật".
15. Máy **được tự cắt khung** theo vùng ghi trong `can_xu_ly`. Máy **không tự làm mờ** mặt người và biển số. Cảnh cần làm mờ thì chỉ dùng đoạn không cần xử lý.
16. **Chưa dùng nhạc nền.**
17. Dùng giọng VieNeu "Hải Đăng" làm tool chính thức hay chờ người dùng kiểm tra giấy phép: bản trả lời ban đầu còn để trống. **Cập nhật 2026-11-15:** người dùng chốt giọng VieNeu "Hải Đăng" trong `brand/vanxuan/san-xuat.yaml`. Máy gọi VieNeu qua `may_reels/giong.py`, không qua tool trong `tools/audio/`. Giấy phép thương mại của VieNeu vẫn **chưa xác minh**.

**Dữ liệu trên repo public**

18. Đồng ý. Đã sửa `tools_local/nap_kenh.py` (xem mục 5.1):
    - `brand.json` không còn đường dẫn tuyệt đối.
    - Thư mục kênh gốc đọc từ `KENH_GOC_DIR` trong `.env`.
    - Toàn văn `context/*.md` tách sang `brand/<id>/_local/` (bị gitignore).
    - Tiền tố mã video, thư mục video và font chuyển sang `brand/<id>/cau-hinh.yaml`.
    - Lịch sử git cũ vẫn còn bản `brand.json` có đường dẫn tuyệt đối và toàn văn context: commit `dc52b79` đã đẩy lên GitHub. **Không viết lại lịch sử git khi chưa hỏi người dùng.**
19. Số liệu cần lấy:
    - lượt xem, thời gian xem trung bình, lượt chia sẻ, bình luận;
    - cột tin nhắn do người dùng nhập tay (máy không ghi vào cột này).

    Đo ở 3 mốc: 1, 3 và 7 ngày sau khi đăng.

### Việc còn chờ người dùng

- Câu 5: có quyền admin Fanpage chưa; kênh YouTube nào.
- Câu 6: số video mỗi ngày (xác nhận 1), giờ đăng 11:30 hay 19:30.
- Giấy phép thương mại của VieNeu và PhoWhisper (câu 17): chưa xác minh.
- Có viết lại lịch sử git để xóa bản `brand.json` cũ khỏi GitHub hay không (xem câu 18).

---

## 8. Dựng một video từ đầu đến cuối (Việc 1, ngày 2026-11-15)

- **Dự án:** `projects/vx-005-a1-xe-150cc`, cùng chủ đề với vx-demo-01, dựng bằng manifest `pipeline_defs/may-reels.yaml`.
  - Có checkpoint ở cả 7 stage.
  - Có file `renders/final.mp4`: 1080×1920, 30 fps, 49,3 giây, −14,0 LUFS.
  - `final_review` đạt `pass`.
  - Stage publish chỉ dùng `export_bundle` và dừng ở `awaiting_human`.
  - Cổng idea ghi `human_approved=True` kèm tham chiếu ô `duyet_chu_de = "Làm"` trên Sheet.
- **Thời gian từng stage** (lần chạy cuối):

  | Stage | Thời gian |
  |---|---|
  | idea | 2,4 giây |
  | script | 0,1 giây |
  | scene_plan | 0,1 giây |
  | assets | khoảng 12 phút ở lần sinh giọng thật (29 lần sinh và nghe lại); 31 giây khi dùng lại cache |
  | edit | 0,2 giây |
  | compose | khoảng 2,5 phút (render 147 giây) |
  | publish | 0,2 giây |

- **Các chỗ agent còn muốn hỏi người**, kèm cách đã xử lý:
  1. Chọn runtime: chốt trong `san-xuat.yaml`.
  2. Chọn giọng: chốt trong `san-xuat.yaml`.
  3. Có nhạc không: chốt trong `san-xuat.yaml`.
  4. Đổi cảnh trùng ở s6: thành luật "không lặp cảnh trong video".
  5. Thời lượng giữ màn kết: thành `khung_hinh.giu_man_ket_giay`.
  6. Bản giọng nào đúng: PhoWhisper nghe lại, thay cho việc người nghe.
  7. Âm lượng sau khi HyperFrames trộn lại (−12,2 LUFS): thêm bước chuẩn hóa sau render.
  8. Hook dài 6,2 giây: thành luật "hook trong 3 giây". Luật này có sau khi `vx-005` đã dựng, nên `vx-005` vẫn vi phạm.
- **Đã sửa trong quá trình dựng:**
  - Giọng VieNeu đôi khi nuốt số hoặc đọc sai, nên bước sinh giọng có nghe lại tự động (`may_reels/giong.py`).
  - Bản đầu ghi checkpoint compose là `completed` dù `final_review` = `revise`; đã sửa thành chỉ ghi `completed` khi kết quả là `pass`.
- **Kiểm tra bộ dựng chung `may_reels/dung/`:** dự án `projects/vx-thu-may` (cùng nội dung, hook rút còn 2,7 giây) đạt điểm QA 100, dài 45,3 giây.

---

## 7. Kết quả test nền

Chạy ngày 2026-11-15 bằng `.\.venv\Scripts\python.exe -m pytest -q` trên nhánh `kenh-vanxuan` (commit `dc52b79` cộng hai tài liệu này). Phải cài `requirements-dev.txt` trước, vì `.venv` chưa có pytest.

**2913 passed, 19 skipped, 2 failed** (khoảng 8 phút). Hai test hỏng đều nằm ở code upstream mà nhánh này không sửa:

- `tests/lib/test_terminal_frame_pacing.py::test_trace_matches_the_actual_terminal_scene_cursor`
- `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]`: file `.webp` bị gắn nhãn `data:image/png`.

Chưa tìm nguyên nhân, và chưa xác minh hai test này có hỏng trên máy khác hay không. Code của Máy Reels không được làm tăng con số 2 này.

Các test quét tài liệu (`test_skill_execute_examples.py`, `test_phase0_contracts.py`, `test_taste_governance_contracts.py`) đều qua sau khi thêm hai tài liệu.

### Lần chạy sau khi sửa `nap_kenh.py` (2026-11-15)

Chạy bằng `tools_local\py.cmd -m pytest -q` (có `PYTHONUTF8=1`):

**2925 passed, 19 skipped, 1 failed** (khoảng 9 phút).

- Vẫn hỏng: `test_checkpoint_only_resume_preserves_media_format[webp]`, giống lần trước.
- Lần này qua: `test_trace_matches_the_actual_terminal_scene_cursor`. Chưa rõ nó qua là nhờ `PYTHONUTF8=1` hay vì test lúc qua lúc hỏng, nên **chưa xác minh**.
- Số test qua tăng 12 so với lần trước. Trong đó có 9 test mới ở `tests/may_reels/` và 1 test vừa nêu. Chưa đối chiếu nguồn gốc của 2 test còn lại.

---

## 9. Chấm điểm nội dung theo rubric (ngày 2026-11-16)

**Vì sao đổi:** `diem_qa` cũ (`DIEM_TRU` trong `may_reels/dung/kiem_tra.py`) chỉ đo kỹ thuật, nên video có nội dung yếu vẫn được 91. Từ nay:

- **`diem_ky_thuat`:** giữ nguyên công thức cũ, chỉ đổi tên. Không còn mục `canh_tam`, vì cảnh tạm đã được tính trong tiêu chí "Chân thực".
- **`diem_qa`:** tổng rubric `brand/<kenh>/rubric.yaml` (100 điểm, 8 tiêu chí). Trọng số, ngưỡng, trần và từ khóa đều nằm trong file này, code không viết cứng.
- **Chia việc:**
  - Python (`may_reels/cham_diem.py`) đo những gì tất định: nhịp, tỉ lệ thời lượng cảnh thật, phụ đề, thương hiệu, CTA, mốc chữ đầu, độ đứng yên của 3 giây đầu.
  - Agent (`claude -p`, `skills/may-reels/cham-diem.md`) chấm hook, độ đúng và giá trị, phụ đề, CTA từ **bằng chứng của bản đã render**: khung hook, lưới khung, lời PhoWhisper chép từ âm thanh cuối. Agent không chấm trên kịch bản.
  - Python áp trần lên điểm agent khi đo được lỗi cứng, rồi áp trần tổng. Kết quả ghi `renders/score.json` (`schemas/may-reels/score.schema.json`).
- **Chặn cứng** (không vào Hàng chờ, job sang `loi`) khi gặp một trong ba trường hợp, tất cả đều kiểm tra trên bản đã render:
  - cụm từ cấm hoặc câu sáo đã chốt, trong lời nghe được và chữ trên màn hình, kể cả viết không dấu;
  - số hoặc số hiệu luật ngoài `y_chinh`/`nguon_doi_chieu`;
  - tài sản ngoài kho kênh, brand hoặc sơ đồ được phép.
- **Vòng sửa:** dùng lại vòng phản hồi của `san_xuat.py`, nhưng nội dung phản hồi là lý do trừ điểm nội dung, nặng nhất trước. Tối đa 2 vòng. Vẫn dưới ngưỡng thì cột `canh_bao` ghi "Dưới ngưỡng (điểm/ngưỡng)" và 2 lý do nặng nhất; cột này tối đa 3 dòng.
- **Hiệu chỉnh:** tab Hàng chờ có thêm hai cột của người là `diem_cua_toi` và `nhan_xet`.
  - Lệnh `cham-lai` chấm lại video mà không dựng lại.
  - Lệnh `hieu-chinh` so điểm của máy với điểm của người, rồi đề xuất sửa `rubric.yaml`; lệnh này không tự sửa.

**Quyết định của máy, cần người xác nhận:**

1. **Trần tổng.** Rubric gốc không đủ để hai mẫu hỏng "3 giây đầu là logo" và "80% cảnh tạm" rơi xuống dưới ngưỡng: hook bằng 0 vẫn còn 80 điểm. Vì vậy `rubric.yaml` có thêm mục `tran_tong`: hook dưới 8 điểm, hoặc cảnh thật dưới 40% thời lượng, thì tổng tối đa 70.
2. **Video bị chặn vẫn được agent chấm,** để người đọc vẫn hiểu video đó ra sao. `dat` = false, và video không vào Hàng chờ.
3. **Miễn cho số không phải số liệu.** Số đếm 1–10 đứng riêng, cùng số điện thoại, địa chỉ và CTA của kênh, không bị coi là số liệu. Số hiệu luật thì luôn phải có nguồn.
4. **Hai cột của người không có dropdown,** vì người dùng tự tạo cột. Máy đọc điểm một cách linh hoạt, chấp nhận giá trị từ 1 đến 10.

**Chạy thật ngày 2026-11-16** (`cham-lai`, `hieu-chinh`):

| Video | QA cũ (kỹ thuật) | QA mới | Hook | Đúng | Nhịp | Chân thực | Phụ đề | Thương hiệu | CTA | Kỹ thuật | Chặn |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vx-005-a1-xe-150cc | — | bỏ qua | | | | | | | | | không có `ke_hoach.json` (dựng trước khi có máy) |
| vx-006-giao-nhau-khong-bao-hieu | 91 | 76 | 17/20 | 13/15 | 7/10 | 5/15 (43% cảnh thật) | 7/10 | 10/10 | 8/10 | 9,1/10 | Điều 22, khoản 2 |
| vx-007-vong-xuyen | 87 | 70 (trần tổng) | 18/20 | 12/15 | 7/10 | 5/15 (40% cảnh thật) | 8/10 | 10/10 | 10/10 | 8,7/10 | Điều 22, khoản 2, 3 |

- **Cả hai video bị chặn vì cùng một lý do:** `nguon_doi_chieu` của chủ đề chỉ ghi "Luật 36/2024/QH15 (điều về đi qua nơi giao nhau)", không ghi số điều. Agent đã mở link và trích nguyên văn Điều 22. Có hai cách gỡ, **người dùng chọn**:
  - ghi rõ điều khoản vào `nguon_doi_chieu` trong `chu-de.md` rồi nạp lại kho;
  - bật `nguon_luat_da_mo` trong `rubric.yaml`.
- **Agent tìm ra lỗi thật mà điểm kỹ thuật bỏ sót:** ở vx-006, khoảng giây 20, sơ đồ đè lên thẻ chữ làm chữ bị cụt ("Có xe thì n").
- **Thời gian mỗi video:** agent khoảng 36 giây (claude báo khoảng 0,45 USD), cộng thời gian PhoWhisper chép lời âm thanh cuối. Lời chép được lưu theo sha1 của video, nên lần chấm lại sau không phải chép nữa.
- **Sau khi sửa `nguon_doi_chieu`** (cùng ngày, xem mục 6 câu 14), chạy lại `cham-lai`:
  - **Kết quả:** vx-006 và vx-007 hết bị chặn. vx-006 được 72, vx-007 được 70 (trần tổng vì cảnh tạm). Cả hai vẫn dưới ngưỡng 75; lý do nặng nhất là "Chân thực", với 43% và 40% cảnh thật.
  - **Điểm agent của vx-006 dao động giữa các lần chấm** (76 → 79 → 72). Lần cuối, agent cho "Đúng" 7/15 vì cho rằng sơ đồ ở giây 20,2 vẽ sai thứ tự xe. Điều này **chưa xác minh**: người cần xem khung đó. Độ dao động khoảng ±7 điểm cho thấy nên dùng `hieu-chinh` khi đã có `diem_cua_toi`, trước khi tin điểm sát ngưỡng.
- **`hieu-chinh`:** chưa có `diem_cua_toi` nào nên chưa đề xuất. Hai cột này được `sheet init` thêm vào Sheet ngày 2026-11-16, vì trên Sheet thật lúc đó chưa có.

---

## 10. Kho cảnh tự nạp và máy gợi ý cần quay (ngày 2026-11-17)

**Mục tiêu:** quay xong thả file vào một thư mục là máy tự phân tích, gắn nhãn, đưa vào kho; và máy chủ động nói cần quay gì.

**Đã làm:**
- `python -m may_reels kho nap --kenh <mã>` (`may_reels/kho.py`): quét `canh-quay/moi-quay/` của thư mục kênh gốc. File chưa có trong `canh-quay/_kho/index.json` được:
  - đo thông số và tách cảnh bằng `audio_probe`, `scene_detect`, `frame_sampler`, ghép thành lưới `khung.jpg` có in mốc giây;
  - chép lời bằng tool `transcriber` (`may_reels/kho_chep_loi.py`, chạy bằng `MAY_REELS_PY_GIONG`);
  - gắn nhãn bằng agent (`skills/may-reels/gan-nhan-canh.md`), Python kiểm nhãn rồi mới thêm vào `nhan.json`.
- **Định dạng bản ghi giữ nguyên** như `scripts/nap_canh_quay.py` và subagent `phan-loai-canh` của bộ kit kênh. Mã cảnh tính bằng cùng thuật toán; test kiểm rằng mã của cảnh cũ trong kho thật không đổi. Chỉ thêm khóa vào bản ghi `index.json`: `ngay_nap`, `nap_luc`, `nap_boi`, `so_lan_dung`, `ngay_dung_gan_nhat`. Chạy thử phân tích trên clip thật `Học Viên Nam_Hạng A_ trung cảnh.mp4`: mọi thông số khớp bản ghi cũ, mất 1,5 giây. Agent gắn nhãn clip đó sát nhãn cũ (cùng đoạn dùng được 0–11 giây, cùng rủi ro mặt học viên và biển số); khác ở `loai` (THAO thay vì BROLL).
- **Quyền hình** (người dùng chốt 2026-11-17): `nap_kenh.py` chỉ áp điều kiện ngày và `bo_sung` của `quyen_hinh` cho cảnh có mặt người; cảnh không có mặt người dùng được ngay. Cảnh có mặt người lên tab **Quyền hình**; người chọn "Đồng ý" thì lần `kho nap` sau chép vào `quyen_hinh.bo_sung` của `channel.yaml`. `brand.json` của Vạn Xuân không đổi sau khi sửa (24 cảnh cũ giữ nguyên kết quả).
- **Số lần dùng cảnh:** `so_lan_dung`, `ngay_dung_gan_nhat` ghi vào `index.json` sau mỗi video vào Hàng chờ (`san-xuat`, `sua`, `thay-canh`) và sau mỗi `kho nap`. Đếm lại từ `projects/*/ke_hoach.json` mỗi lần, chỉ tính video đã dựng xong, nên không đếm trùng. `so_lan_dung_canh` (dùng cho cảnh báo và QA) đổi sang cùng cách đếm: trước đây đếm cả kế hoạch của job lỗi hay đang chờ quay. Agent sản xuất (`san-xuat-khong-hoi.md`) nhận thêm `ngay_dung_canh_gan_nhat`. Lần chạy đầu: 8/24 cảnh đã dùng, nhiều nhất `hoc-vien-tap-xe-a-ga` 3 lần.
- **Job chờ quay tự quay về sản xuất:** xem `NGUYEN-TAC.md` mục 5.
- `python -m may_reels kho thieu --kenh <mã>` (`may_reels/goi_y_quay.py`, `skills/may-reels/goi-y-quay.md`): danh sách quay gộp theo buổi vào tab Cần quay và bản văn bản để gửi Zalo. Chạy thử thật (`--thu`) với 2 chủ đề đã duyệt và 6 yêu cầu đang mở: 10 cảnh, 3 buổi (đường thật, sân tập, thầy nói trước máy), qua bước kiểm ngay lần đầu.
- Sheet: thêm tab Quyền hình và 9 cột vào cuối tab Cần quay (`sheet init` đã chạy trên Sheet thật).

**Phát hiện khi làm:**
- `lib/source_media_review.review_source_media` không dùng nguyên được cho kho: hàm ghi khung hình vào ngay thư mục chứa file gốc (`.source_review_frames_<tên>`), tức thư mục mới quay; và hàm đọc khóa `text` mà `transcriber` không trả về, nên phần tóm tắt lời nói luôn rỗng. `kho nap` gọi thẳng các tool mà hàm này dùng. Không sửa file upstream.
- `audio_probe` không đo phần hình. Kích thước khung (có tính cờ xoay của điện thoại) đo bằng ffprobe như `source_media_review` và `nap_canh_quay.py`.
- GPU của máy không dùng được cho faster-whisper: thiếu `cublas64_12.dll` (CUDA 12). `transcriber` tự chuyển sang CPU int8, nên chép lời model lớn chậm.
- Hugging Face không tạo được symlink trong cache trên Windows này (`WinError 1314`), nên tải model mới bị dở (`faster-whisper-large-v3` trong cache thiếu `model.bin`). Model dùng để so sánh được tải vào thư mục thường `~/.cache/whisper-local/`.

**Có cần PhoWhisper không: CHƯA kết luận.** Thử trên 2 clip thật có tiếng trong kho (`Nhieu_hoc_vien_nu_Cancanh.mp4`, `Video quay demo/snaptik...mp4`), cả ba model đều chạy qua tool `transcriber` bằng CPU. Lần chạy bị hệ thống dừng vì máy thiếu bộ nhớ, và chưa chạy lại.

| Clip 1 (khoảng 2,5 giây có lời) | Thời gian | Kết quả |
|---|---|---|
| `base` (mặc định của transcriber) | 2,3 giây | "Đi theo đi lúc quen là chết hả hình? Đúng rồi" (sai từ) |
| `large-v3` | khoảng 25 phút (chạy cùng lúc với test) | "Đi thế không đến lúc quen là chết hết" |
| PhoWhisper-large | chưa chạy | — |
| Bản chép cũ trong kho (script của bộ kit) | — | "đi thế đến lúc quen là chết đấy…", kèm một câu bịa ở đoạn lặng |

- Clip 2 chưa có kết quả.
- Mặc định tạm thời là PhoWhisper (`MAY_REELS_MODEL_CHEP_LOI` để đổi), vì máy đã dùng nó để nghe lại giọng đọc và nó chạy offline. Nhưng chưa có số liệu chứng minh nó tốt hơn trên cảnh quay thật.
- Model lớn chạy CPU tốn khoảng 3 GB bộ nhớ: `kho nap` với nhiều video có tiếng có thể chậm, hoặc gặp thiếu bộ nhớ khi chạy cùng việc khác.
- Muốn chạy lại phép so sánh: cài thư viện CUDA 12 (cuBLAS, cuDNN) để chạy GPU, hoặc chạy vào lúc máy rảnh.

**Sống chung với script cũ của bộ kit:** `scripts/nap_canh_quay.py` quét cả `canh-quay/moi-quay/`. Nếu script cũ lập index trước, `kho nap` nhận các file đó về (ghi `ngay_nap` thật, gắn nhãn) chứ không bỏ qua; cảnh đã nạp bằng `kho nap` thì script cũ giữ nguyên vì `dau` không đổi. Hướng dẫn `canh-quay/DOC-TOI.md` trong thư mục kênh gốc vẫn chỉ tới script cũ: máy không sửa file đó.

**Việc còn lại / chưa làm:**
- `KHO.md` (bảng tóm tắt cho người đọc, do subagent `phan-loai-canh` viết) **chưa được** `kho nap` cập nhật.
- Mục 6 của yêu cầu (đường dẫn tuyệt đối trong `brand.json`) đã xử lý từ 2026-11-15 (mục 5.1): `brand.json` không còn đường dẫn tuyệt đối, thư mục kênh gốc khai báo một lần bằng `KENH_GOC_DIR` trong `.env`. Lần này không đổi gì thêm. Còn lại: lịch sử git (commit `dc52b79`) vẫn chứa bản cũ.

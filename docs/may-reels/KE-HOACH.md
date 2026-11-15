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
| Cổng (A) | Chỉ những dòng có Duyệt = `Duyệt` mới sang bước Sản xuất. |
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
| compose | `skills/pipelines/hybrid/compose-director.md`, `video_compose` (chọn Remotion, HyperFrames hoặc FFmpeg theo `edit_decisions.render_runtime`), `hyperframes_compose`, `audio_mixer`, `color_grade`. Profile trong `lib/media_profiles.py`: `youtube_shorts`, `instagram_reels`, `tiktok`. | **`lib/media_profiles.py` không có profile Facebook Reels.** Dùng `instagram_reels` cho Facebook hay thêm profile mới là câu hỏi đang chờ chốt. |

Tài liệu nền cho mọi stage: `skills/creative/short-form.md` (1080×1920, vùng an toàn chung 900×1400, chữ từ 42 px, −14 LUFS, đỉnh −1 dBTP, đổi hình mỗi 1–3 giây, có chữ ngay từ 0,5 giây đầu).

### Bước 3: Chấm điểm

| | |
|---|---|
| Tái dùng | `skills/meta/reviewer.md` (tối đa 2 vòng sửa, phân loại critical/suggestion/nitpick). `lib/slideshow_risk.py` `score_slideshow_risk(scenes, edit_decisions, renderer_family, render_runtime)`: điểm từ 0 đến 5, chia mức `strong` < 2, `acceptable` < 3, `revise` < 4, `fail` ≥ 4. Hàm đọc các trường `type`, `description`, `shot_language.shot_size`, `shot_language.camera_movement`, `shot_intent`, `information_role`, `narrative_role`, `hero_moment`, nên scene_plan phải điền đủ các trường này mới chấm được có nghĩa. Schema `schemas/artifacts/final_review.schema.json` bắt buộc 5 nhóm kiểm tra: `technical_probe`, `visual_spotcheck` (cần `frames_sampled` ≥ 4 theo reviewer), `audio_spotcheck`, `promise_preservation`, `subtitle_check`. Tool `visual_qa` (`review`, `probe`, `audio_levels`), `composition_validator`, `audio_probe`, `frame_sampler`. |
| Viết mới | `may_reels/cham_diem.py`, phần tất định: (1) cụm từ cấm và câu sáo trên lời đọc, chữ trên màn hình và caption; (2) ý luật nào cũng có nguồn; (3) mọi cảnh đều `dung_duoc`, nằm trong `doan_dung_duoc`, thỏa quyền hình; (4) thời lượng, khổ, fps, LUFS, đỉnh âm; (5) chữ nằm trong vùng an toàn; (6) không có tool tạo hình/video AI nào trong `asset_manifest`. Kết quả gồm điểm, lý do, và quyết định qua/làm lại/bỏ, ghi vào cột máy trên Sheet. |
| Chưa xác minh | Ngưỡng điểm để được vào hàng chờ. |

### Bước 4: Hàng chờ duyệt

| | |
|---|---|
| Tái dùng | `tools/publishers/export_bundle.py`: đóng gói video, phụ đề, `metadata.json`, `description.txt` vào `projects/<id>/exports/` và trả về `publish_log` có `status: "exported"`. Schema `publish_log` có trạng thái `pending_review`. |
| Viết mới | `may_reels/hang_cho.py`: đưa video đã qua chấm điểm lên tab "Hàng chờ duyệt" kèm link xem, tiêu đề, mô tả, hashtag (lấy từ `brand.json` `hashtags.facebook/tiktok/youtube`), CTA, điểm, nguồn luật. Nội dung này được chốt ở đây và không đổi lúc đăng. |
| Cổng (B) | Người xem video rồi điền Duyệt = `Duyệt`. Chỗ người xem video (Drive hay thư mục chia sẻ) đang chờ chốt. |

### Bước 5: Đăng

| | |
|---|---|
| Tái dùng | Mẫu khai báo `BaseTool` của `export_bundle.py`. Schema `publish_log`. `.gitignore` đã có `.youtube-token.json`, cho thấy upstream đã tính đến OAuth YouTube nhưng **chưa có code**. |
| Viết mới | `tools/publishers/youtube_shorts.py`, `tools/publishers/facebook_reels.py`, `tools/publishers/tiktok.py`. Mỗi file kế thừa `BaseTool`, `capability = "publish"`, mặc định chạy thử, import thư viện mạng bên trong hàm. `may_reels/dang.py`: đọc lại ô Duyệt ngay trước khi đăng, chống trùng theo cặp (mã video, nền tảng), ghi sổ đăng local và tab đăng trên Sheet. |
| Chưa xác minh | Điều kiện API của từng nền tảng: quyền của Meta Graph API cho Reels trên Fanpage, quota của YouTube Data API, và việc TikTok Content Posting API có cần duyệt app trước khi đăng công khai hay không. Chưa đọc tài liệu nền tảng trong phiên này. |

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

**Phương án 2 (khuyên dùng): manifest riêng `pipeline_defs/may-reels.yaml` cộng skill bọc ngoài.**
- Chép cấu trúc stage của `hybrid.yaml` và trỏ `skill` của từng stage về director skill có sẵn của hybrid (`pipelines/hybrid/*-director`). Không viết director mới.
- `idea: human_approval_default: true` ứng với cổng (A) trên Sheet. `publish: true` ứng với cổng (B). `script`, `scene_plan`, `assets`, `edit`, `compose` đặt `false`.
- Thay cho cổng của người ở các stage đó là cổng tự động: reviewer + `may_reels/cham_diem.py`. Trượt thì làm lại tối đa 2 vòng (đúng `reviewer.md`), vẫn trượt thì đánh dấu "bỏ" hoặc "cần quay" trên Sheet.
- Lý do khuyên dùng: cổng duyệt vẫn được code ép đúng như upstream thiết kế, và checkpoint chỉ ghi `human_approved=True` ở đúng hai chỗ người thật sự duyệt.
- Cái giá: phải thêm file vào `pipeline_defs/`. `lib/pipeline_loader.py` chỉ đọc từ `PIPELINE_DEFS_DIR`, và `_stage_requires_approval()` gọi `load_pipeline_readonly(pipeline_type)` không kèm thư mục khác, nên manifest không đặt trong `may_reels/` được. Việc này được ghi ở "Điểm chạm upstream".

**Các luật chọn runtime và hỏi trước khi đổi**, dùng chung cho cả hai phương án: người dùng chốt một lần cho mỗi kênh (runtime, giọng, có nhạc hay không), ghi trong `brand/<id>/`. Mỗi lần chạy, máy ghi lại quyết định `render_runtime_selection` vào `decision_log` với đủ cả hai runtime trong `options_considered` và lý do "đã chốt theo cấu hình kênh". Gặp vật cản (runtime hỏng, thiếu cảnh, thiếu nguồn luật), máy không tự đổi hướng: dừng video đó và ghi lý do lên Sheet.

**Ai chạy trợ lý khi không có người ngồi:** phần sáng tạo cần trợ lý AI, Python không tự chạy director skill được. Dự kiến dùng Claude Code chế độ không tương tác (`claude -p`), gọi theo lịch bằng Windows Task Scheduler. **Chưa xác minh** trên máy này, và đang là câu hỏi chờ chốt.

---

## 4. Chọn pipeline: `hybrid`

| Pipeline | Hợp với loại video nào (theo manifest) | Có khớp video "cảnh thật từ kho + đồ họa chữ" không |
|---|---|---|
| **`hybrid`** | "Source footage plus support visuals". Stage `assets` có `subtitle_gen`, `tts_selector`, `diagram_gen`. `compose` dùng `video_compose` + `hyperframes_compose` + `audio_mixer`. `stability: production`. | **Khớp.** Cảnh thật là lớp chính, đồ họa chữ, phụ đề và giọng đọc là lớp hỗ trợ. vx-demo-01 cũng đã chọn `hybrid`. Mục review_focus "Source content remains visually primary" và "Optional generated inserts do not eclipse source truth" khớp với quy tắc cấm của kênh. |
| `talking-head` | Footage có "a person speaking". Stage `script` **bắt buộc** `transcriber`, và section phải có mốc thời gian lấy từ transcript của footage. `stability: beta`. | Không khớp. Lời đọc ở đây là giọng TTS chạy theo kịch bản, không có người nói trước máy quay. Chỉ hợp nếu sau này kênh quay thầy nói trực tiếp. |
| `clip-factory` | Một nguồn dài (webinar, livestream) cắt ra nhiều clip ngắn. `script` bắt buộc `transcriber` và phải tìm ra "N candidate clips". `stability: beta`. | Không khớp. Kho có 24 cảnh ngắn (video dài nhất khoảng 31 giây), không có nguồn dài để cắt. Cái hợp với máy là ý "nhiều video một lượt", và việc đó làm ở lớp skill bọc ngoài. |

Ghi chú: `documentary-montage` (lấy cảnh từ kho stock miễn phí và kho lưu trữ mở) chưa đọc chi tiết trong phiên này. Theo mô tả trong `AGENT_GUIDE.md` thì nó dựa vào stock bên ngoài, trái với quy tắc "không stock nước ngoài".

Về runtime trong `hybrid`: manifest ghi "Hybrid typically uses render_runtime='remotion'", còn `idea-director.md` ghi "neither is an auto-default". vx-demo-01 đã dựng bằng HyperFrames (`hyperframes check` báo 0 lỗi, có ảnh xem trước). Runtime nào sẽ dùng cho máy là câu hỏi đang chờ chốt.

---

## 5. Rủi ro

### 5.1. Đường dẫn tuyệt đối Windows trong `brand.json`

- Các trường `nguon_kenh`, `context.*.duong_dan`, `kho_canh[].duong_dan`, `anh_that[]` và `kho_md` đều là đường dẫn tuyệt đối dạng `C:\Users\Thinkpad P15V3\Desktop\Claude code\video-agent-team-kit\...`. Riêng `assets.*` và `font.files.*` là đường dẫn tương đối trong repo, không có vấn đề.
- Hậu quả: (1) chạy trên máy khác, trong CI hoặc trên cloud thì gãy; (2) file đã commit lên repo public nên lộ tên người dùng Windows và cấu trúc thư mục; (3) tên file có dấu cách và chữ có dấu tiếng Việt dễ hỏng khi đưa vào lệnh FFmpeg, HyperFrames hay Remotion. Có thể gặp lệch chuẩn Unicode NFC/NFD (chưa xác minh trên máy này). Ngoài ra Remotion đọc file qua `remotion-composer/public/`, thư mục này bị gitignore.
- Hướng xử lý: code của Máy Reels chỉ dùng `file_tuong_doi` (đã có trong `kho_canh`) cộng thư mục gốc của kênh, đọc từ biến môi trường hoặc từ một file cấu hình local bị gitignore. Không đọc `duong_dan`. Có nên sửa `nap_kenh.py` để bỏ hẳn đường dẫn tuyệt đối khỏi brand.json hay không là câu hỏi đang chờ chốt.

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

- `brand/vanxuan/brand.json` (đã commit lên repo public) chứa toàn văn `context/business.md`, `icp.md`, `voice-analysis.md`, `brand-style.md` của kênh. Chưa đọc hết nội dung các file này để biết có thông tin nhạy cảm hay không.
- `brief.target_platform` không có `facebook`, `lib/media_profiles.py` không có profile Facebook (xem mục 2).
- `tools_local/nap_kenh.py` còn viết cứng giá trị của Vạn Xuân (xem `NGUYEN-TAC.md` mục 6). Sẽ gãy với kênh thứ hai.
- Giấy phép thương mại của VieNeu và PhoWhisper chưa xác minh.
- Lỗi mã hóa console: Python mặc định in bằng cp1252 trên máy này và đã báo `UnicodeEncodeError` khi in tiếng Việt.

---

## 6. Câu hỏi cần trả lời trước khi code

**Google Sheet và cách duyệt**
1. Đã có Google Sheet chưa? Sheet thuộc tài khoản nào? Máy truy cập bằng service account (đưa email service account vào danh sách chia sẻ) hay bằng OAuth của chính bạn?
2. Ô Duyệt chỉ nhận đúng `Duyệt`? Có cần thêm giá trị `Sửa` (kèm ghi chú) hoặc `Bỏ` để máy làm lại hoặc gạch bỏ? `duyệt` viết thường có được tính là duyệt không?
3. Lúc duyệt video, bạn xem video ở đâu: link Google Drive, thư mục chia sẻ, hay file trên máy này?
4. Một Sheet cho tất cả kênh (có cột Kênh) hay mỗi kênh một Sheet?

**Đăng bài**
5. Tài khoản đăng: Fanpage `facebook.com/hoclaixephutho` (bạn có quyền admin và sẵn sàng tạo app Meta không?), kênh YouTube nào, tài khoản TikTok nào? Bạn có đồng ý đăng ký app TikTok for Developers không?
6. Lịch đăng: mấy video mỗi ngày cho mỗi kênh, giờ nào, đăng cùng lúc lên 3 nền tảng hay lệch giờ?
7. Chuyển từ chạy thử sang đăng thật bằng cờ dòng lệnh lúc chạy, hay bằng một ô trên Sheet? Ai được bật?
8. Một bản 9:16 dùng chung cho cả 3 nền tảng (vùng an toàn chung 900×1400), hay xuất riêng mỗi nền tảng? Facebook dùng profile `instagram_reels` hay thêm profile mới?

**Chạy không dừng**
9. Đồng ý dùng phương án 2 (manifest riêng `pipeline_defs/may-reels.yaml`, ghi vào "Điểm chạm upstream") không?
10. Máy chạy bằng Claude Code không tương tác (`claude -p`) theo lịch của Windows Task Scheduler trên chính máy này được không? Máy bật vào giờ nào? Chi phí token của trợ lý có cần tính vào sổ chi phí không, và đo bằng cách nào?
11. Runtime dựng cho kênh Vạn Xuân: HyperFrames (vx-demo-01 đã dùng) hay Remotion? Có đồng ý chốt một lần trong `brand/vanxuan/`, sau đó máy không hỏi lại không?
12. Ngưỡng chấm điểm: đạt mức nào thì vào hàng chờ? Trượt sau 2 vòng sửa thì bỏ hay ghi "cần người xem"?

**Nội dung và quyền**
13. Chủ đề chỉ lấy từ `chu-de.md` của kênh (còn 12 chủ đề chưa làm), hay máy được tự đề xuất chủ đề mới? Nếu được thì lấy từ nguồn nào?
14. Nguồn luật: máy có cần tự tải và lưu bản văn bản (PDF hoặc ảnh chụp) vào dự án làm bằng chứng "link đã mở" không? Ai chịu trách nhiệm xác nhận điều khoản đúng: người duyệt chủ đề hay người duyệt video?
15. Cảnh có `can_xu_ly` (làm mờ biển số, cắt khung tránh mặt học viên): máy có được tự làm mờ hoặc tự cắt khung không, hay chỉ dùng đoạn không cần xử lý?
16. Nhạc nền: quy tắc cấm chỉ nói về hình và video. Có dùng nhạc không? Nếu có thì nguồn nào (thư mục `music_library/` của bạn)? vx-demo-01 không dùng nhạc.
17. Giọng đọc: dùng VieNeu "Hải Đăng" làm tool chính thức trong `tools/audio/` được không? Bạn đã kiểm tra giấy phép dùng thương mại của VieNeu chưa?

**Dữ liệu trên repo public**
18. `brand/vanxuan/brand.json` đang lộ đường dẫn tuyệt đối (có tên người dùng Windows) và toàn văn `context/*.md` của kênh trên GitHub. Có muốn sửa `nap_kenh.py` để bỏ đường dẫn tuyệt đối và tách phần context ra file local bị gitignore không? Lịch sử git cũ vẫn còn bản đã đẩy lên.
19. Số liệu: cần những chỉ số nào (lượt xem, thời gian xem trung bình, lượt thích, bình luận, lượt nhắn Zalo?), lấy sau bao lâu kể từ khi đăng, cập nhật bao lâu một lần?

---

## 7. Kết quả test nền

Chạy ngày 2026-11-15 bằng `.\.venv\Scripts\python.exe -m pytest -q` trên nhánh `kenh-vanxuan` (commit `dc52b79` cộng hai tài liệu này). Phải cài `requirements-dev.txt` trước, vì `.venv` chưa có pytest.

**2913 passed, 19 skipped, 2 failed** (khoảng 8 phút). Hai test hỏng đều nằm ở code upstream mà nhánh này không sửa:

- `tests/lib/test_terminal_frame_pacing.py::test_trace_matches_the_actual_terminal_scene_cursor`
- `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]`: file `.webp` bị gắn nhãn `data:image/png`.

Chưa tìm nguyên nhân, và chưa xác minh hai test này có hỏng trên máy khác hay không. Code của Máy Reels không được làm tăng con số 2 này.

Các test quét tài liệu (`test_skill_execute_examples.py`, `test_phase0_contracts.py`, `test_taste_governance_contracts.py`) đều qua sau khi thêm hai tài liệu.

# Máy Reels: nguyên tắc phát triển

Tài liệu này áp dụng cho mọi đoạn code, skill và tài liệu của dự án Máy Reels trên nhánh `kenh-vanxuan`. Máy Reels là cỗ máy tự sản xuất và đăng video dọc 9:16 (Facebook Reels, YouTube Shorts, TikTok) cho từng kênh trong `brand/`. Con người chỉ duyệt trên Google Sheet ở hai chỗ: duyệt chủ đề và duyệt video trước khi đăng.

Mỗi nguyên tắc dưới đây có ghi kèm chỗ trong code hiện tại để đối chiếu. Chỗ nào chưa xác minh được thì có ghi rõ.

---

## 1. Chỗ đặt code và cách sống chung với OpenMontage gốc

### 1.1. Code đặt ở đâu

| Loại | Chỗ đặt | Ghi chú |
|---|---|---|
| Code Python của Máy Reels (đọc/ghi Sheet, chọn cảnh, chấm điểm, hàng chờ, sổ đăng, số liệu) | `may_reels/` (package Python mới ở gốc repo) | Không nằm trong `tools/`. Registry chỉ quét `tools/` (`tools/tool_registry.py`, hàm `discover(package_name="tools")`), nên code ở đây không bị coi là tool. |
| Skill của Máy Reels | `skills/may-reels/` | Skill bọc ngoài pipeline: đọc Sheet, gọi đúng director skill có sẵn, ghi kết quả về Sheet. |
| Publisher mới (đăng lên từng nền tảng) | File mới trong `tools/publishers/`, ví dụ `tools/publishers/youtube_shorts.py` | Kế thừa `BaseTool` (`tools/base_tool.py`), khai báo theo mẫu `tools/publishers/export_bundle.py`: `tier = ToolTier.PUBLISH`, `capability = "publish"`, `provider = "<nền tảng>"`. |
| Tool mới khác (nếu cần, ví dụ giọng VieNeu) | File mới trong gói capability đúng chỗ, ví dụ `tools/audio/` | Theo mục "When Building New Tools" trong `PROJECT_CONTEXT.md`. |
| Test | `tests/may_reels/` | Test chạy không cần mạng, không cần khóa. |
| Tài liệu | `docs/may-reels/` | |

### 1.2. Không sửa file lõi của OpenMontage gốc

Repo có remote `upstream` (`calesthio/OpenMontage`). Muốn kéo được bản cập nhật về sau thì chỉ **thêm file mới**, không sửa file có sẵn của upstream.

Nếu buộc phải sửa (hoặc thêm file vào thư mục lõi mà code lõi đọc theo đường dẫn cứng), phải ghi vào bảng "Điểm chạm upstream" ở cuối tài liệu này, gồm: file nào, sửa gì, vì sao, cách gỡ khi merge.

### 1.3. Lưu ý khi viết tool trong `tools/`

- **Import thư viện nặng bên trong hàm, không đặt ở đầu file.** `registry.discover()` import *mọi* module trong `tools/` (`pkgutil.walk_packages`) và không bắt lỗi import. Một publisher có `import googleapiclient` ở đầu file sẽ làm hỏng toàn bộ registry trên máy chưa cài thư viện đó, kéo theo hỏng hàng loạt test (`tests/contracts/test_agent_skill_pointers.py`, `tests/contracts/test_skill_execute_examples.py`...). `export_bundle.py` cũng import `validate_artifact` bên trong `execute()`.
- `agent_skills` của tool mới chỉ được trỏ tới skill có thật trong `.agents/skills/`. `tests/contracts/test_agent_skill_pointers.py` kiểm tra điều này cho mọi tool registry tìm thấy.
- Tên lớp viết PascalCase, không có hậu tố `Tool` (`AGENT_GUIDE.md`, mục "Tool Class Naming Convention").
- Trong mọi file `.md` thuộc `skills/**`, `docs/**` hoặc ở gốc repo: **không viết ví dụ dạng `<tên>.execute({ ... })` với tên tool chưa đăng ký, hoặc với khóa không có trong `input_schema`.** `tests/contracts/test_skill_execute_examples.py` quét mọi chỗ như vậy và báo lỗi.

### 1.4. Kiến trúc của upstream: Python không điều phối

`PROJECT_CONTEXT.md` và `AGENT_GUIDE.md` quy định: trợ lý AI điều phối, Python chỉ làm tool và lưu trữ, không có "Python orchestrator". Máy Reels giữ đúng tinh thần này:

- Phần **sáng tạo** (kịch bản, kế hoạch cảnh, dựng) do trợ lý làm theo manifest và director skill có sẵn.
- Phần **tất định** (đọc/ghi Sheet, lọc cảnh theo quyền, kiểm tra cụm từ cấm, chống trùng, đăng bài) là Python trong `may_reels/` và `tools/publishers/`.
- "Rule Zero" của `AGENT_GUIDE.md` cấm viết script tạm để gọi tool, bỏ qua pipeline. Dự án mẫu `projects/vx-demo-01/` (gitignore, chỉ có trên máy) đã làm theo kiểu script riêng trong thư mục dự án (`sinh_giong.py`, `chuan_bi_canh.py`, `dung_hf.py`...). Máy Reels sẽ chuyển những việc đó thành code dùng lại được trong `may_reels/` hoặc tool trong `tools/`, không chép script vào từng dự án nữa.

---

## 2. Google Sheet là nguồn sự thật duy nhất về việc duyệt

- Mỗi tab có hai nhóm cột tách bạch: **cột của người** (Duyệt, Ghi chú người duyệt...) và **cột của máy** (Mã video, Trạng thái, Điểm, Link xem trước, Lỗi...). Máy **không bao giờ ghi** vào cột của người, kể cả để "dọn" hay "sửa định dạng".
- Danh sách cột của người được khai báo ở một chỗ duy nhất trong code. Hàm ghi Sheet từ chối ghi vào cột có tên trong danh sách đó và có test chứng minh việc từ chối này.
- Máy chỉ đăng một dòng khi ô Duyệt có đúng giá trị `Duyệt`. Ô trống, `duyệt`, `OK`, `Sửa` hay bất kỳ giá trị nào khác đều là **không đăng**. Việc so khớp chuẩn hóa Unicode NFC và cắt khoảng trắng hai đầu; có phân biệt hoa thường hay không là câu hỏi đang chờ chốt (xem `KE-HOACH.md`).
- Đọc lại ô Duyệt **ngay trước khi đăng**, không dùng giá trị đọc từ đầu lượt chạy. Người có thể rút lại duyệt trong lúc máy đang dựng.
- Trạng thái duyệt không lưu ở chỗ nào khác (không lưu trong checkpoint, không lưu trong file local) như một nguồn thay thế. File local chỉ được ghi lại *bản sao* để kiểm tra về sau.
- Checkpoint của OpenMontage (`lib/checkpoint.py`) vẫn ghi `human_approved=True` ở các cổng duyệt. Lần ghi đó chỉ được phép khi Sheet đang có `Duyệt` cho đúng dòng ấy, và `metadata` của checkpoint phải ghi mã dòng Sheet cùng giá trị đã đọc.

---

## 3. Đăng bài: Python tất định, mặc định chạy thử, chống đăng trùng

- **Không gọi LLM** trong đường đăng bài. Tiêu đề, mô tả và hashtag được chốt *trước* khi dòng vào hàng chờ duyệt, nằm trong cột máy của Sheet để người đọc được khi duyệt. Publisher chỉ đọc lại và gửi đi.
- **Mặc định chạy thử (dry-run).** Muốn đăng thật phải bật bằng một cờ rõ ràng mỗi lần chạy (ví dụ `--that`). Ở chế độ chạy thử, máy kiểm tra đủ mọi điều kiện, in ra sẽ đăng gì lên đâu, và không gọi API ghi nào. Nếu ghi `publish_log`, trạng thái lúc này là `draft`, không phải `published` (schema cho phép `published`, `exported`, `failed`, `draft`, `pending_review`, xem `schemas/artifacts/publish_log.schema.json`).
- **Chống đăng trùng theo cặp (mã video, nền tảng).** Trước khi tải lên:
  1. Tra sổ đăng local và tab đăng trên Sheet. Nếu cặp này đã có trạng thái `published` thì dừng.
  2. Ghi trạng thái "đang đăng" cho cặp đó *trước* khi gọi API. Nếu máy chết giữa chừng, lần chạy sau thấy "đang đăng" thì không tự đăng lại mà báo người kiểm tra.
  3. Đăng xong thì ghi `video_id` và `url` trả về.
- Mỗi lần đăng tạo một mục `publish_log` hợp lệ theo schema (`platform`, `status` và `timestamp` là bắt buộc; `url`, `video_id`, `metadata_used`, `error` thêm vào nếu có).
- Có thể dùng `export_bundle` (`tools/publishers/export_bundle.py`) để đóng gói bản dựng cùng metadata trước khi đăng. Tool này không tải lên đâu cả.

---

## 4. Tuân thủ quy tắc cấm của kênh

Nguồn quy tắc của mỗi kênh:

- `brand/<id>/brand.json`, mục `cam`: `cum_tu_cam`, `noi_dung_cam`, `cau_sao_da_chot`, `cau_sao_cho_duyet`, `cum_tu_cam_du_an`, `cam_du_an`. Mục này do `tools_local/nap_kenh.py` sinh ra từ `banned.md` của kênh và `quy-tac-rieng.yaml`.
- `brand/<id>/quy-tac-rieng.yaml`: `cum_tu_cam`, `quy_tac`, `nguon_canh_khong_dung`.

Với kênh Vạn Xuân hiện tại, các quy tắc là:

| Quy tắc | Máy làm gì |
|---|---|
| Không tạo hình hoặc video bằng AI | Không gọi tool nào thuộc capability `image_generation`, `video_generation`, kể cả qua `image_selector`/`video_selector`. Đồ họa chữ dựng bằng Remotion/HyperFrames từ chữ, màu, font, logo của kênh thì được phép. |
| Không dùng cảnh stock nước ngoài | Chỉ dùng cảnh trong `kho_canh` có `dung_duoc: true`. `nap_kenh.py` đã tự loại cảnh có `nguon` thuộc `nguon_canh_khong_dung` (hiện có 3 cảnh `stock-nuoc-ngoai` bị loại). Không dùng `corpus_builder`, `clip_search` hay các nguồn trong `tools/video/stock_sources/` (Pexels, Pixabay, Archive.org...). |
| Nội dung luật phải có nguồn (tên văn bản và link đã mở) | Kịch bản có ý về luật thì phải kèm tên văn bản và link. Thiếu nguồn thì không đưa vào hàng chờ. `chu_de[].nguon_doi_chieu` trong brand.json là điểm xuất phát, chưa phải "link đã mở". |
| Không hứa kết quả thi | Kiểm tra lời đọc, chữ trên màn hình, caption và mô tả bài đăng theo `cum_tu_cam` + `cum_tu_cam_du_an` (ví dụ "bao đậu", "tỉ lệ đỗ"). Trúng một cụm là trượt. |
| Không bịa số liệu | Con số nào trong kịch bản cũng phải chỉ ra nguồn. `mau_thuan_business_vs_channel` trong brand.json đã đánh dấu các số liệu `chua_co_nguon` và `bi_cam`. |
| Câu sáo | `cau_sao_da_chot` là cấm hẳn. `cau_sao_cho_duyet` thì báo cảnh báo để người duyệt quyết, không tự chặn. |

**Cảnh có mặt người.** Chỉ dùng khi `quyen_hinh` của kênh cho phép:

- `nap_kenh.py` đã gộp điều kiện quyền vào cờ `dung_duoc`: `quyen_hinh.da_dong_y` phải bằng `true`, ngày nạp không được muộn hơn `quyen_hinh.ngay` (hoặc cảnh có tên trong `quyen_hinh.bo_sung`), và mã cảnh không nằm trong `quyen_hinh.ngoai_tru`.
- Lúc chọn cảnh, máy kiểm tra lại: nếu `mat_nguoi: true` thì phải thỏa các điều kiện `quyen_hinh` ở trên, không chỉ tin vào `dung_duoc`.
- Chỉ cắt trong các đoạn `doan_dung_duoc` (nếu cảnh có khai báo). Phải tôn trọng `rui_ro` (ví dụ `mat-hoc-vien`, `bien-so`) và `can_xu_ly`. Máy tự xử lý được đến đâu (tự cắt khung, tự làm mờ) là câu hỏi đang chờ chốt. Trước khi có câu trả lời, cảnh có `can_xu_ly` mà máy không chứng minh được đã xử lý thì không dùng.

---

## 5. Thiếu cảnh quay thì ghi vào tab "Cần quay"

Kho cảnh có chọn được mà không khớp (không đủ cảnh, sai bối cảnh, độ phân giải quá thấp, không có cảnh hợp lệ cho một ý), máy **không** lấp chỗ trống bằng ảnh AI, stock, cảnh lặp lại hay thẻ chữ thay cảnh.

Máy ghi yêu cầu vào tab "Cần quay": kênh, mã video, ý cần minh họa, mô tả cảnh cần quay, khổ, thời lượng tối thiểu, lý do không dùng được cảnh có sẵn. Video đó dừng ở trạng thái "chờ cảnh".

Điều này khớp với luật "No Unilateral Substitutions" và "Escalate Blockers Explicitly" trong `AGENT_GUIDE.md`.

---

## 6. Không viết cứng tên kênh

- Trong `may_reels/`, `skills/may-reels/` và `tools/publishers/` không có chuỗi `vanxuan` hay một giá trị riêng của kênh (số điện thoại, màu, font, hashtag, tiền tố mã video). Mọi thứ đọc từ `brand/<id>/`.
- Mã kênh truyền vào bằng tham số (`--kenh <id>`) hoặc đọc từ cột Kênh trên Sheet.
- Cấu hình chạy riêng từng kênh (ví dụ runtime dựng đã chốt, lịch đăng, tài khoản nền tảng) đặt trong file mới ở `brand/<id>/`. Tên file sẽ chốt khi code.
- Test có một bài kiểm tra quét `may_reels/` để bắt chuỗi `vanxuan`.
- Code có sẵn của nhánh này đang vi phạm nguyên tắc này: `tools_local/nap_kenh.py` viết cứng tiền tố thư mục video `vx-\d+` trong `doc_chu_de`, viết cứng font `BeVietnamPro-*.ttf` trong `FONT_CAN`, và giả định thư mục video nằm ở `<kênh>/../../videos`. Cần sửa khi làm việc với kênh thứ hai.

---

## 7. Repo đang public: không commit bí mật

- Không commit khóa API, token OAuth, file service account, cookie, mật khẩu.
- `.gitignore` hiện đã có `.env`, `.env.local`, `*.env`, `.youtube-token.json`, `gcp-*.json`, `*-service-account.json`, `service-account*.json`, `service_account*.json`.
- **`.gitignore` chưa có `secrets/`.** Phải thêm trước khi tạo thư mục này. Đây là sửa file của upstream, xem "Điểm chạm upstream".
- Mọi token và file service account để trong `secrets/` hoặc `.env`. Code đọc đường dẫn từ biến môi trường, không viết cứng đường dẫn.
- Trước mỗi commit chạy `git status` và xem kỹ danh sách file. Test có một bài kiểm tra `git check-ignore` trả về "bị bỏ qua" cho `.env` và `secrets/`.
- Lưu ý dữ liệu đã lên repo: `brand/vanxuan/brand.json` đang chứa đường dẫn tuyệt đối có tên người dùng Windows và toàn văn các file `context/*.md` của kênh. Xem mục rủi ro trong `KE-HOACH.md`.

---

## 8. Ưu tiên chạy trên máy, miễn phí, và ghi chi phí mỗi lần chạy

- Thứ tự ưu tiên: công cụ chạy trên máy và miễn phí (FFmpeg, faster-whisper `transcriber`, Remotion, HyperFrames, giọng chạy CPU), sau đó mới đến API miễn phí, cuối cùng là API trả phí. API trả phí chỉ dùng khi người dùng đã đồng ý.
- Ngân sách theo `config.yaml` mục `budget` và `tools/cost_tracker.py` (theo thứ tự estimate → reserve → reconcile).
- Mỗi lần chạy máy ghi một dòng chi phí: kênh, mã video, bước, công cụ, số tiền (0 nếu miễn phí), thời gian chạy. Ghi vào file trong dự án và vào tab chi phí trên Sheet. Checkpoint có trường `cost_snapshot`.
- Nếu máy chạy bằng Claude Code chế độ không tương tác, chi phí token của trợ lý cũng phải được ghi (cách đo đang là câu hỏi chờ chốt).

---

## 9. Môi trường và kỷ luật làm việc

- Máy chạy Windows 11, PowerShell 5.1. Lệnh trong tài liệu viết cho PowerShell (dùng `;`, không dùng `&&`).
- Đường dẫn có dấu cách và chữ có dấu tiếng Việt (ví dụ `Thinkpad P15V3`, `Học Viên Nam_Hạng A_ trung cảnh.mp4`). Luôn dùng `pathlib`, đặt đường dẫn trong ngoặc kép khi gọi lệnh, gọi `subprocess` bằng danh sách tham số, không ghép chuỗi lệnh.
- Mọi script in tiếng Việt phải gọi `sys.stdout.reconfigure(encoding="utf-8")`. Mặc định console là cp1252 và sẽ báo `UnicodeEncodeError` (đã gặp khi đọc brand.json).
- Đọc và ghi file luôn có `encoding="utf-8"`.
- Chạy test bằng Python của `.venv`: `.\.venv\Scripts\python.exe -m pytest`. `requirements.txt` không có pytest, phải cài `requirements-dev.txt`.
- **Mỗi prompt phát triển kết thúc bằng ba việc:**
  1. Chạy `pytest` (ít nhất `tests/may_reels/` và các test hợp đồng bị ảnh hưởng) và báo đúng kết quả.
  2. Cập nhật `HUONG-DAN-SU-DUNG.md` nếu có lệnh hoặc cách dùng mới.
  3. Tạo một commit trên nhánh `kenh-vanxuan`.

---

## Điểm chạm upstream

Mọi file của OpenMontage gốc mà Máy Reels sửa, hoặc thư mục lõi mà Máy Reels buộc phải thêm file vào. Cập nhật bảng này mỗi khi có thay đổi.

| File | Loại | Thay đổi | Lý do | Khi merge upstream |
|---|---|---|---|---|
| `.gitignore` | Sửa (dự kiến) | Thêm dòng `secrets/` | Giữ file service account và token ngoài repo public | Giữ dòng này nếu upstream sửa `.gitignore` |
| `pipeline_defs/may-reels.yaml` | Thêm file (dự kiến, chờ duyệt phương án) | Manifest riêng cho chế độ chạy không dừng | `lib/pipeline_loader.py` chỉ đọc manifest trong `pipeline_defs/`, và `lib/checkpoint.py` tìm cổng duyệt qua tên pipeline | Không xung đột trừ khi upstream đổi schema manifest. `tests/contracts/test_pipeline_catalog.py` sẽ tự kiểm tra file này. |
| `HUONG-DAN-SU-DUNG.md` | File của nhánh, không phải upstream | — | — | — |

Hiện chưa sửa file nào của upstream. Hai dòng đầu là dự kiến, chỉ làm khi bắt đầu code.

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

- **Tool mới import thư viện mạng (và thư viện nặng) bên trong hàm, không đặt ở đầu file.** Thư viện mạng gồm `googleapiclient`, `google.oauth2`, `gspread`, `requests`, `httpx`, SDK của Meta hay TikTok... Chỉ import trong `execute()` hoặc trong hàm gọi mạng. `registry.discover()` import *mọi* module trong `tools/` (`pkgutil.walk_packages`) và không bắt lỗi import. Một publisher có `import googleapiclient` ở đầu file sẽ làm hỏng toàn bộ registry trên máy chưa cài thư viện đó, kéo theo hỏng hàng loạt test (`tests/contracts/test_agent_skill_pointers.py`, `tests/contracts/test_skill_execute_examples.py`...). `export_bundle.py` cũng import `validate_artifact` bên trong `execute()`.
- `agent_skills` của tool mới chỉ được trỏ tới skill có thật trong `.agents/skills/`. `tests/contracts/test_agent_skill_pointers.py` kiểm tra điều này cho mọi tool registry tìm thấy.
- Tên lớp viết PascalCase, không có hậu tố `Tool` (`AGENT_GUIDE.md`, mục "Tool Class Naming Convention").
- **File `.md` không viết ví dụ gọi tool theo kiểu dấu chấm `execute`** (tên tool, dấu chấm, `execute`, rồi mở ngoặc với một dict). Luật này áp dụng cho mọi file `.md` thuộc `skills/**` và `docs/**`, và các file `.md` ở gốc repo. `tests/contracts/test_skill_execute_examples.py` quét mẫu này và báo lỗi khi tên tool chưa đăng ký hoặc khóa không có trong `input_schema`. Muốn mô tả cách gọi thì viết bằng lời, hoặc liệt kê tên tool và tên tham số trong bảng.

### 1.4. Kiến trúc của upstream: Python không điều phối

`PROJECT_CONTEXT.md` và `AGENT_GUIDE.md` quy định: trợ lý AI điều phối, Python chỉ làm tool và lưu trữ, không có "Python orchestrator". Máy Reels giữ đúng tinh thần này:

- Phần **sáng tạo** (kịch bản, kế hoạch cảnh, dựng) do trợ lý làm theo manifest và director skill có sẵn.
- Phần **tất định** (đọc/ghi Sheet, lọc cảnh theo quyền, kiểm tra cụm từ cấm, chống trùng, đăng bài) là Python trong `may_reels/` và `tools/publishers/`.
- "Rule Zero" của `AGENT_GUIDE.md` cấm viết script tạm để gọi tool, bỏ qua pipeline. Dự án mẫu `projects/vx-demo-01/` (gitignore, chỉ có trên máy) đã làm theo kiểu script riêng trong thư mục dự án (`sinh_giong.py`, `chuan_bi_canh.py`, `dung_hf.py`...). Máy Reels sẽ chuyển những việc đó thành code dùng lại được trong `may_reels/` hoặc tool trong `tools/`, không chép script vào từng dự án nữa.

---

## 2. Google Sheet là nguồn sự thật duy nhất về việc duyệt

- Mỗi tab có hai nhóm cột tách bạch: **cột của người** (Duyệt, Ghi chú người duyệt...) và **cột của máy** (Mã video, Trạng thái, Điểm, Link xem trước, Lỗi...). Máy **không bao giờ ghi** vào cột của người, kể cả để "dọn" hay "sửa định dạng".
  - Tab và cột chỉ khai báo ở một chỗ: `may_reels/cot_sheet.py`. Mỗi cột có cờ `may` hoặc `nguoi`.
  - `may_reels/sheet.py` từ chối ghi cột của người (lỗi `LoiGhiCotNguoi`), và kiểm tra việc này trước khi gọi mạng.
  - Khi thêm dòng mới, cột của người để trống, trừ ngoại lệ bên dưới. Ô trống được hiểu là giá trị đầu tiên của dropdown.
  - **Hai ngoại lệ duy nhất** (người dùng chốt ngày 2026-11-15). Cả hai chỉ áp dụng cho cột `duyet` của tab Hàng chờ, và chỉ được ghi đúng giá trị `Chờ duyệt`. Code nằm ở `may_reels/sheet.py` (`NGOAI_LE_DUYET`) và có test riêng.
    1. `khoi_tao`: máy tạo dòng **mới** trong Hàng chờ với `duyet = "Chờ duyệt"`. Dòng đã có thì không đụng, kể cả khi người dùng đã xóa trống ô đó.
    2. `sua`: lệnh `python -m may_reels sua` dựng lại video theo ghi chú, rồi đưa `duyet` từ `Sửa` về `Chờ duyệt`. Chỉ đổi ô **đang là `Sửa`**. Nếu cùng mã video còn nền tảng đang `Duyệt` hoặc `Bỏ`, máy không thay video và ghi lỗi; nếu không, lời duyệt dành cho bản cũ sẽ bị gán cho bản mới.

    Mọi lần ghi khác vào cột của người vẫn bị chặn trước khi gọi mạng.
- Máy tìm dòng theo khóa của tab và tìm cột theo tên ở dòng 1. Máy không xóa dòng, không sắp xếp lại, không ghi lại cả bảng: chỉ ghi đúng những ô đổi giá trị, và thêm dòng mới bằng append.
  - Ngay trước khi ghi, máy đọc lại để kiểm tra dòng đích vẫn mang đúng khóa. Nếu lệch thì tính lại, tối đa 3 lần.
  - Còn một khe hở rất nhỏ giữa lần kiểm tra cuối và lúc ghi: Sheets API không có thao tác "so rồi mới ghi" nguyên tử. Hai lượt chạy của máy cùng lúc cũng có thể cùng thêm một dòng, nên máy chỉ được chạy một lượt mỗi lúc.
- Giá trị ghi bằng chế độ RAW, để Sheet không tự đổi chuỗi thành ngày hay số.
- Danh sách cột của người được khai báo ở một chỗ duy nhất trong code. Hàm ghi Sheet từ chối ghi vào cột có tên trong danh sách đó và có test chứng minh việc từ chối này.
- **Cổng A (tab Ý tưởng, cột `duyet_chu_de`, dropdown `Chờ` / `Làm` / `Bỏ`):** chỉ chủ đề có đúng giá trị `Làm` mới được sản xuất.
- **Cổng B (tab Hàng chờ, cột `duyet`, dropdown `Chờ duyệt` / `Duyệt` / `Sửa` / `Bỏ`):** máy chỉ đăng một dòng khi ô có đúng giá trị `Duyệt`. Ô trống, `duyệt`, `OK`, `Sửa` hay bất kỳ giá trị nào khác đều là **không đăng**. Giá trị của hai dropdown theo yêu cầu ngày 2026-11-15; yêu cầu này thay cho câu 2 trong `KE-HOACH.md` mục 6. Máy so khớp đúng chuỗi `Duyệt`, có phân biệt hoa thường, sau khi chuẩn hóa Unicode NFC và cắt khoảng trắng hai đầu. `Sửa` thì máy đọc cột ghi chú của người rồi làm lại; `Bỏ` thì máy dừng dòng đó. Máy không bao giờ tự đổi giá trị ô này.
- Đọc lại ô Duyệt **ngay trước khi đăng**, không dùng giá trị đọc từ đầu lượt chạy. Người có thể rút lại duyệt trong lúc máy đang dựng.
- Trạng thái duyệt không lưu ở chỗ nào khác (không lưu trong checkpoint, không lưu trong file local) như một nguồn thay thế. File local chỉ được ghi lại *bản sao* để kiểm tra về sau.
- Checkpoint của OpenMontage (`lib/checkpoint.py`) vẫn ghi `human_approved=True` ở các cổng duyệt. Lần ghi đó chỉ được phép khi Sheet đang có `Duyệt` cho đúng dòng ấy, và `metadata` của checkpoint phải ghi mã dòng Sheet cùng giá trị đã đọc.

---

## 3. Đăng bài: Python tất định, mặc định chạy thử, chống đăng trùng

- **Không gọi LLM** trong đường đăng bài. Tiêu đề, mô tả và hashtag được chốt *trước* khi dòng vào hàng chờ duyệt, nằm trong cột máy của Sheet để người đọc được khi duyệt. Publisher chỉ đọc lại và gửi đi.
- **Mặc định chạy thử (dry-run).** Muốn đăng thật phải bật bằng một cờ rõ ràng mỗi lần chạy (ví dụ `--that`). Ở chế độ chạy thử, máy kiểm tra đủ mọi điều kiện, in ra sẽ đăng gì lên đâu, và không gọi API ghi nào. Nếu ghi `publish_log`, trạng thái lúc này là `pending_review` (không dùng `draft`, vì `draft` trùng với trạng thái nháp của Facebook), không phải `published` (schema cho phép `published`, `exported`, `failed`, `draft`, `pending_review`, xem `schemas/artifacts/publish_log.schema.json`).
- **Chống đăng trùng theo cặp (mã video, nền tảng).** Trước khi tải lên:
  1. Tra sổ đăng local và tab đăng trên Sheet. Nếu cặp này đã có trạng thái `published` thì dừng.
  2. Ghi trạng thái "đang đăng" cho cặp đó *trước* khi gọi API. Nếu máy chết giữa chừng, lần chạy sau thấy "đang đăng" thì không tự đăng lại mà báo người kiểm tra.
  3. Đăng xong thì ghi `video_id` và `url` trả về.
- Mỗi lần đăng tạo một mục `publish_log` hợp lệ theo schema (`platform`, `status` và `timestamp` là bắt buộc; `url`, `video_id`, `metadata_used`, `error` thêm vào nếu có).
- Có thể dùng `export_bundle` (`tools/publishers/export_bundle.py`) để đóng gói bản dựng cùng metadata trước khi đăng. Tool này không tải lên đâu cả.
- **Đã làm (2026-11-15):** `may_reels/dang_bai.py` (lệnh `python -m may_reels dang [--that]`), cùng các publisher `tools/publishers/facebook_reels.py`, `youtube_shorts.py` và `tiktok_handoff.py`.
  - Thứ tự ghi khi đăng một dòng:
    1. Đọc lại dòng.
    2. Ghi `dang_tai_len`.
    3. Gọi API.
    4. Ghi **sổ đăng local** (`projects/_may_reels/so_dang.jsonl`).
    5. Ghi Sheet.
  - Nếu bước 5 lỗi, lần chạy sau đọc sổ đăng, chỉ sửa lại Sheet và không đăng lại.
  - Lỗi ở bước cuối, khi bài **có thể** đã lên, được xếp loại `khong_ro`, chuyển sang `can_kiem_tra` và không bao giờ tự thử lại.
- Mọi API đăng bài phải có tóm tắt từ tài liệu chính thức, ghi kèm ngày đọc, trong `docs/may-reels/API-DANG-BAI.md`. Trước khi sửa publisher thì đọc lại tài liệu đó. Không viết theo trí nhớ.
- Token đăng bài theo từng kênh. `brand/<id>/dang-bai.yaml` chỉ chứa tên biến môi trường và ID công khai. `may_reels/cau_hinh_dang.py` từ chối giá trị trông giống token.

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
- Chỉ cắt trong các đoạn `doan_dung_duoc` (nếu cảnh có khai báo). Phải tôn trọng `rui_ro` (ví dụ `mat-hoc-vien`, `bien-so`) và `can_xu_ly`. Đã chốt (`KE-HOACH.md` mục 6, câu 15): máy **được tự cắt khung** theo vùng ghi trong `can_xu_ly`. Máy **không tự làm mờ** mặt người hay biển số; cảnh cần làm mờ thì chỉ dùng đoạn không cần xử lý. Không xác định được đoạn như vậy thì không dùng cảnh đó và ghi vào tab "Cần quay".

---

## 5. Thiếu cảnh quay: ghi tab "Cần quay" và dùng cảnh tạm bằng sơ đồ động

Kho cảnh có thể không có cảnh khớp một ý: không đủ cảnh, sai bối cảnh, độ phân giải quá thấp, hoặc không có cảnh hợp lệ. Khi đó máy **không** lấp chỗ trống bằng ảnh AI, stock, cảnh lặp lại hay cảnh kho không khớp ý.

**Cập nhật 2026-11-15** (người dùng chốt):
1. **Vẫn ghi yêu cầu vào tab "Cần quay"**: kênh, mã video, ý cần minh họa, mô tả cảnh cần quay, gợi ý quay, lý do.
2. Đoạn đó dùng **cảnh tạm** dạng sơ đồ động (`canh.so_do`: `giao_nhau`, `vong_xuyen`, `the_chu`). Sơ đồ vẽ bằng code (SVG + GSAP trong HyperFrames), **không phải AI, không phải stock**.
   - Chỉ đoạn có trong `thieu_canh` mới được dùng cảnh tạm.
   - Mỗi cảnh tạm bị trừ 3 điểm QA, tối đa 15.
   - Code nằm ở `may_reels/dung/hf.py`.
3. **Video có cảnh tạm vẫn vào Hàng chờ và được đăng như video khác**, kèm cảnh báo "Có cảnh tạm (sơ đồ): s3, s4". Job ghi danh sách cảnh tạm ở `reel_job.metadata.canh_tam`.
4. **Thay bằng cảnh thật sau:**
   1. Người quay xong thì chọn "Đã quay" ở cột `trang_thai_quay` của tab Cần quay, rồi nạp lại kho (`tools_local/nap_kenh.py`).
   2. Lệnh `python -m may_reels thay-canh` cho agent thay sơ đồ bằng cảnh thật khớp ý, dựng lại, cập nhật Hàng chờ và ghi `trang_thai_nap`.
   3. Nền tảng nào đã "Duyệt"/"Bỏ" thì máy không thay video, vì lời duyệt đó dành cho bản cũ.
5. Trạng thái `cho_quay` chỉ còn dùng khi không dựng được cả cảnh tạm, ví dụ cảnh kho đã chọn không đủ độ dài.
   - Chạy `san-xuat --ca-cho-quay` để dựng lại các chủ đề này với cảnh tạm.

Điều này khớp với luật "No Unilateral Substitutions" và "Escalate Blockers Explicitly" trong `AGENT_GUIDE.md`.

---

## 6. Không viết cứng tên kênh

- Trong `may_reels/`, `skills/may-reels/` và `tools/publishers/` không có chuỗi `vanxuan` hay một giá trị riêng của kênh (số điện thoại, màu, font, hashtag, tiền tố mã video). Mọi thứ đọc từ `brand/<id>/`.
- Mã kênh truyền vào bằng tham số (`--kenh <id>`) hoặc đọc từ cột Kênh trên Sheet.
- Cấu hình chạy riêng từng kênh (ví dụ runtime dựng đã chốt, lịch đăng, tài khoản nền tảng) đặt trong file mới ở `brand/<id>/`. Tên file sẽ chốt khi code.
- Test có một bài kiểm tra quét `may_reels/` để bắt chuỗi `vanxuan`.
- Cấu hình riêng của kênh nằm trong `brand/<id>/cau-hinh.yaml` (sửa tay, script chỉ đọc). Hiện có `tien_to_ma_video`, `thu_muc_video` (tương đối so với thư mục kênh gốc) và `fonts`. Thiếu khóa nào thì code ghi cảnh báo, không tự đoán giá trị mặc định.
- `tools_local/nap_kenh.py` đã bỏ các giá trị viết cứng của Vạn Xuân (ngày 2026-11-15). Test `tests/may_reels/test_nap_kenh.py` quét file này để bắt chuỗi `vanxuan`, `vx-` và `BeVietnam`.

---

## 7. Repo đang public: không commit bí mật

- Không commit khóa API, token OAuth, file service account, cookie, mật khẩu.
- `.gitignore` hiện đã có `.env`, `.env.local`, `*.env`, `.youtube-token.json`, `gcp-*.json`, `*-service-account.json`, `service-account*.json`, `service_account*.json`.
- `.gitignore` đã có thêm `secrets/` và `brand/*/_local/` (ngày 2026-11-15). Đây là sửa file của upstream, xem "Điểm chạm upstream".
- Mọi token và file service account để trong `secrets/` hoặc `.env`. Code đọc đường dẫn từ biến môi trường, không viết cứng đường dẫn.
- Trước mỗi commit chạy `git status` và xem kỹ danh sách file. `tests/may_reels/test_nap_kenh.py` dùng `git check-ignore` để kiểm tra `.env`, `secrets/` và `brand/<id>/_local/` bị bỏ qua.
- `brand.json` không được chứa đường dẫn tuyệt đối. Chỉ ghi `file_tuong_doi`. Thư mục kênh gốc đọc từ `KENH_GOC_DIR` trong `.env`, vì đây là đường dẫn riêng của từng máy.
- Toàn văn `context/*.md` của kênh nằm trong `brand/<id>/_local/` (bị gitignore). Code cần nội dung này thì đọc theo trường `context.<tên>.ban_local` của brand.json.
- Dữ liệu cũ vẫn còn trong lịch sử git: commit `dc52b79` đã đẩy lên GitHub, có đường dẫn tuyệt đối và toàn văn context. **Không viết lại lịch sử git khi chưa hỏi người dùng.**

---

## 8. Ưu tiên chạy trên máy, miễn phí, và ghi chi phí mỗi lần chạy

- Thứ tự ưu tiên: công cụ chạy trên máy và miễn phí (FFmpeg, faster-whisper `transcriber`, Remotion, HyperFrames, giọng chạy CPU), sau đó mới đến API miễn phí, cuối cùng là API trả phí. API trả phí chỉ dùng khi người dùng đã đồng ý.
- Ngân sách theo `config.yaml` mục `budget` và `tools/cost_tracker.py` (theo thứ tự estimate → reserve → reconcile).
- Mỗi lần chạy máy ghi một dòng chi phí: kênh, mã video, bước, công cụ, số tiền (0 nếu miễn phí), thời gian chạy. Ghi vào file trong dự án và vào tab chi phí trên Sheet. Checkpoint có trường `cost_snapshot`.
- Nếu máy chạy bằng Claude Code chế độ không tương tác, sổ chi phí ghi **số lượt chạy** và **thời gian chạy** của trợ lý (`KE-HOACH.md` mục 6, câu 10), không đo token.

---

## 9. Môi trường và kỷ luật làm việc

- Máy chạy Windows 11, PowerShell 5.1. Lệnh trong tài liệu viết cho PowerShell (dùng `;`, không dùng `&&`).
- Đường dẫn có dấu cách và chữ có dấu tiếng Việt (ví dụ `Thinkpad P15V3`, `Học Viên Nam_Hạng A_ trung cảnh.mp4`). Luôn dùng `pathlib`, đặt đường dẫn trong ngoặc kép khi gọi lệnh, gọi `subprocess` bằng danh sách tham số, không ghép chuỗi lệnh.
- Chạy Python với **`PYTHONUTF8=1`**. Mặc định console là cp1252 và sẽ báo `UnicodeEncodeError` khi in tiếng Việt (đã gặp khi đọc brand.json). Có hai cách:
  - Dùng `tools_local\py.cmd`. File này đặt `PYTHONUTF8=1` rồi gọi Python của `.venv`.
  - Đặt `$env:PYTHONUTF8 = "1"` ở đầu phiên PowerShell.

  Script mới vẫn gọi thêm `sys.stdout.reconfigure(encoding="utf-8")` để không phụ thuộc vào cách được gọi. Tác vụ Task Scheduler phải gọi qua `tools_local\py.cmd`.
- Đọc và ghi file luôn có `encoding="utf-8"`.
- Chạy test bằng Python của `.venv`: `tools_local\py.cmd -m pytest`. `requirements.txt` không có pytest, phải cài `requirements-dev.txt`.
- **Mỗi prompt phát triển kết thúc bằng ba việc:**
  1. Chạy `pytest` (ít nhất `tests/may_reels/` và các test hợp đồng bị ảnh hưởng) và báo đúng kết quả.
  2. Cập nhật `HUONG-DAN-SU-DUNG.md` nếu có lệnh hoặc cách dùng mới.
  3. Tạo một commit trên nhánh `kenh-vanxuan`.

---

## 10. Tách phần sáng tạo khỏi phần dựng

- Agent (`claude -p`, skill `skills/may-reels/san-xuat-khong-hoi.md`) chỉ viết `projects/<ma_video>/ke_hoach.json`, theo schema `schemas/may-reels/ke_hoach_video.schema.json`. File này gồm lời đọc, thẻ chữ, nguồn luật (trích nguyên văn, link, ngày mở), cảnh chọn từ kho, caption từng nền tảng và các quyết định đã tự đưa ra.
- Mọi bước còn lại là Python tất định trong `may_reels/dung/`: kiểm tra kế hoạch, sinh giọng có nghe lại, cắt cảnh, dựng HyperFrames, tự kiểm, chấm điểm QA, đóng gói. Agent không được ghi file nào khác. Quyền này được giới hạn bằng `--allowed-tools` khi gọi agent.
- Quyết định thường phải hỏi người đã chốt một lần trong `brand/<kenh>/san-xuat.yaml`. Máy ghi lại các quyết định đó vào `decision_log`, kèm lý do "đã chốt theo cấu hình kênh".
- **Giọng đọc phải qua tai máy.** Mỗi đoạn được sinh tối đa 10 lần, và lần nào cũng cho PhoWhisper nghe lại. Bản được chọn phải đủ số chữ, độ khớp ký tự từ 0,95, và phần chữ thừa ở đuôi không dài quá 0,4 giây (dài hơn tức là TTS đọc lặp thật). Không bản nào đạt thì dừng, không dùng bản sai.

---

## Điểm chạm upstream

Mọi file của OpenMontage gốc mà Máy Reels sửa, hoặc thư mục lõi mà Máy Reels buộc phải thêm file vào. Cập nhật bảng này mỗi khi có thay đổi.

| File | Loại | Thay đổi | Lý do | Khi merge upstream |
|---|---|---|---|---|
| `.gitignore` | Sửa (đã làm 2026-11-15) | Thêm 2 dòng ở cuối file: `secrets/` và `brand/*/_local/` | Giữ file service account, token và nội dung riêng của kênh ngoài repo public | Giữ 2 dòng này nếu upstream sửa `.gitignore` (thêm ở cuối file nên ít xung đột) |
| `.env.example` | Sửa (đã làm 2026-11-15) | Thêm khối `# --- Máy Reels ---` ở cuối file: `MAY_REELS_SA_JSON`, `MAY_REELS_SHEET_ID`, `KENH_GOC_DIR`, `MAY_REELS_GOOGLE_CLIENT_SECRET`, `MAY_REELS_DRIVE_TOKEN`, và ví dụ `VANXUAN_FB_PAGE_TOKEN`, `VANXUAN_YT_TOKEN_FILE` | Người cài mới biết cần đặt biến nào | Thêm ở cuối file nên ít xung đột. Nếu upstream sửa đoạn cuối file thì giữ cả hai. |
| `schemas/may-reels/reel_job.schema.json` | Thêm file vào thư mục lõi `schemas/` (đã làm 2026-11-15) | Schema job của Máy Reels | Theo yêu cầu đặt schema ở đây. Thư mục con riêng `may-reels/` không phải package Python và không bị `schemas.artifacts.list_schemas()` quét | Không xung đột trừ khi upstream tạo thư mục cùng tên. |
| `tools/publishers/facebook_reels.py`, `youtube_shorts.py`, `tiktok_handoff.py`, `_dang_chung.py` | Thêm file mới vào thư mục lõi (2026-11-15) | Publisher của Máy Reels | Registry chỉ tìm tool trong `tools/`. Không sửa file có sẵn nào | Không xung đột trừ khi upstream thêm file cùng tên. `export_bundle.py` giữ nguyên. |
| `pipeline_defs/may-reels.yaml` | Thêm file (đã làm 2026-11-15) | Manifest riêng cho chế độ chạy không dừng | `lib/pipeline_loader.py` chỉ đọc manifest trong `pipeline_defs/`, và `lib/checkpoint.py` tìm cổng duyệt qua tên pipeline | Không xung đột trừ khi upstream đổi schema manifest. `tests/contracts/test_pipeline_catalog.py` sẽ tự kiểm tra file này. |
| `HUONG-DAN-SU-DUNG.md` | File của nhánh, không phải upstream | — | — | — |

File upstream đã sửa: `.gitignore` và `.env.example`. Thư mục lõi đã thêm file: `schemas/`. `pipeline_defs/may-reels.yaml` sẽ thêm khi bắt đầu code luồng sản xuất.

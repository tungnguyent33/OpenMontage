# Máy Reels: tra nguồn luật cho một chủ đề

Skill cho agent chạy không tương tác (`claude -p`), do lệnh `python -m may_reels nguon-luat --kenh <mã>` gọi cho từng chủ đề mà `nguon_doi_chieu` chưa ghi tới mức khoản. Skill áp dụng cho **mọi kênh**.

**Vai trò:** bạn **đề xuất**, người duyệt **quyết định**. Họ đọc đề xuất của bạn trên tab Ý tưởng rồi chọn `xac_nhan_nguon` = Đúng hoặc Sai. Đề xuất sai mà trông chắc chắn còn tệ hơn để trống, nên **không bao giờ đoán số điều, khoản**.

## Đầu vào

Đọc file `projects/_may_reels/nguon_luat/<kenh>/<ma>.yeu_cau.json`:
- `chu_de`: câu hỏi của video;
- `y_chinh`: câu trả lời mà video định nói;
- `nguon_doi_chieu_hien_tai`: gợi ý ban đầu, thường mới tới mức văn bản hoặc điều;
- `ngay_hom_nay`.

## Cách làm

1. **Xác định câu cần căn cứ.** Từ `chu_de` và `y_chinh`, viết ra câu khẳng định mà video sẽ nói. Ví dụ: "Ở nơi giao nhau không có báo hiệu, nhường xe đi đến từ bên phải." Đây là câu cần tìm điều khoản.
2. **Mở bản văn bản chính thức bằng WebFetch.**

   **Văn bản đã được sửa đổi thì ưu tiên văn bản hợp nhất chính thức** (ký hiệu `<số>/VBHN-<cơ quan>`, ví dụ `55/VBHN-VPQH`), vì bản này đã gộp mọi lần sửa đổi và có chú thích ghi rõ khoản nào bị sửa, theo luật nào, hiệu lực từ ngày nào. Chỉ dùng bản hợp nhất do cơ quan nhà nước đăng, ví dụ trên `datafiles.chinhphu.vn`, `vanban.chinhphu.vn` hoặc `quochoi.vn`. Bản hợp nhất do trang thương mại tự làm không được tính.

   Đã biết:
   - Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15 có văn bản hợp nhất `55/VBHN-VPQH` ngày 23/3/2026. Bản này đã hợp nhất Luật 118/2025/QH15. Link: `https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/55-vbhn-vpqh.pdf`. Mọi đề xuất dẫn Luật 36/2024/QH15 đều ghi link này vào `link_nguon`.
   - Trích dẫn và số điều, khoản vẫn ghi theo Luật 36/2024/QH15, vì bản hợp nhất giữ nguyên số điều. Nếu chú thích của bản hợp nhất cho thấy khoản đó đã bị sửa, ghi vào `hieu_luc` là luật nào sửa và hiệu lực từ ngày nào, rồi trích câu chữ **đã sửa**.
   - Không đọc được chữ trong bản hợp nhất thì nói rõ trong `hieu_luc` là "chưa đối chiếu bản hợp nhất". Không suy ra "không bị sửa" từ trang thương mại.

   Khi không có văn bản hợp nhất chính thức, ưu tiên theo thứ tự:
   1. Cổng thông tin điện tử Chính phủ (`chinhphu.vn`, `vanban.chinhphu.vn`, `congbao.chinhphu.vn`);
   2. Cơ sở dữ liệu quốc gia về văn bản pháp luật (`vbpl.vn`);
   3. Trang của cơ quan ban hành, ví dụ `quochoi.vn` hoặc trang bộ `*.gov.vn`.

   Trang thương mại (thư viện pháp luật, báo) chỉ dùng để **tìm** số điều. Link ghi vào kết quả phải là trang chính thức mà bạn **thực sự đã mở** trong lần chạy này. Không mở được trang chính thức thì vẫn ghi link bạn đã mở; máy sẽ cảnh báo người duyệt.
3. **Kiểm tra hiệu lực.**
   - Văn bản còn hiệu lực không?
   - Điều, khoản đó đã bị sửa đổi hoặc thay thế chưa?

   Nếu đã bị thay thế thì ghi văn bản và điều khoản **mới**, và ghi lại việc thay thế vào `hieu_luc`.
4. **Tìm đúng mức chi tiết.**
   - Luật, nghị định, thông tư: ghi tới **khoản**, và tới **điểm** nếu câu nằm trong một điểm. Ví dụ đã được người dùng xác nhận: `Luật 36/2024/QH15, Điều 22, khoản 2`. Có điểm thì thêm: `..., Điều <số>, khoản <số>, điểm <chữ>`.
   - QCVN: ghi tới **mục hoặc phụ lục**, kèm **số hiệu biển hoặc vạch** nếu có. Dạng: `QCVN <số hiệu>, Phụ lục <ký hiệu>, biển <số hiệu biển>` hoặc `QCVN <số hiệu>, Phụ lục <ký hiệu>, vạch <số hiệu vạch>`. Ký hiệu phụ lục và số hiệu phải lấy từ văn bản đã mở.
   - Nhiều khoản thì liệt kê: `Điều 22, khoản 2, 3`. Mỗi lần nhắc một Điều đều phải kèm khoản. Không ghi "Điều 89" trống.
   - Không dùng ký tự `|` và không xuống dòng. Đề xuất sẽ được chép vào một ô của bảng Markdown.
5. **Trích nguyên văn:** chép đúng từng chữ đoạn ngắn nhất chứa căn cứ, khoảng 60 chữ trở xuống. Không tóm tắt, không sửa câu chữ. Có thể dùng "…" để bỏ phần giữa không liên quan.
6. **Đối chiếu với `y_chinh`.**
   - Văn bản nói **khác** `y_chinh` (sai, thiếu ngoại lệ, sai số liệu, sai mốc thời gian) thì ghi rõ vào `mau_thuan_y_chinh`. **Không** tự sửa `y_chinh`.
   - Nếu căn cứ vẫn tìm được thì vẫn đề xuất điều khoản, vì người duyệt cần thấy cả hai.
7. **Không tìm được điều khoản khớp** thì để `nguon_de_xuat` trống, ghi lý do vào `ly_do_khong_tim_duoc` và các trang đã mở. Không đoán.

## Kết quả: chỉ ghi MỘT file

Ghi `projects/_may_reels/nguon_luat/<kenh>/<ma>.json`:

```json
{
  "cau_can_can_cu": "<câu khẳng định video sẽ nói>",
  "nguon_de_xuat": "<văn bản>, Điều <số>, khoản <số>[, điểm <chữ>]",
  "trich_nguyen_van": "<nguyên văn, khoảng 60 chữ>",
  "link_nguon": "https://vbpl.vn/...",
  "ngay_tra": "2026-11-16",
  "hieu_luc": "Còn hiệu lực từ 01/01/2025; chưa thấy văn bản sửa đổi điều này.",
  "mau_thuan_y_chinh": null,
  "ly_do_khong_tim_duoc": null,
  "da_mo": ["https://vbpl.vn/...", "https://chinhphu.vn/..."]
}
```

Ví dụ trên chỉ minh họa **định dạng**: mọi giá trị trong ngoặc nhọn phải thay bằng kết quả tra thật.

Máy (`may_reels/nguon_luat.py`) kiểm tra file này trước khi ghi lên Sheet. Máy bỏ đề xuất trong các trường hợp sau:
- chưa tới mức khoản hoặc mục;
- thiếu trích dẫn;
- trích dẫn dài quá 80 chữ;
- thiếu link.

Link không thuộc cổng chính thức thì bị cảnh báo.

## Kết thúc

Ghi file xong thì dừng. Trả lời một dòng, ví dụ: "<mã>: <nguon_de_xuat> (<tên miền đã mở>)."

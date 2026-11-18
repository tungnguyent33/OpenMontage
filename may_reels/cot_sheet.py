"""Cấu trúc Google Sheet "Máy Reels": NƠI DUY NHẤT khai báo tab và cột.

Mỗi cột thuộc về MÁY hoặc NGƯỜI. Máy không bao giờ ghi vào cột của người
(may_reels/sheet.py từ chối trước khi gọi mạng). Cột của người được tô nền
vàng nhạt; cột có `lua_chon` là dropdown.

Ô trống trong cột duyệt của người được hiểu là giá trị đầu tiên của `lua_chon`
("Chờ" / "Chờ duyệt"): máy không tự ghi giá trị mặc định vào cột của người.

Thứ tự cột ở đây chỉ dùng khi tạo tab mới. Sau đó máy tìm cột theo TÊN ở dòng 1,
nên người dùng chèn hay đổi chỗ cột cũng không làm máy ghi nhầm ô.
"""
from __future__ import annotations

from dataclasses import dataclass

MAY = "may"
NGUOI = "nguoi"

# Nền tảng đích. Dùng chung cho Sheet và schemas/may-reels/reel_job.schema.json.
NEN_TANG = ("fb_reels", "yt_shorts", "tiktok")


@dataclass(frozen=True)
class Cot:
    ten: str
    cua: str = MAY
    lua_chon: tuple[str, ...] = ()
    mo_ta: str = ""

    @property
    def cua_nguoi(self) -> bool:
        return self.cua == NGUOI


@dataclass(frozen=True)
class Tab:
    ten: str
    cot: tuple[Cot, ...]
    khoa: tuple[str, ...] = ()          # cột tạo nên khóa của dòng; rỗng = chỉ thêm dòng (nhật ký)
    tu_dong_cap_nhat: str | None = None  # cột máy tự ghi thời điểm mỗi khi dòng đổi
    mo_ta: str = ""

    def __post_init__(self) -> None:
        ten = [c.ten for c in self.cot]
        if len(ten) != len(set(ten)):
            raise ValueError(f"Tab {self.ten!r} có cột trùng tên")
        for k in self.khoa + ((self.tu_dong_cap_nhat,) if self.tu_dong_cap_nhat else ()):
            if k not in ten:
                raise ValueError(f"Tab {self.ten!r}: cột {k!r} không có trong danh sách cột")
            if self.lay(k).cua_nguoi:
                raise ValueError(f"Tab {self.ten!r}: cột khóa/tự động {k!r} phải là cột của máy")

    def lay(self, ten: str) -> Cot:
        for c in self.cot:
            if c.ten == ten:
                return c
        raise KeyError(f"Tab {self.ten!r} không có cột {ten!r}")

    @property
    def ten_cot(self) -> list[str]:
        return [c.ten for c in self.cot]

    @property
    def cot_nguoi(self) -> list[str]:
        return [c.ten for c in self.cot if c.cua_nguoi]

    @property
    def chi_them(self) -> bool:
        return not self.khoa


def _m(ten: str, mo_ta: str = "") -> Cot:
    return Cot(ten, MAY, (), mo_ta)


def _n(ten: str, lua_chon: tuple[str, ...] = (), mo_ta: str = "") -> Cot:
    return Cot(ten, NGUOI, lua_chon, mo_ta)


Y_TUONG = Tab(
    "Ý tưởng",
    (
        _m("ma", "mã chủ đề trong brand/<kênh>/brand.json"),
        _m("kenh", "mã kênh (brand/<kenh>/)"),
        _m("tru_cot"),
        _m("dinh_dang"),
        _m("chu_de"),
        _m("hook_de_xuat"),
        _m("nguon_doi_chieu"),
        _m("diem"),
        _n("duyet_chu_de", ("Chờ", "Làm", "Bỏ"), "cổng A: chỉ 'Làm' mới được sản xuất; ô trống = Chờ"),
        _m("trang_thai_san_xuat"),
        # Nguồn luật máy đề xuất (lệnh nguon-luat); người xác nhận, máy mới chép vào chu-de.md (nguon-luat ap-dung).
        _m("nguon_de_xuat", "văn bản, điều, khoản, điểm; QCVN: mục, phụ lục, số hiệu biển/vạch"),
        _m("trich_nguyen_van", "đoạn trích nguyên văn ngắn (khoảng 60 chữ)"),
        _m("link_nguon", "link văn bản chính thức agent đã mở"),
        _m("ngay_tra"),
        _m("ghi_chu_may", "lý do không đề xuất, mâu thuẫn với y_chinh, hiệu lực, lý do chưa sản xuất"),
        _n("xac_nhan_nguon", ("Đúng", "Sai"), "người xác nhận nguon_de_xuat; Đúng = cho áp dụng vào chu-de.md"),
    ),
    # Một Sheet cho mọi kênh: mã chủ đề chỉ duy nhất trong một kênh, nên khóa gồm cả kênh.
    khoa=("kenh", "ma"),
    mo_ta="Chủ đề chờ người duyệt (cổng A).",
)

HANG_CHO = Tab(
    "Hàng chờ",
    (
        _m("ma_video"),
        _m("kenh"),
        _m("nen_tang", "fb_reels / yt_shorts / tiktok"),
        _m("link_xem_thu", "link Google Drive"),
        _m("caption"),
        _m("hashtag"),
        _m("diem_qa"),
        _m("canh_bao", "ví dụ 'Dưới ngưỡng'"),
        _n("duyet", ("Chờ duyệt", "Duyệt", "Sửa", "Bỏ"), "cổng B: chỉ 'Duyệt' mới được đăng; ô trống = Chờ duyệt"),
        _n("ghi_chu_sua", mo_ta="bắt buộc khi chọn Sửa"),
        _n("gio_dang", mo_ta="để trống thì dùng lịch mặc định của kênh"),
        _m("trang_thai_dang"),
        _m("link_bai"),
        _m("id_bai"),
        _m("loi"),
        _m("cap_nhat_luc"),
        _m("ghi_chu_may", "thư mục đăng tay (export_bundle), ghi chú của máy"),
        # Không đặt dropdown: cột người dùng đã tự tạo, máy không áp ràng buộc lên ô người nhập (đọc lỏng 1-10).
        _n("diem_cua_toi", mo_ta="điểm của người duyệt 1-10; dùng cho lệnh hieu-chinh"),
        _n("nhan_xet", mo_ta="nhận xét của người duyệt; hieu-chinh đọc để đề xuất sửa rubric"),
    ),
    khoa=("ma_video", "nen_tang"),
    tu_dong_cap_nhat="cap_nhat_luc",
    mo_ta="Một dòng = một video trên một nền tảng, chờ người duyệt (cổng B).",
)

CAN_QUAY = Tab(
    "Cần quay",
    (
        _m("ma_yeu_cau", "<kenh>:<ma_chu_de>:<stt>"),
        _m("kenh"),
        _m("ma_chu_de"),
        _m("ma_video"),
        _m("y_can_canh", "ý trong kịch bản chưa có cảnh"),
        _m("mo_ta_canh", "cảnh cần quay"),
        _m("goi_y_quay", "khung dọc/ngang, thời lượng, tránh mặt/biển số"),
        _m("ly_do", "không có cảnh / cảnh bị loại vì ..."),
        _m("tao_luc"),
        _n("trang_thai_quay", ("Chưa quay", "Đã quay", "Không quay"), "ô trống = Chưa quay"),
        _n("ghi_chu_nguoi"),
        _m("trang_thai_nap", "máy ghi khi cảnh mới đã vào kho (kho nap)"),
        # Danh sách quay gộp theo buổi (lệnh `kho thieu`): ma_yeu_cau = <kenh>:goi-y:<mã cảnh>, ma_chu_de = các chủ đề
        # cảnh phục vụ (cách nhau dấu phẩy). Thêm sau cột cũ: sheet init chỉ nối cột thiếu vào cuối, không đổi chỗ.
        _m("buoi", "buổi quay gộp: địa điểm + thời điểm"),
        _m("loai_canh", "NOI / BROLL / THAO"),
        _m("goc_may"),
        _m("thoi_luong", "giây"),
        _m("loi_thoai", "lời cần nói nếu là cảnh nói trước máy"),
        _m("luu_y", "ánh sáng, tiếng ồn"),
        _m("xin_phep", "người lên hình cần đồng ý gì"),
        _m("gop_yeu_cau", "các ma_yeu_cau của video đang chờ mà cảnh này đáp ứng"),
        _m("uu_tien", "1 = quay trước"),
    ),
    khoa=("ma_yeu_cau",),
    mo_ta="Ý thiếu cảnh thật. Máy không lấp bằng cảnh khác.",
)

QUYEN_HINH = Tab(
    "Quyền hình",
    (
        _m("ma_canh", "mã cảnh trong kho (canh-quay/_kho/index.json)"),
        _m("kenh"),
        _m("file", "đường dẫn tính từ thư mục kênh gốc"),
        _m("khung_hinh", "lưới khung hình để xem lại: canh-quay/_kho/<ma_canh>/khung.jpg"),
        _m("mo_ta"),
        _m("rui_ro", "mat-hoc-vien, bien-so, ten-nguoi, giay-to, nguoi-ngoai"),
        _m("can_xu_ly"),
        _m("tao_luc"),
        _n("xac_nhan_quyen", ("Chờ", "Đồng ý", "Không"),
           "Đồng ý = người trong hình đã đồng ý lên hình; ô trống = Chờ"),
        _n("ghi_chu_nguoi"),
        _m("trang_thai_ap_dung", "máy ghi khi đã chép xác nhận vào quyen_hinh.bo_sung của channel.yaml"),
    ),
    khoa=("kenh", "ma_canh"),
    mo_ta="Cảnh mới có mặt người: chưa được dùng cho tới khi người chọn Đồng ý.",
)

SO_LIEU = Tab(
    "Số liệu",
    (
        _m("ma_video"),
        _m("kenh"),
        _m("nen_tang"),
        _m("id_bai"),
        _m("moc_ngay", "1 / 3 / 7 ngày sau khi đăng"),
        _m("do_luc"),
        _m("luot_xem"),
        _m("thoi_gian_xem_tb_giay"),
        _m("chia_se"),
        _m("binh_luan"),
        _n("tin_nhan", mo_ta="người dùng nhập tay"),
        _m("loi"),
    ),
    khoa=("ma_video", "nen_tang", "moc_ngay"),
    mo_ta="Số liệu ở mốc 1, 3, 7 ngày sau khi đăng.",
)

NHAT_KY = Tab(
    "Nhật ký",
    (
        _m("thoi_gian"),
        _m("kenh"),
        _m("ma", "mã chủ đề hoặc mã video"),
        _m("buoc", "ví dụ sheet.init, nap_chu_de, san_xuat, dang"),
        _m("che_do", "thu / that"),
        _m("ket_qua", "ok / loi"),
        _m("chi_tiet"),
        _m("chi_phi_vnd"),
        _m("thoi_gian_chay_giay"),
        _m("so_luot_tro_ly", "số lượt chạy trợ lý (claude -p)"),
    ),
    khoa=(),
    mo_ta="Sổ chạy và chi phí. Chỉ thêm dòng.",
)

TAT_CA: tuple[Tab, ...] = (Y_TUONG, HANG_CHO, CAN_QUAY, SO_LIEU, NHAT_KY, QUYEN_HINH)


def tab_theo_ten(ten: str) -> Tab:
    for t in TAT_CA:
        if t.ten == ten:
            return t
    raise KeyError(ten)

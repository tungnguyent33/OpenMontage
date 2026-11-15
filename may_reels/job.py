"""Job của Máy Reels và máy trạng thái.

    y_tuong -> dang_san_xuat -> cho_quay | cho_duyet -> da_duyet -> da_dang
    (loi và bo là nhánh rẽ, xem CHUYEN_HOP_LE)

Mọi thay đổi trạng thái đi qua chuyen_trang_thai(): bước nhảy không có trong
CHUYEN_HOP_LE bị từ chối. Hàm không sửa job cũ mà trả về bản mới.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "may-reels" / "reel_job.schema.json"
TZ_VN = timezone(timedelta(hours=7))

TRANG_THAI = ("y_tuong", "dang_san_xuat", "cho_quay", "cho_duyet", "da_duyet", "da_dang", "loi", "bo")
KET_THUC = frozenset({"da_dang", "bo"})

CHUYEN_HOP_LE: dict[str, frozenset[str]] = {
    "y_tuong": frozenset({"dang_san_xuat", "bo"}),
    # Sản xuất xong: thiếu cảnh thật -> cho_quay; đủ cảnh và đã chấm điểm -> cho_duyet.
    "dang_san_xuat": frozenset({"cho_quay", "cho_duyet", "loi", "bo"}),
    # Đã quay bổ sung và nạp kho -> sản xuất lại.
    "cho_quay": frozenset({"dang_san_xuat", "bo"}),
    # Người chọn Duyệt -> da_duyet; Sửa -> sản xuất lại; Bỏ -> bo.
    "cho_duyet": frozenset({"da_duyet", "dang_san_xuat", "bo"}),
    "da_duyet": frozenset({"da_dang", "loi", "bo"}),
    # Sửa xong lỗi: quay lại bước bị lỗi (sản xuất hoặc đăng).
    "loi": frozenset({"dang_san_xuat", "da_duyet", "bo"}),
    "da_dang": frozenset(),
    "bo": frozenset(),
}
assert set(CHUYEN_HOP_LE) == set(TRANG_THAI)


class LoiChuyenTrangThai(ValueError):
    pass


def bay_gio_vn() -> str:
    return datetime.now(TZ_VN).isoformat(timespec="seconds")


def kiem_tra(job: dict) -> None:
    """Kiểm tra job theo schemas/may-reels/reel_job.schema.json. Sai thì ném jsonschema.ValidationError."""
    import jsonschema
    jsonschema.validate(job, json.loads(SCHEMA.read_text(encoding="utf-8")))


def tao_job(*, ma_video: str, kenh: str, ma_chu_de: str, chu_de: str, dinh_dang: str,
            nen_tang_dich: list[str], project_dir: str, luc: str | None = None,
            metadata: dict | None = None) -> dict:
    luc = luc or bay_gio_vn()
    job = {
        "phien_ban": 1,
        "ma_video": ma_video, "kenh": kenh, "ma_chu_de": ma_chu_de, "chu_de": chu_de,
        "dinh_dang": dinh_dang, "nen_tang_dich": list(nen_tang_dich),
        "project_dir": project_dir.replace("\\", "/"),
        "trang_thai": "y_tuong",
        "lich_su": [{"tu": None, "den": "y_tuong", "luc": luc}],
        "loi": None,
        "tao_luc": luc, "cap_nhat_luc": luc,
    }
    if metadata is not None:
        job["metadata"] = metadata
    kiem_tra(job)
    return job


def chuyen_trang_thai(job: dict, den: str, *, ly_do: str = "", loi: str | None = None,
                      luc: str | None = None) -> dict:
    """Trả về bản job mới ở trạng thái `den`. Bước nhảy không hợp lệ -> LoiChuyenTrangThai."""
    tu = job.get("trang_thai")
    if den not in CHUYEN_HOP_LE:
        raise LoiChuyenTrangThai(f"Trạng thái không tồn tại: {den!r}")
    if tu not in CHUYEN_HOP_LE:
        raise LoiChuyenTrangThai(f"Job đang ở trạng thái không tồn tại: {tu!r}")
    if den not in CHUYEN_HOP_LE[tu]:
        cho_phep = ", ".join(sorted(CHUYEN_HOP_LE[tu])) or "không có (trạng thái kết thúc)"
        raise LoiChuyenTrangThai(f"{job.get('ma_video')}: không được chuyển {tu} -> {den}. Từ {tu} chỉ được sang: {cho_phep}")
    if den == "loi" and not (loi or "").strip():
        raise LoiChuyenTrangThai("Chuyển sang 'loi' phải kèm thông báo lỗi")
    luc = luc or bay_gio_vn()
    moi = copy.deepcopy(job)
    moi["trang_thai"] = den
    buoc = {"tu": tu, "den": den, "luc": luc}
    if ly_do:
        buoc["ly_do"] = ly_do
    moi["lich_su"].append(buoc)
    moi["loi"] = loi if den == "loi" else None
    moi["cap_nhat_luc"] = luc
    kiem_tra(moi)
    return moi


# Nhãn hiển thị ở cột trang_thai_san_xuat (tab Ý tưởng).
NHAN_TRANG_THAI = {
    "y_tuong": "ý tưởng",
    "dang_san_xuat": "đang sản xuất",
    "cho_quay": "chờ quay",
    "cho_duyet": "chờ duyệt",
    "da_duyet": "đã duyệt",
    "da_dang": "đã đăng",
    "loi": "lỗi",
    "bo": "bỏ",
}
# Chủ đề đã có video từ trước khi có Máy Reels (brand.json chu_de[].da_lam = true).
DA_LAM_TRUOC = "đã làm"

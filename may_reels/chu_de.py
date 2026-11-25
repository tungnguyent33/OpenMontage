"""Đẩy danh sách chủ đề của một kênh (brand/<kenh>/brand.json) lên tab "Ý tưởng"."""
from __future__ import annotations

import json
import re
from pathlib import Path

from may_reels.cot_sheet import Y_TUONG
from may_reels.job import DA_LAM_TRUOC, NHAN_TRANG_THAI
from may_reels.sheet import BangNguon, KetQuaGhi, ghi_theo_khoa

GOC = Path(__file__).resolve().parent.parent
MA_KENH = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def doc_brand(kenh: str, goc: Path | None = None) -> dict:
    goc = goc or GOC
    if not MA_KENH.fullmatch(kenh or ""):
        raise ValueError(f"Mã kênh không hợp lệ: {kenh!r}")
    p = goc / "brand" / kenh / "brand.json"
    if not p.is_file():
        raise FileNotFoundError(f"Không thấy brand/{kenh}/brand.json: chạy tools_local/nap_kenh.py --id {kenh} trước")
    return ghep_chu_de_may(json.loads(p.read_text(encoding="utf-8")), kenh, goc)


CHU_DE_MAY_LOCAL = ("_local", "chu-de-may.json")


def ghep_chu_de_may(brand: dict, kenh: str, goc: Path | None = None) -> dict:
    """Ghép chủ đề máy đề xuất (brand/<kenh>/_local/chu-de-may.json, do nap_kenh.py sinh từ chu-de-may.md) vào
    brand["chu_de"]. File nằm trong _local/ (gitignore) vì ý chính có thể nhắc học phí, ưu đãi. Mã trùng: giữ chủ đề
    của brand.json. Không có file thì trả nguyên brand."""
    f = (goc or GOC) / "brand" / kenh / Path(*CHU_DE_MAY_LOCAL)
    if not f.is_file():
        return brand
    co = {c.get("ma") for c in brand.get("chu_de") or []}
    them = [c for c in json.loads(f.read_text(encoding="utf-8")) if c.get("ma") not in co]
    return {**brand, "chu_de": list(brand.get("chu_de") or []) + them}


def dong_y_tuong(kenh: str, brand: dict) -> tuple[list[dict], list[dict]]:
    """(dòng đã làm, dòng chưa làm). hook_de_xuat và diem để None: lệnh này không đụng tới."""
    da, chua = [], []
    for c in brand.get("chu_de") or []:
        d = {
            "ma": c.get("ma"), "kenh": kenh,
            "tru_cot": c.get("tru_cot"), "dinh_dang": c.get("dinh_dang"),
            "chu_de": c.get("chu_de"), "nguon_doi_chieu": c.get("nguon_doi_chieu"),
        }
        if c.get("da_lam"):
            d["trang_thai_san_xuat"] = DA_LAM_TRUOC
            da.append(d)
        else:
            d["trang_thai_san_xuat"] = NHAN_TRANG_THAI["y_tuong"]
            chua.append(d)
    return da, chua


def nap_chu_de(bang: BangNguon, kenh: str, *, thu: bool = False, goc: Path | None = None) -> tuple[KetQuaGhi, KetQuaGhi]:
    """Chạy lại bao nhiêu lần cũng không tạo dòng trùng (khóa kenh + ma).

    - Chủ đề da_lam: trang_thai_san_xuat = "đã làm" (ghi đè, vì đã có video thật).
    - Chủ đề chưa làm: chỉ ghi "ý tưởng" khi ô còn trống, để không lùi tiến độ máy đã ghi.
    - dinh_dang của chủ đề chưa làm chỉ ghi khi ô trống: lệnh y-tuong đổi ô này sang mã định dạng của dinh-dang.yaml
      (ví dụ luat-hoi-nhanh-dap-dung thay cho hoi-dap của chu-de.md), nạp lại không được đè.
    """
    da, chua = dong_y_tuong(kenh, doc_brand(kenh, goc))
    kq_da = ghi_theo_khoa(bang, Y_TUONG, da, thu=thu)
    kq_chua = ghi_theo_khoa(bang, Y_TUONG, chua, chi_khi_trong={"trang_thai_san_xuat", "dinh_dang"}, thu=thu)
    return kq_da, kq_chua

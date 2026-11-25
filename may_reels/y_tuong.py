"""Chủ đề theo nhóm và lịch tuần (prompt C1): `python -m may_reels y-tuong --kenh <mã> [--tuan YYYY-Www] [--thu]`.

Mỗi tuần 7 ô theo brand/<kenh>/lich.yaml (thứ 2 .. Chủ Nhật). Python chuẩn bị, agent viết, Python kiểm rồi mới ghi:

  1. Python: ô còn trống của tuần (ô đã có chủ đề chưa Bỏ thì giữ), định dạng đủ điều kiện của từng ô
     (dinh-dang.yaml dieu_kien, dữ kiện da_xac_nhan trong ban-hang.yaml), mùa đang chạy (2 ô chuyển đổi đầu tiên
     phải nói với nhóm của mùa), câu hỏi khách chưa dùng, ma trận nhóm x nỗi lo chưa làm, chủ đề luật còn lại,
     lịch sử 60 ngày, nhóm và định dạng chưa thử. Ghi projects/_may_reels/y_tuong/<kenh>/<tuan>/yeu_cau.json.
  2. Agent (claude -p, skills/may-reels/y-tuong.md) ghi y_tuong.json: một chủ đề cho mỗi ô.
  3. Python kiểm (kiem): định dạng đúng ô, nhóm và nỗi lo có thật, cụm từ cấm / câu sáo / hook sáo / gấp gáp giả,
     số tiền chỉ là số đã xác nhận, dữ kiện bán hàng chỉ dùng mục da_xac_nhan, chống trùng 60 ngày (cùng nhóm, cùng
     nỗi lo, cùng định dạng). Lỗi thì gửi lại agent một vòng; vẫn lỗi thì bỏ chủ đề đó và ghi lý do vào Nhật ký.
  4. Ghi: chủ đề mới vào <KENH_GOC_DIR>/<kenh>/chu-de-may.md (file của máy; chu-de.md của người không bị sửa), chạy
     tools_local/nap_kenh.py, rồi ghi tab Ý tưởng (trạng thái duyệt để trống = Chờ), đánh dấu câu hỏi khách đã dùng,
     ghi Nhật ký kèm chi phí agent.

Chủ đề có nội dung luật vẫn đi qua `nguon-luat` như cũ: san-xuat từ chối khi nguồn chưa tới mức khoản.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from may_reels.chu_de import ghep_chu_de_may
from may_reels.cot_sheet import CAU_HOI_KHACH, NHAT_KY, Y_TUONG
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, danh_ma_dong, doc_dong, ghi_theo_khoa, them_nhat_ky

GOC = Path(__file__).resolve().parent.parent
SKILL = "skills/may-reels/y-tuong.md"
CHU_DE_MAY = "chu-de-may.md"
THU_MUC = ("projects", "_may_reels", "y_tuong")
SO_NGAY_TRUNG = 60          # cùng nhóm + cùng nỗi lo + cùng định dạng trong 60 ngày = trùng
SO_O_MUA = 2                # trong mùa: ít nhất 2 ô chuyển đổi nói với nhóm của mùa (lich.yaml: "đổi 2-3 ô")
TANG = ("keo_xem", "niem_tin", "chuyen_doi")
KHONG_CAN = "Không cần nguồn luật"
TRANG_THAI_CHUA_SX = {"", "ý tưởng"}
MA_CHU_DE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TEN_THU = {2: "Thứ Hai", 3: "Thứ Ba", 4: "Thứ Tư", 5: "Thứ Năm", 6: "Thứ Sáu", 7: "Thứ Bảy", 8: "Chủ Nhật"}

HE_THONG = ("Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi, không được dừng chờ trả lời. "
            f"Chỉ làm theo {SKILL}; bỏ qua mọi quy trình OpenMontage khác. "
            "Chỉ ghi đúng một file y_tuong.json trong thư mục được giao.")


class LoiYTuong(RuntimeError):
    pass


# ---------------------------------------------------------------- tuần, ngày
def tuan_toi(hom_nay: dt.date) -> str:
    y, w, _ = (hom_nay + dt.timedelta(days=7)).isocalendar()
    return f"{y}-W{w:02d}"


def thu_hai_cua(tuan: str) -> dt.date:
    m = re.fullmatch(r"(\d{4})-W(\d{2})", tuan or "")
    if not m:
        raise LoiYTuong(f"Tuần không đúng dạng YYYY-Www (ví dụ 2026-W49): {tuan!r}")
    try:
        return dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    except ValueError as e:
        raise LoiYTuong(f"Tuần không có thật: {tuan}") from e


def ngay_cua(thu_hai: dt.date, thu: int) -> dt.date:
    """lich.yaml: thu 2..7, 8 = Chủ Nhật."""
    return thu_hai + dt.timedelta(days=int(thu) - 2)


def _ngay(x) -> dt.date | None:
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    try:
        return dt.date.fromisoformat(str(x)[:10]) if x else None
    except ValueError:
        return None


# ---------------------------------------------------------------- dữ liệu kênh
def _yaml(p: Path) -> dict:
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.is_file() else {}


def doc_du_lieu(kenh: str, goc: Path = GOC) -> dict:
    b = goc / "brand" / kenh
    thieu = [f for f in ("lich.yaml", "dinh-dang.yaml") if not (b / f).is_file()]
    if not (b / "doi-tuong.yaml").is_file():
        thieu.append("doi-tuong.yaml (tạo từ doi-tuong.mau.yaml)")
    if thieu:
        raise LoiYTuong(f"brand/{kenh}/ thiếu {', '.join(thieu)}")
    bj = b / "brand.json"
    if not bj.is_file():
        raise LoiYTuong(f"Không thấy brand/{kenh}/brand.json: chạy tools_local/nap_kenh.py --id {kenh} trước")
    rb = _yaml(b / "rubric-kich-ban.yaml")
    return {
        "lich": _yaml(b / "lich.yaml"), "dinh_dang": _yaml(b / "dinh-dang.yaml"),
        "doi_tuong": _yaml(b / "doi-tuong.yaml"), "dinh_vi": _yaml(b / "dinh-vi.yaml"),
        "ban_hang": _yaml(b / "ban-hang.yaml") if (b / "ban-hang.yaml").is_file() else None,
        "san_xuat": _yaml(b / "san-xuat.yaml"), "hook": _yaml(b / "hook.yaml"),
        "gap_gap": ((rb.get("kiem_tra_may") or {}).get("uu_dai_thuong_xuyen") or {}).get("cum_gap_gap") or [],
        "brand": ghep_chu_de_may(json.loads(bj.read_text(encoding="utf-8")), kenh, goc),
    }


def _xn(x) -> bool:
    return isinstance(x, dict) and x.get("trang_thai") == "da_xac_nhan"


def _tien(n) -> str:
    return f"{int(n):,}".replace(",", ".") + "đ"


def du_kien(bh: dict | None, hom_nay: dt.date) -> tuple[list[dict], list[str], set[int]]:
    """(dữ kiện đã xác nhận [{id, noi_dung}], dữ kiện còn thiếu [mô tả], số tiền được nói).
    Chỉ mục trang_thai: da_xac_nhan; ô trống coi là chưa có; cho_xac_nhan không bao giờ dùng."""
    if not bh:
        return [], ["ban-hang.yaml chưa có trên máy: không có dữ kiện bán hàng nào"], set()
    co, thieu, tien = [], [], set()
    for k in bh.get("khoa_hoc") or []:
        if not _xn(k) or not k.get("ma"):
            thieu.append(f"khóa {k.get('ten') or k.get('ma') or '?'}: chưa xác nhận")
            continue
        ten = k.get("ten") or k["ma"]
        if k.get("hoc_phi_vnd"):
            co.append({"id": f"khoa_hoc.{k['ma']}.hoc_phi", "noi_dung": f"{ten}: học phí {_tien(k['hoc_phi_vnd'])} trọn gói"})
            tien.add(int(k["hoc_phi_vnd"]))
        if k.get("gom"):
            co.append({"id": f"khoa_hoc.{k['ma']}.gom", "noi_dung": f"{ten}, học phí đã gồm: " + "; ".join(k["gom"])})
        if k.get("khong_gom"):
            co.append({"id": f"khoa_hoc.{k['ma']}.khong_gom",
                       "noi_dung": f"{ten}, học phí chưa gồm: " + "; ".join(k["khong_gom"])})
        for o, mo_ta in (("so_buoi", "số buổi học"), ("thoi_gian_hoc", "thời gian học")):
            if k.get(o):
                co.append({"id": f"khoa_hoc.{k['ma']}.{o}", "noi_dung": f"{ten}: {mo_ta} {k[o]}"})
            else:
                thieu.append(f"{ten}: {mo_ta}")
    for muc, mo_ta, ds_khoa in (("quy_trinh_dang_ky", "quy trình đăng ký", "buoc"), ("giay_to", "giấy tờ cần mang", "danh_sach")):
        v = bh.get(muc) or {}
        if _xn(v) and v.get(ds_khoa):
            co.append({"id": muc, "noi_dung": f"{mo_ta}: " + json.dumps(v[ds_khoa], ensure_ascii=False)})
        else:
            thieu.append(mo_ta)
    lich = [x for x in bh.get("lich_khai_giang") or [] if _xn(x) and _ngay(x.get("ngay")) and _ngay(x["ngay"]) >= hom_nay]
    for i, x in enumerate(lich):
        co.append({"id": f"lich_khai_giang.{i}", "noi_dung": f"khóa {x.get('khoa')}: khai giảng {_ngay(x['ngay'])}"
                   + (f", hạn đăng ký {x['han_dang_ky']}" if x.get("han_dang_ky") else "")})
    if not lich:
        thieu.append("lịch khai giảng (ngày thật chưa qua)")
    for i, u in enumerate(bh.get("uu_dai") or []):
        if not _xn(u) or not u.get("noi_dung"):
            continue
        het = _ngay(u.get("het_han"))
        if not u.get("thuong_xuyen") and (not het or het < hom_nay):
            continue
        co.append({"id": f"uu_dai.{i}", "noi_dung": u["noi_dung"] + (
            " (ưu đãi thường xuyên: KHÔNG nói hạn chót, 'sắp hết')" if u.get("thuong_xuyen") else f" (hết hạn {het})")})
        tien |= so_tien(u["noi_dung"])
    for i, c in enumerate(bh.get("cau_hoi_thuong_gap") or []):
        if _xn(c) and c.get("hoi") and c.get("tra_loi"):
            co.append({"id": f"cau_hoi_thuong_gap.{i}", "noi_dung": f"{c['hoi']} {c['tra_loi']}"})
            tien |= so_tien(c["tra_loi"])
    moi = [m for m in bh.get("moi_nhu") or [] if _xn(m) and m.get("ma")]
    for m in moi:
        co.append({"id": f"moi_nhu.{m['ma']}", "noi_dung": f"mồi nhử {m.get('ten') or m['ma']} (nhóm {m.get('nhom_hop')})"})
    if not moi:
        thieu.append("mồi nhử (thứ gửi qua Zalo khi người xem nhắn mã)")
    if not any(_xn(n) and n.get("ma") for n in bh.get("nguoi_dong_y_len_hinh") or []):
        thieu.append("người đã đồng ý lên hình")
    thieu += [f"chờ xác nhận: {c['noi_dung']}" for c in bh.get("cho_xac_nhan") or [] if c.get("noi_dung")]
    return co, thieu, tien


_SO_TIEN = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(triệu|tr\b|nghìn|ngàn|k\b|đồng|đ\b|vnđ|vnd)", re.I)


def so_tien(van_ban: str) -> set[int]:
    """Các số tiền (đồng) nhắc trong văn bản: '1.500.000đ', '1,5 triệu', '70 nghìn', '70k'."""
    ra = set()
    for so, dv in _SO_TIEN.findall(unicodedata.normalize("NFC", van_ban or "")):
        dv = dv.lower()
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", so):
            n = float(re.sub(r"[.,]", "", so))
        else:
            n = float(so.replace(",", "."))
        n *= 1_000_000 if dv in ("triệu", "tr") else 1000 if dv in ("nghìn", "ngàn", "k") else 1
        ra.add(int(round(n)))
    return ra


def moi_nhu_cho(bh: dict | None, nhom: str) -> str:
    for m in (bh or {}).get("moi_nhu") or []:
        if _xn(m) and m.get("ma") and (not m.get("nhom_hop") or nhom in m["nhom_hop"]):
            return m["ma"]
    return ""


# ---------------------------------------------------------------- điều kiện định dạng
def dieu_kien_dinh_dang(dd: dict, bh: dict | None, co_cau_hoi: bool) -> str:
    """'' = làm được; khác rỗng = lý do không làm được tuần này (dieu_kien trong dinh-dang.yaml)."""
    from may_reels.chien_luoc import CAN_SO_LIEU, _co_so_lieu
    thieu = [m for m in CAN_SO_LIEU.get(dd["ma"], []) if not _co_so_lieu(bh, m)]
    if thieu:
        return f"{dd['ma']}: ban-hang.yaml chưa có mục đã xác nhận và đủ ô: {', '.join(thieu)}"
    if dd.get("theo_cau_hoi") and not co_cau_hoi:
        return f"{dd['ma']}: cần câu hỏi thật của khách, tab Câu hỏi khách chưa có câu nào chưa dùng"
    return ""


def tru_cot_cua(dd: dict, sx: dict) -> str:
    """Định dạng luật trỏ khung nhịp có sẵn: trụ cột = trụ cột của khung (san-xuat chọn khung theo trụ cột)."""
    k = (sx.get("khung_nhip") or {}).get(dd.get("khung_nhip") or "") or {}
    return k.get("tru_cot") or dd.get("ten") or dd["ma"]


def _nfc(s) -> str:
    return " ".join(unicodedata.normalize("NFC", str(s or "")).split()).casefold()


def trung(a: dict, b: dict) -> bool:
    return all(_nfc(a.get(k)) and _nfc(a.get(k)) == _nfc(b.get(k)) for k in ("doi_tuong", "noi_lo", "dinh_dang"))


# ---------------------------------------------------------------- đầu vào cho agent
@dataclass
class O:
    """Một ô của lịch tuần."""
    thu: int
    ngay: dt.date
    tang: str
    dinh_dang: list[str]                       # định dạng làm được, theo thứ tự ưu tiên
    ghi_chu: str = ""
    mua: list[str] = field(default_factory=list)   # ô mùa: nhóm phải thuộc danh sách này
    du_phong: str = ""                         # lý do dùng định dạng của ngày khác cùng tầng
    bo: str = ""                               # không lấp được: lý do


def _cau_hoi(bang: BangNguon, kenh: str, thu: bool) -> tuple[list[dict], list[str]]:
    """Câu hỏi khách của kênh (đánh mã cho dòng mới trước). Trả về (dòng, cảnh báo)."""
    canh_bao = []

    def tao_ma(d):
        h = hashlib.sha1("|".join(_nfc(d.get(k)) for k in ("kenh", "ngay", "nen_tang", "cau_hoi")).encode()).hexdigest()
        return f"ch-{h[:6]}"
    from may_reels.sheet import tim_tab
    if tim_tab(bang, CAU_HOI_KHACH.ten) is None:
        if thu:
            return [], [f"Chưa có tab {CAU_HOI_KHACH.ten!r}: chạy `python -m may_reels sheet init`"]
        raise LoiYTuong(f"Chưa có tab {CAU_HOI_KHACH.ten!r}: chạy `python -m may_reels sheet init` trước")
    danh_ma_dong(bang, CAU_HOI_KHACH, tao_ma, thu=thu)
    ra = []
    for d in doc_dong(bang, CAU_HOI_KHACH):
        if not d.get("cau_hoi"):
            continue
        if not d.get("kenh"):
            canh_bao.append(f"Câu hỏi khách {d.get('ma_cau_hoi') or '(chưa có mã)'}: thiếu cột kenh, bỏ qua")
            continue
        if d["kenh"] == kenh and d.get("ma_cau_hoi"):
            ra.append(d)
    return ra, canh_bao


def dau_vao(bang: BangNguon, kenh: str, tuan: str, *, goc: Path = GOC, hom_nay: dt.date | None = None,
            thu: bool = False) -> dict:
    hom_nay = hom_nay or dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
    dl = doc_du_lieu(kenh, goc)
    t2 = thu_hai_cua(tuan)
    bh = dl["ban_hang"]
    co, thieu_dk, tien = du_kien(bh, hom_nay)
    ds_dd = {d["ma"]: d for d in (dl["dinh_dang"].get("dinh_dang") or [])}
    nhom = {n["ma"]: n for n in (dl["doi_tuong"].get("nhom") or [])}
    cau_hoi, canh_bao = _cau_hoi(bang, kenh, thu)
    cau_hoi_chua = [c for c in cau_hoi if not c.get("da_dung_cho")]

    dong = [d for d in doc_dong(bang, Y_TUONG) if d.get("kenh") == kenh]
    lich_su = [d for d in dong if _ngay(d.get("ngay_du_kien")) and chuan(d.get("duyet_chu_de")) != "Bỏ"]
    co_ngay = {_ngay(d["ngay_du_kien"]) for d in lich_su}

    # mùa
    lich = dl["lich"]
    mua = None
    m = next((x for x in lich.get("mua") or [] if x.get("ma") == lich.get("mua_dang_chay")), None)
    if m and m.get("tu_ngay") and m.get("den_ngay") and _ngay(m["tu_ngay"]) <= t2 + dt.timedelta(days=6) \
            and t2 <= _ngay(m["den_ngay"]):
        mua = m
    elif m and m.get("theo_su_kien"):
        canh_bao.append(f"Mùa {m['ma']} tính theo sự kiện, lich.yaml chưa có ngày mốc: không áp mùa")

    # ô của tuần
    o: list[O] = []
    ly_do_dd: dict[str, str] = {}
    for t in sorted(lich.get("tuan") or [], key=lambda x: x["thu"]):
        ngay = ngay_cua(t2, t["thu"])
        oo = O(t["thu"], ngay, t["tang"], [], t.get("ghi_chu") or "")
        if ngay in co_ngay:
            oo.bo = "đã có chủ đề cho ngày này trên tab Ý tưởng (chưa Bỏ)"
        elif ngay < hom_nay:
            oo.bo = "ngày đã qua"
        for ma in t.get("dinh_dang") or []:
            if ma not in ds_dd:
                ly_do_dd[ma] = f"{ma}: không có trong dinh-dang.yaml"
                continue
            ld = dieu_kien_dinh_dang(ds_dd[ma], bh, bool(cau_hoi_chua))
            if ld:
                ly_do_dd[ma] = ld
            else:
                oo.dinh_dang.append(ma)
        o.append(oo)
    for oo in o:
        if oo.bo or oo.dinh_dang:
            continue
        # Không định dạng nào của ngày làm được: dùng định dạng làm được của ngày khác cùng tầng (lấp đủ 7 ô).
        goc_dd = [ma for t in lich.get("tuan") or [] if t["thu"] == oo.thu for ma in t.get("dinh_dang") or []]
        thay = [ma for x in o if x.tang == oo.tang and x.thu != oo.thu for ma in x.dinh_dang]
        thay = list(dict.fromkeys(thay))
        ly = "; ".join(ly_do_dd.get(m, m) for m in goc_dd)
        if thay:
            oo.dinh_dang, oo.du_phong = thay, f"định dạng của ngày không làm được ({ly}); dùng định dạng cùng tầng"
        else:
            oo.bo = f"không định dạng nào làm được: {ly}"
    if mua:
        for oo in [x for x in o if x.tang == "chuyen_doi" and not x.bo][:SO_O_MUA]:
            oo.mua = list(mua.get("nhom") or [])

    # lịch sử, ma trận, chủ đề luật, chưa thử
    gan = [{"ma": d.get("ma"), "doi_tuong": d.get("doi_tuong"), "noi_lo": d.get("noi_lo"), "dinh_dang": d.get("dinh_dang"),
            "ngay": d.get("ngay_du_kien")} for d in lich_su
           if d.get("doi_tuong") and abs((_ngay(d["ngay_du_kien"]) - t2).days) <= SO_NGAY_TRUNG + 7]
    da_cap = {(_nfc(d.get("doi_tuong")), _nfc(d.get("noi_lo"))) for d in dong
              if d.get("doi_tuong") and chuan(d.get("duyet_chu_de")) != "Bỏ"}
    ma_tran = [{"nhom": n, "noi_lo": nl} for n, v in sorted(nhom.items(), key=lambda x: x[1].get("uu_tien") or 99)
               for nl in v.get("noi_lo") or [] if (_nfc(n), _nfc(nl)) not in da_cap]
    cd_brand = {c["ma"]: c for c in dl["brand"].get("chu_de") or []}
    theo_ma = {d.get("ma"): d for d in dong}
    luat = []
    for ma, c in cd_brand.items():
        r = theo_ma.get(ma, {})
        if c.get("da_lam") or KHONG_CAN.casefold() in _nfc(c.get("nguon_doi_chieu")) or _nfc(c.get("dinh_dang")) == "bo":
            continue
        if chuan(r.get("duyet_chu_de")) in ("Làm", "Bỏ") or chuan(r.get("trang_thai_san_xuat")) not in TRANG_THAI_CHUA_SX \
                or r.get("ngay_du_kien"):
            continue
        luat.append({k: c.get(k) for k in ("ma", "tru_cot", "chu_de", "y_chinh", "nguon_doi_chieu")})
    da_sx = [d for d in dong if chuan(d.get("trang_thai_san_xuat")) not in TRANG_THAI_CHUA_SX]
    thu_nhom = {d.get("doi_tuong") for d in da_sx if d.get("doi_tuong")}
    khung_dd = {dd.get("khung_nhip"): ma for ma, dd in ds_dd.items() if dd.get("khung_nhip")}
    khung_tc = {v.get("tru_cot"): k for k, v in (dl["san_xuat"].get("khung_nhip") or {}).items()}
    thu_dd = {d.get("dinh_dang") for d in da_sx if d.get("dinh_dang") in ds_dd}
    thu_dd |= {khung_dd.get(khung_tc.get(c.get("tru_cot"))) for c in cd_brand.values() if c.get("da_lam")} - {None}
    chua_thu = {"nhom": [n for n in nhom if n not in thu_nhom], "dinh_dang": [m for m in ds_dd if m not in thu_dd]}

    cam = dl["brand"].get("cam") or {}
    yc = {
        "kenh": kenh, "tuan": tuan, "ngay_hom_nay": hom_nay.isoformat(),
        "o": [{"thu": x.thu, "ten_thu": TEN_THU.get(x.thu, str(x.thu)), "ngay": x.ngay.isoformat(), "tang": x.tang,
               "dinh_dang_duoc": [{k: ds_dd[m].get(k) for k in ("ma", "ten", "tang", "nhom_chinh", "hook_mau", "giong",
                                                              "dieu_kien", "ghi_chu")} for m in x.dinh_dang],
               "ghi_chu_lich": x.ghi_chu, "nhom_mua_bat_buoc": x.mua, "du_phong": x.du_phong}
              for x in o if not x.bo],
        "mua": ({k: mua.get(k) for k in ("ma", "ten", "nhom", "goc", "dieu_kien_duoc_noi")} if mua else None),
        "doi_tuong": [{k: v.get(k) for k in ("ma", "uu_tien", "ten", "ai_quyet_dinh", "noi_lo", "khoanh_khac_mua",
                                              "bang_chung_thuyet_phuc", "ghi_chu")} for v in nhom.values()],
        "dinh_vi": dl["dinh_vi"] or None,
        "du_kien_da_xac_nhan": co, "du_kien_chua_co": thieu_dk,
        "cau_hoi_khach_chua_dung": [{k: c.get(k) for k in ("ma_cau_hoi", "ngay", "nen_tang", "cau_hoi", "nhom")}
                                    for c in cau_hoi_chua],
        "ma_tran_chua_lam": ma_tran, "chu_de_luat_con_lai": luat,
        "da_len_lich_gan_day": gan, "chua_thu": chua_thu,
        "cong_thuc_hook": [{k: c.get(k) for k in ("ma", "ten", "mo_ta", "khi_dung")}
                           for c in (dl["hook"].get("cong_thuc") or [])],
        "cam": {"cum_tu_cam": (cam.get("cum_tu_cam") or []) + (cam.get("cum_tu_cam_du_an") or []),
                "cau_sao": (cam.get("cau_sao_da_chot") or []) + (cam.get("cau_sao_cho_duyet") or []),
                "hook_sao": dl["hook"].get("hook_sao") or [], "gap_gap": dl["gap_gap"],
                "noi_dung_cam": (cam.get("noi_dung_cam") or []) + (cam.get("cam_du_an") or [])},
    }
    return {"yeu_cau": yc, "o": o, "dl": dl, "tien": tien, "co": co, "thieu_dk": thieu_dk, "ds_dd": ds_dd,
            "nhom": nhom, "cau_hoi": cau_hoi, "cau_hoi_chua": cau_hoi_chua, "lich_su": lich_su, "luat": luat,
            "cd_brand": cd_brand, "chua_thu": chua_thu, "mua": mua, "canh_bao": canh_bao, "ly_do_dd": ly_do_dd,
            "hom_nay": hom_nay}


# ---------------------------------------------------------------- kiểm kết quả agent
def _cum_cam(van_ban: str, vao: dict) -> tuple[list[str], list[str]]:
    """(lỗi chặn, cảnh báo) về câu chữ."""
    from may_reels.cham_diem import tim_cum_tu
    cam = vao["yeu_cau"]["cam"]
    brand_cam = vao["dl"]["brand"].get("cam") or {}
    chan = [f"cụm từ cấm '{c}'" for c in tim_cum_tu(van_ban, cam["cum_tu_cam"])]
    chan += [f"câu sáo đã cấm '{c}'" for c in tim_cum_tu(van_ban, brand_cam.get("cau_sao_da_chot") or [])]
    chan += [f"hook sáo '{c}'" for c in tim_cum_tu(van_ban, cam["hook_sao"])]
    # Gấp gáp giả: chỉ được nói hạn khi có ưu đãi đã xác nhận còn hạn thật.
    co_han = any(_xn(u) and not u.get("thuong_xuyen") and _ngay(u.get("het_han")) and _ngay(u["het_han"]) >= vao["hom_nay"]
                 for u in (vao["dl"]["ban_hang"] or {}).get("uu_dai") or [])
    if not co_han:
        chan += [f"tạo gấp gáp giả '{c}'" for c in tim_cum_tu(van_ban, cam["gap_gap"])]
    # Câu trong ngoặc kép ở dieu_kien_duoc_noi của mùa: chỉ nói khi đã có lịch khai giảng đã xác nhận.
    if vao["mua"] and not any(x["id"].startswith("lich_khai_giang") for x in vao["co"]):
        for dk in vao["mua"].get("dieu_kien_duoc_noi") or []:
            for c in re.findall(r'"([^"]+)"', dk):
                if tim_cum_tu(van_ban, [c]):
                    chan.append(f"'{c}': {dk} (ban-hang.yaml chưa có lịch khai giảng đã xác nhận)")
    canh = [f"câu sáo chờ duyệt '{c}'" for c in tim_cum_tu(van_ban, [x for x in brand_cam.get("cau_sao_cho_duyet") or []
                                                                    if "…" not in x])]
    return chan, canh


def kiem_mot(c: dict, oo: O, vao: dict, da_chon: list[dict]) -> tuple[list[str], list[str]]:
    """Kiểm một chủ đề agent đề xuất cho ô `oo`. (lỗi, cảnh báo). da_chon: chủ đề hợp lệ trước đó trong lô."""
    from may_reels.bien_tap import so_am_tiet
    from may_reels.nguon_luat import _QCVN, _VB_LUAT, _bo_dau
    loi, canh = [], []
    dd = c.get("dinh_dang")
    if dd not in oo.dinh_dang:
        loi.append(f"định dạng {dd!r} không thuộc ô này (được: {oo.dinh_dang})")
    n = c.get("doi_tuong")
    if n not in vao["nhom"]:
        loi.append(f"nhóm {n!r} không có trong doi-tuong.yaml")
    else:
        nc = (vao["ds_dd"].get(dd) or {}).get("nhom_chinh") or []
        if nc and n not in nc:
            canh.append(f"nhóm {n} không thuộc nhóm chính của {dd} ({nc})")
    if oo.mua and n not in oo.mua:
        loi.append(f"ô mùa {vao['mua']['ma']}: nhóm phải là một trong {oo.mua}")
    nguon_yt = chuan(c.get("nguon_y_tuong"))
    ma_ch = chuan(c.get("ma_cau_hoi"))
    ch = next((x for x in vao["cau_hoi_chua"] if x.get("ma_cau_hoi") == ma_ch), None) if ma_ch else None
    if nguon_yt == "cau_hoi_khach":
        if not ch:
            loi.append(f"ma_cau_hoi {ma_ch!r} không phải câu hỏi khách chưa dùng")
        elif ch.get("nhom") and n != ch["nhom"]:
            loi.append(f"câu hỏi {ma_ch} ghi nhóm {ch['nhom']}, chủ đề lại cho nhóm {n}")
        if any(chuan(x.get("ma_cau_hoi")) == ma_ch for x in da_chon):
            loi.append(f"câu hỏi {ma_ch} đã dùng cho chủ đề khác trong tuần")
    elif nguon_yt not in ("ma_tran", "luat"):
        loi.append(f"nguon_y_tuong {nguon_yt!r} phải là cau_hoi_khach / ma_tran / luat")
    if (vao["ds_dd"].get(dd) or {}).get("theo_cau_hoi") and nguon_yt != "cau_hoi_khach":
        loi.append(f"{dd} phải trả lời một câu hỏi thật của khách (nguon_y_tuong = cau_hoi_khach)")
    nl = chuan(c.get("noi_lo"))
    if not nl:
        loi.append("thiếu noi_lo")
    elif n in vao["nhom"] and _nfc(nl) not in {_nfc(x) for x in vao["nhom"][n].get("noi_lo") or []} \
            and nguon_yt != "cau_hoi_khach":
        loi.append(f"nỗi lo {nl!r} không có trong noi_lo của nhóm {n} (chỉ chủ đề từ câu hỏi khách được dùng chữ của khách)")

    # mã: chủ đề luật có sẵn hoặc mã mới
    ma_cs = chuan(c.get("ma_co_san"))
    if ma_cs:
        if ma_cs not in {x["ma"] for x in vao["luat"]}:
            loi.append(f"ma_co_san {ma_cs!r} không phải chủ đề luật còn lại chưa lên lịch")
        if any(x.get("ma_co_san") == ma_cs for x in da_chon):
            loi.append(f"chủ đề {ma_cs} đã dùng cho ô khác")
    else:
        ma = chuan(c.get("ma"))
        if not MA_CHU_DE.fullmatch(ma) or len(ma) > 40:
            loi.append(f"mã {ma!r} phải là chữ thường không dấu, số, gạch nối, tối đa 40 ký tự")
        elif ma in vao["cd_brand"] or any(x.get("ma") == ma for x in da_chon):
            loi.append(f"mã {ma!r} đã có")
        for k in ("chu_de", "y_chinh"):
            if not chuan(c.get(k)):
                loi.append(f"thiếu {k}")
    hook = chuan(c.get("hook_de_xuat"))
    if not hook:
        loi.append("thiếu hook_de_xuat")
    elif so_am_tiet(hook) > 16:
        canh.append(f"hook {so_am_tiet(hook)} âm tiết, dài hơn 3 giây đọc")

    # câu chữ, số tiền, dữ kiện bán hàng
    van_ban = " . ".join(chuan(c.get(k)) for k in ("chu_de", "y_chinh", "hook_de_xuat"))
    ch_, cb_ = _cum_cam(van_ban, vao)
    loi += ch_
    canh += cb_
    la = sorted(so_tien(van_ban) - vao["tien"])
    if la:
        loi.append(f"số tiền chưa xác nhận trong ban-hang.yaml: {', '.join(_tien(x) for x in la)}")
    ids = {x["id"] for x in vao["co"]}
    sai_id = [x for x in c.get("du_kien_dung") or [] if x not in ids]
    if sai_id:
        loi.append(f"du_kien_dung không phải dữ kiện đã xác nhận: {sai_id}")
    if c.get("du_kien_thieu"):
        loi.append(f"thiếu dữ kiện bán hàng: {'; '.join(map(str, c['du_kien_thieu']))}")

    # nguồn luật
    if c.get("co_noi_dung_luat"):
        b = _bo_dau(chuan(c.get("nguon_doi_chieu")))
        if not ma_cs and (not b or KHONG_CAN.casefold() in _nfc(c.get("nguon_doi_chieu"))
                          or not (_VB_LUAT.search(b) or _QCVN.search(b))):
            loi.append("chủ đề có nội dung luật phải ghi văn bản cần đối chiếu ở nguon_doi_chieu")

    # chống trùng 60 ngày (cùng nhóm, cùng nỗi lo, cùng định dạng)
    for h in vao["lich_su"]:
        nh = _ngay(h.get("ngay_du_kien"))
        if nh and abs((nh - oo.ngay).days) <= SO_NGAY_TRUNG and trung(c, h):
            loi.append(f"trùng chủ đề {h.get('ma')} ({nh}): cùng nhóm, nỗi lo, định dạng trong {SO_NGAY_TRUNG} ngày")
    for x in da_chon:
        if trung(c, x):
            loi.append(f"trùng chủ đề {x.get('ma') or x.get('ma_co_san')} trong cùng tuần")
    return loi, canh


@dataclass
class KetQuaKiem:
    hop_le: list[dict] = field(default_factory=list)      # chủ đề đạt (kèm _o, _canh_bao)
    loi: dict[int, list[str]] = field(default_factory=dict)   # thu -> lỗi
    loi_chung: list[str] = field(default_factory=list)
    bo: dict[int, str] = field(default_factory=dict)     # agent tự bỏ ô: thu -> lý do


def kiem(de_xuat: dict, vao: dict) -> KetQuaKiem:
    kq = KetQuaKiem()
    o = {x.thu: x for x in vao["o"] if not x.bo}
    theo_thu: dict[int, dict] = {}
    for c in de_xuat.get("chu_de") or []:
        try:
            t = int(c.get("thu"))
        except (TypeError, ValueError):
            kq.loi_chung.append(f"chủ đề không có thu hợp lệ: {str(c)[:80]}")
            continue
        if t not in o:
            kq.loi_chung.append(f"thu {t}: không phải ô cần lấp")
        elif t in theo_thu:
            kq.loi.setdefault(t, []).append("hai chủ đề cho cùng một ô")
        else:
            theo_thu[t] = c
    for b in de_xuat.get("bo_qua") or []:
        try:
            kq.bo[int(b.get("thu"))] = chuan(b.get("ly_do")) or "agent không ghi lý do"
        except (TypeError, ValueError):
            pass
    for t, oo in sorted(o.items()):
        c = theo_thu.get(t)
        if not c:
            if t not in kq.bo:
                kq.loi.setdefault(t, []).append("ô chưa có chủ đề")
            continue
        kq.bo.pop(t, None)
        loi, canh = kiem_mot(c, oo, vao, kq.hop_le)
        if loi:
            kq.loi.setdefault(t, []).extend(loi)
        else:
            kq.hop_le.append({**c, "thu": t, "_o": oo, "_canh_bao": canh})
    # 1 trong 5 chủ đề dành cho nhóm hoặc định dạng chưa thử
    ct = vao["chua_thu"]
    if kq.hop_le and (ct["nhom"] or ct["dinh_dang"]) and not any(
            c.get("thu_moi") and (c.get("doi_tuong") in ct["nhom"] or c.get("dinh_dang") in ct["dinh_dang"])
            for c in kq.hop_le):
        kq.loi_chung.append("chưa có chủ đề thu_moi nào cho nhóm hoặc định dạng chưa thử (chua_thu)")
    return kq


# ---------------------------------------------------------------- ghi
def _o_bang(s) -> str:
    return " ".join(str(s or "").replace("|", "/").split())


def ghi_chu_de_may(tm: Path, ds: list[dict]) -> Path | None:
    """Thêm dòng vào <thư mục kênh gốc>/chu-de-may.md (tạo nếu chưa có). Sao lưu trước khi sửa. Trả về file sao lưu."""
    f = tm / CHU_DE_MAY
    sl = None
    if f.is_file():
        text = f.read_bytes().decode("utf-8")
        sl = f.with_name(f"{CHU_DE_MAY}.bak-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(f, sl)
    else:
        text = ("# Chủ đề máy đề xuất\n\n"
                "File do `python -m may_reels y-tuong` ghi: máy chỉ thêm dòng (sao lưu trước khi sửa), "
                "`nguon-luat ap-dung` sửa ô nguồn. Cùng cột với `chu-de.md`; `tools_local/nap_kenh.py` đọc cả hai. "
                "Không muốn làm chủ đề nào thì chọn Bỏ trên Sheet, không cần xóa dòng.\n\n"
                "| Mã | Trụ cột | Định dạng | Chủ đề (câu hỏi) | Ý chính cần kiểm | Nguồn cần đối chiếu | Trend |\n"
                "|---|---|---|---|---|---|---|\n")
    nl = "\r\n" if "\r\n" in text else "\n"
    if not text.endswith(("\n", "\r\n")):
        text += nl
    for c in ds:
        text += "| " + " | ".join(_o_bang(c.get(k)) for k in ("ma", "tru_cot", "dinh_dang", "chu_de", "y_chinh",
                                                             "nguon_doi_chieu")) + " | |" + nl
    tm.mkdir(parents=True, exist_ok=True)
    f.write_bytes(text.encode("utf-8"))
    return sl


def goi_agent_y_tuong(prompt: str, *, du_an: Path, goc: Path) -> dict:
    from may_reels.san_xuat import goi_agent
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=("y_tuong.json",), web=False, he_thong=HE_THONG)


def _nap_kenh(kenh: str, goc: Path) -> None:
    from may_reels.nguon_luat import chay_nap_kenh
    chay_nap_kenh(kenh, goc)


@dataclass
class KetQua:
    tuan: str
    chu_de: list[dict] = field(default_factory=list)
    bo: list[tuple[str, str]] = field(default_factory=list)   # (ô, lý do)
    canh_bao: list[str] = field(default_factory=list)
    so_luot: int = 0
    giay_agent: float = 0.0
    chi_phi_usd: float = 0.0
    sao_luu: Path | None = None


def chay(bang: BangNguon, kenh: str, tuan: str | None = None, *, goc: Path = GOC, thu: bool = False,
         agent: Callable[..., dict] = goi_agent_y_tuong, nap: Callable[[str, Path], None] = _nap_kenh,
         thu_muc_kenh: Path | None = None, hom_nay: dt.date | None = None,
         log: Callable[[str], None] = print) -> KetQua:
    t0 = time.monotonic()
    hom_nay = hom_nay or dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
    tuan = tuan or tuan_toi(hom_nay)
    vao = dau_vao(bang, kenh, tuan, goc=goc, hom_nay=hom_nay, thu=thu)
    kq = KetQua(tuan, canh_bao=list(vao["canh_bao"]))
    o_mo = [x for x in vao["o"] if not x.bo]
    for x in vao["o"]:
        if x.bo and x.bo != "đã có chủ đề cho ngày này trên tab Ý tưởng (chưa Bỏ)":
            kq.bo.append((f"{TEN_THU.get(x.thu)} {x.ngay}", x.bo))
    log(f"Tuần {tuan} ({thu_hai_cua(tuan)} .. {thu_hai_cua(tuan) + dt.timedelta(days=6)}), kênh {kenh}: "
        f"{len(o_mo)} ô cần lấp" + (f"; mùa {vao['mua']['ten']}" if vao["mua"] else ""))
    for x in vao["o"]:
        log(f"   {TEN_THU.get(x.thu)} {x.ngay} {x.tang:10} "
            + (f"bỏ: {x.bo}" if x.bo else ", ".join(x.dinh_dang) + (" [dự phòng]" if x.du_phong else "")
               + (f" [mùa: {', '.join(x.mua)}]" if x.mua else "")))
    if vao["thieu_dk"]:
        log("   Dữ kiện bán hàng còn thiếu: " + "; ".join(vao["thieu_dk"]))
    for x in vao["canh_bao"]:
        log(f"   ! {x}")
    if not o_mo:
        log("Không còn ô nào cần lấp.")
        return kq
    if thu:
        log("[thử] Không gọi agent, không ghi gì.")
        return kq

    thu_muc = goc.joinpath(*THU_MUC, kenh, tuan)
    thu_muc.mkdir(parents=True, exist_ok=True)
    rel = thu_muc.relative_to(goc).as_posix()
    yc = dict(vao["yeu_cau"])
    kiem_kq = None
    for vong in range(2):
        (thu_muc / "yeu_cau.json").write_text(json.dumps(yc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        f = thu_muc / "y_tuong.json"
        f.unlink(missing_ok=True)
        r = agent(f"Đọc và làm đúng theo {SKILL}. Đọc {rel}/yeu_cau.json rồi ghi {rel}/y_tuong.json.",
                  du_an=thu_muc, goc=goc)
        kq.so_luot += 1
        kq.giay_agent += round((r.get("duration_ms") or 0) / 1000, 1)
        kq.chi_phi_usd += float(r.get("total_cost_usd") or 0)
        try:
            raw = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        except ValueError as e:
            raw = {}
            kq.canh_bao.append(f"y_tuong.json không đọc được: {e}")
        if r.get("is_error") or not raw:
            kq.canh_bao.append(f"agent lỗi (vòng {vong + 1}): {str(r.get('result'))[:200]}")
        kiem_kq = kiem(raw, vao)
        log(f"Vòng {vong + 1}: {len(kiem_kq.hop_le)} chủ đề đạt, {len(kiem_kq.loi)} ô lỗi"
            + (f", lỗi chung: {'; '.join(kiem_kq.loi_chung)}" if kiem_kq.loi_chung else ""))
        if not kiem_kq.loi and not kiem_kq.loi_chung:
            break
        yc = {**vao["yeu_cau"], "phan_hoi": {
            "loi_theo_o": {str(t): ds for t, ds in kiem_kq.loi.items()}, "loi_chung": kiem_kq.loi_chung,
            "chu_de_da_dat": [{k: v for k, v in c.items() if not k.startswith("_")} for c in kiem_kq.hop_le],
            "huong_dan": "Giữ nguyên chủ đề đã đạt (có thể đổi một chủ đề để thỏa lỗi chung), viết lại chủ đề cho các ô "
                         "bị lỗi, ghi lại TOÀN BỘ y_tuong.json."}}
    assert kiem_kq is not None
    kq.canh_bao += [f"chưa đạt: {x}" for x in kiem_kq.loi_chung]
    for t, ly in kiem_kq.bo.items():
        oo = next(x for x in vao["o"] if x.thu == t)
        kq.bo.append((f"{TEN_THU.get(t)} {oo.ngay}", f"agent bỏ: {ly}"))
    for t, ds in kiem_kq.loi.items():
        oo = next(x for x in vao["o"] if x.thu == t)
        if t not in kiem_kq.bo:
            kq.bo.append((f"{TEN_THU.get(t)} {oo.ngay}", "; ".join(ds)))

    # dựng dòng
    bh = vao["dl"]["ban_hang"]
    moi, dong = [], []
    for c in kiem_kq.hop_le:
        oo: O = c["_o"]
        dd = vao["ds_dd"][c["dinh_dang"]]
        ma = chuan(c.get("ma_co_san")) or chuan(c["ma"])
        nguon = chuan(c.get("nguon_doi_chieu")) if c.get("co_noi_dung_luat") else KHONG_CAN
        ch = next((x for x in vao["cau_hoi_chua"] if x.get("ma_cau_hoi") == chuan(c.get("ma_cau_hoi"))), None)
        nyt = {"cau_hoi_khach": f"cau-hoi-khach:{c.get('ma_cau_hoi')}", "ma_tran": "ma-tran", "luat": "luat"}[
            chuan(c["nguon_y_tuong"])] + ("; thử mới" if c.get("thu_moi") else "") + ("; dự phòng" if oo.du_phong else "")
        moi_nhu = moi_nhu_cho(bh, c["doi_tuong"])
        if not moi_nhu and oo.tang == "chuyen_doi":
            c["_canh_bao"].append("chưa có mồi nhử đã xác nhận hợp nhóm: CTA chỉ mời nhắn hỏi")
        d = {"kenh": kenh, "ma": ma, "dinh_dang": dd["ma"], "hook_de_xuat": chuan(c["hook_de_xuat"]),
             "trang_thai_san_xuat": "ý tưởng", "doi_tuong": c["doi_tuong"], "noi_lo": chuan(c["noi_lo"]),
             "tang": oo.tang, "moi_nhu": moi_nhu, "ngay_du_kien": oo.ngay.isoformat(),
             "cau_hoi_khach": (ch or {}).get("cau_hoi") or "", "nguon_y_tuong": nyt}
        if not c.get("ma_co_san"):
            cd = {"ma": ma, "tru_cot": tru_cot_cua(dd, vao["dl"]["san_xuat"]), "dinh_dang": dd["ma"],
                  "chu_de": chuan(c["chu_de"]), "y_chinh": chuan(c["y_chinh"]), "nguon_doi_chieu": nguon}
            moi.append(cd)
            d.update({k: cd[k] for k in ("tru_cot", "chu_de", "nguon_doi_chieu")})
        if c["_canh_bao"]:
            d["ghi_chu_may"] = "; ".join(c["_canh_bao"])[:1000]
        dong.append(d)
        kq.chu_de.append({**d, "thu": c["thu"], "ly_do": chuan(c.get("ly_do")), "canh_bao": c["_canh_bao"],
                          "ma_cau_hoi": (ch or {}).get("ma_cau_hoi"),
                          "co_luat": bool(c.get("co_noi_dung_luat") or c.get("ma_co_san"))})

    if moi:
        if thu_muc_kenh is None:
            from tools_local.nap_kenh import nap_env, thu_muc_kenh as tmk
            nap_env()
            thu_muc_kenh = tmk(kenh)
        if not thu_muc_kenh:
            raise LoiYTuong("Chưa đặt KENH_GOC_DIR trong .env: không có chỗ ghi chu-de-may.md")
        kq.sao_luu = ghi_chu_de_may(thu_muc_kenh, moi)
        nap(kenh, goc)
    if dong:
        ghi_theo_khoa(bang, Y_TUONG, dong, chi_khi_trong={"trang_thai_san_xuat"})
    dung_ch = [{"ma_cau_hoi": c["ma_cau_hoi"], "da_dung_cho": c["ma"]} for c in kq.chu_de if c.get("ma_cau_hoi")]
    if dung_ch:
        ghi_theo_khoa(bang, CAU_HOI_KHACH, dung_ch)

    giay = round(time.monotonic() - t0, 1)
    nk = [{"thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": tuan, "buoc": "y_tuong", "che_do": "that",
           "ket_qua": "ok" if kq.chu_de else "loi",
           "chi_tiet": (f"{len(kq.chu_de)} chủ đề {[c['ma'] for c in kq.chu_de]}; bỏ {len(kq.bo)} ô; "
                        f"{kq.so_luot} lượt agent, claude báo {kq.chi_phi_usd:.2f} USD")[:500],
           "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(giay), "so_luot_tro_ly": str(kq.so_luot)}]
    nk += [{"thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": tuan, "buoc": "y_tuong.bo", "che_do": "that",
            "ket_qua": "bo", "chi_tiet": f"{o}: {ly}"[:500], "chi_phi_vnd": "0", "thoi_gian_chay_giay": "0",
            "so_luot_tro_ly": "0"} for o, ly in kq.bo]
    them_nhat_ky(bang, NHAT_KY, nk)
    (thu_muc / "ket_qua.json").write_text(json.dumps(
        {"tuan": tuan, "chu_de": kq.chu_de, "bo": kq.bo, "canh_bao": kq.canh_bao, "so_luot": kq.so_luot,
         "giay_agent": kq.giay_agent, "chi_phi_usd": round(kq.chi_phi_usd, 4)}, ensure_ascii=False, indent=1,
        default=str), encoding="utf-8")
    return kq


def in_ket_qua(kq: KetQua) -> str:
    ra = [f"Tuần {kq.tuan}: {len(kq.chu_de)} chủ đề mới ở trạng thái Chờ trên tab Ý tưởng."]
    for c in sorted(kq.chu_de, key=lambda x: x["ngay_du_kien"]):
        ra.append(f"  {c['ngay_du_kien']} {TEN_THU.get(c['thu'])}: [{c['tang']}] {c['ma']} | {c['dinh_dang']} | "
                  f"{c['doi_tuong']}: {c['noi_lo']} | {c['nguon_y_tuong']}")
        ra.append(f"      hook: {c['hook_de_xuat']}")
        for x in c["canh_bao"]:
            ra.append(f"      ! {x}")
    for o, ly in kq.bo:
        ra.append(f"  BỎ {o}: {ly}")
    for x in kq.canh_bao:
        ra.append(f"  ! {x}")
    luat = [c["ma"] for c in kq.chu_de if c.get("co_luat")]
    if luat:
        ra.append(f"  Chủ đề có nội dung luật, chạy tiếp: python -m may_reels nguon-luat --kenh <mã> "
                  + " ".join(f"--ma {m}" for m in luat))
    ra.append(f"Agent: {kq.so_luot} lượt, {kq.giay_agent:.0f} s, claude báo {kq.chi_phi_usd:.2f} USD."
              + (f" Sao lưu {kq.sao_luu.name}." if kq.sao_luu else ""))
    return "\n".join(ra)

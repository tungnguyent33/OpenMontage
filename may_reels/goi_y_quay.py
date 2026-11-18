"""Máy chủ động nói cần quay gì: `python -m may_reels kho thieu --kenh <mã> [--ca-chua-duyet] [--thu]`.

  1. Python gom đầu vào: chủ đề đã duyệt ("Làm" trên tab Ý tưởng, chưa đăng/bỏ; --ca-chua-duyet thêm chủ đề chưa
     quyết), thư viện định dạng (khung_nhip trong brand/<kênh>/san-xuat.yaml), kho cảnh (brand.json kho_canh, kèm số lần
     dùng), các yêu cầu đang mở ở tab Cần quay.
  2. Agent (claude -p, skills/may-reels/goi-y-quay.md) viết danh sách quay gộp theo buổi, ưu tiên cảnh dùng lại được
     cho nhiều video.
  3. Python kiểm (mã chủ đề, mã yêu cầu có thật; cảnh nói trước máy phải có lời thoại; mọi cảnh có lưu ý xin phép...),
     ghi tab Cần quay (ma_yeu_cau = <kenh>:goi-y:<mã cảnh>) và xuất bản văn bản gọn để gửi Zalo cho người quay.
Dòng đã "Đã quay"/"Không quay" không bị ghi đè. Gợi ý cũ không còn trong lần chạy mới thì ghi lý do, không xóa dòng.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import CAN_QUAY, NHAT_KY, Y_TUONG
from may_reels.kho import GOC, TZ_VN, thong_ke_dung_canh
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky

SKILL = "skills/may-reels/goi-y-quay.md"
LOAI_QUAY = ("NOI", "BROLL", "THAO")
XONG = ("Đã quay", "Không quay")
TRANG_THAI_KET_THUC = ("đã đăng", "bỏ", "đã làm")


def dau_vao(bang: BangNguon, kenh: str, *, goc: Path = GOC, ca_chua_duyet: bool = False) -> dict:
    import yaml
    from may_reels.dung.ke_hoach import doc_brand
    brand = doc_brand(kenh, goc)
    cd = {c["ma"]: c for c in brand.get("chu_de") or []}
    f = goc / "brand" / kenh / "san-xuat.yaml"
    sx = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.is_file() else {}
    chu_de = []
    for r in doc_dong(bang, Y_TUONG):
        if r.get("kenh") != kenh or r.get("ma") not in cd:
            continue
        duyet = chuan(r.get("duyet_chu_de"))
        if duyet == "Bỏ" or chuan(r.get("trang_thai_san_xuat")) in TRANG_THAI_KET_THUC or cd[r["ma"]].get("da_lam"):
            continue
        if duyet != "Làm" and not ca_chua_duyet:
            continue
        c = cd[r["ma"]]
        chu_de.append({"ma": c["ma"], "da_duyet": duyet == "Làm", "tru_cot": c.get("tru_cot"),
                       "dinh_dang": c.get("dinh_dang"), "chu_de": c.get("chu_de"), "y_chinh": c.get("y_chinh"),
                       "trang_thai_san_xuat": r.get("trang_thai_san_xuat")})
    tk = thong_ke_dung_canh(goc, kenh)
    kho = [{k: c.get(k) for k in ("ma", "loai", "loai_file", "mo_ta", "dia_diem", "co_canh", "the", "huong",
                                  "thoi_luong", "chat_luong", "dung_duoc", "ly_do_loai", "mat_nguoi", "rui_ro")}
           | {"so_lan_dung": (tk.get(c["ma"]) or {}).get("so_lan", 0), "rong": c.get("rong"), "cao": c.get("cao")}
           for c in brand.get("kho_canh") or []]
    mo = [{k: d.get(k) for k in ("ma_yeu_cau", "ma_chu_de", "ma_video", "y_can_canh", "mo_ta_canh", "goi_y_quay", "ly_do")}
          for d in doc_dong(bang, CAN_QUAY)
          if d.get("kenh") == kenh and ":goi-y:" not in d.get("ma_yeu_cau", "") and chuan(d.get("trang_thai_quay")) not in XONG]
    return {"kenh": kenh, "ngay_hom_nay": datetime.now(TZ_VN).date().isoformat(), "chu_de": chu_de,
            "thu_vien_dinh_dang": sx.get("khung_nhip") or {}, "khung_hinh": sx.get("khung_hinh") or {},
            "kho_canh": kho, "yeu_cau_dang_mo": mo,
            "quyen_hinh": {k: (brand.get("quyen_hinh") or {}).get(k) for k in ("da_dong_y", "pham_vi")},
            "quy_tac_kenh": (brand.get("cam") or {}).get("noi_dung_cam") or []}


def kiem(goi_y: dict, vao: dict) -> tuple[list[dict], list[str]]:
    """Trả về (danh sách cảnh đã phẳng hóa theo buổi, lỗi). Có lỗi thì không ghi gì lên Sheet."""
    loi, canh = [], []
    ma_cd = {c["ma"] for c in vao["chu_de"]}
    ma_yc = {d["ma_yeu_cau"] for d in vao["yeu_cau_dang_mo"]}
    da_thay = set()
    buoi = goi_y.get("buoi")
    if not isinstance(buoi, list) or not buoi:
        return [], ["thiếu danh sách buoi"]
    for b in buoi:
        ten = str(b.get("ten") or "").strip()
        if not ten:
            loi.append("buổi thiếu tên")
        for c in b.get("canh") or []:
            ma = str(c.get("ma") or "")
            nhan = f"{ten}/{ma}"
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", ma) or len(ma) > 40:
                loi.append(f"{nhan}: mã cảnh phải không dấu, nối gạch ngang, tối đa 40 ký tự")
            if ma in da_thay:
                loi.append(f"{nhan}: trùng mã cảnh")
            da_thay.add(ma)
            if c.get("loai") not in LOAI_QUAY:
                loi.append(f"{nhan}: loai phải thuộc {list(LOAI_QUAY)}")
            for k in ("mo_ta", "goc_may", "anh_sang", "tieng_on", "xin_phep"):
                if not str(c.get(k) or "").strip():
                    loi.append(f"{nhan}: thiếu {k}")
            if c.get("cam_doc") is not True and not str(c.get("ly_do_ngang") or "").strip():
                loi.append(f"{nhan}: cam_doc phải là true (quay ngang thì ghi ly_do_ngang)")
            tl = c.get("thoi_luong_giay")
            if not (isinstance(tl, list) and len(tl) == 2 and 0 < tl[0] <= tl[1] <= 120):
                loi.append(f"{nhan}: thoi_luong_giay phải là [tối thiểu, tối đa] giây")
            if c.get("loai") == "NOI" and not str(c.get("loi_thoai") or "").strip():
                loi.append(f"{nhan}: cảnh nói trước máy phải có loi_thoai")
            pv = c.get("phuc_vu_chu_de") or []
            gop = c.get("gop_yeu_cau") or []
            if not pv and not gop:
                loi.append(f"{nhan}: phải phục vụ ít nhất một chủ đề hoặc yêu cầu đang mở")
            if set(pv) - ma_cd:
                loi.append(f"{nhan}: chủ đề không có trong đầu vào: {sorted(set(pv) - ma_cd)}")
            if set(gop) - ma_yc:
                loi.append(f"{nhan}: yêu cầu không có trong đầu vào: {sorted(set(gop) - ma_yc)}")
            canh.append({**c, "_buoi": ten, "_thoi_diem": b.get("thoi_diem") or "", "_dia_diem": b.get("dia_diem") or ""})
    if not canh:
        loi.append("không có cảnh nào")
    return canh, loi


def _cau(s: str) -> str:
    """Bỏ dấu chấm cuối câu của agent để nối câu không ra hai dấu chấm."""
    return str(s).strip().rstrip(".").rstrip()


def _tl(c: dict) -> str:
    a, b = c["thoi_luong_giay"]
    return f"{a:g}" if a == b else f"{a:g}-{b:g}"


def dong_sheet(kenh: str, canh: list[dict], vao: dict, luc: str) -> list[dict]:
    ten_cd = {c["ma"]: c["chu_de"] for c in vao["chu_de"]}
    out = []
    for c in canh:
        pv = list(c.get("phuc_vu_chu_de") or [])
        out.append({
            "ma_yeu_cau": f"{kenh}:goi-y:{c['ma']}", "kenh": kenh, "ma_chu_de": ", ".join(pv), "ma_video": "",
            "y_can_canh": "Phục vụ: " + "; ".join(ten_cd.get(m, m) for m in pv) if pv else "Đáp ứng yêu cầu đang mở",
            "mo_ta_canh": c["mo_ta"],
            "goi_y_quay": ("Cầm dọc 9:16" if c.get("cam_doc") is True else f"Quay ngang: {c.get('ly_do_ngang')}")
                          + f"; {c['goc_may']}; {_tl(c)} giây",
            "ly_do": c.get("ly_do") or "Gợi ý quay (kho thieu)", "tao_luc": luc,
            "buoi": " | ".join(x for x in (c["_buoi"], c["_thoi_diem"]) if x), "loai_canh": c["loai"],
            "goc_may": c["goc_may"], "thoi_luong": _tl(c), "loi_thoai": c.get("loi_thoai") or "",
            "luu_y": f"Ánh sáng: {_cau(c['anh_sang'])}. Tiếng ồn: {_cau(c['tieng_on'])}", "xin_phep": c["xin_phep"],
            "gop_yeu_cau": ", ".join(c.get("gop_yeu_cau") or []), "uu_tien": str(c.get("uu_tien") or ""),
        })
    return out


def van_ban_zalo(kenh_ten: str, goi_y: dict, canh: list[dict], ngay: str) -> str:
    """Bản gọn để dán vào Zalo: không bảng, không markdown, mỗi cảnh vài dòng."""
    dong = [f"DANH SÁCH QUAY {kenh_ten.upper()} ({ngay})", "Cầm máy DỌC, 1080p 30 hình/giây, bấm quay trước 2 giây và "
            "dừng sau 2 giây. Quay xong chép file vào thư mục canh-quay/moi-quay.", ""]
    stt = 0
    for b in goi_y["buoi"]:
        ds = [c for c in canh if c["_buoi"] == b.get("ten")]
        if not ds:
            continue
        dong.append(f"== {b['ten']}" + (f" ({b['thoi_diem']})" if b.get("thoi_diem") else ""))
        for c in sorted(ds, key=lambda x: (x.get("uu_tien") or 9)):
            stt += 1
            dong.append(f"{stt}. [{c['loai']}] {c['mo_ta']}")
            dong.append(f"   Góc máy: {_cau(c['goc_may'])}. Dài {_tl(c)} giây"
                        + ("" if c.get("cam_doc") is True else f". Quay NGANG: {c.get('ly_do_ngang')}"))
            if c.get("loi_thoai"):
                dong.append(f"   Lời nói: \"{c['loi_thoai']}\"")
            dong.append(f"   Ánh sáng: {_cau(c['anh_sang'])}. Tiếng ồn: {_cau(c['tieng_on'])}")
            dong.append(f"   Xin phép: {c['xin_phep']}")
        dong.append("")
    if goi_y.get("ghi_chu_chung"):
        dong.append(f"Lưu ý chung: {goi_y['ghi_chu_chung']}")
    return "\n".join(dong).rstrip() + "\n"


def goi_agent_goi_y(prompt: str, *, du_an: Path, goc: Path) -> dict:
    from may_reels.san_xuat import goi_agent
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=("goi_y_quay.json",), web=False, giay=900,
                     he_thong=("Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi. Chỉ làm theo "
                               f"{SKILL}. Chỉ ghi đúng một file goi_y_quay.json trong thư mục được giao."))


def thieu(bang: BangNguon, kenh: str, *, goc: Path = GOC, ca_chua_duyet: bool = False, thu: bool = False,
          agent: Callable[..., dict] = goi_agent_goi_y, log: Callable[[str], None] = print) -> dict:
    t0 = time.monotonic()
    vao = dau_vao(bang, kenh, goc=goc, ca_chua_duyet=ca_chua_duyet)
    D = goc / "projects" / "_may_reels" / "kho" / kenh
    D.mkdir(parents=True, exist_ok=True)
    log(f"Chủ đề: {len(vao['chu_de'])} ({sum(c['da_duyet'] for c in vao['chu_de'])} đã duyệt) | kho {len(vao['kho_canh'])} "
        f"cảnh | yêu cầu đang mở {len(vao['yeu_cau_dang_mo'])}")
    kq = {"canh": [], "loi": [], "file_zalo": None, "giay_agent": 0.0}
    if not vao["chu_de"] and not vao["yeu_cau_dang_mo"]:
        log("Không có chủ đề đã duyệt hay yêu cầu nào đang mở. Thêm --ca-chua-duyet để gợi ý cho cả chủ đề chưa duyệt.")
        return kq
    (D / "goi_y_quay.yeu_cau.json").write_text(json.dumps(vao, ensure_ascii=False, indent=1), encoding="utf-8")
    f = D / "goi_y_quay.json"
    f.unlink(missing_ok=True)
    rel = D.relative_to(goc).as_posix()
    r = agent(f"Đọc và làm đúng theo {SKILL}. Đọc {rel}/goi_y_quay.yeu_cau.json rồi ghi {rel}/goi_y_quay.json.",
              du_an=D, goc=goc)
    kq["giay_agent"] = (r.get("duration_ms") or 0) / 1000
    if r.get("is_error") or not f.is_file():
        kq["loi"].append(f"agent lỗi: {str(r.get('result'))[:300]}")
        return kq
    goi_y = json.loads(f.read_text(encoding="utf-8"))
    canh, loi = kiem(goi_y, vao)
    if loi:
        kq["loi"] = loi
        log("Danh sách quay chưa đạt, không ghi Sheet:\n  - " + "\n  - ".join(loi))
        return kq
    kq["canh"] = canh
    luc = bay_gio_vn()
    ngay = vao["ngay_hom_nay"]
    from may_reels.dung.ke_hoach import doc_brand
    ten_kenh = ((doc_brand(kenh, goc).get("kenh") or {}).get("ten_kenh") or kenh)
    txt = van_ban_zalo(ten_kenh, goi_y, canh, ngay)
    fz = D / f"goi-y-quay-{ngay}.txt"
    kq["file_zalo"] = fz
    if thu:
        log(txt)
        return kq
    fz.write_text(txt, encoding="utf-8")
    hien = {d["ma_yeu_cau"]: d for d in doc_dong(bang, CAN_QUAY) if d.get("kenh") == kenh}
    moi = [d for d in dong_sheet(kenh, canh, vao, luc) if chuan((hien.get(d["ma_yeu_cau"]) or {}).get("trang_thai_quay")) not in XONG]
    ma_moi = {d["ma_yeu_cau"] for d in dong_sheet(kenh, canh, vao, luc)}
    cu = [{"ma_yeu_cau": m, "ly_do": f"Không còn trong gợi ý quay {ngay}"} for m, d in hien.items()
          if ":goi-y:" in m and m not in ma_moi and chuan(d.get("trang_thai_quay")) not in XONG
          and not (d.get("ly_do") or "").startswith("Không còn trong gợi ý")]
    if moi:
        ghi_theo_khoa(bang, CAN_QUAY, moi, chi_khi_trong={"tao_luc"})
    if cu:
        ghi_theo_khoa(bang, CAN_QUAY, cu)
    log(txt)
    log(f"Đã ghi {len(moi)} cảnh vào tab Cần quay; bản gửi Zalo: {fz}")
    try:
        them_nhat_ky(bang, NHAT_KY, [{
            "thoi_gian": luc, "kenh": kenh, "ma": "", "buoc": "kho_thieu", "che_do": "that", "ket_qua": "ok",
            "chi_tiet": f"{len(canh)} cảnh, {len(goi_y['buoi'])} buổi; {fz.name}"[:500], "chi_phi_vnd": "0",
            "thoi_gian_chay_giay": str(round(time.monotonic() - t0, 1)), "so_luot_tro_ly": "1"}])
    except Exception:  # pragma: no cover
        pass
    return kq

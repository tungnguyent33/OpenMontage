"""Viết lại canh-quay/_kho/KHO.md (bảng tóm tắt kho cảnh cho người đọc) sau mỗi lần `kho nap`.

Mục 1 (Tóm tắt) và mục 2 (Bảng cảnh) do Python sinh lại toàn bộ từ index.json, nhan.json và quyền hình
(cùng hàm doc_kho của tools_local/nap_kenh.py, nên "dùng được" khớp brand.json). Cột thêm so với bản của subagent
phan-loai-canh: "Đã dùng" (số video đã dựng xong dùng cảnh) và "Trạng thái" (dùng được / lý do chưa dùng).

Mục 3 (Độ phủ theo chủ đề) và mục 4 (Nên quay thêm) cần đánh giá của agent, Python không tự viết. Phần đó của
KHO.md cũ được giữ nguyên, kèm dòng ghi các cảnh nạp sau lần agent viết (chưa được tính). Danh sách quay theo chủ
đề đã duyệt thì lấy bằng `python -m may_reels kho thieu`.

Lần đầu ghi đè một KHO.md không do máy sinh (không có dấu MARKER), bản cũ được sao lưu thành KHO.md.bak-<giờ>.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

MARKER = "<!-- may-reels:kho-md"
TEN_DIA_DIEM = {"san-tap": "Sân tập", "phong-hoc": "Phòng học", "van-phong": "Văn phòng",
                "duong-thuc": "Đường thật", "khac": "Khác"}
TEN_NGUON = {"trung-tam": "trung tâm", "stock-trong-nuoc": "stock trong nước", "stock-nuoc-ngoai": "stock nước ngoài"}
TEN_CHAT_LUONG = {"tot": "tốt", "dung-duoc": "dùng được", "kem": "kém"}
TEN_DUNG_CHO = {"toan-man": "toàn màn", "chi-khung-anh": "chỉ khung ảnh"}
TEN_CO_CANH = {"trung-can": "trung-cận", "can": "cận", "chi-tiet": "chi tiết", "rong": "rộng", "trung": "trung"}
COT = ("Mã", "Loại", "Nguồn", "Kích thước", "Dùng cho", "Mô tả", "Địa điểm", "Cỡ cảnh", "Dùng được (giây)",
       "Chất lượng", "Rủi ro", "Đã dùng", "Trạng thái")


def _o(s) -> str:
    """Một ô bảng Markdown: một dòng, không có dấu | thô."""
    return re.sub(r"\s+", " ", str(s if s is not None else "")).replace("|", "/").strip()


def _so(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _ngan(s: str, n: int = 110) -> str:
    s = _o(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def _phut(giay: float) -> str:
    g = int(round(giay))
    return f"{g // 60} phút {g % 60:02d} giây"


def _doan(d: list) -> str:
    return "; ".join(f"{_so(a)}-{_so(b)}" for a, b in d) if d else ""


def _trang_thai(c: dict) -> str:
    if c["dung_duoc"]:
        return "dùng được"
    ly = c["ly_do_loai"]
    ngan = []
    for s in ly:
        if s.startswith("có mặt người, chờ xác nhận"):
            ngan.append("chờ xác nhận quyền hình")
        elif s.startswith("nhan.json: duoc_dung=false"):
            ly_do = s.split("(", 1)[1][:-1] if "(" in s else ""
            ngan.append("KHÔNG DÙNG" + (f" ({_ngan(ly_do, 80)})" if ly_do else ""))
        else:
            ngan.append(s)
    return "; ".join(ngan)


def dong_bang(c: dict, idx: dict, dung_cho_fn) -> str:
    rong, cao = c.get("rong"), c.get("cao")
    kich = f"{rong}x{cao}" if rong and cao else ""
    n = c.get("_nhan", {})
    dc = n.get("dung_cho") or dung_cho_fn(rong, cao)
    doan = "(ảnh)" if c.get("loai_file") == "anh" else _doan(c.get("doan_dung_duoc") or [])
    lan = idx.get("so_lan_dung") or 0
    da_dung = f"{lan} ({idx['ngay_dung_gan_nhat']})" if lan and idx.get("ngay_dung_gan_nhat") else str(lan)
    o = (c["ma"], c.get("loai") or "?", TEN_NGUON.get(c.get("nguon"), c.get("nguon") or ""), kich,
         TEN_DUNG_CHO.get(dc, dc), c.get("mo_ta") or "", c.get("dia_diem") or "",
         TEN_CO_CANH.get(c.get("co_canh"), c.get("co_canh") or ""), doan,
         TEN_CHAT_LUONG.get(c.get("chat_luong"), c.get("chat_luong") or ""),
         ", ".join(c.get("rui_ro") or []) or "không", da_dung, _trang_thai(c))
    return "| " + " | ".join(_o(x) for x in o) + " |"


def phan_agent(cu: str | None) -> tuple[str, str | None]:
    """Tách mục 3 trở đi của KHO.md cũ (phần agent viết). Trả về (văn bản, ngày agent viết nếu biết)."""
    if not cu:
        return "", None
    m = re.search(r"^## 3\..*", cu, flags=re.M | re.S)
    if not m:
        return "", None
    van = m.group(0)
    # Bỏ ghi chú máy đã chèn ở lần trước (sẽ chèn lại cho đúng).
    van = re.sub(r"^> \*\*Máy ghi chú:\*\*.*?(?:\n(?!>).*)?$\n?", "", van, count=1, flags=re.M)
    ngay = None
    mk = re.search(r"may-reels:kho-md[^>]*agent_viet=(\S+)", cu)
    if mk:
        ngay = mk.group(1)
    return van.rstrip() + "\n", ngay


def viet(*, ten_kenh: str, kho: list[dict], index: dict, nhan: dict, cu: str | None, bay_gio: str,
         dung_cho_fn) -> str:
    theo_ma = {m["ma"]: m for m in index.values()}
    for c in kho:
        c["_nhan"] = nhan.get(c["ma"], {})
    video = [c for c in kho if c.get("loai_file") == "video"]
    anh = [c for c in kho if c.get("loai_file") == "anh"]
    tong_giay = sum(c.get("thoi_luong") or 0 for c in video)
    dem = lambda ds, k: {v: sum(1 for c in ds if (c.get(k) or "?") == v) for v in sorted({c.get(k) or "?" for c in ds})}
    loai = dem(kho, "loai")
    nguon = dem(kho, "nguon")
    dung = [c for c in kho if c["dung_duoc"]]
    khong = [c for c in kho if c["_nhan"].get("duoc_dung") is False]
    cho_quyen = [c for c in kho if any(s.startswith("có mặt người, chờ xác nhận") for s in c["ly_do_loai"])]
    chua_nhan = [c for c in kho if not c["_nhan"]]
    thap = [c for c in video if min(c.get("rong") or 0, c.get("cao") or 0) < 1080]
    da_dung = sorted((c for c in kho if (theo_ma.get(c["ma"], {}).get("so_lan_dung") or 0) > 0),
                     key=lambda c: -theo_ma[c["ma"]]["so_lan_dung"])
    nap_moi = sorted((m for m in index.values() if m.get("nap_boi") == "kho-nap"),
                     key=lambda m: m.get("nap_luc") or m.get("ngay_nap") or "")

    agent, ngay_agent = phan_agent(cu)
    if cu and not ngay_agent and MARKER not in cu:
        ngay_agent = "?"  # KHO.md của subagent: không biết ngày, coi mọi cảnh kho-nap là chưa được tính
    ds_chua_tinh = [m["ma"] for m in nap_moi
                    if ngay_agent and (ngay_agent == "?" or (m.get("nap_luc") or m.get("ngay_nap") or "") > ngay_agent)]

    L = [f"{MARKER} sinh_luc={bay_gio} agent_viet={ngay_agent or ''} -->",
         f"# Kho cảnh quay kênh {ten_kenh}",
         "",
         f"Mục 1 và 2 do `python -m may_reels kho nap` sinh lại lúc {bay_gio} từ `index.json`, `nhan.json` và quyền "
         "hình (khớp `kho_canh` trong brand.json). Sửa nhãn thì sửa `nhan.json`, không sửa bảng này.",
         "",
         "## 1. Tóm tắt",
         "",
         f"- Tổng {len(kho)} file: {len(video)} video (tổng khoảng {_phut(tong_giay)}) và {len(anh)} ảnh "
         f"({sum(1 for c in anh if c.get('huong') == 'doc')} dọc, {sum(1 for c in anh if c.get('huong') == 'ngang')} "
         "ngang).",
         "- Theo loại: " + ", ".join(f"{v} {k}" for k, v in loai.items()) + "."
         + ("" if loai.get("NOI") else " Chưa có cảnh NOI (người nói trước máy)."),
         "- Theo nguồn: " + ", ".join(f"{v} {TEN_NGUON.get(k, k)}" for k, v in nguon.items()) + ".",
         f"- Dùng được ngay: {len(dung)}/{len(kho)}.",
         ]
    if khong:
        L.append(f"- Không được dùng ({len(khong)}): " + "; ".join(
            f"`{c['ma']}` ({_ngan(c['_nhan'].get('can_xu_ly') or 'duoc_dung=false')})" for c in khong) + ".")
    if cho_quyen:
        L.append(f"- Chờ xác nhận quyền hình ở tab Quyền hình ({len(cho_quyen)}): "
                 + ", ".join(f"`{c['ma']}`" for c in cho_quyen) + ".")
    khac = [c for c in kho if not c["dung_duoc"] and c not in khong and c not in cho_quyen and c not in chua_nhan]
    if khac:
        L.append(f"- Chưa dùng được vì lý do khác ({len(khac)}): " + "; ".join(
            f"`{c['ma']}` ({_ngan('; '.join(c['ly_do_loai']), 80)})" for c in khac) + ".")
    if chua_nhan:
        L.append(f"- Chưa có nhãn ({len(chua_nhan)}): " + ", ".join(f"`{c['ma']}`" for c in chua_nhan) + ".")
    if thap:
        L.append(f"- Video dưới 1080p ({len(thap)}/{len(video)}): "
                 + ", ".join(f"`{c['ma']}` {c.get('rong')}x{c.get('cao')}" for c in thap) + ".")
    if da_dung:
        L.append(f"- Đã dùng trong video dựng xong: {len(da_dung)}/{len(kho)} cảnh; nhiều nhất "
                 + ", ".join(f"`{c['ma']}` {theo_ma[c['ma']]['so_lan_dung']} lần" for c in da_dung[:3]) + ".")
    else:
        L.append("- Chưa cảnh nào được dùng trong video dựng xong.")
    if nap_moi:
        L.append(f"- Nạp bằng `kho nap` ({len(nap_moi)}): " + ", ".join(
            f"`{m['ma']}` ({m.get('ngay_nap') or '?'})" for m in nap_moi[-10:])
                 + (f" và {len(nap_moi) - 10} cảnh khác" if len(nap_moi) > 10 else "") + ".")

    L += ["", "## 2. Bảng cảnh (nhóm theo địa điểm)", ""]
    nhom: dict[str, list[dict]] = {}
    for c in kho:
        nhom.setdefault(c.get("dia_diem") or "khac", []).append(c)
    thu_tu = [k for k in TEN_DIA_DIEM if k in nhom] + sorted(k for k in nhom if k not in TEN_DIA_DIEM)
    for k in thu_tu:
        L += [f"### {TEN_DIA_DIEM.get(k, k)}", "", "| " + " | ".join(COT) + " |",
              "|" + "---|" * len(COT)]
        for c in sorted(nhom[k], key=lambda c: (c.get("loai") or "", c["ma"])):
            L.append(dong_bang(c, theo_ma.get(c["ma"], {}), dung_cho_fn))
        L.append("")

    if agent:
        if ds_chua_tinh:
            L.append(f"> **Máy ghi chú:** mục 3 và 4 do agent viết"
                     + (f" ({ngay_agent})" if ngay_agent and ngay_agent != "?" else "")
                     + f", chưa tính {len(ds_chua_tinh)} cảnh nạp sau đó: "
                     + ", ".join(f"`{m}`" for m in ds_chua_tinh) + ". Danh sách quay cho chủ đề đã duyệt: "
                     "`python -m may_reels kho thieu`.")
            L.append("")
        L.append(agent.rstrip())
    else:
        L += ["## 3. Độ phủ theo chủ đề và cảnh nên quay", "",
              "Chưa có đánh giá của agent. Chạy `python -m may_reels kho thieu --kenh <mã>` để đối chiếu chủ đề đã "
              "duyệt với kho và ghi danh sách quay vào tab Cần quay."]
    return "\n".join(L).rstrip() + "\n"


def cap_nhat(kenh: str, thu_muc_kenh: Path, goc: Path, index: dict, nhan: dict, *, bay_gio: str,
             dung_cho_fn) -> Path:
    """Ghi lại KHO.md cho kênh. Trả về đường dẫn file đã ghi."""
    import yaml
    from tools_local.nap_kenh import doc_kho

    ch_f = thu_muc_kenh / "channel.yaml"
    ch = (yaml.safe_load(ch_f.read_text(encoding="utf-8")) or {}) if ch_f.is_file() else {}
    qt_f = goc / "brand" / kenh / "quy-tac-rieng.yaml"
    qt = (yaml.safe_load(qt_f.read_text(encoding="utf-8")) or {}) if qt_f.is_file() else {}
    kho = doc_kho(thu_muc_kenh, index, nhan, ch.get("quyen_hinh") or {}, qt.get("nguon_canh_khong_dung") or {})
    f = thu_muc_kenh / "canh-quay" / "_kho" / "KHO.md"
    cu = f.read_text(encoding="utf-8") if f.is_file() else None
    moi = viet(ten_kenh=ch.get("ten_kenh") or kenh, kho=kho, index=index, nhan=nhan, cu=cu, bay_gio=bay_gio,
               dung_cho_fn=dung_cho_fn)
    if cu is not None and MARKER not in cu:
        f.with_name(f"KHO.md.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}").write_text(cu, encoding="utf-8")
    tam = f.with_name("KHO.md.dang-ghi")
    tam.write_text(moi, encoding="utf-8")
    os.replace(tam, f)
    return f

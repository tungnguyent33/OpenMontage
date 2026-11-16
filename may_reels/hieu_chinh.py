"""Chấm lại và hiệu chỉnh rubric theo người duyệt.

    python -m may_reels cham-lai --kenh <mã>     chấm lại mọi video của kênh đang có trong Hàng chờ (không dựng lại),
                                                 cập nhật diem_qa và canh_bao (cột của máy), ghi Nhật ký từng video.
    python -m may_reels hieu-chinh --kenh <mã>   so điểm máy với diem_cua_toi (cột của người, 1-10), đọc nhan_xet,
                                                 chỉ ra tiêu chí lệch nhiều nhất và ĐỀ XUẤT sửa rubric.yaml.
                                                 Chỉ đề xuất: không sửa file nào ngoài bản báo cáo
                                                 projects/_may_reels/hieu-chinh/<kenh>-<ngày>.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import HANG_CHO
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa

GOC = Path(__file__).resolve().parent.parent
TIEN_TO_CU = ("Dưới ngưỡng", "Nhiều cảnh tạm", "CHẶN", "Điểm QA", "Trần tổng")


def _nhom(bang: BangNguon, kenh: str) -> dict[str, list[dict]]:
    nhom: dict[str, list[dict]] = {}
    for d in doc_dong(bang, HANG_CHO):
        if d.get("kenh") == kenh and d.get("ma_video"):
            nhom.setdefault(d["ma_video"], []).append(d)
    return nhom


def _canh_bao_cu(dong: list[dict]) -> list[str]:
    """canh_bao đang có trên Sheet, bỏ các dòng do lần chấm trước sinh ra (để không chồng lên nhau)."""
    ra = []
    for d in dong:
        for x in re.split(r"\n|; ", d.get("canh_bao") or ""):
            x = x.strip()
            if x and not x.startswith(TIEN_TO_CU) and not re.match(r"^.+ -[\d.]+: ", x) and x not in ra:
                ra.append(x)
    return ra


def cham_lai(bang: BangNguon, kenh: str, *, goc: Path = GOC, cham: Callable | None = None,
             log: Callable[[str], None] = print) -> list[dict]:
    from may_reels.dung.ke_hoach import doc_san_xuat
    from may_reels.hang_cho import cau_hinh_canh_bao, gon_canh_bao
    from may_reels.san_xuat import canh_bao_duoi_nguong, cham_mac_dinh, nhat_ky_cham
    cham = cham or cham_mac_dinh
    nguong = int((doc_san_xuat(kenh, goc).get("cham_diem") or {}).get("nguong", 75))
    cbc = cau_hinh_canh_bao(kenh, goc)
    ket = []
    for ma, dong in sorted(_nhom(bang, kenh).items()):
        P = goc / "projects" / ma
        if not (P / "ke_hoach.json").is_file() or not (P / "renders" / "final.mp4").is_file():
            log(f"{ma}: bỏ qua (không do máy sản xuất hoặc thiếu renders/final.mp4)")
            ket.append({"ma_video": ma, "trang_thai": "bo_qua"})
            continue
        try:
            kc = cham(ma, goc=goc, log=log)
        except Exception as e:
            log(f"{ma}: lỗi chấm: {type(e).__name__}: {e}")
            ket.append({"ma_video": ma, "trang_thai": "loi", "loi": str(e)[:300]})
            continue
        nhat_ky_cham(bang, kenh, ma, kc, buoc="cham_lai")
        if kc.chan:
            cb = ["CHẶN: " + x for x in kc.chan]
        else:
            cb = (canh_bao_duoi_nguong(kc, nguong) if kc.diem_qa < nguong else []) + list(kc.canh_bao)
        cb = gon_canh_bao(cb + _canh_bao_cu(dong), int(cbc.get("so_dong", 3)), int(cbc.get("ky_tu_moi_dong", 90)))
        cu = {d.get("diem_qa") for d in dong}
        def _loi(d: dict) -> dict:
            if kc.chan:
                return {"loi": ("Chặn cứng: " + "; ".join(kc.chan))[:500]}
            # Hết bị chặn: xóa thông báo chặn cũ, giữ nguyên lỗi khác (vd. lỗi sửa/đăng).
            return {"loi": ""} if (d.get("loi") or "").startswith("Chặn cứng:") else {}
        ghi = [{"ma_video": ma, "nen_tang": d["nen_tang"], "diem_qa": "" if kc.diem_qa is None else str(kc.diem_qa),
                "canh_bao": "\n".join(cb)} | _loi(d) for d in dong]
        ghi_theo_khoa(bang, HANG_CHO, ghi)
        log(f"{ma}: QA {', '.join(sorted(x for x in cu if x)) or '-'} -> {kc.diem_qa}"
            + (f" | CHẶN: {'; '.join(kc.chan)}" if kc.chan else ""))
        ket.append({"ma_video": ma, "trang_thai": "ok", "diem_cu": sorted(x for x in cu if x), "diem_qa": kc.diem_qa,
                    "chan": kc.chan, "tieu_chi": kc.tieu_chi})
    return ket


# ---------------------------------------------------------------- hiệu chỉnh
def _diem_nguoi(dong: list[dict]) -> float | None:
    ds = []
    for d in dong:
        m = re.search(r"\d+(?:[.,]\d+)?", d.get("diem_cua_toi") or "")
        if m:
            v = float(m.group(0).replace(",", "."))
            if 1 <= v <= 10:
                ds.append(v)
    return round(sum(ds) / len(ds), 2) if ds else None


def phan_tich(mau: list[dict], rb: dict) -> dict:
    """mau: [{ma_video, may (0-100), nguoi (1-10), tieu_chi: [{ma, diem, toi_da}], nhan_xet}].
    Lệch của tiêu chí = trung bình (điểm tiêu chí quy về thang 10 - điểm người). Dương = máy chấm cao hơn người."""
    from may_reels.cham_diem import bo_dau
    co = [m for m in mau if m.get("nguoi") is not None and m.get("may") is not None]
    if not co:
        return {"n": 0}
    lech_tong = [m["may"] / 10 - m["nguoi"] for m in co]
    tc: dict[str, list[float]] = {}
    for m in co:
        for x in m.get("tieu_chi") or []:
            if x.get("toi_da"):
                tc.setdefault(x["ma"], []).append(x["diem"] / x["toi_da"] * 10 - m["nguoi"])
    lech_tc = {k: {"tb": round(sum(v) / len(v), 2), "tb_tuyet_doi": round(sum(abs(y) for y in v) / len(v), 2), "n": len(v)}
               for k, v in tc.items()}
    nhac = {}
    for k, tu in (rb.get("tu_khoa_nhan_xet") or {}).items():
        dem = sum(1 for m in co for t in tu if bo_dau(t) in bo_dau(m.get("nhan_xet") or ""))
        if dem:
            nhac[k] = dem
    return {"n": len(co), "lech_tb": round(sum(lech_tong) / len(co), 2),
            "lech_tb_tuyet_doi": round(sum(abs(x) for x in lech_tong) / len(co), 2),
            "lech_tieu_chi": dict(sorted(lech_tc.items(), key=lambda kv: -kv[1]["tb_tuyet_doi"])), "nhac_trong_nhan_xet": nhac}


def de_xuat(pt: dict, rb: dict, nguong: int) -> list[str]:
    if not pt.get("n"):
        return ["Chưa có dòng nào có diem_cua_toi: chưa đề xuất được."]
    tc = rb.get("tieu_chi") or {}
    ra = []
    if pt["n"] < 5:
        ra.append(f"Mới có {pt['n']} video có điểm của bạn: các đề xuất dưới đây chỉ để tham khảo, nên chờ đủ 5-10 video.")
    lt = pt["lech_tb"]
    if lt >= 1.0:
        ra.append(f"Máy chấm CAO hơn bạn trung bình {lt * 10:.0f} điểm/100. Cân nhắc nâng san-xuat.yaml "
                  f"cham_diem.nguong từ {nguong} lên {min(95, nguong + round(lt * 10 / 2))}, hoặc siết tiêu chí bên dưới.")
    elif lt <= -1.0:
        ra.append(f"Máy chấm THẤP hơn bạn trung bình {-lt * 10:.0f} điểm/100. Cân nhắc hạ cham_diem.nguong từ {nguong} "
                  f"xuống {max(50, nguong + round(lt * 10 / 2))}, hoặc nới trần ở tiêu chí bên dưới.")
    else:
        ra.append(f"Điểm tổng của máy khớp bạn (lệch trung bình {lt * 10:+.0f}/100): giữ ngưỡng.")
    ltc = pt["lech_tieu_chi"]
    if ltc:
        ma, v = next(iter(ltc.items()))
        ten, ts = (tc.get(ma) or {}).get("ten", ma), (tc.get(ma) or {}).get("trong_so")
        huong = "cao hơn" if v["tb"] > 0 else "thấp hơn"
        ra.append(f"Lệch nhiều nhất: '{ten}' (máy {huong} bạn {abs(v['tb']):.1f}/10 trung bình, trên {v['n']} video).")
        nhac = pt.get("nhac_trong_nhan_xet") or {}
        dich = next((k for k in sorted(nhac, key=lambda k: -nhac[k]) if k != ma and k in tc), None)
        if v["tb"] > 0 and ts:
            bot = min(5, int(ts) // 2) or 1
            ra.append(f"Đề xuất: giảm tieu_chi.{ma}.trong_so {ts} -> {int(ts) - bot}"
                      + (f" và cộng {bot} vào tieu_chi.{dich}.trong_so (nhận xét của bạn nhắc '{dich}' {nhac[dich]} lần)."
                         if dich else f"; chuyển {bot} điểm sang tiêu chí bạn hay phàn nàn nhất (chưa thấy trong nhan_xet)."))
            if (tc.get(ma) or {}).get("nguon") == "agent":
                ra.append(f"Hoặc siết hướng dẫn chấm '{ma}' trong skills/may-reels/cham-diem.md (agent đang dễ dãi).")
        elif v["tb"] < 0:
            ra.append(f"Đề xuất: xem lại trần của tieu_chi.{ma} trong rubric.yaml (máy đang trừ nặng hơn bạn cảm nhận).")
    for k, dem in sorted((pt.get("nhac_trong_nhan_xet") or {}).items(), key=lambda kv: -kv[1])[:3]:
        ra.append(f"nhan_xet nhắc '{(tc.get(k) or {}).get('ten', k)}' {dem} lần.")
    return ra


def hieu_chinh(bang: BangNguon, kenh: str, *, goc: Path = GOC, log: Callable[[str], None] = print) -> dict:
    from may_reels.cham_diem import doc_rubric
    from may_reels.dung.ke_hoach import doc_san_xuat
    rb = doc_rubric(kenh, goc)
    nguong = int((doc_san_xuat(kenh, goc).get("cham_diem") or {}).get("nguong", 75))
    mau = []
    for ma, dong in sorted(_nhom(bang, kenh).items()):
        sc_f = goc / "projects" / ma / "renders" / "score.json"
        sc = json.loads(sc_f.read_text(encoding="utf-8")) if sc_f.is_file() else {}
        try:
            may = sc.get("diem_qa") if sc else float(next(d["diem_qa"] for d in dong if d.get("diem_qa")))
        except (StopIteration, ValueError):
            may = None
        mau.append({"ma_video": ma, "may": may, "nguoi": _diem_nguoi(dong), "tieu_chi": sc.get("tieu_chi") or [],
                    "nhan_xet": " | ".join(x for x in {(d.get("nhan_xet") or "").strip() for d in dong} if x)})
    pt = phan_tich(mau, rb)
    dx = de_xuat(pt, rb, nguong)
    ma_tc = list((rb.get("tieu_chi") or {}).keys())
    tieu_de = ["Video", "Máy", "Bạn×10", "Lệch"] + [(rb["tieu_chi"][k].get("ten") or k)[:12] for k in ma_tc]
    dong_bang = []
    for m in mau:
        tcm = {x["ma"]: x for x in m["tieu_chi"]}
        lech = (f"{m['may'] - m['nguoi'] * 10:+.0f}" if m["may"] is not None and m["nguoi"] is not None else "")
        dong_bang.append([m["ma_video"], "" if m["may"] is None else f"{m['may']:g}",
                          "" if m["nguoi"] is None else f"{m['nguoi'] * 10:g}", lech]
                         + [f"{tcm[k]['diem']:g}/{tcm[k]['toi_da']:g}" if k in tcm else "" for k in ma_tc])
    md = [f"# Hiệu chỉnh rubric kênh {kenh} ({bay_gio_vn()})", "",
          "| " + " | ".join(tieu_de) + " |", "|" + "---|" * len(tieu_de)]
    md += ["| " + " | ".join(r) + " |" for r in dong_bang]
    md += ["", "## Nhận xét của bạn", ""] + [f"- {m['ma_video']}: {m['nhan_xet']}" for m in mau if m["nhan_xet"]]
    md += ["", "## Lệch theo tiêu chí (thang 10, dương = máy cao hơn bạn)", ""]
    md += [f"- {(rb['tieu_chi'].get(k) or {}).get('ten', k)}: {v['tb']:+.1f} (tuyệt đối {v['tb_tuyet_doi']:.1f}, n={v['n']})"
           for k, v in (pt.get("lech_tieu_chi") or {}).items()]
    md += ["", "## Đề xuất (KHÔNG tự sửa rubric.yaml)", ""] + [f"- {x}" for x in dx]
    ra = goc / "projects" / "_may_reels" / "hieu-chinh" / f"{kenh}-{bay_gio_vn()[:10]}.md"
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text("\n".join(md) + "\n", encoding="utf-8")
    for x in md:
        log(x)
    log(f"\n(Đã lưu {ra.relative_to(goc).as_posix()})")
    return {"mau": mau, "phan_tich": pt, "de_xuat": dx, "bao_cao": ra}

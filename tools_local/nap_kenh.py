#!/usr/bin/env python3
"""Nạp dữ liệu kênh (chỉ đọc) -> brand/<id>/brand.json + brand/<id>/assets/.

Mỗi kênh một thư mục riêng, không dùng chung file nào với kênh khác:
    brand/<id>/brand.json          (sinh tự động, đừng sửa tay)
    brand/<id>/quy-tac-rieng.yaml  (sửa tay; script chỉ đọc, không ghi đè)
    brand/<id>/assets/             (logo + fonts chép từ thư mục kênh)

Dùng:
    python tools_local/nap_kenh.py "<thư mục kênh>" [--out brand] [--id <mã>]

Tất định: không gọi LLM, không ghi thời điểm chạy, khóa JSON sắp xếp cố định.
Thư mục kênh chỉ được đọc; mọi file ghi ra nằm trong dự án này.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

FILE_CAN_DOC = [
    "channel.yaml",
    "context/business.md",
    "context/brand-style.md",
    "context/icp.md",
    "context/voice-analysis.md",
    "banned.md",
    "chu-de.md",
    "logo.png",
    "logo-emblem.png",
    "image",
    "canh-quay/_kho/index.json",
    "canh-quay/_kho/nhan.json",
    "canh-quay/_kho/KHO.md",
    "mau/TONG-HOP.md",
]

FONT_CAN = ["BeVietnamPro-ExtraBold.ttf", "BeVietnamPro-Bold.ttf"]
ANH_DUOI = {".jpg", ".jpeg", ".png", ".webp"}
TZ_VN = timezone(timedelta(hours=7))


def doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


def so(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def chuan_url(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.rstrip("/")


# ---------- banned.md ----------
def doc_banned(text: str) -> dict:
    muc = None
    sub = "cau_sao_cho_duyet"
    out = {"cum_tu_cam": [], "noi_dung_cam": [], "cau_sao_da_chot": [], "cau_sao_cho_duyet": []}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            t = s[3:].lower()
            muc = "cum_tu_cam" if "cụm từ cấm" in t else "noi_dung_cam" if "nội dung cấm" in t else "cau_sao" if "câu sáo" in t else None
            continue
        if muc == "cau_sao" and not s.startswith("- "):
            if s.startswith("Đã chốt"):
                sub = "cau_sao_da_chot"
            elif s.startswith("Đề xuất"):
                sub = "cau_sao_cho_duyet"
            continue
        if not s.startswith("- ") or muc is None:
            continue
        item = s[2:].strip()
        if muc == "cum_tu_cam":
            item = re.sub(r"\s*\(.*?\)\s*$", "", item)
            out["cum_tu_cam"] += [x.strip() for x in item.split(",") if x.strip()]
        elif muc == "noi_dung_cam":
            out["noi_dung_cam"].append(item)
        elif muc == "cau_sao":
            out[sub] += [x.strip() for x in item.split(",") if x.strip()]
    return out


# ---------- chu-de.md ----------
def doc_chu_de(text: str, thu_muc_videos: Path | None) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Mã"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        rows.append(dict(zip(["ma", "tru_cot", "dinh_dang", "chu_de", "y_chinh", "nguon_doi_chieu", "trend"], cells)))
    da_lam = {}
    if thu_muc_videos and thu_muc_videos.is_dir():
        for d in sorted(thu_muc_videos.iterdir()):
            m = re.match(r"^vx-\d+[a-z]?-(.+)$", d.name)
            if d.is_dir() and m:
                ma = re.sub(r"-thu$", "", m.group(1))
                da_lam.setdefault(ma, []).append(d.name)
    for r in rows:
        r["da_lam"] = r["ma"] in da_lam
        r["thu_muc_da_lam"] = da_lam.get(r["ma"], [])
    return rows


# ---------- business.md vs channel.yaml ----------
def tim_dong(text: str, nhan: str) -> str | None:
    m = re.search(rf"^- {re.escape(nhan)}:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def so_sanh(ch: dict, biz: str, cum_cam: list[str] = ()) -> list[dict]:
    kq = []

    def them(truong, yaml_v, biz_v, kieu, ghi_chu):
        kq.append({"truong": truong, "channel_yaml": yaml_v, "business_md": biz_v, "kieu": kieu, "ghi_chu": ghi_chu})

    v = tim_dong(biz, "Hotline")
    if v is not None:
        if so(v) != so(ch.get("hotline")):
            them("hotline", ch.get("hotline"), v, "khac_noi_dung", "Số khác nhau")
        elif v != ch.get("hotline"):
            them("hotline", ch.get("hotline"), v, "khac_cach_viet", "Cùng số, khác cách viết; dùng bản channel.yaml")
    v = tim_dong(biz, "Zalo OA")
    if v is not None and chuan_url(v) != chuan_url(ch.get("zalo_oa")):
        them("zalo_oa", ch.get("zalo_oa"), v, "khac_noi_dung", "Link Zalo khác nhau")
    v = tim_dong(biz, "Fanpage")
    if v is not None:
        if chuan_url(v) != chuan_url(ch.get("fanpage")):
            them("fanpage", ch.get("fanpage"), v, "khac_noi_dung", "Fanpage khác nhau")
        elif v != ch.get("fanpage"):
            them("fanpage", ch.get("fanpage"), v, "khac_cach_viet", "Cùng trang, khác cách viết (https/www)")
    v = tim_dong(biz, "Địa chỉ")
    if v is not None and v != ch.get("dia_chi"):
        them("dia_chi", ch.get("dia_chi"), v, "khac_cach_viet" if v.startswith(ch.get("dia_chi", "")) else "khac_noi_dung",
             "business.md thêm phần chú thích" if v.startswith(ch.get("dia_chi", "")) else "Địa chỉ khác nhau")
    v = tim_dong(biz, "Tên đầy đủ")
    if v is not None and v != ch.get("ten_day_du"):
        them("ten_day_du", ch.get("ten_day_du"), v, "khac_noi_dung",
             "business.md ghi 'Tên đầy đủ' bằng tên kênh (ten_kenh), không phải ten_day_du")
    # Số điện thoại có trong business.md mà channel.yaml không có
    yaml_so = {so(ch.get("hotline")), so(ch.get("zalo"))}
    for m in sorted(set(re.findall(r"0\d{2,3}[ .]?\d{3}[ .]?\d{3,4}", biz))):
        if so(m) not in yaml_so:
            them("so_dien_thoai_phu", None, m, "chi_co_trong_business",
                 "Số chưa có trong channel.yaml: không dùng tới khi người dùng xác nhận")
    # Website chỉ có trong business.md
    v = tim_dong(biz, "Website")
    if v and "website" not in ch:
        them("website", None, v, "chi_co_trong_business", "channel.yaml không có website: không chèn vào video")
    # Số liệu business.md bị quy tắc dự án cấm
    for dong in biz.splitlines():
        trung = next((c for c in cum_cam if c and c.lower() in dong.lower()), None)
        if trung:
            them("so_lieu", None, dong.strip("- ").strip(), "bi_cam",
                 f"Quy tắc dự án cấm '{trung}': không dùng")
        elif re.search(r"học viên đã đào tạo|hoạt động từ", dong, re.I):
            them("so_lieu", None, dong.strip("- ").strip(), "chua_co_nguon",
                 "Số liệu chỉ có trong business.md, chưa có nguồn mở được: không dùng trong demo")
    return kq


# ---------- kho cảnh ----------
def ngay_nap(dau: str) -> str | None:
    try:
        ts = int(str(dau).split("-")[-1])
        return datetime.fromtimestamp(ts, TZ_VN).date().isoformat()
    except (ValueError, OSError):
        return None


def doc_kho(kenh: Path, index: dict, nhan: dict, qh: dict, nguon_cam: dict | None = None) -> list[dict]:
    nguon_cam = nguon_cam or {}
    ngoai_tru = set(qh.get("ngoai_tru") or [])
    bo_sung = {b["ma"]: b for b in (qh.get("bo_sung") or [])}
    han = str(qh.get("ngay") or "")
    out = []
    for rel, meta in sorted(index.items(), key=lambda kv: kv[1]["ma"]):
        ma = meta["ma"]
        n = nhan.get(ma, {})
        p = kenh / rel
        nn = ngay_nap(meta.get("dau", ""))
        ly_do = []
        if not n:
            ly_do.append("chưa gắn nhãn trong nhan.json")
        if n and not n.get("duoc_dung", False):
            ly_do.append("nhan.json: duoc_dung=false (" + (n.get("can_xu_ly") or "") + ")")
        if ma in ngoai_tru:
            ly_do.append("quyen_hinh.ngoai_tru")
        if n.get("nguon") in nguon_cam:
            ly_do.append(f"{nguon_cam[n['nguon']]}: yêu cầu dự án không dùng")
        trong_pham_vi = bool(qh.get("da_dong_y")) and ((nn is not None and nn <= han) or ma in bo_sung)
        if not trong_pham_vi:
            ly_do.append(f"ngoài phạm vi quyen_hinh (nạp {nn}, hạn {han})")
        if not p.exists():
            ly_do.append("file không tồn tại")
        out.append({
            "ma": ma,
            "duong_dan": str(p),
            "file_tuong_doi": rel,
            "ton_tai": p.exists(),
            "loai_file": meta.get("loai_file"),
            "rong": meta.get("rong"), "cao": meta.get("cao"), "huong": meta.get("huong"),
            "fps": meta.get("fps"), "thoi_luong": meta.get("thoi_luong"),
            "co_am_thanh": meta.get("co_am_thanh"),
            "ngay_nap": nn,
            "loai": n.get("loai"), "mo_ta": n.get("mo_ta"), "dia_diem": n.get("dia_diem"),
            "co_canh": n.get("co_canh"), "the": n.get("the", []),
            "doan_dung_duoc": n.get("doan_dung_duoc", []),
            "chat_luong": n.get("chat_luong"), "rui_ro": n.get("rui_ro", []),
            "can_xu_ly": n.get("can_xu_ly"), "ghi_chu": n.get("ghi_chu"),
            "nguon": n.get("nguon"), "mat_nguoi": n.get("mat_nguoi"),
            "quyen_bo_sung": bo_sung.get(ma, {}).get("ghi_chu"),
            "dung_duoc": not ly_do,
            "ly_do_loai": ly_do,
        })
    return out


# ---------- font ----------
def tim_font(ten: str) -> Path | None:
    cho = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path.home() / ".fonts", Path("/usr/share/fonts"), Path.home() / "Library/Fonts",
    ]
    for d in cho:
        p = d / ten
        if p.is_file():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kenh")
    ap.add_argument("--out", default=str(ROOT / "brand"), help="thư mục gốc chứa các kênh")
    ap.add_argument("--id", help="mã kênh (mặc định: id trong channel.yaml, rồi tên thư mục kênh)")
    a = ap.parse_args()
    kenh = Path(a.kenh).resolve()
    if not kenh.is_dir():
        print(f"LỖI: không thấy thư mục kênh {kenh}", file=sys.stderr)
        return 2

    thieu = [f for f in FILE_CAN_DOC if not (kenh / f).exists()]
    ch = yaml.safe_load(doc(kenh / "channel.yaml")) if (kenh / "channel.yaml").exists() else {}
    ma = a.id or ch.get("id") or kenh.name
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", ma):
        print(f"LỖI: mã kênh {ma!r} chỉ được gồm chữ thường không dấu, số, '-' hoặc '_'.", file=sys.stderr)
        return 2
    out = Path(a.out).resolve() / ma
    if out == kenh or kenh in out.parents or out in kenh.parents:
        print("LỖI: thư mục ra trùng/lồng với thư mục kênh (chỉ đọc).", file=sys.stderr)
        return 2
    (out / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    ctx = {}
    for k in ["business", "brand-style", "icp", "voice-analysis"]:
        p = kenh / "context" / f"{k}.md"
        ctx[k] = {"duong_dan": str(p), "noi_dung": doc(p)} if p.exists() else None
    biz = (ctx["business"] or {}).get("noi_dung", "")

    banned = doc_banned(doc(kenh / "banned.md")) if (kenh / "banned.md").exists() else {}
    # Quy tắc riêng của kênh này do người dùng bổ sung (sửa tay trong brand/<id>/quy-tac-rieng.yaml)
    qt_file = out / "quy-tac-rieng.yaml"
    qt = (yaml.safe_load(doc(qt_file)) or {}) if qt_file.exists() else {}
    banned["cum_tu_cam_du_an"] = list(qt.get("cum_tu_cam") or [])
    banned["cam_du_an"] = list(qt.get("quy_tac") or [])

    videos_dir = (kenh / ".." / ".." / "videos").resolve()
    chu_de = doc_chu_de(doc(kenh / "chu-de.md"), videos_dir) if (kenh / "chu-de.md").exists() else []

    qh = ch.get("quyen_hinh") or {}
    kho_dir = kenh / "canh-quay" / "_kho"
    index = json.loads(doc(kho_dir / "index.json")) if (kho_dir / "index.json").exists() else {}
    nhan = json.loads(doc(kho_dir / "nhan.json")) if (kho_dir / "nhan.json").exists() else {}
    kho = doc_kho(kenh, index, nhan, qh, qt.get("nguon_canh_khong_dung") or {})
    nhan_thieu_index = sorted(set(nhan) - {m["ma"] for m in index.values()})

    anh = []
    if (kenh / "image").is_dir():
        for p in sorted((kenh / "image").iterdir()):
            if p.suffix.lower() in ANH_DUOI:
                anh.append(str(p))

    # Chép logo + font
    assets = {}
    for k, ten in [("logo", ch.get("logo", "logo.png")), ("logo_nho", ch.get("logo_nho", "logo-emblem.png"))]:
        src = kenh / ten
        if src.exists():
            dst = out / "assets" / Path(ten).name
            shutil.copyfile(src, dst)
            assets[k] = {"duong_dan": str(dst.relative_to(ROOT)).replace("\\", "/"), "sha1": sha1(dst)}
    fonts = {}
    for f in FONT_CAN:
        src = (kenh / "fonts" / f) if (kenh / "fonts" / f).exists() else tim_font(f)
        if src:
            dst = out / "assets" / "fonts" / f
            shutil.copyfile(src, dst)
            fonts[f] = {"duong_dan": str(dst.relative_to(ROOT)).replace("\\", "/"),
                        "nguon": "thư mục kênh" if src.parent == kenh / "fonts" else "font đã cài trên máy",
                        "sha1": sha1(dst)}
        else:
            thieu.append(f"font {f}")
    assets["fonts"] = fonts

    mau_tonghop = kenh / "mau" / "TONG-HOP.md"
    brand = {
        "id": ch.get("id"),
        "nguon_kenh": str(kenh),
        "kenh": {k: ch.get(k) for k in ["ten_kenh", "ten_day_du", "khan_gia", "tru_cot_noi_dung"]},
        "lien_he": {k: ch.get(k) for k in ["hotline", "zalo", "zalo_oa", "fanpage", "dia_chi"]},
        "cta": ch.get("cta", []),
        "hashtags": ch.get("hashtags", {}),
        "mau": ch.get("mau", {}),
        "font": {"tieu_de": ch.get("font_tieu_de"), "files": fonts},
        "giong_doc": ch.get("giong_doc"),
        "quyen_hinh": qh,
        "assets": assets,
        "context": ctx,
        "cam": banned,
        "chu_de": chu_de,
        "anh_that": anh,
        "kho_canh": kho,
        "kho_md": str(kho_dir / "KHO.md") if (kho_dir / "KHO.md").exists() else None,
        "mau_tong_hop": doc(mau_tonghop) if mau_tonghop.exists() else None,
        "mau_thuan_business_vs_channel": so_sanh(ch, biz, banned["cum_tu_cam_du_an"]),
        "file_thieu": thieu,
        "nhan_khong_co_trong_index": nhan_thieu_index,
    }
    brand["id"] = ma
    dst = out / "brand.json"
    dst.write_text(json.dumps(brand, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ---- tóm tắt ----
    p = print
    p(f"Đã ghi: {dst}")
    p(f"Kênh: {ch.get('ten_kenh')} | {ch.get('ten_day_du')}")
    lh = brand["lien_he"]
    p(f"Hotline: {lh['hotline']} | Zalo: {lh['zalo']} ({lh['zalo_oa']}) | Fanpage: {lh['fanpage']}")
    p(f"Địa chỉ: {lh['dia_chi']}")
    p(f"Màu: {ch.get('mau')} | Font: {ch.get('font_tieu_de')} | Giọng: {ch.get('giong_doc')}")
    p(f"CTA: {len(brand['cta'])} câu | Hashtag: " + ", ".join(f"{k}={len(v)}" for k, v in brand['hashtags'].items()))
    p(f"Cụm từ cấm: {len(banned.get('cum_tu_cam', []))} + câu sáo đã chốt {len(banned.get('cau_sao_da_chot', []))}"
      f" + chờ duyệt {len(banned.get('cau_sao_cho_duyet', []))} + dự án {len(banned['cum_tu_cam_du_an'])}")
    p(f"Chủ đề: {len(chu_de)} (đã làm {sum(r['da_lam'] for r in chu_de)}). Chưa làm, dựng được ngay (hoi-dap/giai-thich):")
    for r in chu_de:
        if not r["da_lam"] and r["dinh_dang"] in ("hoi-dap", "giai-thich"):
            p(f"   - {r['ma']}: {r['chu_de']}")
    ok = [c for c in kho if c["dung_duoc"]]
    p(f"Kho cảnh: {len(kho)} mã, dùng được {len(ok)}, loại {len(kho) - len(ok)}:")
    for c in kho:
        if not c["dung_duoc"]:
            p(f"   x {c['ma']}: {'; '.join(c['ly_do_loai'])[:140]}")
    p(f"Ảnh thật trong image/: {len(anh)}")
    p(f"Assets đã chép: logo={'logo' in assets}, logo_nho={'logo_nho' in assets}, font={list(fonts)}")
    p("Mâu thuẫn business.md vs channel.yaml:")
    for m in brand["mau_thuan_business_vs_channel"]:
        p(f"   ! [{m['kieu']}] {m['truong']}: yaml={m['channel_yaml']!r} | business={m['business_md']!r} -> {m['ghi_chu']}")
    p(f"File thiếu: {thieu or 'không có'}")
    if nhan_thieu_index:
        p(f"Nhãn không có trong index: {nhan_thieu_index}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

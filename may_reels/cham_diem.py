"""Chấm điểm nội dung một video ĐÃ RENDER theo brand/<kenh>/rubric.yaml, và chặn cứng.

Luồng (cham_video):
  1. Bằng chứng: chép lời âm thanh cuối (PhoWhisper, review/chep_loi.json), khung hook 0 / 0,5 / 1,5 / 3 giây
     (review/hook-*.png), chữ trên màn hình đọc từ nguồn HyperFrames (hf/index.html + hf/compositions/*.html).
  2. Chặn cứng (Python): cụm từ cấm / câu sáo đã chốt trong lời nghe được và chữ trên màn hình (cả dạng không dấu);
     con số / số hiệu luật không có trong nguồn cho phép; tài sản ngoài kho kênh, brand, sơ đồ được phép.
     Vi phạm -> KetQuaCham.chan khác rỗng: không vào Hàng chờ, job sang loi.
  3. Đo tất định: nhịp, tỉ lệ cảnh thật, phụ đề, thương hiệu, CTA, mốc chữ đầu, độ đứng yên của 3 giây đầu;
     cỡ chữ của MỌI chữ trên màn hình (đọc từ nguồn HyperFrames, may_reels/co_chu.py) và chữ ra ngoài vùng an toàn
     (hyperframes check). Thiếu thì áp trần tiêu chí phu_de và ghi canh_bao.
     Ghi review/bang_chung.json.
  4. Agent (claude -p, skills/may-reels/cham-diem.md) chấm các tiêu chí nguon=agent từ bằng chứng, ghi renders/score.json.
  5. Python gộp: tiêu chí nguon=may lấy số đo, tiêu chí agent bị áp trần khi đo được lỗi cứng, áp trần tổng
     (rubric tran_tong). Ghi lại renders/score.json theo schemas/may-reels/score.schema.json.
Mọi trọng số và ngưỡng đọc từ rubric.yaml; file này không viết cứng con số chấm điểm nào.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from may_reels import co_chu
from may_reels.sheet import bay_gio_vn

GOC = Path(__file__).resolve().parent.parent
SKILL_CHAM = "skills/may-reels/cham-diem.md"
MOC_HOOK = (0.0, 0.5, 1.5, 3.0)
BIEN_PY = "MAY_REELS_PY_GIONG"
# hyperframes check (vùng an toàn). Test thay bằng hàm giả (tests/may_reels/conftest.py).
kiem_vung_mac_dinh: Callable[[Path, str], tuple[dict | None, str]] = co_chu.chay_check


class LoiRubric(RuntimeError):
    pass


@dataclass
class KetQuaCham:
    ma_video: str
    diem_qa: int | None = None
    diem_ky_thuat: int | None = None
    tieu_chi: list[dict] = field(default_factory=list)
    chan: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    ly_do_tru: list[str] = field(default_factory=list)   # nặng nhất trước
    giay: float = 0.0
    giay_agent: float = 0.0
    so_luot_agent: int = 0
    chi_phi_agent_usd: float = 0.0

    def phan_hoi(self, nguong: int) -> str:
        """Phản hồi cho agent viết kế hoạch ở vòng sửa: lý do trừ điểm NỘI DUNG, nặng nhất trước."""
        return (f"Điểm QA {self.diem_qa} < {nguong} (rubric nội dung). Sửa ke_hoach.json theo các lý do trừ điểm, "
                "nặng nhất trước:\n" + "\n".join(f"- {x}" for x in self.ly_do_tru))


# ---------------------------------------------------------------- cấu hình
def doc_rubric(kenh: str, goc: Path = GOC) -> dict:
    p = goc / "brand" / kenh / "rubric.yaml"
    if not p.is_file():
        raise LoiRubric(f"Chưa có brand/{kenh}/rubric.yaml")
    rb = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    tc = rb.get("tieu_chi") or {}
    tong = sum(float(v.get("trong_so", 0)) for v in tc.values())
    if abs(tong - 100) > 1e-6:
        raise LoiRubric(f"rubric.yaml: tổng trọng số = {tong}, phải bằng 100")
    return rb


# ---------------------------------------------------------------- văn bản
def chuan(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").casefold()


def bo_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", chuan(s)).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


_TU = re.compile(r"\w+", re.UNICODE)


def tim_cum_tu(van_ban: str, cum: list[str]) -> list[str]:
    """Cụm có trong văn bản (theo từ). Khớp đúng dấu, hoặc khớp dạng không dấu khi đoạn trong văn bản được VIẾT
    không dấu (né bộ lọc: "bao dau"). Không bắt nhầm chữ có dấu khác nghĩa ("đảm bảo độ an toàn" != "đảm bảo đỗ")."""
    tu = _TU.findall(chuan(van_ban))
    ra = []
    for c in cum:
        p = _TU.findall(chuan(c))
        if not p:
            continue
        pk = [bo_dau(x) for x in p]
        for i in range(len(tu) - len(p) + 1):
            w = tu[i:i + len(p)]
            if w == p or ([bo_dau(x) for x in w] == pk and all(x == bo_dau(x) for x in w)):
                ra.append(c)
                break
    return ra


def _bo_the(s: str) -> str:
    s = re.sub(r"(?is)<(script|style|title|head)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _file_hf(hf: Path) -> list[Path]:
    return [hf / "index.html"] + sorted((hf / "compositions").glob("*.html"))


def chu_tren_man_hinh(hf: Path) -> str:
    """Toàn bộ chữ hiển thị trong nguồn HyperFrames (bỏ script, style, thuộc tính)."""
    return " ".join(_bo_the(f.read_text(encoding="utf-8")) for f in _file_hf(hf) if f.is_file())


def moc_chu_dau(hf: Path) -> float | None:
    """Giây chữ đầu tiên xuất hiện: nhóm phụ đề đầu, hoặc thẻ chữ của cảnh (mốc tween đầu của nó)."""
    idx = (hf / "index.html").read_text(encoding="utf-8")
    bat_dau = {m.group(1): float(m.group(2)) for m in
               re.finditer(r'data-composition-src="compositions/([^"]+)\.html"[^>]*?data-start="([\d.]+)"', idx)}
    moc = []
    for ten, t0 in bat_dau.items():
        f = hf / "compositions" / f"{ten}.html"
        if not f.is_file():
            continue
        s = f.read_text(encoding="utf-8")
        if ten == "phude":
            st = [float(x) for x in re.findall(r'class="clip grp[^"]*"[^>]*data-start="([\d.]+)"', s)]
            if st:
                moc.append(t0 + min(st))
        elif re.fullmatch(r"s\d+", ten):
            the = re.search(rf'id="{ten}-card">(.*?)</div>\s*</div>', s, re.S)
            if the and _bo_the(the.group(1)):
                off = re.search(rf'tl\.fromTo\("#{ten}-l1".*?,\s*([\d.]+)\)', s)
                moc.append(t0 + (float(off.group(1)) if off else 0.0))
    return round(min(moc), 2) if moc else None


# ---------------------------------------------------------------- khung hình
def _xam(video: Path, t: float, w: int = 36, h: int = 64) -> bytes:
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf",
                        f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True)
    return r.stdout


def do_dung_yen(video: Path, moc: tuple = MOC_HOOK) -> float:
    """Chênh lệch điểm ảnh trung bình lớn nhất (0-255) giữa khung đầu và các khung hook. Nhỏ = đứng yên."""
    ds = [_xam(video, t) for t in moc]
    a = ds[0]
    return round(max((sum(abs(x - y) for x, y in zip(a, b)) / max(len(a), 1) for b in ds[1:]), default=0.0), 2)


def lay_khung_hook(video: Path, ra: Path, moc: tuple = MOC_HOOK) -> list[str]:
    ra.mkdir(parents=True, exist_ok=True)
    out = []
    for t in moc:
        f = ra / f"hook-{t:.1f}s.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(f)],
                       check=True)
        out.append(f.name)
    return out


# ---------------------------------------------------------------- số đo tất định
def ti_le_canh_that(cat: list[dict]) -> float:
    """Thời lượng cảnh kho kênh (video + ảnh thật) / tổng thời lượng phần có cảnh (không tính màn kết)."""
    tong = sum(float(c["dai"]) for c in cat)
    that = sum(float(c["dai"]) for c in cat if not c.get("so_do"))
    return round(that / tong, 3) if tong else 0.0


def do_nhip(cat: list[dict], kh: dict, tu: list[dict], giay_toi_da: float) -> dict:
    """Mốc 'đổi hình hoặc nhấn': đầu mỗi cảnh, thẻ chữ, xe trong sơ đồ giao nhau/vòng xuyến, từ khóa tô màu phụ đề."""
    from may_reels.dung.hf import tu_khoa
    if not cat:
        return {"khoang_dai_nhat": 0.0, "so_lan_vuot": 0, "khoang_vuot": []}
    co_the = {d["id"] for d in kh.get("doan", []) if d.get("the")}
    moc = {round(float(c["start"]), 2) for c in cat}
    for c in cat:
        if c["doan"] in co_the:
            moc.add(round(float(c["start"]) + 0.1, 2))
        sd = c.get("so_do") or {}
        for i, _x in enumerate(sd.get("xe") or []):
            moc.add(round(float(c["start"]) + 1.3 + 1.4 * i, 2))
    moc |= {round(float(w["start"]), 2) for w in tu if tu_khoa(w.get("text", ""))}
    het = round(float(cat[-1]["start"]) + float(cat[-1]["dai"]), 2)
    ds = sorted(x for x in moc if x <= het) + [het]
    khoang = [(ds[i], ds[i + 1]) for i in range(len(ds) - 1)]
    vuot = [(a, b) for a, b in khoang if b - a > giay_toi_da + 1e-6]
    return {"khoang_dai_nhat": round(max((b - a for a, b in khoang), default=0.0), 2), "so_lan_vuot": len(vuot),
            "khoang_vuot": [[a, b] for a, b in vuot]}


def _mau(s: str) -> tuple[float, float, float] | None:
    m = re.match(r"#([0-9a-f]{6})", s.strip(), re.I)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    m = re.match(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)", s.strip())
    return tuple(float(m.group(i)) / 255 for i in (1, 2, 3)) if m else None


def tuong_phan(a: tuple, b: tuple) -> float:
    def L(c):
        f = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]
    la, lb = sorted((L(a), L(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def do_phu_de(hf: Path, cfg: dict) -> dict:
    """Số dòng ước lượng, vị trí so với vùng an toàn, tương phản chữ/nền của phụ đề (đọc CSS trong phude.html)."""
    f = hf / "compositions" / "phude.html"
    if not f.is_file():
        return {"co_phu_de": False}
    s = f.read_text(encoding="utf-8")
    nhom = [_bo_the(g) for g in re.findall(r'class="clip grp[^"]*"[^>]*>(.*?)</div>', s, re.S)]
    ktd = int(cfg.get("ky_tu_moi_dong", 19))
    so_dong = max((math.ceil(len(t) / ktd) for t in nhom if t), default=0)
    css = re.search(r"\.grp\s*\{([^}]*)\}", s)
    pill = re.search(r"\.pill\s*\{([^}]*)\}", s)
    get = lambda blk, k: (re.search(rf"(?<![-\w]){k}\s*:\s*([^;]+);", blk.group(1)) if blk else None)  # noqa: E731
    left = float(get(css, "left").group(1).rstrip("px")) if get(css, "left") else None
    top = float(get(css, "top").group(1).rstrip("px")) if get(css, "top") else None
    rong = float(get(css, "width").group(1).rstrip("px")) if get(css, "width") else None
    co = float(get(pill, "font-size").group(1).rstrip("px")) if get(pill, "font-size") else 58.0
    lh = float(get(pill, "line-height").group(1)) if get(pill, "line-height") else 1.4
    vung = cfg.get("vung_an_toan") or {}
    trong_vung = None
    thap = re.search(r"\.grp\.thap\s*\{([^}]*)\}", s)  # phụ đề hạ thấp trong cảnh sơ đồ: đo vị trí thấp hơn
    if top is not None and get(thap, "top"):
        top = max(top, float(get(thap, "top").group(1).rstrip("px")))
    if None not in (left, top, rong):
        day = top + max(so_dong, 1) * co * lh + 16
        trong_vung = (left >= vung.get("x0", 0) and left + rong <= vung.get("x1", 1080)
                      and top >= vung.get("y0", 0) and day <= vung.get("y1", 1920))
    tp = None
    if pill:
        c = _mau(get(pill, "color").group(1)) if get(pill, "color") else None
        b = _mau(get(pill, "background").group(1)) if get(pill, "background") else None
        tp = tuong_phan(c, b) if c and b else None
    return {"co_phu_de": bool(nhom), "so_nhom": len(nhom), "so_dong_lon_nhat": so_dong, "trong_vung_an_toan": trong_vung,
            "tuong_phan": tp}


def _sha1(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for k in iter(lambda: f.read(1 << 20), b""):
            h.update(k)
    return h.hexdigest()


def do_thuong_hieu(P: Path, brand: dict, goc: Path) -> dict:
    hf = P / "hf"
    nguon = " ".join(f.read_text(encoding="utf-8") for f in _file_hf(hf) if f.is_file()).lower()
    m = brand.get("mau") or {}
    mau = bool(m.get("navy")) and m["navy"].lower() in nguon and any(
        (m.get(k) or "").lower() in nguon for k in ("xanh_chinh", "cam_nhan") if m.get(k))
    fonts_brand = set(((brand.get("font") or {}).get("files") or {}).keys())
    fonts = set(re.findall(r'url\("assets/fonts/([^"]+)"\)', nguon, re.I))
    font = bool(fonts) and {f.lower() for f in fonts} <= {f.lower() for f in fonts_brand}
    logo_f = hf / "assets" / "img" / "logo.png"
    lg = (brand.get("assets") or {}).get("logo") or {}
    logo = False
    if logo_f.is_file():
        if lg.get("sha1"):
            logo = _sha1(logo_f).startswith(lg["sha1"])
        elif lg.get("duong_dan") and (goc / lg["duong_dan"]).is_file():
            logo = logo_f.read_bytes() == (goc / lg["duong_dan"]).read_bytes()
    ket = hf / "compositions" / "ket.html"
    ket_chu = re.sub(r"\s+", "", _bo_the(ket.read_text(encoding="utf-8"))) if ket.is_file() else ""
    lh = brand.get("lien_he") or {}
    so = re.sub(r"\s+", "", lh.get("hotline") or lh.get("zalo") or "")
    dc = re.sub(r"\s+", "", lh.get("dia_chi") or "")
    man_ket = bool(so) and so in ket_chu and bool(dc) and dc in ket_chu
    return {"mau": mau, "font": font, "logo": logo, "man_ket": man_ket}


def do_cta(kh: dict, brand: dict, van_ban: str) -> dict:
    ds = [unicodedata.normalize("NFC", c).strip() for c in brand.get("cta") or []]
    cta = next((d for d in reversed(kh.get("doan", [])) if d.get("vai") == "cta"), None)
    nguyen_van = bool(cta) and unicodedata.normalize("NFC", cta["loi"]).strip() in ds
    goc_vb = " ".join(_TU.findall(bo_dau(van_ban)))
    nghe = [c for c in ds if " ".join(_TU.findall(bo_dau(c))[:5]) in goc_vb]
    return {"nguyen_van": nguyen_van, "so_cta": len(nghe), "cta_nghe_thay": nghe}


# ---------------------------------------------------------------- chặn cứng
_LUAT = re.compile(r"\b(dieu|khoan|diem|chuong)\s+(\d+)\b")
_LUAT_DS = re.compile(r"\b(dieu|khoan|diem|chuong)\s+(\d+(?:\s*(?:,|va)\s*\d+\b)*)")
_SO_HIEU = re.compile(r"\b(\d+/\d{4}(?:/[a-z0-9-]+)?|qcvn\s*\d+\s*:\s*\d{4})\b")
_SO = re.compile(r"\d+(?:[.,]\d+)*")


def _nguon_cho_phep(chu_de: dict, brand: dict, rb: dict, kh: dict | None = None) -> str:
    ds = []
    for k in (rb.get("chan_cung") or {}).get("nguon_so_cho_phep") or []:
        if k in ("y_chinh", "nguon_doi_chieu", "chu_de"):
            ds.append(str(chu_de.get(k) or ""))
        elif k == "lien_he":
            ds += [str(v) for v in (brand.get("lien_he") or {}).values()]
        elif k == "cta":
            ds += list(brand.get("cta") or [])
        elif k == "nguon_luat_da_mo":  # nguồn agent đã mở: đủ link, ngày mở và trích nguyên văn
            for n in (kh or {}).get("nguon_luat") or []:
                if n.get("link") and n.get("ngay_mo") and n.get("trich_nguyen_van"):
                    ds += [str(n.get(x) or "") for x in ("van_ban", "ten_ngan", "dieu_khoan", "trich_nguyen_van")]
    return bo_dau(" ".join(ds))


def so_khong_nguon(van_ban: str, cho_phep: str, so_dem_toi_da: int) -> list[str]:
    """Số hiệu luật (Điều/khoản/điểm N, N/YYYY, QCVN N:YYYY) và con số không có trong văn bản cho phép."""
    vb = bo_dau(van_ban)
    # Nguồn cho phép có thể liệt kê: "khoản 2, 3" / "khoản 2 và 3" = khoản 2 và khoản 3.
    luat_cp = {(m.group(1), so) for m in _LUAT_DS.finditer(cho_phep) for so in re.findall(r"\d+", m.group(2))}
    ra = []
    for m in _LUAT.finditer(vb):
        if (m.group(1), m.group(2)) not in luat_cp:
            ra.append(f"{m.group(1)} {m.group(2)}")
    for m in _SO_HIEU.finditer(vb):
        so = re.sub(r"\s+", "", m.group(1))
        if so not in re.sub(r"\s+", "", cho_phep):
            ra.append(m.group(1))
    con = _SO_HIEU.sub(" ", _LUAT.sub(" ", vb))
    so_cp = set(_SO.findall(cho_phep))
    for s in _SO.findall(con):
        if s in so_cp or (s.isdigit() and int(s) <= so_dem_toi_da):
            continue
        ra.append(s)
    return sorted(set(ra))


def tai_san_ngoai(P: Path, kh: dict, brand: dict, cat: list[dict], rb: dict) -> list[str]:
    cc = rb.get("chan_cung") or {}
    kho = {k["ma"]: k for k in brand.get("kho_canh") or []}
    tam = {t.get("doan") for t in kh.get("thieu_canh") or []}
    loi = []
    cho_phep = {"assets/audio/vo.wav", "assets/img/logo.png"}
    cho_phep |= {f"assets/fonts/{f}" for f in ((brand.get("font") or {}).get("files") or {})}
    for c in cat:
        if c.get("so_do"):
            if c["so_do"].get("kieu") not in (cc.get("so_do_cho_phep") or []):
                loi.append(f"{c['doan']}: sơ đồ kiểu {c['so_do'].get('kieu')!r} không được phép")
            if c["doan"] not in tam:
                loi.append(f"{c['doan']}: dùng cảnh tạm nhưng không có trong thieu_canh")
            continue
        k = kho.get(c.get("ma"))
        if not k or not k.get("dung_duoc"):
            loi.append(f"{c['doan']}: cảnh {c.get('ma')!r} không thuộc kho kênh (hoặc dung_duoc = false)")
            continue
        if c.get("anh"):
            cho_phep |= {f"assets/img/{f.name}" for f in (P / "hf/assets/img").glob(c["id"] + ".*")}
            cho_phep.add(f"assets/img/{c['id']}{Path(k.get('file_tuong_doi', '.jpg')).suffix.lower()}")
        else:
            cho_phep.add(f"assets/video/{c['id']}.mp4")
    ngoai = tuple(cc.get("url_ngoai_cho_phep") or [])
    for f in _file_hf(P / "hf"):
        if not f.is_file():
            continue
        s = f.read_text(encoding="utf-8")
        for ref in re.findall(r'(?:src|href)="([^"]+)"|url\(["\']?([^"\')]+)', s):
            r = ref[0] or ref[1]
            if r.startswith("compositions/") and r.endswith(".html"):
                continue
            if r.startswith(("http://", "https://", "//")):
                if not r.startswith(ngoai):
                    loi.append(f"{f.name}: tải tài nguyên ngoài {r}")
                continue
            if r.startswith("data:") or r not in cho_phep:
                loi.append(f"{f.name}: tài sản {r[:80]} không thuộc kho kênh/brand")
    for d in kh.get("doan", []):
        if (d.get("canh") or {}).get("so_do") and d["id"] not in tam:
            loi.append(f"{d['id']}: kế hoạch dùng sơ đồ nhưng không khai trong thieu_canh")
    return sorted(set(loi))


def chan_cung(P: Path, kh: dict, brand: dict, chu_de: dict, rb: dict, loi_nghe: str, man_hinh: str,
              cat: list[dict]) -> list[str]:
    cc = rb.get("chan_cung") or {}
    cam = brand.get("cam") or {}
    cum = [c for k in cc.get("cum_tu") or [] for c in cam.get(k) or [] if c and c.strip()]
    ra = []
    for nhan, vb in (("lời nghe được", loi_nghe), ("chữ trên màn hình", man_hinh)):
        trung = tim_cum_tu(vb, cum)
        if trung:
            ra.append(f"Cụm từ cấm trong {nhan}: {', '.join(trung)}")
    so = so_khong_nguon(loi_nghe + " " + man_hinh, _nguon_cho_phep(chu_de, brand, rb, kh),
                        int(cc.get("so_dem_toi_da", 0)))
    if so:
        ra.append(f"Số/số hiệu luật không có trong y_chinh/nguon_doi_chieu: {', '.join(so)}")
    ts = tai_san_ngoai(P, kh, brand, cat, rb)
    if ts:
        ra.append("Tài sản không được phép: " + "; ".join(ts))
    return ra


# ---------------------------------------------------------------- gộp điểm
def tinh_diem(rb: dict, do: dict, agent: dict, diem_ky_thuat: float | None) -> tuple[list[dict], int, list[dict], list[str]]:
    """Trả về (tiêu chí, diem_qa, trần tổng đã áp, cảnh báo). agent: {ma: {"diem", "ly_do"}}."""
    ra, canh_bao = [], []
    for ma, c in (rb.get("tieu_chi") or {}).items():
        toi_da = float(c["trong_so"])
        nguon = c.get("nguon", "agent")
        tran: list[str] = []
        if ma == "nhip":
            n = do["nhip"]
            d = max(0.0, toi_da - float(c.get("tru_moi_lan_vuot", 0)) * n["so_lan_vuot"])
            ly = (f"Khoảng dài nhất không đổi hình/nhấn {n['khoang_dai_nhat']}s; {n['so_lan_vuot']} khoảng quá "
                  f"{c.get('giay_toi_da')}s" + (f" ({n['khoang_vuot']})" if n["khoang_vuot"] else ""))
        elif ma == "chan_thuc":
            r = do["ti_le_canh_that"]
            d = toi_da * min(1.0, r / float(c.get("ti_le_du_diem", 1)))
            ly = f"Cảnh quay thật chiếm {r:.0%} thời lượng"
            if r < float(c.get("ti_le_toi_thieu", 0)):
                d = min(d, float(c.get("khi_duoi_toi_thieu", toi_da)))
                tran.append(f"dưới {float(c['ti_le_toi_thieu']):.0%}")
                if c.get("canh_bao"):
                    canh_bao.append(f"{c['canh_bao']} ({1 - r:.0%} thời lượng)")
        elif ma == "thuong_hieu":
            th = do["thuong_hieu"]
            d = toi_da * sum(1 for v in th.values() if v) / max(len(th), 1)
            thieu = [k for k, v in th.items() if not v]
            ly = "Đủ màu, font, logo, màn kết đúng brand.json" if not thieu else f"Không đạt: {', '.join(thieu)}"
        elif ma == "ky_thuat":
            dk = float(diem_ky_thuat if diem_ky_thuat is not None else 0)
            d = toi_da * dk / 100
            ly = f"diem_ky_thuat {diem_ky_thuat}/100"
        else:
            a = agent.get(ma) or {}
            try:
                d = float(a.get("diem"))
            except (TypeError, ValueError):
                d = 0.0
            d = max(0.0, min(toi_da, d))
            ly = str(a.get("ly_do") or "Agent không chấm tiêu chí này")
            t = c.get("tran") or {}
            if ma == "hook":
                cd = do.get("moc_chu_dau")
                if cd is None or cd > float(t.get("chu_muon_hon_giay", 99)):
                    d = min(d, float(t.get("khi_chu_muon", toi_da)))
                    tran.append(f"chữ đầu tiên ở {cd}s")
                if do.get("dung_yen") is not None and do["dung_yen"] < float(t.get("dung_yen_nguong", -1)):
                    d = min(d, float(t.get("khi_dung_yen", toi_da)))
                    tran.append("3 giây đầu đứng yên")
            elif ma == "phu_de":
                pd = do.get("phu_de") or {}
                vp = []
                if not pd.get("co_phu_de"):
                    vp.append("không có phụ đề")
                if pd.get("so_dong_lon_nhat", 0) > int(c.get("so_dong_toi_da", 99)):
                    vp.append(f"{pd['so_dong_lon_nhat']} dòng")
                if pd.get("trong_vung_an_toan") is False:
                    vp.append("ra ngoài vùng an toàn")
                if pd.get("tuong_phan") is not None and pd["tuong_phan"] < float(c.get("tuong_phan_toi_thieu", 0)):
                    vp.append(f"tương phản {pd['tuong_phan']}")
                if vp:
                    d = min(d, float(c.get("khi_vi_pham", toi_da)))
                    tran += vp
                # Mọi chữ trên màn hình (cả nguồn luật, khung logo, màn kết): cỡ tối thiểu và vùng an toàn.
                cc = do.get("co_chu") or {}
                if cc.get("duoi_toi_thieu"):
                    d = min(d, float(c.get("khi_chu_nho", c.get("khi_vi_pham", toi_da))))
                    tran.append(f"{len(cc['duoi_toi_thieu'])} nhóm chữ dưới {cc['toi_thieu']:g}px")
                    canh_bao.append(tom_tat_chu_nho(cc))
                va = do.get("vung_an_toan") or {}
                if va.get("ngoai_vung"):
                    d = min(d, float(c.get("khi_ngoai_vung", c.get("khi_vi_pham", toi_da))))
                    tran.append(f"{len(va['ngoai_vung'])} chữ ra ngoài vùng an toàn")
                    canh_bao.append("Chữ ra ngoài vùng an toàn: " + "; ".join(
                        f"\"{x['chu']}\" ({x['file']}, {x['giay']}s)" for x in va["ngoai_vung"][:4]))
                elif va.get("loi"):
                    canh_bao.append(f"Chưa đo được vùng an toàn: {va['loi'][:60]}")
            elif ma == "cta":
                ct = do.get("cta") or {}
                if not ct.get("nguyen_van"):
                    d = min(d, float(c.get("khi_khong_nguyen_van", toi_da)))
                    tran.append("CTA không nguyên văn brand.json")
                if ct.get("so_cta", 0) >= 2:
                    d = min(d, float(c.get("khi_nhieu_cta", toi_da)))
                    tran.append(f"{ct['so_cta']} câu CTA")
        if tran:
            ly = f"{ly} [máy áp trần: {'; '.join(tran)}]"
        ra.append({"ma": ma, "ten": c.get("ten", ma), "toi_da": toi_da, "diem": round(d, 1), "ly_do": ly,
                   "nguon": nguon})
    tong = sum(x["diem"] for x in ra)
    ap = []
    theo_ma = {x["ma"]: x for x in ra}
    for luat in rb.get("tran_tong") or []:
        trung = False
        if luat.get("tieu_chi") in theo_ma and theo_ma[luat["tieu_chi"]]["diem"] < float(luat.get("diem_duoi", -1)):
            trung = True
        if luat.get("do") and do.get(luat["do"]) is not None and do[luat["do"]] < float(luat.get("duoi", -1)):
            trung = True
        if trung and tong > float(luat["toi_da"]):
            tong = float(luat["toi_da"])
            ap.append({"toi_da": luat["toi_da"], "ly_do": luat.get("ly_do", "")})
    return ra, int(round(tong)), ap, canh_bao


def _nhom_chu(x: dict) -> str:
    """Tên nhóm dễ hiểu cho canh_bao, theo file và phần tử nguồn HyperFrames."""
    pt, f = x["phan_tu"], x["file"]
    if pt.endswith("src") or str(x.get("vi_du", "")).startswith("Nguồn"):
        return "nguồn luật"
    if f == "ket.html":
        return "màn kết"
    if f == "khung.html":
        return "chữ cạnh logo"
    if f == "phude.html":
        return "phụ đề"
    if re.search(r"-x[ev]\d", pt):
        return "số trên xe sơ đồ"
    if pt.endswith("-l2"):
        return "dòng phụ thẻ chữ"
    if pt.endswith("-l1") or "-l1 " in pt:
        return "dòng chính thẻ chữ"
    return f"{f} {pt}"


def tom_tat_chu_nho(cc: dict) -> str:
    """Một dòng canh_bao: 'Chữ dưới 42px: nguồn luật 30px; màn kết 32-40px; ...' (nhỏ nhất trước)."""
    nhom: dict[str, list[float]] = {}
    for x in cc.get("duoi_toi_thieu") or []:
        nhom.setdefault(_nhom_chu(x), []).append(x["px"])
    phan = sorted(nhom.items(), key=lambda kv: min(kv[1]))
    return f"Chữ dưới {cc['toi_thieu']:g}px: " + "; ".join(
        f"{k} {min(v):g}px" if min(v) == max(v) else f"{k} {min(v):g}-{max(v):g}px" for k, v in phan)


def ly_do_tru(tieu_chi: list[dict], tran: list[dict]) -> list[str]:
    """Lý do trừ điểm, nặng nhất trước (trần tổng đứng đầu)."""
    ds = sorted((x for x in tieu_chi if x["toi_da"] - x["diem"] > 0.05), key=lambda x: x["diem"] - x["toi_da"])
    return [f"Trần tổng {t['toi_da']}: {t['ly_do']}" for t in tran] + \
           [f"{x['ten']} -{x['toi_da'] - x['diem']:g}: {x['ly_do']}" for x in ds]


# ---------------------------------------------------------------- chạy ngoài
def chep_loi_mac_dinh(video: Path, ra: Path, *, sha1: str, model: str, goc: Path = GOC) -> dict:
    py = os.environ.get(BIEN_PY, "") or "python"
    r = subprocess.run([py, "-m", "may_reels.dung.chep_loi", str(video), str(ra), "--model", model, "--sha1", sha1],
                       cwd=goc, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode != 0 or not ra.is_file():
        raise RuntimeError(f"chép lời PhoWhisper lỗi: {r.stderr.strip()[-800:]}")
    return json.loads(ra.read_text(encoding="utf-8"))


def goi_agent_cham(prompt: str, *, du_an: Path, goc: Path = GOC) -> dict:
    from may_reels.san_xuat import goi_agent
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=("renders/score.json",), web=False,
                     he_thong=("Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi. Chỉ làm theo "
                               f"{SKILL_CHAM}. Chỉ ghi đúng một file renders/score.json trong thư mục dự án được giao."))


# ---------------------------------------------------------------- một video
def _doc_json(p: Path, mac_dinh=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else mac_dinh


def cham_video(ma_video: str, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent_cham,
               chep: Callable[..., dict] = chep_loi_mac_dinh, log: Callable[[str], None] = print,
               tom: dict | None = None,
               kiem_vung: Callable[[Path, str], tuple[dict | None, str]] | None = None) -> KetQuaCham:
    from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat
    from may_reels.dung.pipeline import doc_diem_ky_thuat
    t0 = time.monotonic()
    P = goc / "projects" / ma_video
    kq = KetQuaCham(ma_video)
    kh = _doc_json(P / "ke_hoach.json")
    video = P / "renders" / "final.mp4"
    if kh is None or not video.is_file():
        raise RuntimeError(f"{ma_video}: thiếu ke_hoach.json hoặc renders/final.mp4")
    kenh = kh["kenh"]
    brand, sx, rb = doc_brand(kenh, goc), doc_san_xuat(kenh, goc), doc_rubric(kenh, goc)
    chu_de = next((c for c in brand.get("chu_de") or [] if c.get("ma") == kh.get("ma_chu_de")), {})
    cat = _doc_json(P / "cat_canh.json", [])
    tu = _doc_json(P / "assets" / "audio" / "tu_phu_de.json", [])
    rv = P / "review"
    rv.mkdir(exist_ok=True)

    sha = _sha1(video)
    cl = _doc_json(rv / "chep_loi.json")
    if not cl or cl.get("sha1") != sha:
        log(f"  [{ma_video}] chép lời âm thanh cuối (PhoWhisper)")
        cl = chep(video, rv / "chep_loi.json", sha1=sha, model=(sx.get("giong") or {}).get("nghe_lai",
                                                                                         "kiendt/PhoWhisper-large-ct2"))
    loi_nghe = cl.get("van_ban", "")
    man_hinh = chu_tren_man_hinh(P / "hf")
    kq.diem_ky_thuat = (tom or {}).get("diem_ky_thuat")
    if kq.diem_ky_thuat is None:
        kq.diem_ky_thuat = doc_diem_ky_thuat(P)

    kq.chan = chan_cung(P, kh, brand, chu_de, rb, loi_nghe, man_hinh, cat)
    khung = lay_khung_hook(video, rv)
    tc = rb.get("tieu_chi") or {}
    do = {"moc_chu_dau": moc_chu_dau(P / "hf"), "dung_yen": do_dung_yen(video),
          "ti_le_canh_that": ti_le_canh_that(cat),
          "nhip": do_nhip(cat, kh, tu, float((tc.get("nhip") or {}).get("giay_toi_da", 4.0))),
          "phu_de": do_phu_de(P / "hf", tc.get("phu_de") or {}), "thuong_hieu": do_thuong_hieu(P, brand, goc),
          "cta": do_cta(kh, brand, loi_nghe + " " + man_hinh),
          "co_chu": co_chu.do_co_chu(P / "hf", float((tc.get("phu_de") or {}).get("co_chu_toi_thieu", 42)))}
    bc_check, loi_check = (kiem_vung or kiem_vung_mac_dinh)(P / "hf", str(sx.get("hyperframes_phien_ban") or "0.9.46"))
    do["vung_an_toan"] = {"ngoai_vung": co_chu.doc_ngoai_vung(bc_check) if bc_check else [], "loi": loi_check}
    bang_chung = {"ma_video": ma_video, "sha1_video": sha, "khung_hook": khung,
                  "khung_review": sorted(f.name for f in rv.glob("khung-*.png")), "luoi": "luoi.png",
                  "chep_loi": loi_nghe, "chu_tren_man_hinh": man_hinh, "do_dac": do,
                  "chu_de": {k: chu_de.get(k) for k in ("ma", "chu_de", "y_chinh", "nguon_doi_chieu")},
                  "chan_cung": kq.chan, "diem_ky_thuat": kq.diem_ky_thuat,
                  "tieu_chi_agent": {m: {"ten": c.get("ten"), "toi_da": c.get("trong_so"), "mo_ta": c.get("mo_ta")}
                                     for m, c in tc.items() if c.get("nguon", "agent") == "agent"}}
    (rv / "bang_chung.json").write_text(json.dumps(bang_chung, ensure_ascii=False, indent=1), encoding="utf-8")
    score_f = P / "renders" / "score.json"

    # Bị chặn vẫn chấm: điểm giúp người hiểu video, còn chặn thì vẫn chặn (dat = false, không vào Hàng chờ).
    score_f.unlink(missing_ok=True)
    ra = agent(f"Đọc và làm đúng theo {SKILL_CHAM}. Dự án: projects/{ma_video}. Đọc "
               f"projects/{ma_video}/review/bang_chung.json rồi ghi projects/{ma_video}/renders/score.json.",
               du_an=P, goc=goc)
    kq.so_luot_agent += 1
    kq.giay_agent += (ra.get("duration_ms") or 0) / 1000
    kq.chi_phi_agent_usd += float(ra.get("total_cost_usd") or 0)
    if ra.get("is_error") or not score_f.is_file():
        raise RuntimeError(f"agent chấm điểm không ghi được renders/score.json: {str(ra.get('result'))[:300]}")
    try:
        agent_tc = (_doc_json(score_f) or {}).get("tieu_chi") or {}
    except ValueError as e:
        raise RuntimeError(f"renders/score.json của agent không phải JSON: {e}") from e
    if isinstance(agent_tc, list):
        agent_tc = {x.get("ma"): x for x in agent_tc if isinstance(x, dict)}

    tieu_chi, diem, tran, cb = tinh_diem(rb, do, agent_tc, kq.diem_ky_thuat)
    kq.tieu_chi, kq.canh_bao = tieu_chi, cb
    kq.diem_qa = diem
    kq.ly_do_tru = ly_do_tru(tieu_chi, tran)
    kq.giay = round(time.monotonic() - t0, 1)
    nguong = int((sx.get("cham_diem") or {}).get("nguong", 75))
    score = {"version": "1.0", "ma_video": ma_video, "kenh": kenh, "sha1_video": sha,
             "cham_luc": bay_gio_vn(),
             "rubric_phien_ban": rb.get("phien_ban"), "diem_qa": kq.diem_qa, "nguong": nguong,
             "dat": bool(not kq.chan and kq.diem_qa >= nguong), "diem_ky_thuat": kq.diem_ky_thuat,
             "tieu_chi": tieu_chi, "tran_tong": tran, "chan_cung": kq.chan, "canh_bao": cb, "ly_do_tru": kq.ly_do_tru,
             "do_dac": do, "agent": {"so_luot": kq.so_luot_agent, "giay": round(kq.giay_agent, 1),
                                     "chi_phi_usd": round(kq.chi_phi_agent_usd, 4)}, "giay": kq.giay}
    kiem_score(score)
    score_f.parent.mkdir(parents=True, exist_ok=True)
    score_f.write_text(json.dumps(score, ensure_ascii=False, indent=1), encoding="utf-8")
    return kq


def kiem_score(score: dict) -> None:
    import jsonschema
    sc = json.loads((GOC / "schemas" / "may-reels" / "score.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(score, sc)


if __name__ == "__main__":  # pragma: no cover
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    k = cham_video(sys.argv[1])
    print(json.dumps({"diem_qa": k.diem_qa, "chan": k.chan, "ly_do_tru": k.ly_do_tru}, ensure_ascii=False, indent=1))

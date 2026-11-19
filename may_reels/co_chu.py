"""Cỡ chữ và vùng an toàn của MỌI chữ trên màn hình, đọc từ nguồn HyperFrames (không đoán từ ảnh).

- Cỡ chữ: dựng cây phần tử của hf/index.html và hf/compositions/*.html, áp CSS trong <style> (bộ chọn #id, .class,
  thẻ, nối bằng dấu cách = con cháu; độ ưu tiên id > class > thẻ, rule sau thắng rule trước), style inline, kế thừa
  từ cha; <text font-size> trong SVG nhân tỉ lệ width/viewBox. Mỗi phần tử có chữ trực tiếp cho một dòng kết quả.
  Không tính phóng to/thu nhỏ do GSAP (chỉ thoáng qua lúc chữ vào/ra).
- Vùng an toàn: cảnh báo `outside_safe_zone` của `hyperframes check` (layout thật trong trình duyệt, vùng an toàn
  TikTok / Reels / Shorts), chạy trên chính thư mục hf/ của video. Chạy lại khi nguồn không đổi thì hyperframes trả
  kết quả lưu sẵn.

Ngưỡng nằm trong brand/<kênh>/rubric.yaml (tieu_chi.phu_de.co_chu_toi_thieu), theo skills/creative/short-form.md:
"TEXT SIZE: 42px+ minimum" ở 1080p.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

CO_MAC_DINH = 16.0  # cỡ chữ mặc định của trình duyệt
THE_KHONG_HIEN = {"script", "style", "title", "head", "template-script"}
THE_RONG = {"img", "br", "meta", "link", "source", "input", "hr", "path", "rect", "circle", "line", "audio", "video"}


@dataclass
class PhanTu:
    tag: str
    attrs: dict
    cha: "PhanTu | None"
    con: list = field(default_factory=list)
    chu: str = ""

    @property
    def id(self) -> str:
        return self.attrs.get("id") or ""

    @property
    def lop(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class _Dung(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.goc = PhanTu("#doc", {}, None)
        self.cur = self.goc
        self.css: list[str] = []
        self._trong: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title"):
            self._trong = tag
            return
        p = PhanTu(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.con.append(p)
        if tag not in THE_RONG:
            self.cur = p

    def handle_startendtag(self, tag, attrs):
        self.cur.con.append(PhanTu(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title"):
            self._trong = None
            return
        p = self.cur
        while p is not None and p.tag != tag:
            p = p.cha
        if p is not None and p.cha is not None:
            self.cur = p.cha

    def handle_data(self, data):
        if self._trong == "style":
            self.css.append(data)
        elif self._trong is None:
            self.cur.chu += data


# ---------------------------------------------------------------- CSS
def _rules(css: str) -> list[tuple[list[tuple[str, str | None, set[str]]], tuple[int, int, int], int, str]]:
    """[(chuỗi bộ chọn đơn [(tag, id, lớp)], độ ưu tiên, thứ tự, giá trị font-size)] cho các rule có font-size."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", css)
    out = []
    for n, m in enumerate(re.finditer(r"([^{}]+)\{([^{}]*)\}", css)):
        fs = re.search(r"(?<![-\w])font-size\s*:\s*([^;]+)", m.group(2))
        if not fs:
            continue
        for sel in m.group(1).split(","):
            sel = sel.strip()
            if not sel or re.search(r"[>+~:\[]", sel):
                continue  # bộ chọn phức tạp: trình sinh mẫu không dùng
            chuoi, uu = [], [0, 0, 0]
            for don in sel.split():
                tag = re.match(r"^[a-zA-Z][\w-]*", don)
                id_ = re.search(r"#([\w-]+)", don)
                lop = set(re.findall(r"\.([\w-]+)", don))
                chuoi.append((tag.group(0).lower() if tag else "", id_.group(1) if id_ else None, lop))
                uu[0] += bool(id_)
                uu[1] += len(lop)
                uu[2] += bool(tag)
            out.append((chuoi, tuple(uu), n, fs.group(1).strip()))
    return out


def _khop_don(p: PhanTu, don: tuple) -> bool:
    tag, id_, lop = don
    return (not tag or p.tag == tag) and (id_ is None or p.id == id_) and lop <= p.lop


def _khop(p: PhanTu, chuoi: list) -> bool:
    if not _khop_don(p, chuoi[-1]):
        return False
    i, q = len(chuoi) - 2, p.cha
    while i >= 0 and q is not None:
        if _khop_don(q, chuoi[i]):
            i -= 1
        q = q.cha
    return i < 0


def _px(gia_tri: str, cha: float) -> float | None:
    v = gia_tri.replace("!important", "").strip()
    m = re.fullmatch(r"([\d.]+)\s*(px|em|rem|%)?", v)
    if not m:
        return None
    x, dv = float(m.group(1)), m.group(2) or "px"
    return {"px": x, "em": x * cha, "rem": x * CO_MAC_DINH, "%": x * cha / 100}[dv]


def _ti_le_svg(p: PhanTu) -> float:
    """Tỉ lệ đơn vị SVG -> px của thẻ <svg> gần nhất (width / chiều rộng viewBox)."""
    q = p
    while q is not None and q.tag != "svg":
        q = q.cha
    if q is None:
        return 1.0
    vb = (q.attrs.get("viewBox") or q.attrs.get("viewbox") or "").split()
    try:
        return float(re.sub(r"px$", "", q.attrs.get("width", ""))) / float(vb[2]) if len(vb) == 4 else 1.0
    except (ValueError, ZeroDivisionError):
        return 1.0


def _ten(p: PhanTu) -> str:
    """Tên dễ đọc: #id gần nhất + đường đi ngắn."""
    phan, q = [], p
    while q is not None and q.tag != "#doc":
        phan.append(f"#{q.id}" if q.id else q.tag + "".join(f".{c}" for c in sorted(q.lop)))
        if q.id:
            break
        q = q.cha
    return " ".join(reversed(phan))


def do_co_chu_file(f: Path) -> list[dict]:
    """Mỗi phần tử có chữ trực tiếp: {file, phan_tu, chu, px}. Bỏ qua phần tử đánh dấu data-layout-ignore."""
    d = _Dung()
    d.feed(f.read_text(encoding="utf-8"))
    rules = _rules("\n".join(d.css))
    out = []

    def di(p: PhanTu, co_cha: float, bo_qua: bool) -> None:
        co = co_cha
        trung = [(uu, n, v) for chuoi, uu, n, v in rules if _khop(p, chuoi)]
        if trung:
            x = _px(max(trung)[2], co_cha)
            co = x if x is not None else co
        if p.tag == "text" and p.attrs.get("font-size"):
            x = _px(p.attrs["font-size"], co_cha)
            co = x * _ti_le_svg(p) if x is not None else co
        inline = re.search(r"(?<![-\w])font-size\s*:\s*([^;]+)", p.attrs.get("style", ""))
        if inline:
            x = _px(inline.group(1), co_cha)
            co = x if x is not None else co
        bo_qua = bo_qua or "data-layout-ignore" in p.attrs
        chu = re.sub(r"\s+", " ", html.unescape(p.chu)).strip()
        if chu and not bo_qua and p.tag != "#doc":
            out.append({"file": f.name, "phan_tu": _ten(p), "chu": chu[:40], "px": round(co, 1)})
        for c in p.con:
            di(c, co, bo_qua)

    di(d.goc, CO_MAC_DINH, False)
    return out


def do_co_chu(hf: Path, toi_thieu: float) -> dict:
    """Đo mọi file của dự án; gộp các phần tử nhỏ hơn `toi_thieu` theo (file, cỡ, phần tử)."""
    files = [hf / "index.html"] + sorted((hf / "compositions").glob("*.html"))
    tat_ca = [x for f in files if f.is_file() for x in do_co_chu_file(f)]
    nho: dict[tuple, dict] = {}
    for x in tat_ca:
        if x["px"] < toi_thieu:
            k = (x["file"], re.sub(r"-?\d+$", "#", re.sub(r"(pd|kt-w|s\d+-xe|s\d+-xv)\d+(-\d+)?", r"\1#", x["phan_tu"])), x["px"])
            g = nho.setdefault(k, {"file": x["file"], "phan_tu": x["phan_tu"], "px": x["px"], "vi_du": x["chu"], "so_lan": 0})
            g["so_lan"] += 1
    ds = sorted(nho.values(), key=lambda g: (g["px"], g["file"]))
    return {"toi_thieu": toi_thieu, "so_phan_tu": len(tat_ca), "nho_nhat": min((x["px"] for x in tat_ca), default=None),
            "duoi_toi_thieu": ds}


# ---------------------------------------------------------------- vùng an toàn (hyperframes check)
def doc_ngoai_vung(bao_cao: dict) -> list[dict]:
    """Cảnh báo outside_safe_zone trong báo cáo JSON của hyperframes check, gộp theo (file, chữ)."""
    gop: dict[tuple, dict] = {}
    for f in (bao_cao.get("layout") or {}).get("findings") or []:
        if f.get("code") != "outside_safe_zone":
            continue
        k = (Path(str(f.get("sourceFile") or "")).name, f.get("text") or f.get("selector"))
        g = gop.setdefault(k, {"file": k[0], "chu": str(k[1])[:40], "phan_tu": f.get("selector", ""),
                               "vi_tri": f.get("message", ""), "giay": f.get("firstSeen", f.get("time"))})
        g["giay"] = min(g["giay"] or 0, f.get("firstSeen", f.get("time")) or 0)
    return list(gop.values())


def _json_trong(s: str) -> dict | None:
    i = s.find("{")
    while i >= 0:
        try:
            return json.loads(s[i:])
        except ValueError:
            i = s.find("{", i + 1)
    return None


def chay_check(hf: Path, phien_ban: str, giay: int = 600) -> tuple[dict | None, str]:
    """`hyperframes check --json --no-craft --no-contrast` trên hf/. Trả về (báo cáo, lỗi)."""
    cmd = ["npx", "--yes", f"hyperframes@{phien_ban}", "check", "--json", "--no-craft", "--no-contrast"]
    try:
        r = subprocess.run(cmd, cwd=hf, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=giay, shell=(__import__("os").name == "nt"))
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"không chạy được hyperframes check: {e}"
    bc = _json_trong(r.stdout)
    if bc is None or "layout" not in bc:
        return None, f"hyperframes check không trả JSON (mã {r.returncode}): {(r.stderr or r.stdout)[-300:]}"
    return bc, ""

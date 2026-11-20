"""Viết dự án HyperFrames (<dự án>/hf/) từ kế hoạch + mốc giọng + đoạn cắt. Chuyển từ projects/vx-demo-01/dung_hf.py.

Mọi phần tử có thời gian được ghi thẳng vào HTML (sửa được trong HyperFrames Studio).
Màu, font, logo, liên hệ lấy từ brand.json; chữ cạnh logo lấy từ san-xuat.yaml man_ket.logo_chu.
Vùng an toàn chung TikTok/Reels/Shorts: x 120..888, y 288..1248; dưới y 840 TikTok chỉ an toàn tới x 780
(nên dòng nguồn luật, có thể xuống quá y 840 khi 2 dòng, chỉ rộng tới XCW = 660, tức x 780).
Cỡ chữ: MỌI chữ hiển thị từ rubric.yaml tieu_chi.phu_de.co_chu_toi_thieu px trở lên (skills/creative/short-form.md "42px+ minimum"), kể cả nguồn
luật, chữ cạnh logo, số trên xe của sơ đồ và màn kết. Bước chấm điểm đo lại từ nguồn (may_reels/co_chu.py).
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

LEAD = 0.15
CO_CHU_TOI_THIEU = 42  # dự phòng khi kênh chưa có rubric.yaml tieu_chi.phu_de.co_chu_toi_thieu
W, H, X0, XW = 1080, 1920, 120, 768
XC0, XCW = 120, 660
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"
FONT = """@font-face{font-family:"BVP";src:url("assets/fonts/FONT_DAM") format("truetype");font-weight:800;}
@font-face{font-family:"BVP";src:url("assets/fonts/FONT_VUA") format("truetype");font-weight:700;}"""
KHONG_TACH = ("phân", "hạng", "bằng", "năm", "đến", "dưới", "từ", "mô", "bắt", "của", "trật", "giao", "thời", "hiệu", "ôn")


def e(s: str) -> str:
    return html.escape(s, quote=True)


def co_chu(text: str, toi_da: int, nho_nhat: int, rong: int = XW - 60, he: float = 0.74) -> int:
    return int(max(nho_nhat, min(toi_da, rong / (max(len(text), 1) * he))))


def co_chu_toi_thieu(kenh: str, goc: Path) -> int:
    """Cỡ chữ tối thiểu (px) của kênh: rubric.yaml tieu_chi.phu_de.co_chu_toi_thieu, cùng số mà bước chấm điểm đo."""
    import yaml
    p = goc / "brand" / kenh / "rubric.yaml"
    try:
        v = ((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("tieu_chi") or {}).get("phu_de", {}).get("co_chu_toi_thieu")
    except OSError:
        v = None
    return int(v or CO_CHU_TOI_THIEU)


def tu_khoa(t: str) -> bool:
    t = re.sub(r"[^\wÀ-ỹ]", "", t)
    return bool(re.search(r"\d", t)) or bool(re.fullmatch(r"[A-Z]\d?", t)) or t == "Zalo"


class Dung:
    def __init__(self, du_an: Path, kh: dict, brand: dict, sx: dict, cat: list[dict], tu: list[dict], moc: dict,
                 goc: Path) -> None:
        self.P, self.kh, self.B, self.sx, self.cat, self.tu, self.moc = du_an, kh, brand, sx, cat, tu, moc
        m = brand["mau"]
        self.NAVY, self.XANH, self.CAM, self.TRANG = m["navy"], m["xanh_chinh"], m["cam_nhan"], m["trang"]
        self.CAM_CHU = "#E56C28" if self.CAM.upper() == "#E4661F" else self.CAM  # chỉnh nhẹ để đạt tương phản trên navy
        self.LH = brand["lien_he"]
        self.TEN = brand["kenh"]["ten_kenh"]
        self.logo_chu = (sx.get("man_ket") or {}).get("logo_chu") or {"dong1": "", "dong2": self.TEN, "dong2_nhan": ""}
        self.KET0 = round(cat[-1]["start"] + cat[-1]["dai"], 2)
        giu = float((sx.get("khung_hinh") or {}).get("giu_man_ket_giay", 1.5))
        self.TONG = round(moc["doan"][-1]["end"] + LEAD + giu, 2)
        self.cta_id = kh["doan"][-1]["id"]
        fonts = sorted((brand.get("font") or {}).get("files") or {})
        dam = next((f for f in fonts if "ExtraBold" in f), fonts[0] if fonts else "")
        vua = next((f for f in fonts if f.endswith("-Bold.ttf")), dam)
        self.FONT = FONT.replace("FONT_DAM", dam).replace("FONT_VUA", vua)
        self.fonts, self.goc = fonts, goc
        self.CO = co_chu_toi_thieu(kh["kenh"], goc)
        self._ti_le = 1.0  # tỉ lệ thu phóng của sơ đồ đang vẽ (so_do đặt rồi trả về 1)
        nguon = {n["id"]: n for n in kh["nguon_luat"]}
        self.the = {}
        for d in kh["doan"]:
            if d["the"]:
                src = "; ".join(f"{nguon[i]['ten_ngan']}, {nguon[i]['dieu_khoan']}" for i in d["nguon_ids"]) or None
                self.the[d["id"]] = (d["the"]["dong1"], d["the"]["dong2"], src,
                                     self.CAM if d["the"]["mau"] == "cam" else self.XANH, d["the"]["kieu"])

    # ---------- tài nguyên ----------
    def chep_tai_nguyen(self) -> None:
        hf = self.P / "hf"
        for sub in ("compositions", "assets/fonts", "assets/img", "assets/audio", "assets/video"):
            (hf / sub).mkdir(parents=True, exist_ok=True)
        bdir = self.goc / "brand" / self.kh["kenh"] / "assets"
        for f in self.fonts:
            shutil.copyfile(bdir / "fonts" / f, hf / "assets" / "fonts" / f)
        logo = ((self.B.get("assets") or {}).get("logo") or {}).get("duong_dan")
        shutil.copyfile(self.goc / logo if logo else bdir / "logo.png", hf / "assets" / "img" / "logo.png")
        v = (self.sx.get("hyperframes_phien_ban") or "0.9.46")
        (hf / "hyperframes.json").write_text(json.dumps({
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
            "media": {"autoProxy": True}}, indent=2), encoding="utf-8")
        (hf / "package.json").write_text(json.dumps({
            "name": "hf", "private": True, "type": "module",
            "scripts": {k: f"npx --yes hyperframes@{v} {k if k != 'dev' else 'preview'}"
                        for k in ("dev", "check", "render")}}, indent=2), encoding="utf-8")

    # ---------- cảnh tạm: sơ đồ động (SVG + GSAP), không AI, không stock ----------
    # Tọa độ sơ đồ (đơn vị SVG) quanh tâm (540, 840). Xe đi bên phải đường.
    # Bố cục trên màn hình (2026-11-20): trong cảnh sơ đồ, dòng phụ và nguồn luật của thẻ chữ hiện SD_DOC_GIAY giây rồi mờ,
    # chỉ còn tiêu đề; phụ đề hạ xuống PD_TOP_SO_DO; sơ đồ được thu phóng/dời bằng viewBox để mọi xe và số trên xe nằm
    # trong khoảng trống giữa tiêu đề và phụ đề, và xe chỉ bắt đầu chạy sau khi chữ đã mờ. Trước đó xe chờ ở nhánh trên
    # nằm dưới thẻ chữ, ở nhánh dưới nằm dưới phụ đề (vx-007 cảnh s3, s5).
    CX, CY, NUA = 540, 840, 130
    SD_DOC_GIAY = 2.6
    PD_TOP_SO_DO = 1075  # 2 dòng phụ đề cao ~158px: đáy ~1233 < 1248 (mép dưới Reels/Shorts theo hyperframes check)
    SO = {"r": 33, "lech": 90, "ty": 15}  # số trên xe: px trên màn hình, không đổi theo tỉ lệ sơ đồ
    # Phần sơ đồ phải nằm trọn trong khoảng trống: (trên, dưới) tính từ tâm, đơn vị SVG, và số trên xe có nằm phía
    # trên xe cao nhất không. Vòng xuyến: số đặt bên cạnh xe chờ (không đè lên làn trong vòng khi sơ đồ thu nhỏ).
    TAM_VUNG = {"giao_nhau": (170, 224, True), "vong_xuyen": (379, 379, False)}
    LAN = {  # tu: (điểm xuất phát, điểm dừng chờ, điểm ra, góc quay của xe [xe vẽ hướng lên])
        "duoi": ((605, 1500), (605, 1000), (605, 520), 0),
        "tren": ((475, 520), (475, 670), (475, 1500), 180),
        "trai": ((110, 905), (380, 905), (1000, 905), 90),
        "phai": ((970, 775), (700, 775), (80, 775), -90),
    }
    GOC_NHANH = {"phai": 0, "duoi": 90, "trai": 180, "tren": -90}  # góc màn hình của nhánh vòng xuyến

    def _xe_svg(self, xid: str, loai: str, mau: str, so: int | None, huong: tuple[float, float] = (0, -1)) -> str:
        """huong: hướng đặt số so với tâm xe (mặc định phía trên)."""
        N, T = self.NAVY, self.TRANG
        if loai == "xe_may":
            than = (f'<rect x="-17" y="-42" width="34" height="84" rx="15" fill="{mau}" stroke="{T}" stroke-width="3"/>'
                    f'<circle cx="0" cy="-4" r="14" fill="{N}" stroke="{T}" stroke-width="3"/>')
        else:
            nen = T if loai == "uu_tien" else mau
            than = (f'<rect x="-35" y="-64" width="70" height="128" rx="18" fill="{nen}" stroke="{T}" stroke-width="3"/>'
                    f'<rect x="-26" y="-40" width="52" height="26" rx="6" fill="{N}" opacity="0.85"/>')
            if loai == "uu_tien":
                than += ('<rect x="-35" y="4" width="70" height="14" fill="#D7263D"/>'
                         '<rect x="-16" y="-58" width="14" height="10" rx="3" fill="#D7263D"/>'
                         '<rect x="2" y="-58" width="14" height="10" rx="3" fill="#1E5BD8"/>')
        q = 1 / self._ti_le  # số trên xe giữ đúng cỡ trên màn hình dù sơ đồ thu nhỏ
        bx, by = huong[0] * self.SO["lech"] * q, huong[1] * self.SO["lech"] * q
        huy_hieu = (f'<g id="{xid}-so"><circle cx="{bx:.1f}" cy="{by:.1f}" r="{self.SO["r"] * q:.1f}" fill="{T}" stroke="{N}" stroke-width="{4 * q:.1f}"/>'
                    f'<text x="{bx:.1f}" y="{by + self.SO["ty"] * q:.1f}" data-layout-allow-occlusion text-anchor="middle" font-family="BVP" font-weight="800" font-size="{self.CO * q:.1f}" '
                    f'fill="{N}">{so}</text></g>') if so else ""
        # Xe có thể chạy vào dưới thẻ chữ: chồng lớp có chủ ý (thẻ chữ luôn ở trên sơ đồ).
        return f'<g id="{xid}" data-layout-allow-occlusion><g id="{xid}-q">{than}</g>{huy_hieu}</g>'

    def _nen_duong(self, sd: dict) -> str:
        CX, CY, H2 = self.CX, self.CY, self.NUA
        duong, vach, sang = "#2B3F5C", "#E8EEF6", "#3A5478"
        uu = sd.get("duong_uu_tien")
        mau_doc = sang if uu == "doc" else duong
        mau_ngang = sang if uu == "ngang" else duong
        s = [f'<rect x="{CX - H2}" y="-2000" width="{2 * H2}" height="6000" fill="{mau_doc}"/>',
             f'<rect x="-2000" y="{CY - H2}" width="5000" height="{2 * H2}" fill="{mau_ngang}"/>',
             f'<rect x="{CX - H2}" y="{CY - H2}" width="{2 * H2}" height="{2 * H2}" fill="{sang if uu else duong}"/>']
        for y0, y1 in ((-2000, CY - H2 - 30), (CY + H2 + 30, 4000)):
            s.append(f'<line x1="{CX}" y1="{y0}" x2="{CX}" y2="{y1}" stroke="{vach}" stroke-width="6" stroke-dasharray="34 26"/>')
        for x0, x1 in ((-2000, CX - H2 - 30), (CX + H2 + 30, 3000)):
            s.append(f'<line x1="{x0}" y1="{CY}" x2="{x1}" y2="{CY}" stroke="{vach}" stroke-width="6" stroke-dasharray="34 26"/>')
        if uu:
            ten = "ĐƯỜNG ƯU TIÊN"
            co = round(self.CO / self._ti_le, 1)
            if uu == "ngang":  # chữ nằm trên mặt đường ưu tiên, bên phải ngã tư; 2 dòng để không vượt x 888
                x = CX + H2 + 24
                s.append(f'<text x="{x}" y="{CY - 30}" font-family="BVP" font-weight="800" font-size="{co}" fill="{self.TRANG}">'
                         f'<tspan x="{x}">ĐƯỜNG</tspan><tspan x="{x}" dy="{round(co * 1.1)}">ƯU TIÊN</tspan></text>')
            else:
                s.append(f'<text x="{CX + 18}" y="{CY + H2 + 60}" font-family="BVP" font-weight="800" font-size="{co}" fill="{self.TRANG}" '
                         f'transform="rotate(90 {CX + 18} {CY + H2 + 60})">{ten}</text>')
        return "".join(s)

    def _xa(self, x: float, y: float) -> tuple[int, int]:
        """Điểm xuất phát/điểm ra: đẩy ra xa theo tỉ lệ để vẫn ở mép khung khi sơ đồ thu nhỏ."""
        q = 1 / self._ti_le
        return round(self.CX + (x - self.CX) * q), round(self.CY + (y - self.CY) * q)

    def _so_do_giao_nhau(self, sid: str, sd: dict, D: float, t0: float = 0.0) -> tuple[str, list[str]]:
        """t0: giây bắt đầu chuyển động (sau khi chữ của thẻ mờ). Mọi tween dời thêm t0; tl.set vẫn ở 0."""
        xe = sorted(sd.get("xe") or [], key=lambda x: x["thu_tu"])
        svg, js = [self._nen_duong(sd)], []
        can = 1.3 + 1.4 * len(xe)
        k = min(1.0, max(0.4, (D - t0 - 0.4) / can))  # co giãn cho vừa thời lượng cảnh
        for i, x in enumerate(xe):
            (sx, sy), (dx, dy), (ex, ey), goc = self.LAN[x["tu"]]
            (sx, sy), (ex, ey) = self._xa(sx, sy), self._xa(ex, ey)
            xid = f"{sid}-xe{i}"
            mau = self.CAM if x["thu_tu"] == 1 else self.XANH
            svg.append(self._xe_svg(xid, x.get("loai", "xe_may"), mau, x["thu_tu"]))
            js.append(f'tl.set("#{xid}",{{x:{sx},y:{sy}}},0); tl.set("#{xid}-q",{{rotation:{goc},transformOrigin:"50% 50%"}},0);')
            js.append(f'tl.to("#{xid}",{{x:{dx},y:{dy},duration:{0.8 * k:.2f},ease:"power2.out"}},{t0 + 0.2 * k:.2f});')
            # Điểm xuất phát nằm sát mép khung (ngoài vùng an toàn): số trên xe chỉ hiện khi xe gần tới điểm dừng chờ.
            js.append(f'tl.fromTo("#{xid}-so",{{opacity:0}},{{opacity:1,duration:{0.2 * k:.2f}}},{t0 + 0.75 * k:.2f});')
            t = round(t0 + (1.3 + 1.4 * (x["thu_tu"] - 1)) * k, 2)
            js.append(f'tl.to("#{xid}",{{x:{ex},y:{ey},duration:{1.2 * k:.2f},ease:"power1.in"}},{t});')
            # Số trên xe mờ hẳn trước khi xe chạm mép vùng an toàn lúc chạy ra khỏi khung (hyperframes check).
            js.append(f'tl.to("#{xid}-so",{{opacity:0,duration:{0.25 * k:.2f}}},{round(t + 0.6 * 1.2 * k, 2)});')
            if x["thu_tu"] > 1:
                js.append(f'tl.fromTo("#{xid}",{{opacity:1}},{{opacity:0.55,duration:0.25,yoyo:true,repeat:{max(1, x["thu_tu"] - 1)}}},{round(t0 + 1.0 * k, 2)});')
        return "".join(svg), js

    def _so_do_vong_xuyen(self, sid: str, sd: dict, D: float, t0: float = 0.0) -> tuple[str, list[str]]:
        import math
        CX, CY, R = self.CX, self.CY, 165
        duong, vach = "#2B3F5C", "#E8EEF6"
        svg = []
        for ten, phi in self.GOC_NHANH.items():  # 4 nhánh đường
            rad = math.radians(phi)
            x2, y2 = CX + 3000 * math.cos(rad), CY + 3000 * math.sin(rad)
            svg.append(f'<line x1="{CX}" y1="{CY}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{duong}" stroke-width="210"/>')
        svg.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{duong}" stroke-width="130"/>')
        svg.append(f'<circle cx="{CX}" cy="{CY}" r="{R - 72}" fill="#2E7D4F" stroke="{vach}" stroke-width="6"/>')
        for a in (45, 135, 225, 315):  # mũi tên chiều đi: ngược chiều kim đồng hồ
            rad = math.radians(a)
            px, py = CX + R * math.cos(rad), CY + R * math.sin(rad)
            svg.append(f'<g transform="translate({px:.0f},{py:.0f}) rotate({a})"><path d="M -14 18 L 0 -18 L 14 18 Z" fill="{vach}"/></g>')
        xe = sorted(sd.get("xe") or [], key=lambda x: x["thu_tu"])
        js = []
        if not xe:
            return "".join(svg), js
        k = min(1.0, max(0.4, (D - t0 - 0.4) / (1.0 + 1.6 * len(xe))))
        cho = xe[1]["tu"] if len(xe) > 1 else xe[0]["tu"]
        phi_cho = self.GOC_NHANH[cho]
        for i, x in enumerate(xe):
            mau = self.CAM if x["thu_tu"] == 1 else self.XANH
            loai = x.get("loai", "xe_may")
            if x["thu_tu"] == 1:  # xe đang đi trong vòng xuyến, đến từ bên trái của xe chờ -> được đi trước
                gid = f"{sid}-vong{i}"
                svg.append(f'<g id="{gid}"><g transform="translate({CX + R},{CY})">{self._xe_svg(f"{sid}-xe{i}", loai, mau, None)}</g></g>')
                js.append(f'tl.set("#{gid}",{{rotation:{phi_cho + 100},svgOrigin:"{CX} {CY}"}},0);')
                js.append(f'tl.to("#{gid}",{{rotation:{phi_cho - 80},duration:{2.2 * k:.2f},ease:"none"}},{t0 + 0.2 * k:.2f});')
                # Qua nhánh của xe chờ rồi thì rẽ ra khỏi vòng (mờ dần), trước khi xe chờ vào vòng. Trước 2026-11-20
                # xe này đứng lại trong vòng và xe chờ chạy đè lên nó (vx-007 cảnh s3, giây 13).
                js.append(f'tl.to("#{gid}",{{opacity:0,duration:{0.3 * k:.2f}}},{t0 + 2.2 * k:.2f});')
            else:  # xe chờ ở nhánh, nhường rồi mới vào
                phi = self.GOC_NHANH[x["tu"]]
                rad = math.radians(phi)
                ax, ay = CX + (R + 150) * math.cos(rad), CY + (R + 150) * math.sin(rad)
                aid, gid = f"{sid}-xe{i}", f"{sid}-vao{i}"
                svg.append(self._xe_svg(aid, loai, mau, x["thu_tu"], (-math.sin(rad), math.cos(rad))))
                svg.append(f'<g id="{gid}" opacity="0"><g transform="translate({CX + R},{CY})">'
                           f'{self._xe_svg(f"{sid}-xv{i}", loai, mau, None)}</g></g>')
                js.append(f'tl.set("#{aid}",{{x:{ax:.0f},y:{ay:.0f}}},0); tl.set("#{aid}-q",{{rotation:{phi - 90},transformOrigin:"50% 50%"}},0);')
                # Số trên xe chờ hiện khi chữ của thẻ đã mờ (trước đó có thể nằm dưới dòng phụ / nguồn luật).
                js.append(f'tl.fromTo("#{aid}-so",{{opacity:0}},{{opacity:1,duration:0.2}},{t0:.2f});')
                t = round(t0 + (1.0 + 1.6 * (x["thu_tu"] - 1)) * k + 0.6, 2)
                js.append(f'tl.to("#{aid}",{{opacity:0,duration:0.2}},{t});')
                js.append(f'tl.set("#{gid}",{{rotation:{phi},svgOrigin:"{CX} {CY}"}},0);')
                js.append(f'tl.to("#{gid}",{{opacity:1,duration:0.2}},{t});')
                js.append(f'tl.to("#{gid}",{{rotation:{phi - 90},duration:{1.4 * k:.2f},ease:"none"}},{t});')
        return "".join(svg), js

    def bo_cuc_so_do(self, kieu: str, y0: float, y1: float) -> tuple[float, float]:
        """(tỉ lệ, tâm y trên màn hình) để phần sơ đồ cần thấy nằm trọn trong [y0, y1] px. Số trên xe giữ cỡ cố định."""
        tren, duoi, so_tren = self.TAM_VUNG[kieu]
        so = self.SO["lech"] + self.SO["r"] if so_tren else 0
        s = min(1.0, max(0.35, (y1 - y0 - so) / (tren + duoi)))
        return s, y0 + so + tren * s

    def so_do(self, sid: str, sd: dict, D: float, t0: float = 0.0, y0: float | None = None) -> tuple[str, list[str]]:
        vb = f"0 0 {W} {H}"
        self._ti_le = 1.0
        if sd["kieu"] in self.TAM_VUNG and y0 is not None:
            s, yc = self.bo_cuc_so_do(sd["kieu"], y0, self.PD_TOP_SO_DO - 20)
            self._ti_le = s
            vb = f"{self.CX - self.CX / s:.1f} {self.CY - yc / s:.1f} {W / s:.1f} {H / s:.1f}"
        if sd["kieu"] == "giao_nhau":
            ve, js = self._so_do_giao_nhau(sid, sd, D, t0)
        elif sd["kieu"] == "vong_xuyen":
            ve, js = self._so_do_vong_xuyen(sid, sd, D, t0)
        else:  # the_chu: chữ lớn trên nền thương hiệu
            chu = e(sd.get("chu", ""))
            ve = (f'<rect x="120" y="760" width="840" height="300" rx="36" fill="{self.TRANG}"/>'
                  f'<foreignObject x="150" y="780" width="780" height="260"><div xmlns="http://www.w3.org/1999/xhtml" '
                  f'style="font-family:BVP,sans-serif;font-weight:800;font-size:64px;line-height:1.15;color:{self.NAVY};'
                  f'display:flex;align-items:center;justify-content:center;height:260px;text-align:center">{chu}</div></foreignObject>')
            js = [f'tl.fromTo("#{sid}-sd",{{opacity:0,scale:0.96}},{{opacity:1,scale:1,duration:0.4,ease:"expo.out",transformOrigin:"50% 50%"}},0.1);']
        media = (f'<svg id="{sid}-sd" class="clip" data-start="0" data-duration="{D}" data-track-index="0" '
                 f'data-layout-allow-occlusion data-layout-allow-overflow '
                 f'viewBox="{vb}" width="{W}" height="{H}" style="position:absolute;left:0;top:0;'
                 f'background:linear-gradient(180deg,{self.NAVY},#16467F)">{ve}</svg>')
        self._ti_le = 1.0
        return media, js

    # ---------- cảnh có thẻ chữ ----------
    def canh(self, c: dict) -> str:
        sid = c["doan"]
        l1, l2, src, mau2, kieu = self.the.get(sid) or ("", "", None, self.XANH, "word")
        D = c["dai"]
        cid = c["id"]
        js_so_do: list[str] = []
        co_so_do = bool(c.get("so_do")) and c["so_do"].get("kieu") in self.TAM_VUNG
        f1 = co_chu(l1, 80 if co_so_do else 104, 60)
        t0 = round(min(self.SD_DOC_GIAY, max(1.4, D * 0.5)), 2) if co_so_do else 0.0
        if c.get("so_do"):
            dong1 = max(1, -(-len(l1) * f1 * 0.74 // (XW - 60)))  # số dòng ước lượng của tiêu đề
            y0 = 452 + 34 + dong1 * f1 * 1.12 + 24 if co_so_do else None
            media, js_so_do = self.so_do(sid, c["so_do"], D, t0, y0)
        elif c["anh"]:
            anh = next((p.name for p in (self.P / "hf/assets/img").glob(f"{cid}.*")), f"{cid}.jpg")
            media = (f'<img id="{sid}-v" class="clip" data-start="0" data-duration="{D}" data-track-index="0" '
                     f'src="assets/img/{anh}" alt="{e(self.TEN)}" />')
        else:
            media = (f'<video id="{sid}-v" class="clip" data-start="0" data-duration="{D}" data-track-index="0" '
                     f'src="assets/video/{cid}.mp4" muted playsinline></video>')
        f2 = co_chu(l2, 50, self.CO, he=0.62)
        tu1 = "".join(f'<span class="w">{e(w)}</span> ' for w in l1.split()).strip()
        srch = f'<div id="{sid}-src" class="src">Nguồn: {e(src)}</div>' if src else ""
        js = []
        if kieu in ("wipe", "hook"):
            js += [f'tl.fromTo("#{sid}-l1",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:0.45,ease:"expo.out"}},0.08);',
                   f'tl.fromTo("#{sid}-l2",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:0.45,ease:"expo.out"}},0.26);']
        elif kieu == "word":
            js += [f'tl.fromTo("#{sid}-l1 .w",{{opacity:0,filter:"blur(6px)"}},{{opacity:1,filter:"blur(0px)",duration:0.13,stagger:0.067,ease:"power2.out"}},0.08);',
                   f'tl.fromTo("#{sid}-l2",{{opacity:0,filter:"blur(8px)"}},{{opacity:1,filter:"blur(0px)",duration:0.18,ease:"power2.out"}},0.32);']
        else:  # scale
            js += [f'tl.fromTo("#{sid}-l1",{{scale:1.14,opacity:0,filter:"blur(10px)"}},{{scale:1,opacity:1,filter:"blur(0px)",duration:0.38,ease:"expo.out"}},0.06);',
                   f'tl.fromTo("#{sid}-l2",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:0.42,ease:"expo.out"}},0.3);']
        if src:
            js.append(f'tl.fromTo("#{sid}-src",{{opacity:0}},{{opacity:1,duration:0.25,ease:"power1.out"}},0.6);')
        if co_so_do:  # nhường chỗ cho sơ đồ: dòng phụ và nguồn luật mờ trước khi xe chạy
            dich = ", ".join(f'"#{sid}-{x}"' for x in (["l2", "src"] if src else ["l2"]))
            js.append(f'tl.to([{dich}],{{opacity:0,duration:0.3,ease:"power1.in"}},{round(t0 - 0.3, 2)});')
        if c["anh"]:
            js.append(f'tl.fromTo("#{sid}-cam",{{scale:1}},{{scale:1.08,duration:{D},ease:"none"}},0);')
        elif sid == self.kh["doan"][0]["id"] and not c.get("so_do"):
            js.append(f'tl.fromTo("#{sid}-cam",{{scale:1}},{{scale:1.06,duration:{D},ease:"none"}},0);')
        js.append(f'tl.to("#{sid}-card",{{opacity:0,filter:"blur(6px)",duration:0.16,ease:"power2.in"}},{round(D-0.18,2)});')
        js += js_so_do
        N, T = self.NAVY, self.TRANG
        return f"""<template>
  <style>
    {self.FONT}
    #root {{ position:absolute; inset:0; overflow:hidden; background:{N}; }}
    #{sid}-cam {{ position:absolute; inset:0; transform-origin:50% 55%; }}
    #{sid}-v {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; object-fit:cover; }}
    #{sid}-card {{ position:absolute; left:{X0}px; top:452px; width:{XW}px; display:flex; flex-direction:column; align-items:flex-start; gap:14px; font-family:"BVP",sans-serif; }}
    #{sid}-l1 {{ background:{N}; color:{T}; font-weight:800; font-size:{f1}px; line-height:1.12; padding:16px 28px 18px; border-radius:14px; transform-origin:0 50%; }}
    #{sid}-l2 {{ background:{mau2}; color:{T}; font-weight:800; font-size:{f2}px; line-height:1.2; padding:12px 24px 14px; border-radius:12px; text-wrap:balance; }}
    #{sid}-card .w {{ display:inline-block; }}
    #{sid}-src {{ margin-top:6px; background:rgba(14,57,112,0.88); color:{T}; font-weight:700; font-size:{self.CO}px; line-height:1.22; padding:8px 18px 10px; border-radius:10px; max-width:{XCW}px; text-wrap:balance; }}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    <div id="{sid}-cam">
      {media}
    </div>
    <div id="{sid}-card">
      <div id="{sid}-l1">{tu1}</div>
      <div id="{sid}-l2">{e(l2)}</div>
      {srch}
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join("    " + j for j in js).strip()}
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""

    # ---------- phụ đề từng chữ ----------
    @staticmethod
    def nhom_phu_de(tu: list[dict], toi_da: int = 4) -> list[list[dict]]:
        cum, cur = [], []
        for k, w in enumerate(tu):
            cur.append(w)
            nxt = tu[k + 1] if k + 1 < len(tu) else None
            if nxt is None or nxt["doan"] != w["doan"] or re.search(r"[,.?:!]$", w["text"]) or nxt["start"] - w["end"] >= 0.25:
                cum.append(cur)
                cur = []

        def cam_tach(a, b):
            ta, tb = a["text"].lower().strip(",.?:"), b["text"].lower()
            return (tb.startswith("phân") and re.search(r"\d", ta)) or ta in KHONG_TACH

        nhom = []
        for c in cum:
            n = -(-len(c) // toi_da)
            co = len(c) / n
            cuts2 = []
            for x in [round(co * i) for i in range(1, n)]:
                for dd in (0, 1, -1, 2, -2):
                    y = x + dd
                    if 0 < y < len(c) and not cam_tach(c[y - 1], c[y]) and y not in cuts2:
                        cuts2.append(y)
                        break
                else:
                    cuts2.append(x)
            prev = 0
            for y in sorted(cuts2) + [len(c)]:
                nhom.append(c[prev:y])
                prev = y
        gop = []
        for g in nhom:
            if len(g) == 1 and gop and gop[-1][0]["doan"] == g[0]["doan"] and len(gop[-1]) <= 4:
                gop[-1] = gop[-1] + g
            else:
                gop.append(g)
        return gop

    def phu_de(self) -> str:
        tu = [dict(w) for w in self.tu if w["doan"] != self.cta_id]
        nhom = self.nhom_phu_de(tu)
        bat_dau_canh = {c["doan"]: c["start"] for c in self.cat}
        canh_so_do = [(c["start"], c["start"] + c["dai"]) for c in self.cat
                      if c.get("so_do") and c["so_do"].get("kieu") in self.TAM_VUNG]
        rows, js = [], []
        for n, g in enumerate(nhom):
            a = max(round(g[0]["start"] - 0.08, 2), 0.1 if n == 0 else 0)
            if n and a < nhom[n - 1][-1]["end"]:
                a = round(nhom[n - 1][-1]["end"], 2)
            sau = nhom[n + 1][0]["start"] - 0.08 if n + 1 < len(nhom) else self.KET0
            b = round(min(sau, g[-1]["end"] + 0.6, self.KET0), 2)
            if n + 1 < len(nhom) and nhom[n + 1][0]["doan"] != g[0]["doan"] and nhom[n + 1][0]["doan"] in bat_dau_canh:
                b = round(min(b, bat_dau_canh[nhom[n + 1][0]["doan"]] - 0.02), 2)
            spans = []
            for m, w in enumerate(g):
                wid = f"pd{n}-{m}"
                w["_id"] = wid
                chu = "kW" if re.fullmatch(r"kW\.?", w["text"]) else w["text"].rstrip(",.:?!").upper()
                spans.append(f'<span id="{wid}" class="w{" kw" if tu_khoa(w["text"]) else ""}">{e(chu)}</span>')
            thap = " thap" if any(x0 - 0.05 <= a < x1 for x0, x1 in canh_so_do) else ""  # cảnh sơ đồ: phụ đề hạ thấp
            rows.append(f'<div id="pd{n}" class="clip grp{thap}" data-start="{a}" data-duration="{round(b - a, 2)}" '
                        f'data-track-index="0"><span class="pill">{" ".join(spans)}</span></div>')
            js.append(f'tl.fromTo("#pd{n} .pill",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.1,ease:"power2.out"}},{a});')
            for m, w in enumerate(g):
                kw = tu_khoa(w["text"])
                s0 = round(max(w["start"], a), 3)
                s1 = round(g[m + 1]["start"], 3) if m + 1 < len(g) else round(min(w["end"] + 0.05, b - 0.13), 3)
                js.append(f'tl.fromTo("#{w["_id"]}",{{opacity:0.45,color:"{self.TRANG}",scale:1}},{{opacity:1,color:"{self.CAM_CHU}",scale:1.08,duration:0.08,ease:"power2.out"}},{s0});')
                js.append(f'tl.to("#{w["_id"]}",{{color:"{self.CAM_CHU if kw else self.TRANG}",scale:1,duration:0.1,ease:"power2.out"}},{max(s1, round(s0 + 0.09, 3))});')
            js.append(f'tl.to("#pd{n} .pill",{{opacity:0,duration:0.12,ease:"power2.in"}},{round(b - 0.12, 3)});')
            js.append(f'tl.set("#pd{n} .pill",{{opacity:0}},{b});')
        return f"""<template>
  <style>
    {self.FONT}
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #root .grp {{ position:absolute; left:{XC0}px; top:1050px; width:{XCW}px; text-align:center; overflow:visible; font-family:"BVP",sans-serif; }}
    #root .grp.thap {{ top:{self.PD_TOP_SO_DO}px; }}
    #root .pill {{ display:inline; background:rgba(14,57,112,0.92); color:{self.TRANG}; font-weight:800; font-size:58px; line-height:1.42; padding:6px 22px 10px; border-radius:16px; -webkit-box-decoration-break:clone; box-decoration-break:clone; }}
    #root .w {{ display:inline-block; opacity:0.45; margin:0 0.09em; }}  /* từ đang đọc phóng 1.08: chừa khoảng để không dính chữ bên cạnh */
  </style>
  <div id="root" data-composition-id="phude" data-width="{W}" data-height="{H}">
    {chr(10).join("    " + r for r in rows).strip()}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join("    " + j for j in js).strip()}
    window.__timelines["phude"] = tl;
  </script>
</template>
"""

    # ---------- khung logo ----------
    def _logo_chu(self) -> str:
        lc = self.logo_chu
        nhan = f" <b>{e(lc.get('dong2_nhan', ''))}</b>" if lc.get("dong2_nhan") else ""
        return e(lc.get("dong1", "")), f"{e(lc.get('dong2', ''))}{nhan}"

    def khung(self) -> str:
        d1, d2 = self._logo_chu()
        N, T, C = self.NAVY, self.TRANG, self.CAM
        return f"""<template>
  <style>
    {self.FONT}
    #root {{ position:absolute; inset:0; pointer-events:none; }}
    #kh-tren {{ position:absolute; left:0; top:0; width:{W}px; height:380px; background:linear-gradient(180deg, rgba(0,0,0,0.30), rgba(0,0,0,0)); }}
    #kh-duoi {{ position:absolute; left:0; top:1300px; width:{W}px; height:620px; background:linear-gradient(180deg, rgba(14,57,112,0), rgba(14,57,112,0.55)); }}
    #kh-logo {{ position:absolute; left:{X0}px; top:292px; display:flex; align-items:center; gap:8px; background:{T}; border-radius:20px; padding:8px 24px 8px 8px; font-family:"BVP",sans-serif; box-shadow:0 6px 24px rgba(0,0,0,0.25); }}
    #kh-logo img {{ height:92px; width:auto; display:block; }}
    #kh-t1 {{ color:{N}; font-weight:700; font-size:{self.CO}px; letter-spacing:0.01em; line-height:1.05; }}
    #kh-t2 {{ color:{N}; font-weight:800; font-size:44px; line-height:1.05; }}
    #kh-t2 b {{ color:{C}; font-weight:800; }}
  </style>
  <div id="root" data-composition-id="khung" data-width="{W}" data-height="{H}">
    <div id="kh-tren"></div>
    <div id="kh-duoi"></div>
    <div id="kh-logo">
      <img src="assets/img/logo.png" alt="Logo {e(self.TEN)}" />
      <div><div id="kh-t1">{d1}</div><div id="kh-t2">{d2}</div></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.set("#kh-logo", {{ opacity: 1 }}, 0);
    window.__timelines["khung"] = tl;
  </script>
</template>
"""

    # ---------- màn kết ----------
    def ket(self) -> tuple[str, float]:
        D = round(self.TONG - self.KET0, 2)
        mk = self.sx.get("man_ket") or {}
        tu = [w for w in self.tu if w["doan"] == self.cta_id]
        spans, js, so_idx = [], [], []
        for m, w in enumerate(tu):
            wid = f"kt-w{m}"
            kw = tu_khoa(w["text"])
            if re.fullmatch(r"\d+", w["text"]):
                so_idx.append(m)
            spans.append(f'<span id="{wid}" class="w">{e(w["text"].rstrip(".").upper())}</span>')
            s0 = round(w["start"] - self.KET0, 3)
            s1 = round(tu[m + 1]["start"] - self.KET0, 3) if m + 1 < len(tu) else round(w["end"] - self.KET0 + 0.05, 3)
            js.append(f'tl.fromTo("#{wid}",{{opacity:0.35,color:"{self.TRANG}"}},{{opacity:1,color:"{self.CAM_CHU}",duration:0.08,ease:"power2.out"}},{max(s0, 0.0)});')
            js.append(f'tl.to("#{wid}",{{color:"{self.CAM_CHU if kw else self.TRANG}",duration:0.1}},{max(s1, round(max(s0, 0) + 0.09, 3))});')
        if so_idx:  # giữ số điện thoại trên một dòng
            a, b = so_idx[0], so_idx[-1] + 1
            cta_html = " ".join(spans[:a]) + ' <span class="nw">' + " ".join(spans[a:b]) + "</span> " + " ".join(spans[b:])
            t_zalo = round(tu[a]["start"] - self.KET0 - 0.1, 2)
        else:
            cta_html, t_zalo = " ".join(spans), 0.6
        d1, d2 = self._logo_chu()
        zalo = (f'<div id="kt-zalo"><span>ZALO</span>{e(self.LH.get("zalo") or self.LH.get("hotline") or "")}</div>'
                if mk.get("hotline", True) else "")
        # Địa chỉ: mỗi cụm giữa hai dấu phẩy không bị ngắt dòng (tên xã, tên tỉnh không bị tách đôi).
        cum_dc = [x.strip() for x in (self.LH.get("dia_chi") or "").split(",") if x.strip()]
        dc = ('<div id="kt-dc">' + ", ".join(f'<span class="nw">{e(x)}</span>' for x in cum_dc) + "</div>"
              if mk.get("dia_chi", True) else "")
        N, T, C, X = self.NAVY, self.TRANG, self.CAM, self.XANH
        return f"""<template>
  <style>
    {self.FONT}
    #root {{ position:absolute; inset:0; overflow:hidden; font-family:"BVP",sans-serif; }}
    #kt-nen {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; background:{N}; }}
    #kt-soc1 {{ position:absolute; left:-200px; top:1520px; width:1600px; height:90px; background:{X}; transform:rotate(-14deg); }}
    #kt-soc2 {{ position:absolute; left:-200px; top:1660px; width:1600px; height:90px; background:{C}; transform:rotate(-14deg); }}
    #kt-cot {{ position:absolute; left:{XC0}px; top:330px; width:{XCW}px; display:flex; flex-direction:column; align-items:center; text-align:center; }}
    #kt-the {{ background:{T}; border-radius:32px; padding:28px 56px 32px; display:flex; flex-direction:column; align-items:center; box-shadow:0 18px 50px rgba(0,0,0,0.35); }}
    #kt-the img {{ height:210px; width:auto; display:block; }}
    #kt-n1 {{ color:{N}; font-weight:700; font-size:{self.CO}px; letter-spacing:0.03em; margin-top:6px; }}
    #kt-n2 {{ color:{N}; font-weight:800; font-size:68px; line-height:1.05; }}
    #kt-n2 b {{ color:{C}; font-weight:800; }}
    #kt-cta {{ margin-top:40px; color:{T}; font-weight:800; font-size:50px; line-height:1.25; max-width:{XCW}px; text-wrap:balance; }}
    #kt-cta .w {{ display:inline-block; opacity:0.35; }}
    #kt-cta .nw, #kt-dc .nw {{ white-space:nowrap; }}
    #kt-zalo {{ margin-top:32px; background:{C}; color:{T}; font-weight:800; font-size:60px; line-height:1.1; padding:20px 40px 24px; border-radius:20px; }}
    #kt-zalo span {{ font-size:{self.CO}px; font-weight:700; margin-right:18px; vertical-align:middle; }}
    #kt-dc {{ margin-top:28px; color:rgba(255,255,255,0.88); font-weight:700; font-size:{self.CO}px; line-height:1.2; text-wrap:balance; }}
  </style>
  <div id="root" data-composition-id="ket" data-width="{W}" data-height="{H}">
    <div id="kt-nen"></div>
    <div id="kt-soc1" data-layout-allow-overflow></div>
    <div id="kt-soc2" data-layout-allow-overflow></div>
    <div id="kt-cot">
      <div id="kt-the">
        <img src="assets/img/logo.png" alt="Logo {e(self.TEN)}" />
        <div id="kt-n1">{d1}</div>
        <div id="kt-n2">{d2}</div>
      </div>
      <div id="kt-cta">{cta_html}</div>
      {zalo}
      {dc}
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#kt-nen",{{clipPath:"inset(100% 0 0 0)"}},{{clipPath:"inset(0% 0 0 0)",duration:0.4,ease:"power2.inOut"}},0);
    tl.fromTo("#kt-soc1",{{x:-1400}},{{x:0,duration:0.5,ease:"expo.out"}},0.25);
    tl.fromTo("#kt-soc2",{{x:1400}},{{x:0,duration:0.5,ease:"expo.out"}},0.32);
    tl.fromTo("#kt-the",{{opacity:0,scale:0.92}},{{opacity:1,scale:1,duration:0.4,ease:"expo.out"}},0.22);
    tl.fromTo("#kt-cta",{{opacity:0}},{{opacity:1,duration:0.15}},0.1);
    {"tl.fromTo(\"#kt-zalo\",{clipPath:\"inset(0 100% 0 0)\"},{clipPath:\"inset(0 0% 0 0)\",duration:0.45,ease:\"expo.out\"}," + str(t_zalo) + ");" if zalo else ""}
    {"tl.fromTo(\"#kt-dc\",{opacity:0},{opacity:1,duration:0.3}," + str(round(t_zalo + 0.6, 2)) + ");" if dc else ""}
    {chr(10).join("    " + j for j in js).strip()}
    window.__timelines["ket"] = tl;
  </script>
</template>
""", D

    # ---------- ghi file ----------
    def viet(self) -> dict:
        self.chep_tai_nguyen()
        comp = self.P / "hf" / "compositions"
        for c in self.cat:
            (comp / f"{c['doan']}.html").write_text(self.canh(c), encoding="utf-8")
        (comp / "phude.html").write_text(self.phu_de(), encoding="utf-8")
        (comp / "khung.html").write_text(self.khung(), encoding="utf-8")
        kt, DK = self.ket()
        (comp / "ket.html").write_text(kt, encoding="utf-8")

        def host(cid, a, d, tr, kind, z):
            return (f'<div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
                    f'data-start="{a}" data-duration="{d}" data-track-index="{tr}" data-track-kind="{kind}" '
                    f'data-width="{W}" data-height="{H}" style="z-index:{z}"></div>')
        hosts = [host(c["doan"], c["start"], c["dai"], 1, "graphics", 1) for c in self.cat]
        hosts.append(host("ket", self.KET0, DK, 1, "graphics", 1))
        hosts.append(host("khung", 0, self.KET0, 2, "graphics", 5))
        hosts.append(host("phude", 0, self.KET0, 3, "captions", 6))
        idx = f"""<!doctype html>
<html lang="vi" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(self.TEN)} – {e(self.kh['tieu_de'])}</title>
    <script src="{GSAP}"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{self.NAVY}; }}
      #root {{ position:relative; width:{W}px; height:{H}px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{self.TONG}" data-width="{W}" data-height="{H}">
      {(chr(10) + "      ").join(hosts)}
      <audio id="vo" class="clip" src="assets/audio/vo.wav" data-start="{LEAD}" data-track-index="4" data-volume="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
        (self.P / "hf" / "index.html").write_text(idx, encoding="utf-8")
        return {"tong": self.TONG, "ket0": self.KET0}

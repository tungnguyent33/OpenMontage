"""Viết dự án HyperFrames (<dự án>/hf/) từ kế hoạch + mốc giọng + đoạn cắt. Chuyển từ projects/vx-demo-01/dung_hf.py.

Mọi phần tử có thời gian được ghi thẳng vào HTML (sửa được trong HyperFrames Studio).
Màu, font, logo, liên hệ lấy từ brand.json; chữ cạnh logo lấy từ san-xuat.yaml man_ket.logo_chu.
Vùng an toàn chung TikTok/Reels/Shorts: x 120..888, y 288..1248; dưới y 840 TikTok chỉ an toàn tới x 780.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

LEAD = 0.15
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

    # ---------- cảnh có thẻ chữ ----------
    def canh(self, c: dict) -> str:
        sid = c["doan"]
        l1, l2, src, mau2, kieu = self.the.get(sid) or ("", "", None, self.XANH, "word")
        D = c["dai"]
        cid = c["id"]
        if c["anh"]:
            anh = next((p.name for p in (self.P / "hf/assets/img").glob(f"{cid}.*")), f"{cid}.jpg")
            media = (f'<img id="{sid}-v" class="clip" data-start="0" data-duration="{D}" data-track-index="0" '
                     f'src="assets/img/{anh}" alt="{e(self.TEN)}" />')
        else:
            media = (f'<video id="{sid}-v" class="clip" data-start="0" data-duration="{D}" data-track-index="0" '
                     f'src="assets/video/{cid}.mp4" muted playsinline></video>')
        f1 = co_chu(l1, 104, 60)
        f2 = co_chu(l2, 50, 34, he=0.62)
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
        if c["anh"]:
            js.append(f'tl.fromTo("#{sid}-cam",{{scale:1}},{{scale:1.08,duration:{D},ease:"none"}},0);')
        elif sid == self.kh["doan"][0]["id"]:
            js.append(f'tl.fromTo("#{sid}-cam",{{scale:1}},{{scale:1.06,duration:{D},ease:"none"}},0);')
        js.append(f'tl.to("#{sid}-card",{{opacity:0,filter:"blur(6px)",duration:0.16,ease:"power2.in"}},{round(D-0.18,2)});')
        N, T = self.NAVY, self.TRANG
        return f"""<template>
  <style>
    {self.FONT}
    #root {{ position:absolute; inset:0; overflow:hidden; background:{N}; }}
    #{sid}-cam {{ position:absolute; inset:0; transform-origin:50% 55%; }}
    #{sid}-v {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; object-fit:cover; }}
    #{sid}-card {{ position:absolute; left:{X0}px; top:452px; width:{XW}px; display:flex; flex-direction:column; align-items:flex-start; gap:14px; font-family:"BVP",sans-serif; }}
    #{sid}-l1 {{ background:{N}; color:{T}; font-weight:800; font-size:{f1}px; line-height:1.12; padding:16px 28px 18px; border-radius:14px; transform-origin:0 50%; }}
    #{sid}-l2 {{ background:{mau2}; color:{T}; font-weight:800; font-size:{f2}px; line-height:1.2; padding:12px 24px 14px; border-radius:12px; }}
    #{sid}-card .w {{ display:inline-block; }}
    #{sid}-src {{ margin-top:6px; background:rgba(14,57,112,0.88); color:{T}; font-weight:700; font-size:30px; line-height:1.3; padding:8px 18px; border-radius:10px; max-width:{XW}px; }}
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
            rows.append(f'<div id="pd{n}" class="clip grp" data-start="{a}" data-duration="{round(b - a, 2)}" '
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
    #root .pill {{ display:inline; background:rgba(14,57,112,0.92); color:{self.TRANG}; font-weight:800; font-size:58px; line-height:1.42; padding:6px 22px 10px; border-radius:16px; -webkit-box-decoration-break:clone; box-decoration-break:clone; }}
    #root .w {{ display:inline-block; opacity:0.45; }}
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
    #kh-t1 {{ color:{N}; font-weight:700; font-size:28px; letter-spacing:0.02em; line-height:1.1; }}
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
        dc = f'<div id="kt-dc">{e(self.LH.get("dia_chi") or "")}</div>' if mk.get("dia_chi", True) else ""
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
    #kt-n1 {{ color:{N}; font-weight:700; font-size:34px; letter-spacing:0.05em; margin-top:6px; }}
    #kt-n2 {{ color:{N}; font-weight:800; font-size:68px; line-height:1.05; }}
    #kt-n2 b {{ color:{C}; font-weight:800; }}
    #kt-cta {{ margin-top:40px; color:{T}; font-weight:800; font-size:50px; line-height:1.25; max-width:{XCW}px; }}
    #kt-cta .w {{ display:inline-block; opacity:0.35; }}
    #kt-cta .nw {{ white-space:nowrap; }}
    #kt-zalo {{ margin-top:32px; background:{C}; color:{T}; font-weight:800; font-size:60px; line-height:1.1; padding:20px 40px 24px; border-radius:20px; }}
    #kt-zalo span {{ font-size:40px; font-weight:700; margin-right:18px; vertical-align:middle; }}
    #kt-dc {{ margin-top:28px; color:rgba(255,255,255,0.88); font-weight:700; font-size:32px; }}
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

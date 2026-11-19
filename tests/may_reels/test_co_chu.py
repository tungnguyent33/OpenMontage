"""Cỡ chữ đọc từ nguồn HyperFrames và vùng an toàn (may_reels/co_chu.py), áp vào tiêu chí phu_de khi chấm."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from may_reels import cham_diem as C
from may_reels import co_chu
from tests.may_reels.test_cham_diem import RUBRIC, agent_de_dai, can_ffmpeg, chep_gia, du_an_mau

HTML = """<template>
  <style>
    @font-face{font-family:"BVP";src:url("x.ttf");font-weight:800;}
    #root { position:absolute; }
    #card { font-size:60px; }
    #card .nho { font-size:0.5em; }
    .pill { font-size:30px; }
    #root .pill { font-size:58px; }
    #src { font-size:30px; }
  </style>
  <div id="root">
    <div id="card">Tiêu đề <b>đậm</b><span class="nho">phụ</span></div>
    <div class="pill">Phụ đề</div>
    <div id="src">Nguồn: Luật 36/2024/QH15</div>
    <div style="font-size:20px">inline</div>
    <div data-layout-ignore style="font-size:10px">trang trí</div>
    <svg viewBox="0 0 540 960" width="1080" height="1920"><text font-size="24">1</text></svg>
  </div>
  <script>const tl = gsap.timeline({ paused: true }); // font-size:5px trong script không tính</script>
</template>"""


def test_co_chu_theo_cascade_ke_thua_inline_svg(tmp_path: Path):
    f = tmp_path / "a.html"
    f.write_text(HTML, encoding="utf-8")
    co = {x["chu"]: x["px"] for x in co_chu.do_co_chu_file(f)}
    assert co["Tiêu đề"] == 60 and co["đậm"] == 60          # kế thừa
    assert co["phụ"] == 30                                   # em theo cha
    assert co["Phụ đề"] == 58                                # #root .pill (id+class) thắng .pill
    assert co["Nguồn: Luật 36/2024/QH15"] == 30
    assert co["inline"] == 20                                # style inline
    assert co["1"] == 48                                     # SVG: 24 x (1080/540)
    assert "trang trí" not in co                             # data-layout-ignore
    assert not any("5px" in k for k in co)


def test_do_co_chu_gom_nhom_duoi_nguong(tmp_path: Path):
    hf = tmp_path / "hf"
    (hf / "compositions").mkdir(parents=True)
    (hf / "index.html").write_text("<html><body><div id='root'></div></body></html>", encoding="utf-8")
    (hf / "compositions" / "s2.html").write_text(HTML, encoding="utf-8")
    r = co_chu.do_co_chu(hf, 42)
    assert r["nho_nhat"] == 20
    assert {x["px"] for x in r["duoi_toi_thieu"]} == {20, 30}
    assert "nguồn luật 30px" in C.tom_tat_chu_nho(r)


def test_mau_do_hoa_moi_chu_tu_42px(tmp_path: Path):
    """Mẫu đồ họa (may_reels/dung/hf.py): mọi chữ, kể cả nguồn luật, khung logo, số trên xe, màn kết, đạt 42px."""
    goc, P, kh = du_an_mau(tmp_path)
    nguong = RUBRIC["tieu_chi"]["phu_de"]["co_chu_toi_thieu"]
    r = co_chu.do_co_chu(P / "hf", nguong)
    assert r["duoi_toi_thieu"] == [], r["duoi_toi_thieu"]
    src = [x for f in (P / "hf/compositions").glob("s*.html") for x in co_chu.do_co_chu_file(f)
           if x["chu"].startswith("Nguồn:")]
    assert src and all(x["px"] >= nguong for x in src)


def test_mau_doc_nguong_tu_rubric(tmp_path: Path):
    goc, P, kh = du_an_mau(tmp_path)
    rb = goc / "brand/kenhthu/rubric.yaml"
    y = yaml.safe_load(rb.read_text(encoding="utf-8"))
    y["tieu_chi"]["phu_de"]["co_chu_toi_thieu"] = 50
    rb.write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    from may_reels.dung.hf import co_chu_toi_thieu
    assert co_chu_toi_thieu("kenhthu", goc) == 50


def test_doc_ngoai_vung_tu_bao_cao_hyperframes():
    bc = {"layout": {"findings": [
        {"code": "outside_safe_zone", "text": "2", "selector": "#s5-xe1 text", "sourceFile": "compositions/s5.html",
         "message": "outside the safe area: TikTok (right edge)", "firstSeen": 24.3},
        {"code": "outside_safe_zone", "text": "2", "selector": "#s5-xe1 text", "sourceFile": "compositions/s5.html",
         "message": "x", "firstSeen": 22.0},
        {"code": "content_overlap", "text": "1"}]}}
    ds = co_chu.doc_ngoai_vung(bc)
    assert len(ds) == 1 and ds[0]["file"] == "s5.html" and ds[0]["giay"] == 22.0


def _do(co_chu_kq=None, ngoai=None, loi=""):
    return {"nhip": {"so_lan_vuot": 0, "khoang_dai_nhat": 2, "khoang_vuot": []}, "ti_le_canh_that": 1.0,
            "thuong_hieu": {"mau": True}, "cta": {"nguyen_van": True, "so_cta": 1}, "moc_chu_dau": 0.1,
            "dung_yen": 50, "phu_de": {"co_phu_de": True, "so_dong_lon_nhat": 1, "trong_vung_an_toan": True,
                                        "tuong_phan": 9},
            "co_chu": co_chu_kq or {"toi_thieu": 42, "duoi_toi_thieu": []},
            "vung_an_toan": {"ngoai_vung": ngoai or [], "loi": loi}}


def _agent_toi_da():
    return {m: {"diem": c["trong_so"], "ly_do": "ok"} for m, c in RUBRIC["tieu_chi"].items()}


def test_chu_nho_tru_diem_phu_de_va_ghi_canh_bao():
    cc = {"toi_thieu": 42, "duoi_toi_thieu": [{"file": "s2.html", "phan_tu": "#s2-src", "px": 30, "vi_du": "Nguồn", "so_lan": 1},
                                              {"file": "ket.html", "phan_tu": "#kt-dc", "px": 32, "vi_du": "Thôn", "so_lan": 1}]}
    tc, diem, _, cb = C.tinh_diem(RUBRIC, _do(cc), _agent_toi_da(), 100)
    pd = next(x for x in tc if x["ma"] == "phu_de")
    assert pd["diem"] == RUBRIC["tieu_chi"]["phu_de"]["khi_chu_nho"]
    assert "dưới 42px" in pd["ly_do"]
    assert diem == 100 - (RUBRIC["tieu_chi"]["phu_de"]["trong_so"] - RUBRIC["tieu_chi"]["phu_de"]["khi_chu_nho"])
    assert any(x.startswith("Chữ dưới 42px: nguồn luật 30px; màn kết 32px") for x in cb)


def test_ngoai_vung_tru_diem_va_loi_check_chi_canh_bao():
    ngoai = [{"file": "s5.html", "chu": "2", "phan_tu": "#s5-xe1", "vi_tri": "TikTok", "giay": 24.3}]
    tc, _, _, cb = C.tinh_diem(RUBRIC, _do(ngoai=ngoai), _agent_toi_da(), 100)
    assert next(x for x in tc if x["ma"] == "phu_de")["diem"] == RUBRIC["tieu_chi"]["phu_de"]["khi_ngoai_vung"]
    assert any("ngoài vùng an toàn" in x for x in cb)
    tc, diem, _, cb = C.tinh_diem(RUBRIC, _do(loi="không chạy được hyperframes check"), _agent_toi_da(), 100)
    assert diem == 100 and any(x.startswith("Chưa đo được vùng an toàn") for x in cb)


@can_ffmpeg
def test_cham_video_ghi_co_chu_va_vung_vao_score(tmp_path: Path):
    goc, P, kh = du_an_mau(tmp_path)
    goi = []
    bao_cao = {"layout": {"findings": [{"code": "outside_safe_zone", "text": "1", "sourceFile": "compositions/s3.html",
                                        "firstSeen": 3.0}]}}
    C.cham_video(kh["ma_video"], goc=goc, agent=agent_de_dai(goi), chep=chep_gia(kh), log=lambda s: None,
                 kiem_vung=lambda hf, v: (bao_cao, ""))
    score = json.loads((P / "renders/score.json").read_text(encoding="utf-8"))
    assert score["do_dac"]["co_chu"]["duoi_toi_thieu"] == []
    assert score["do_dac"]["vung_an_toan"]["ngoai_vung"][0]["chu"] == "1"
    assert any("ngoài vùng an toàn" in x for x in score["canh_bao"])
    assert "co_chu" in goi[0]["do_dac"]   # agent cũng thấy số đo trong bang_chung.json

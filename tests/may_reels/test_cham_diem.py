"""Chấm điểm theo rubric, chặn cứng, chống chấm dễ dãi, cham-lai, hieu-chinh. Agent và PhoWhisper đều giả.

Ba mẫu cố ý hỏng (Việc 7) dựng thành dự án thật (HTML HyperFrames bằng may_reels.dung.hf.Dung, video bằng FFmpeg):
  bao_dau  : "bao đậu" trong lời đọc                  -> phải bị CHẶN
  logo     : 3 giây đầu là logo đứng yên, không chữ   -> phải DƯỚI NGƯỠNG
  canh_tam : khoảng 80% thời lượng là cảnh tạm        -> phải DƯỚI NGƯỠNG
Agent giả chấm TỐI ĐA mọi tiêu chí: chứng minh điểm thấp đến từ số đo của máy, không nhờ agent khó tính.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from may_reels import cham_diem as C
from may_reels import sheet as S
from may_reels.cot_sheet import HANG_CHO, NHAT_KY, Y_TUONG
from may_reels.dung import canh
from may_reels.dung.hf import Dung
from may_reels.dung.kiem_tra import DIEM_TRU, kiem
from may_reels.hang_cho import gon_canh_bao
from may_reels.hieu_chinh import cham_lai, hieu_chinh, phan_tich
from may_reels.san_xuat import MA_OK, san_xuat
from tests.may_reels.sheet_gia import BangGia
from tests.may_reels.test_san_xuat import (BRAND, SO_DO, SX, agent_gia, dung_gia, ke_hoach, moc_gia,  # noqa: F401
                                           nha_may)

REPO = Path(__file__).resolve().parents[2]
RUBRIC = yaml.safe_load((REPO / "brand" / "vanxuan" / "rubric.yaml").read_text(encoding="utf-8"))
CO_FFMPEG = bool(shutil.which("ffmpeg"))
can_ffmpeg = pytest.mark.skipif(not CO_FFMPEG, reason="cần FFmpeg")


# ---------------------------------------------------------------- dự án mẫu
def _brand(goc: Path) -> dict:
    b = copy.deepcopy(BRAND)
    b["cam"]["cum_tu_cam"] = ["bao đỗ", "bao đậu", "đảm bảo đỗ"]
    b["cam"]["cau_sao_da_chot"] = ["bạn có biết"]
    b["chu_de"][0].update(y_chinh="Bên phải đi trước", nguon_doi_chieu="Luật 1/2024 Điều 1 khoản 2")
    logo = goc / "brand/kenhthu/assets/logo.png"
    b["assets"] = {"logo": {"duong_dan": "brand/kenhthu/assets/logo.png",
                            "sha1": hashlib.sha1(logo.read_bytes()).hexdigest()[:12]}}
    return b


def _video(p: Path, dung_yen_giay: float = 0.0, dai: float = 4.5) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    s = "270x480"
    if dung_yen_giay:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x0E3970:s={s}:d={dung_yen_giay}:r=30",
               "-f", "lavfi", "-i", f"testsrc2=s={s}:d={dai - dung_yen_giay}:r=30",
               "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]"]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={s}:d={dai}:r=30"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)


def du_an_mau(tmp_path: Path, kieu: str = "tot") -> tuple[Path, Path, dict]:
    goc = tmp_path / "repo"
    (goc / "brand/kenhthu/assets/fonts").mkdir(parents=True)
    for f in ("F-ExtraBold.ttf", "F-Bold.ttf"):
        (goc / "brand/kenhthu/assets/fonts" / f).write_bytes(b"f")
    (goc / "brand/kenhthu/assets/logo.png").write_bytes(b"png-logo")
    brand = _brand(goc)
    (goc / "brand/kenhthu/brand.json").write_text(json.dumps(brand, ensure_ascii=False), encoding="utf-8")
    (goc / "brand/kenhthu/san-xuat.yaml").write_text(yaml.safe_dump(SX, allow_unicode=True), encoding="utf-8")
    shutil.copyfile(REPO / "brand/vanxuan/rubric.yaml", goc / "brand/kenhthu/rubric.yaml")
    kh = ke_hoach(ma_video="kt-001-cd-a")
    if kieu == "bao_dau":
        kh["doan"][1]["loi"] = kh["doan"][1]["loi"].replace("được ưu tiên", "được ưu tiên, học ở đây bao đậu")
    if kieu == "logo":
        kh["doan"][0]["the"] = None
    if kieu == "canh_tam":
        kh["thieu_canh"] = []
        for i in (1, 2, 3, 4):
            kh["doan"][i]["canh"] = copy.deepcopy(SO_DO)
            kh["thieu_canh"].append({"doan": kh["doan"][i]["id"], "y_can_canh": "x", "mo_ta_canh": "x",
                                     "goi_y_quay": "x", "ly_do": "x"})
    P = goc / "projects" / kh["ma_video"]
    (P / "hf/assets/img").mkdir(parents=True)
    (P / "hf/assets/img/c4.jpg").write_bytes(b"j")
    moc = moc_gia(kh)
    cat = canh.tinh_cat(kh, brand, SX, moc)
    tu = []
    for d in kh["doan"]:
        if kieu == "logo" and d["id"] == "s1":
            continue  # 3 giây đầu: không phụ đề, không thẻ chữ
        for i, w in enumerate(d["loi"].split()):
            tu.append({"doan": d["id"], "text": w, "start": round(moc[d["id"]]["start"] + 0.15 + i * 0.2, 2),
                       "end": round(moc[d["id"]]["start"] + 0.3 + i * 0.2, 2)})
    Dung(P, kh, brand, SX, cat, tu, {"doan": list(moc.values())}, goc).viet()
    (P / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
    (P / "cat_canh.json").write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    (P / "assets/audio").mkdir(parents=True)
    (P / "assets/audio/tu_phu_de.json").write_text(json.dumps(tu, ensure_ascii=False), encoding="utf-8")
    (P / "checkpoint_compose.json").write_text(json.dumps(
        {"artifacts": {"final_review": {"metadata": {"diem_ky_thuat": 100}}}}), encoding="utf-8")
    if CO_FFMPEG:
        _video(P / "renders/final.mp4", 3.6 if kieu == "logo" else 0.0)
    return goc, P, kh


def chep_gia(kh: dict, them: str = ""):
    def ham(video, ra, *, sha1, model, goc=None):
        kq = {"sha1": sha1, "model": model, "van_ban": " ".join(d["loi"] for d in kh["doan"]) + " " + them, "doan": []}
        ra.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
        return kq
    return ham


def agent_de_dai(goi: list | None = None):
    """Agent dễ dãi: chấm tối đa mọi tiêu chí agent."""
    def ham(prompt, *, du_an, goc):
        bc = json.loads((du_an / "review/bang_chung.json").read_text(encoding="utf-8"))
        if goi is not None:
            goi.append(bc)
        tc = {m: {"diem": v["toi_da"], "ly_do": "Rất tốt."} for m, v in bc["tieu_chi_agent"].items()}
        (du_an / "renders/score.json").write_text(json.dumps({"tieu_chi": tc}, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 1200, "num_turns": 2}
    return ham


def cham(goc, kh, them_loi: str = "", goi=None):
    return C.cham_video(kh["ma_video"], goc=goc, agent=agent_de_dai(goi), chep=chep_gia(kh, them_loi), log=lambda s: None)


# ---------------------------------------------------------------- Việc 7: ba mẫu hỏng + một mẫu tốt
@can_ffmpeg
def test_mau_tot_dat_nguong_va_score_hop_schema(tmp_path):
    goc, P, kh = du_an_mau(tmp_path)
    goi = []
    kc = cham(goc, kh, goi=goi)
    assert kc.chan == [] and kc.diem_qa >= 75, kc.ly_do_tru
    sc = json.loads((P / "renders/score.json").read_text(encoding="utf-8"))
    C.kiem_score(sc)
    assert sc["dat"] and sum(x["diem"] for x in sc["tieu_chi"]) == pytest.approx(sc["diem_qa"], abs=0.6)
    assert {x["ma"] for x in sc["tieu_chi"]} == set(RUBRIC["tieu_chi"])
    assert all(x["ly_do"] for x in sc["tieu_chi"])
    bc = goi[0]  # agent chấm từ bằng chứng của bản đã render
    assert bc["khung_hook"] == ["hook-0.0s.png", "hook-0.5s.png", "hook-1.5s.png", "hook-3.0s.png"]
    assert all((P / "review" / f).is_file() for f in bc["khung_hook"]) and bc["chep_loi"]
    assert set(bc["tieu_chi_agent"]) == {"hook", "dung_gia_tri", "phu_de", "cta"}


@can_ffmpeg
def test_mau_bao_dau_trong_loi_doc_bi_chan(tmp_path):
    goc, P, kh = du_an_mau(tmp_path, "bao_dau")
    kc = cham(goc, kh)
    assert any("bao đậu" in x for x in kc.chan)
    sc = json.loads((P / "renders/score.json").read_text(encoding="utf-8"))
    assert sc["dat"] is False and sc["chan_cung"]


@can_ffmpeg
def test_mau_logo_dung_yen_3_giay_dau_duoi_nguong(tmp_path):
    goc, P, kh = du_an_mau(tmp_path, "logo")
    kc = cham(goc, kh)
    hook = next(x for x in kc.tieu_chi if x["ma"] == "hook")
    assert kc.chan == [] and kc.diem_qa < 75, (kc.diem_qa, kc.ly_do_tru)
    assert hook["diem"] <= RUBRIC["tieu_chi"]["hook"]["tran"]["khi_dung_yen"] and "đứng yên" in hook["ly_do"]
    assert kc.ly_do_tru[0].startswith("Trần tổng")


@can_ffmpeg
def test_mau_80_phan_tram_canh_tam_duoi_nguong(tmp_path):
    goc, P, kh = du_an_mau(tmp_path, "canh_tam")
    kc = cham(goc, kh)
    ct = next(x for x in kc.tieu_chi if x["ma"] == "chan_thuc")
    sc = json.loads((P / "renders/score.json").read_text(encoding="utf-8"))
    assert sc["do_dac"]["ti_le_canh_that"] <= 0.25
    assert kc.chan == [] and kc.diem_qa < 75 and ct["diem"] <= 5
    assert any(x.startswith("Nhiều cảnh tạm") for x in kc.canh_bao)


@can_ffmpeg
def test_chu_khong_dau_tren_man_hinh_cung_bi_chan(tmp_path):
    goc, P, kh = du_an_mau(tmp_path)
    f = P / "hf/compositions/s3.html"
    f.write_text(f.read_text(encoding="utf-8").replace("</template>", "<div>HOC LA BAO DAU</div></template>"),
                 encoding="utf-8")
    kc = cham(goc, kh)
    assert any("chữ trên màn hình" in x and "bao đậu" in x for x in kc.chan)


# ---------------------------------------------------------------- chặn cứng: đơn vị
def test_tim_cum_tu_dung_dau_va_khong_dau_khong_bat_nham():
    cum = ["bao đậu", "đảm bảo đỗ", "bạn có biết"]
    assert C.tim_cum_tu("Học ở đây BAO ĐẬU nhé", cum) == ["bao đậu"]
    assert C.tim_cum_tu("hoc o day bao dau", cum) == ["bao đậu"]
    assert C.tim_cum_tu("Bạn có biết vì sao?", cum) == ["bạn có biết"]
    assert C.tim_cum_tu("Phải đảm bảo độ an toàn, bao đâu cũng được", cum) == []


def test_so_khong_nguon():
    cho_phep = C.bo_dau("Luật 36/2024/QH15 Điều 11; QCVN 41:2024 0823 279 999 Thôn 18")
    vb = "Theo Luật 36/2024/QH15, Điều 22 khoản 2: nhớ 3 điều. Gọi 0823 279 999. Phạt 800.000 đồng. QCVN 41:2024"
    assert C.so_khong_nguon(vb, cho_phep, 10) == ["800.000", "dieu 22", "khoan 2"]
    assert C.so_khong_nguon("Điều 11", cho_phep, 10) == []


def test_tai_san_ngoai_kho_va_url_ngoai(tmp_path):
    P = tmp_path / "p"
    (P / "hf/compositions").mkdir(parents=True)
    (P / "hf/index.html").write_text('<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>'
                                     '<div data-composition-src="compositions/s1.html"></div>', encoding="utf-8")
    (P / "hf/compositions/s1.html").write_text('<video src="assets/video/c1.mp4"></video><img src="assets/img/ai.png">'
                                               '<img src="https://pexels.com/x.jpg">', encoding="utf-8")
    kh = {"doan": [{"id": "s1", "canh": {"ma": "v1"}}], "thieu_canh": []}
    cat = [{"id": "c1", "doan": "s1", "ma": "v1", "anh": False}, {"id": "c2", "doan": "s2", "ma": "bi-loai", "anh": False}]
    loi = C.tai_san_ngoai(P, kh, BRAND, cat, RUBRIC)
    assert any("ai.png" in x for x in loi) and any("pexels" in x for x in loi) and any("bi-loai" in x for x in loi)
    assert not any("c1.mp4" in x or "gsap" in x for x in loi)


# ---------------------------------------------------------------- gộp điểm, rubric, kỹ thuật
def test_rubric_tong_100_va_khong_viet_cung_trong_so():
    assert sum(v["trong_so"] for v in RUBRIC["tieu_chi"].values()) == 100
    src = (REPO / "may_reels/cham_diem.py").read_text(encoding="utf-8")
    for so in ("20", "15"):  # trọng số không nằm trong code
        assert f'"trong_so": {so}' not in src and f"toi_da = {so}" not in src


def test_doc_rubric_bao_loi_khi_tong_sai(tmp_path):
    (tmp_path / "brand/k").mkdir(parents=True)
    rb = copy.deepcopy(RUBRIC)
    rb["tieu_chi"]["hook"]["trong_so"] = 25
    (tmp_path / "brand/k/rubric.yaml").write_text(yaml.safe_dump(rb, allow_unicode=True), encoding="utf-8")
    with pytest.raises(C.LoiRubric):
        C.doc_rubric("k", tmp_path)


def test_ky_thuat_quy_doi_va_tran_agent():
    do = {"moc_chu_dau": 0.1, "dung_yen": 30, "ti_le_canh_that": 1.0,
          "nhip": {"khoang_dai_nhat": 3, "so_lan_vuot": 0, "khoang_vuot": []},
          "phu_de": {"co_phu_de": True, "so_dong_lon_nhat": 3, "trong_vung_an_toan": True, "tuong_phan": 10},
          "thuong_hieu": {"mau": True, "font": True, "logo": False, "man_ket": True},
          "cta": {"nguyen_van": True, "so_cta": 2}}
    agent = {m: {"diem": 100, "ly_do": "x"} for m in RUBRIC["tieu_chi"]}
    tc, diem, tran, _ = C.tinh_diem(RUBRIC, do, agent, 80)
    d = {x["ma"]: x["diem"] for x in tc}
    assert d["ky_thuat"] == 8 and d["thuong_hieu"] == 7.5
    assert d["phu_de"] == RUBRIC["tieu_chi"]["phu_de"]["khi_vi_pham"] and d["cta"] == 5
    assert d["hook"] == 20  # agent không được vượt toi_da


def test_diem_ky_thuat_doi_ten_va_bo_canh_tam():
    import inspect
    assert "canh_tam" not in DIEM_TRU and "so_canh_tam" not in inspect.signature(kiem).parameters
    assert "diem_ky_thuat" in (REPO / "may_reels/dung/kiem_tra.py").read_text(encoding="utf-8")


def test_gon_canh_bao_toi_da_3_dong():
    ds = ["Dưới ngưỡng (60/75)", "Hook -12: " + "x" * 200, "Nhịp -3: dài", "Có cảnh tạm", "Dưới ngưỡng (60/75)"]
    g = gon_canh_bao(ds, 3, 90)
    assert len(g) == 3 and g[0].startswith("Dưới ngưỡng") and len(g[1]) <= 90


# ---------------------------------------------------------------- luồng sản xuất: chặn, vòng sửa
def test_san_xuat_bi_chan_thi_khong_vao_hang_cho(nha_may):  # noqa: F811
    goc, bang = nha_may
    kb = {"kt-005-cd-a": [(MA_OK, {"diem_qa": 95, "chan": ["Cụm từ cấm trong lời nghe được: bao đậu"]})]}
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), dung=dung_gia(kb), log=lambda s: None)
    assert ds[0].trang_thai == "loi" and "bao đậu" in ds[0].loi and ds[0].vong == 0
    assert S.doc_dong(bang, HANG_CHO) == []
    job = json.loads((goc / "projects/kt-005-cd-a/reel_job.json").read_text(encoding="utf-8"))
    assert job["trang_thai"] == "loi" and "Chặn cứng" in job["loi"]


def test_vong_sua_gui_ly_do_tru_diem_noi_dung_va_canh_bao_gon(nha_may):  # noqa: F811
    goc, bang = nha_may
    goi = []
    kb = {"kt-005-cd-a": [(MA_OK, {"diem_qa": 60}), (MA_OK, {"diem_qa": 65}), (MA_OK, {"diem_qa": 70})]}
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None)
    assert ds[0].vong == 2 and len(goi) == 3
    assert "Hook 0-3 giây -40" in goi[1][2]["phan_hoi"] and "Hook 0-3 giây -35" in goi[2][2]["phan_hoi"]
    hang = S.doc_dong(bang, HANG_CHO)
    cb = hang[0]["canh_bao"].split("\n")
    assert len(cb) <= 3 and cb[0] == "Dưới ngưỡng (70/75)" and cb[1].startswith("Hook 0-3 giây -30")
    nk = [d for d in S.doc_dong(bang, NHAT_KY) if d["buoc"] == "cham_diem"]
    assert len(nk) == 3  # mỗi lần chấm một dòng Nhật ký


# ---------------------------------------------------------------- Sheet: cột của người
def test_sheet_init_khong_tao_trung_cot_nguoi_da_tu_them():
    bang = BangGia()
    S.khoi_tao(bang)
    t = bang.tab("Hàng chờ")
    assert {"diem_cua_toi", "nhan_xet"} <= set(t.doc_tat_ca()[0])
    assert HANG_CHO.lay("diem_cua_toi").cua_nguoi and HANG_CHO.lay("nhan_xet").cua_nguoi
    # người dùng tự thêm hai cột (khác vị trí) trước khi có khai báo: init không thêm lần nữa
    bang2 = BangGia()
    ws = bang2.tao_tab("Hàng chờ", 10, 30)
    cot_cu = [c for c in HANG_CHO.ten_cot if c not in ("diem_cua_toi", "nhan_xet")]
    ws.ghi_o([(1, i, c) for i, c in enumerate(["nhan_xet"] + cot_cu + ["diem_cua_toi"], start=1)])
    kq = S.khoi_tao(bang2)
    assert "Hàng chờ" not in kq.cot_them
    hang = bang2.tab("Hàng chờ").doc_tat_ca()[0]
    assert hang.count("diem_cua_toi") == 1 and hang.count("nhan_xet") == 1


def test_may_khong_ghi_cot_diem_cua_toi():
    bang = BangGia()
    S.khoi_tao(bang)
    with pytest.raises(S.LoiGhiCotNguoi):
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "a", "nen_tang": "fb_reels", "diem_cua_toi": "8"}])


# ---------------------------------------------------------------- cham-lai, hieu-chinh
def _hang_cho(bang, rows):
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": m, "kenh": "kenhthu", "nen_tang": nt, "diem_qa": "91",
                                      "canh_bao": "Có cảnh tạm (sơ đồ): s3\nDưới ngưỡng (60/75)", "duyet": "Chờ duyệt"}
                                     for m, nt, *_ in rows], ngoai_le_duyet="khoi_tao")
    t = bang.tab("Hàng chờ")
    h = t.doc_tat_ca()
    td = h[0]
    for m, nt, diem, nx in rows:
        r = next(i for i, x in enumerate(h, start=1) if i > 1 and x[0] == m and x[td.index("nen_tang")] == nt)
        t.dat(r, td.index("diem_cua_toi") + 1, diem)
        t.dat(r, td.index("nhan_xet") + 1, nx)


def test_cham_lai_cap_nhat_diem_va_canh_bao(nha_may, monkeypatch):  # noqa: F811
    goc, bang = nha_may
    for m in ("kt-001-cd-a", "kt-002-cd-b"):
        P = goc / "projects" / m
        (P / "renders").mkdir(parents=True)
        (P / "renders/final.mp4").write_bytes(b"v")
        (P / "ke_hoach.json").write_text("{}", encoding="utf-8")
    _hang_cho(bang, [("kt-001-cd-a", "fb_reels", "", ""), ("kt-001-cd-a", "tiktok", "", ""),
                     ("kt-002-cd-b", "fb_reels", "", ""), ("ngoai-may", "fb_reels", "", "")])

    def cham_that_gia(ma, *, goc, log=None, tom=None):
        from may_reels.cham_diem import KetQuaCham
        if ma == "kt-002-cd-b":
            return KetQuaCham(ma, diem_qa=88, chan=["Số/số hiệu luật không có trong y_chinh/nguon_doi_chieu: dieu 22"])
        return KetQuaCham(ma, diem_qa=62, ly_do_tru=["Nhịp -6: 2 khoảng quá 4s", "Hook -5: chậm"])
    ket = cham_lai(bang, "kenhthu", goc=goc, cham=cham_that_gia, log=lambda s: None)
    assert [k["trang_thai"] for k in ket] == ["ok", "ok", "bo_qua"]
    rows = {(d["ma_video"], d["nen_tang"]): d for d in S.doc_dong(bang, HANG_CHO)}
    a = rows[("kt-001-cd-a", "tiktok")]
    assert a["diem_qa"] == "62" and a["canh_bao"].split("\n") == ["Dưới ngưỡng (62/75)", "Nhịp -6: 2 khoảng quá 4s",
                                                                   "Hook -5: chậm"]
    b = rows[("kt-002-cd-b", "fb_reels")]
    assert b["canh_bao"].startswith("CHẶN: ") and "dieu 22" in b["loi"] and b["duyet"] == "Chờ duyệt"
    assert len([d for d in S.doc_dong(bang, NHAT_KY) if d["buoc"] == "cham_lai"]) == 2


def test_phan_tich_lech_va_hieu_chinh_chi_de_xuat(nha_may):  # noqa: F811
    goc, bang = nha_may
    shutil.copyfile(REPO / "brand/vanxuan/rubric.yaml", goc / "brand/kenhthu/rubric.yaml")
    truoc = (goc / "brand/kenhthu/rubric.yaml").read_bytes()
    rows = [("kt-001-cd-a", "fb_reels", "5", "Mở đầu nhạt, lướt qua ngay"), ("kt-002-cd-b", "fb_reels", "6", "hook yếu"),
            ("kt-003-cd-c", "fb_reels", "9", "")]
    _hang_cho(bang, rows)
    for m, hook, tong in (("kt-001-cd-a", 20, 92), ("kt-002-cd-b", 19, 90), ("kt-003-cd-c", 18, 91)):
        P = goc / "projects" / m / "renders"
        P.mkdir(parents=True)
        tc = [{"ma": k, "ten": v["ten"], "toi_da": v["trong_so"], "diem": v["trong_so"] if k != "hook" else hook,
               "ly_do": "x", "nguon": v["nguon"]} for k, v in RUBRIC["tieu_chi"].items()]
        (P / "score.json").write_text(json.dumps({"diem_qa": tong, "tieu_chi": tc}), encoding="utf-8")
    kq = hieu_chinh(bang, "kenhthu", goc=goc, log=lambda s: None)
    pt = kq["phan_tich"]
    assert pt["n"] == 3 and pt["lech_tb"] > 1.0
    assert next(iter(pt["lech_tieu_chi"])) in ("hook", "dung_gia_tri", "nhip", "chan_thuc", "phu_de",
                                                "thuong_hieu", "cta", "ky_thuat")
    assert pt["nhac_trong_nhan_xet"].get("hook", 0) >= 2
    assert any("nâng" in x and "nguong" in x for x in kq["de_xuat"])
    assert any("tieu_chi." in x for x in kq["de_xuat"])
    assert kq["bao_cao"].is_file() and "| Video | Máy |" in kq["bao_cao"].read_text(encoding="utf-8")
    assert (goc / "brand/kenhthu/rubric.yaml").read_bytes() == truoc  # chỉ đề xuất, không sửa


def test_phan_tich_khong_co_diem_nguoi():
    assert phan_tich([{"ma_video": "a", "may": 80, "nguoi": None}], RUBRIC) == {"n": 0}

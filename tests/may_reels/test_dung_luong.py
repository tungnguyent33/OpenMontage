"""Dung lượng: đo, bản xem thử nhẹ, dọn cảnh trung gian, cắt lại cảnh khi thiếu, lệnh don-dep. Không gọi mạng."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from may_reels import sheet as S
from may_reels.cot_sheet import HANG_CHO, NHAT_KY
from may_reels.don_dep import don_dep, lap_ke_hoach
from may_reels.dung import am_thanh, canh
from may_reels.dung.pipeline import Pipeline
from may_reels.dung_luong import bao_cao, do_du_an
from may_reels.hang_cho import ban_xem_thu_cu, cau_hinh_xem_thu, chep_xem_thu
from tests.may_reels.conftest import NEN_XEM_THU_THAT
from tests.may_reels.sheet_gia import BangGia
from tests.may_reels.test_san_xuat import agent_gia, dung_gia, nha_may  # noqa: F401  (fixture)
from may_reels.san_xuat import MA_OK, san_xuat
from may_reels.sua import sua


def viet(p: Path, n: int = 10) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * n)
    return p


# ---------------------------------------------------------------- đo
def test_dung_luong_hard_link_dem_mot_lan(tmp_path):
    P = tmp_path / "projects" / "kt-001"
    final = viet(P / "renders/final.mp4", 1000)
    for nt in ("fb_reels", "tiktok"):
        (P / f"exports/{nt}/video").mkdir(parents=True)
        os.link(final, P / f"exports/{nt}/video/output.mp4")
    viet(P / "exports/fb_reels/metadata/description.txt", 5)
    viet(P / "hf/assets/video/c1.mp4", 300)
    viet(P / "assets/audio/_da_dat/s1.wav", 200)
    viet(P / "review/khung-0.png", 50)
    viet(P / "ke_hoach.json", 7)
    d = do_du_an(P)
    assert d.theo_loai == {"renders": 1000, "exports": 5, "hf/assets/video": 300, "assets/audio": 200, "review": 50,
                           "con_lai": 7}
    kq = bao_cao(tmp_path, in_ra=lambda s: None)
    assert kq["tong_may"] == 1562


# ---------------------------------------------------------------- bản xem thử
def test_xem_thu_xoa_ban_cu_cung_ma_khong_dung_ma_khac(tmp_path, monkeypatch):
    xt = tmp_path / "drive"
    for ten in ("kt-005.mp4", "kt-005-v2.mp4", "kt-005-dai.mp4", "kt-0050.mp4", "khac.txt"):
        viet(xt / ten)
    monkeypatch.setenv("MAY_REELS_XEM_THU_DIR", str(xt))
    monkeypatch.delenv("MAY_REELS_XEM_THU_LINK", raising=False)
    video = viet(tmp_path / "du-an" / "final.mp4", 99)
    link, cb = chep_xem_thu(video, "kt-005", phien_ban="-v3")
    assert link == "kt-005-v3.mp4" and cb == []
    assert sorted(f.name for f in xt.iterdir()) == ["khac.txt", "kt-005-dai.mp4", "kt-005-v3.mp4", "kt-0050.mp4"]
    assert not list(video.parent.glob(".xem-thu-*"))  # file tạm đã dọn
    assert ban_xem_thu_cu(xt, "kt-005", giu="") == [xt / "kt-005-v3.mp4"]


def test_cau_hinh_xem_thu_mac_dinh_va_tu_san_xuat(tmp_path):
    assert cau_hinh_xem_thu("khong-co", tmp_path) == {"rong": 720, "cao": 1280, "crf": 28, "am_thanh_kbps": 96}
    (tmp_path / "brand/k").mkdir(parents=True)
    (tmp_path / "brand/k/san-xuat.yaml").write_text("xem_thu:\n  crf: 30\n", encoding="utf-8")
    assert cau_hinh_xem_thu("k", tmp_path)["crf"] == 30


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="cần FFmpeg")
def test_nen_xem_thu_that_720p_aac_96k(tmp_path):
    src = tmp_path / "goc.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=2", "-f", "lavfi",
                    "-i", "sine=f=440:d=2", "-c:v", "libx264", "-crf", "16", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    str(src)], check=True)
    dst = tmp_path / "nhe.mp4"
    NEN_XEM_THU_THAT(src, dst, cau_hinh_xem_thu("khong-co", tmp_path))
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(dst)],
                                   capture_output=True, text=True).stdout)["streams"]
    v = next(s for s in pr if s["codec_type"] == "video")
    a = next(s for s in pr if s["codec_type"] == "audio")
    assert (v["width"], v["height"], v["pix_fmt"]) == (720, 1280, "yuv420p")
    assert a["codec_name"] == "aac" and int(a["bit_rate"]) <= 110_000


# ---------------------------------------------------------------- bản cuối và cảnh trung gian
def test_tuy_chon_render_doc_tu_san_xuat():
    assert am_thanh.tuy_chon_render({}) == ["--crf", "20", "--max-bitrate", "12M", "--buffer-size", "24M"]
    assert am_thanh.tuy_chon_render({"xuat": {"crf": 18}})[:2] == ["--crf", "18"]


def test_canh_trung_gian_crf_18():
    assert canh.CRF == 18


def _pipeline(P: Path) -> Pipeline:
    pl = Pipeline.__new__(Pipeline)
    pl.P, pl.log, pl.kenh = P, (lambda s: None), "kenhthu"
    return pl


CAT = [{"id": "c1", "anh": False}, {"id": "c2", "anh": True}, {"id": "c3", "so_do": {"kieu": "the_chu"}, "anh": False}]


def test_don_canh_trung_gian_giu_cache_giong_va_review(tmp_path):
    P = tmp_path / "du-an"
    viet(P / "hf/assets/video/c1.mp4", 100)
    giong = viet(P / "assets/audio/_da_dat/s1.wav")
    rv = viet(P / "review/khung-0.png")
    anh = viet(P / "hf/assets/img/c2.jpg")
    assert _pipeline(P).don_canh_trung_gian() == 100
    assert not list((P / "hf/assets/video").glob("*.mp4")) and giong.is_file() and rv.is_file() and anh.is_file()


def test_dam_bao_canh_cat_lai_khi_thieu(tmp_path, monkeypatch):
    P = tmp_path / "du-an"
    viet(P / "hf/assets/img/c2.jpg")
    pl = _pipeline(P)
    goi = []
    monkeypatch.setattr(pl, "_cat_canh", lambda cat: goi.append([c["id"] for c in cat]) or viet(P / "hf/assets/video/c1.mp4"))
    assert pl.dam_bao_canh(CAT) == ["c1"] and len(goi) == 1
    assert pl.dam_bao_canh(CAT) == [] and len(goi) == 1  # đủ file: không cắt lại


def test_compose_cat_lai_canh_truoc_khi_dung(tmp_path, monkeypatch):
    """Cảnh đã dọn sau lần compose trước: compose (kể cả chạy riêng --stage compose) cắt lại trước khi viết HTML."""
    P = tmp_path / "du-an"
    (P / "cat_canh.json").parent.mkdir(parents=True)
    (P / "cat_canh.json").write_text(json.dumps(CAT), encoding="utf-8")
    viet(P / "hf/assets/img/c2.jpg")
    pl = _pipeline(P)
    thu_tu = []
    monkeypatch.setattr(pl, "_cat_canh", lambda cat: thu_tu.append("cat") or viet(P / "hf/assets/video/c1.mp4"))

    class Dung:
        def __init__(self, *a, **k):
            pass

        def viet(self):
            thu_tu.append("viet")
            raise RuntimeError("dừng ở đây")
    monkeypatch.setattr("may_reels.dung.hf.Dung", Dung)
    for f in ("moc_giong.json", "tu_phu_de.json"):
        viet(P / "assets/audio" / f).write_text("{}", encoding="utf-8")
    pl.kh, pl.brand, pl.sx, pl.goc = {}, {}, {}, tmp_path
    with pytest.raises(RuntimeError, match="dừng ở đây"):
        pl.compose()
    assert thu_tu == ["cat", "viet"]


def test_sua_dung_lai_tu_assets_nen_cat_lai_canh(nha_may):  # noqa: F811
    goc, bang = nha_may
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})]}))
    hc = bang.tab("Hàng chờ")
    td = hc.doc_tat_ca()[0]
    for r in range(2, len(hc.doc_tat_ca()) + 1):
        hc.dat(r, td.index("duyet") + 1, "Sửa")
        hc.dat(r, td.index("ghi_chu_sua") + 1, "đổi câu chốt")

    def agent_sua(prompt, *, du_an, goc):
        kh = json.loads((du_an / "ke_hoach.json").read_text(encoding="utf-8"))
        kh["doan"][4]["loi"] = "Nhớ ba điều này nhé."
        (du_an / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok"}
    stages = []
    dg = dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 91})]})

    def dung(ma, *, goc, stages=None, giay=None, _ghi=stages):
        _ghi.append(stages)
        return dg(ma, goc=goc, stages=stages)
    sua(bang, goc=goc, agent=agent_sua, dung=dung, log=lambda s: None)
    assert stages and "assets" in stages[0] and stages[0].index("assets") < stages[0].index("compose")


# ---------------------------------------------------------------- don-dep
BAY_GIO = datetime(2026, 11, 16, 12, 0, 0)


@pytest.fixture()
def kho(tmp_path, monkeypatch):
    goc = tmp_path / "repo"
    (goc / "projects").mkdir(parents=True)
    xt = tmp_path / "drive"
    xt.mkdir()
    monkeypatch.delenv("KENH_GOC_DIR", raising=False)
    bang = BangGia()
    S.khoi_tao(bang)

    def du_an(ma: str) -> Path:
        P = goc / "projects" / ma
        final = viet(P / "renders/final.mp4", 1000)
        (P / "exports/fb_reels/video").mkdir(parents=True)
        os.link(final, P / "exports/fb_reels/video/output.mp4")
        viet(P / "hf/assets/video/c1.mp4", 300)
        viet(P / "assets/audio/_da_dat/s1.wav", 200)
        viet(P / "review/khung.png", 50)
        viet(P / "hf/compositions/s1.html", 5)
        for f in ("ke_hoach.json", "checkpoint_compose.json", "artifacts/final_review.json"):
            viet(P / f, 3)
        viet(xt / f"{ma}.mp4", 70)
        return P

    def dong(ma: str, duyet: list[str], cap_nhat: str = "2026-11-15 10:00:00"):
        nt = ["fb_reels", "yt_shorts", "tiktok"][:len(duyet)]
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": ma, "kenh": "kenhthu", "nen_tang": x} for x in nt])
        t = bang.tab("Hàng chờ")
        h = t.doc_tat_ca()
        td = h[0]
        for r, row in enumerate(h[1:], start=2):
            if row[0] == ma:
                i = nt.index(row[td.index("nen_tang")])
                t.dat(r, td.index("duyet") + 1, duyet[i])
                t.dat(r, td.index("cap_nhat_luc") + 1, cap_nhat)
    return {"goc": goc, "bang": bang, "xt": xt, "du_an": du_an, "dong": dong}


def _con(P: Path) -> set[str]:
    return {f.relative_to(P).as_posix() for f in P.rglob("*") if f.is_file()}


def test_don_dep_bo_moi_nen_tang_xoa_media_va_xem_thu_giu_json(kho):
    P = kho["du_an"]("kt-001")
    kho["dong"]("kt-001", ["Bỏ", "Bỏ", "Bỏ"])
    kq = don_dep(kho["bang"], that=True, goc=kho["goc"], bay_gio=BAY_GIO, thu_muc_xem_thu=kho["xt"], log=lambda s: None)
    assert _con(P) == {"ke_hoach.json", "checkpoint_compose.json", "artifacts/final_review.json",
                       "hf/compositions/s1.html"}
    assert not (kho["xt"] / "kt-001.mp4").exists()
    assert kq["giai_phong"] == 1000 + 300 + 200 + 50 + 70
    nk = S.doc_dong(kho["bang"], NHAT_KY)
    assert len(nk) == 1 and nk[0]["buoc"] == "don_dep" and nk[0]["che_do"] == "that" and "kt-001:bo" in nk[0]["chi_tiet"]


def test_don_dep_chua_quyet_dinh_thi_khong_dung(kho):
    P1, P2 = kho["du_an"]("kt-002"), kho["du_an"]("kt-003")
    truoc1, truoc2 = _con(P1), _con(P2)
    kho["dong"]("kt-002", ["Bỏ", "Chờ duyệt", "Bỏ"])
    kho["dong"]("kt-003", ["Duyệt", "Sửa", "Duyệt"], "2026-01-01 00:00:00")
    kho["du_an"]("kt-004")  # không có dòng nào trên Hàng chờ
    kq = don_dep(kho["bang"], that=True, goc=kho["goc"], bay_gio=BAY_GIO, thu_muc_xem_thu=kho["xt"], log=lambda s: None)
    assert kq["viec"] == [] and _con(P1) == truoc1 and _con(P2) == truoc2
    assert (kho["goc"] / "projects/kt-004/renders/final.mp4").is_file()


def test_don_dep_da_duyet_qua_han_chi_giu_final_va_json(kho):
    P = kho["du_an"]("kt-005")
    kho["dong"]("kt-005", ["Duyệt", "Bỏ", "Duyệt"], (BAY_GIO - timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S"))
    P2 = kho["du_an"]("kt-006")
    kho["dong"]("kt-006", ["Duyệt", "Duyệt", "Duyệt"], (BAY_GIO - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S"))
    truoc2 = _con(P2)
    kq = don_dep(kho["bang"], that=True, goc=kho["goc"], bay_gio=BAY_GIO, thu_muc_xem_thu=kho["xt"], log=lambda s: None)
    assert [v.ma_video for v in kq["viec"]] == ["kt-005"]
    assert _con(P) == {"renders/final.mp4", "ke_hoach.json", "checkpoint_compose.json", "artifacts/final_review.json",
                       "hf/compositions/s1.html"}
    assert kq["giai_phong"] == 300 + 200 + 50  # bản link trong exports xóa nhưng không trả lại ổ (final còn)
    assert _con(P2) == truoc2 and (kho["xt"] / "kt-005.mp4").is_file()


def test_don_dep_mac_dinh_chay_thu_khong_xoa_khong_ghi_nhat_ky(kho):
    P = kho["du_an"]("kt-007")
    kho["dong"]("kt-007", ["Bỏ"])
    truoc = _con(P)
    ra = []
    kq = don_dep(kho["bang"], goc=kho["goc"], bay_gio=BAY_GIO, thu_muc_xem_thu=kho["xt"], log=ra.append)
    assert kq["giai_phong"] > 0 and _con(P) == truoc and (kho["xt"] / "kt-007.mp4").is_file()
    assert S.doc_dong(kho["bang"], NHAT_KY) == [] and any("[thử]" in x and "MB" in x for x in ra)


def test_don_dep_khong_dung_thu_muc_kenh_goc(kho, monkeypatch):
    P = kho["du_an"]("kt-008")
    kho["dong"]("kt-008", ["Bỏ"])
    monkeypatch.setenv("KENH_GOC_DIR", str(P / "hf"))  # kênh gốc nằm trong dự án: không đụng cả dự án
    truoc = _con(P)
    viec, bo_qua = lap_ke_hoach(kho["bang"], goc=kho["goc"], bay_gio=BAY_GIO, thu_muc_xem_thu=None)
    assert viec == [] and any("kênh gốc" in b for b in bo_qua) and _con(P) == truoc

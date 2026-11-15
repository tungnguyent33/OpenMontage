"""Khâu đăng bài với API giả: không gọi mạng."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from may_reels import dang_bai as D
from may_reels import sheet as S
from may_reels.cau_hinh_dang import LoiCauHinh, doc_cau_hinh_dang
from may_reels.cot_sheet import HANG_CHO
from may_reels.hang_cho import CANH_BAO_CO_SAN, them_video
from may_reels.khoa_tien_trinh import LoiDangChay, khoa
from may_reels.kiem_tra_video import ThongSo
from may_reels.so_dang import SoDang
from tests.may_reels.sheet_gia import BangGia

REPO = Path(__file__).resolve().parents[2]
BAY = datetime(2026, 11, 15, 12, 0, 0, tzinfo=D.TZ_VN)
CHUAN = ThongSo(1080, 1920, 30.0, 30.0)

DANG_BAI_YAML = """
nen_tang: [fb_reels, yt_shorts, tiktok]
fb_reels: {page_id: "1234", bien_token: KT_FB_TOKEN}
yt_shorts: {kenh_id: "UCkenhthu", bien_token_file: KT_YT_TOKEN_FILE}
tiktok: {che_do: tay}
"""


class DriveGia:
    def __init__(self):
        self.tai = []
        self.thu_muc_tao = []

    def thu_muc(self, ten, cha=None):
        self.thu_muc_tao.append((ten, cha))
        return {"id": f"tm-{ten}", "webViewLink": f"https://drive.example/folders/{ten}"}

    def tai_len(self, duong_dan, ten, thu_muc_id, mime):
        self.tai.append((Path(duong_dan).name, ten, thu_muc_id, mime))
        return {"id": f"f-{ten}", "webViewLink": f"https://drive.example/file/{ten}"}


class APIGia:
    """Thay cho ba publisher. `kich_ban[nen_tang]` là danh sách kết quả lần lượt (KetQuaDang hoặc Exception)."""

    def __init__(self):
        self.goi: list[tuple[str, dict]] = []
        self.kich_ban: dict[str, list] = {}

    def cong_cu(self):
        def tao(nt):
            def ham(yc):
                self.goi.append((nt, yc))
                ds = self.kich_ban.get(nt)
                kq = ds.pop(0) if ds else D.KetQuaDang(True, f"id-{nt}-{len(self.goi)}", f"https://x/{nt}",
                                                        "public", ban_giao=(nt == "tiktok"))
                if isinstance(kq, Exception):
                    raise kq
                return kq
            return ham
        return {nt: tao(nt) for nt in ("fb_reels", "yt_shorts", "tiktok")}


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    goc = tmp_path / "repo"
    (goc / "brand" / "kenhthu").mkdir(parents=True)
    (goc / "brand" / "kenhthu" / "brand.json").write_text(json.dumps({
        "id": "kenhthu",
        "hashtags": {"facebook": ["#fb"], "youtube": ["#yt"], "tiktok": ["#tt"]},
        "cam": {"cum_tu_cam": ["cam tuyệt đối"], "cum_tu_cam_du_an": ["tỉ lệ đỗ"]},
    }, ensure_ascii=False), encoding="utf-8")
    (goc / "brand" / "kenhthu" / "dang-bai.yaml").write_text(DANG_BAI_YAML, encoding="utf-8")
    for k, v in {"KT_FB_TOKEN": "gia", "KT_YT_TOKEN_FILE": "secrets/yt.json",
                 "MAY_REELS_GOOGLE_CLIENT_SECRET": "secrets/client.json"}.items():
        monkeypatch.setenv(k, v)
    video = tmp_path / "Video Thử.mp4"
    video.write_bytes(b"video-1")
    cap = tmp_path / "caption.txt"
    cap.write_text("Ngã tư không đèn: ai đi trước?\nXem hết video nhé.", encoding="utf-8")
    xem_thu = tmp_path / "drive-dong-bo"
    xem_thu.mkdir()
    monkeypatch.setenv("MAY_REELS_XEM_THU_DIR", str(xem_thu))
    monkeypatch.setenv("MAY_REELS_XEM_THU_LINK", "https://drive.example/thu-muc")
    bang = BangGia()
    S.khoi_tao(bang)
    api = APIGia()
    so = SoDang(goc / "projects" / "_may_reels" / "so_dang.jsonl")
    ngu = []

    def chay(that=True, bay=BAY, **kw):
        return D.chay_dang(bang, that=that, bay_gio=lambda: bay, cong_cu=api.cong_cu(), so_dang=so,
                           file_khoa=goc / "projects" / "_may_reels" / "dang.lock", goc=goc,
                           do=lambda p: CHUAN, ngu=ngu.append, **kw)

    def them(**kw):
        return them_video(bang, video=video, kenh="kenhthu", caption_file=cap, goc=goc, do=lambda p: CHUAN, **kw)

    return {"goc": goc, "bang": bang, "api": api, "so": so, "chay": chay, "them": them, "video": video,
            "cap": cap, "ngu": ngu, "xem_thu": xem_thu}


def hc(bang):
    return bang.tab("Hàng chờ")


def dong(bang, ma, nt):
    return next(d for d in S.doc_dong(bang, HANG_CHO) if d["ma_video"] == ma and d["nen_tang"] == nt)


def nguoi_dat(bang, ma, nt, cot, gia_tri):
    """Giả lập người sửa ô trên Sheet (không đi qua lớp ghi của máy)."""
    t = hc(bang)
    hang = t.doc_tat_ca()
    c = hang[0].index(cot) + 1
    r = next(i for i, h in enumerate(hang, start=1) if i > 1 and h[0] == ma and h[hang[0].index("nen_tang")] == nt)
    t.dat(r, c, gia_tri)


def duyet(bang, ma, nt, gia_tri="Duyệt"):
    nguoi_dat(bang, ma, nt, "duyet", gia_tri)


# ---------------------------------------------------------------- hang-cho them
def test_hang_cho_them_tao_moi_nen_tang_mot_dong_cot_nguoi_trong(moi_truong):
    kq = moi_truong["them"]()
    assert kq.loi == [] and kq.ma_video == "video-thu" and kq.them == 3
    b = moi_truong["bang"]
    for nt, tag in (("fb_reels", "#fb"), ("yt_shorts", "#yt"), ("tiktok", "#tt")):
        d = dong(b, "video-thu", nt)
        assert d["duyet"] == "Chờ duyệt" and d["ghi_chu_sua"] == "" and d["gio_dang"] == ""
        assert d["trang_thai_dang"] == "" and d["id_bai"] == ""
        assert d["hashtag"] == tag and d["canh_bao"] == CANH_BAO_CO_SAN
        assert d["link_xem_thu"] == "video-thu.mp4 — https://drive.example/thu-muc"
        thu_muc = moi_truong["goc"] / d["ghi_chu_may"].split(": ", 1)[1]
        assert (thu_muc / "metadata" / "description.txt").is_file() and list((thu_muc / "video").glob("*.mp4"))
    assert (moi_truong["xem_thu"] / "video-thu.mp4").read_bytes() == b"video-1"
    ban_ghi = json.loads((moi_truong["goc"] / "projects/_may_reels/hang_cho/video-thu.json").read_text(encoding="utf-8"))
    assert ban_ghi["sha1"] and ban_ghi["video"].endswith("Video Thử.mp4")


def test_hang_cho_them_chay_lai_khong_trung(moi_truong):
    moi_truong["them"]()
    kq = moi_truong["them"]()
    assert kq.them == 0 and kq.loi == []
    assert len(hc(moi_truong["bang"]).doc_tat_ca()) == 4


def test_hang_cho_thieu_thu_muc_xem_thu_thi_ghi_duong_dan_may(moi_truong, monkeypatch):
    monkeypatch.delenv("MAY_REELS_XEM_THU_DIR")
    kq = moi_truong["them"]()
    assert kq.link_xem_thu == str(moi_truong["video"].resolve())
    assert any("MAY_REELS_XEM_THU_DIR" in c for c in kq.canh_bao)
    assert "MAY_REELS_XEM_THU_DIR" in dong(moi_truong["bang"], "video-thu", "fb_reels")["canh_bao"]


def test_hang_cho_khoi_tao_khong_de_duyet_cua_nguoi(moi_truong):
    moi_truong["them"]()
    nguoi_dat(moi_truong["bang"], "video-thu", "fb_reels", "duyet", "")  # người xóa ô
    moi_truong["them"]()
    assert dong(moi_truong["bang"], "video-thu", "fb_reels")["duyet"] == ""


@pytest.mark.parametrize("caption,tim", [("Tỉ lệ đỗ 100%", "tỉ lệ đỗ"), ("CAM TUYỆT ĐỐI", "cam tuyệt đối")])
def test_hang_cho_them_tu_choi_cum_tu_cam(moi_truong, caption, tim):
    moi_truong["cap"].write_text(caption, encoding="utf-8")
    kq = moi_truong["them"]()
    assert any(tim in x for x in kq.loi) and len(hc(moi_truong["bang"]).doc_tat_ca()) == 1


def test_hang_cho_them_tu_choi_sai_thong_so(moi_truong):
    kq = them_video(moi_truong["bang"], video=moi_truong["video"], kenh="kenhthu", caption_file=moi_truong["cap"],
                    goc=moi_truong["goc"], do=lambda p: ThongSo(1920, 1080, 120.0, 30.0))
    assert any("9:16" in x for x in kq.loi) and any("fb_reels" in x and "90" in x for x in kq.loi)
    assert len(hc(moi_truong["bang"]).doc_tat_ca()) == 1


def test_hang_cho_them_khong_doi_dong_da_duyet(moi_truong):
    moi_truong["them"]()
    duyet(moi_truong["bang"], "video-thu", "fb_reels")
    moi_truong["cap"].write_text("Caption mới", encoding="utf-8")
    kq = moi_truong["them"]()
    assert kq.loi and dong(moi_truong["bang"], "video-thu", "fb_reels")["caption"].startswith("Ngã tư")


def test_hang_cho_them_che_do_thu_khong_ghi(moi_truong):
    kq = them_video(moi_truong["bang"], video=moi_truong["video"], kenh="kenhthu", caption_file=moi_truong["cap"],
                    goc=moi_truong["goc"], do=lambda p: CHUAN, thu=True)
    assert kq.them == 3 and len(hc(moi_truong["bang"]).doc_tat_ca()) == 1
    assert list(moi_truong["xem_thu"].iterdir()) == []


# ---------------------------------------------------------------- dang: duyệt và chạy thử
def test_khong_dang_dong_chua_duyet(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels", "Chờ duyệt")
    duyet(b, "video-thu", "yt_shorts", "duyệt")   # sai hoa thường
    duyet(b, "video-thu", "tiktok", "Sửa")
    bc = moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and bc.da_dang == 0
    for nt in ("fb_reels", "yt_shorts", "tiktok"):
        assert dong(b, "video-thu", nt)["trang_thai_dang"] == ""


def test_chay_thu_khong_goi_api_khong_ghi_hang_cho(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    for nt in ("fb_reels", "yt_shorts", "tiktok"):
        duyet(b, "video-thu", nt)
    truoc = hc(b).doc_tat_ca()
    so_lan_ghi = len(hc(b).lan_ghi)
    bc = moi_truong["chay"](that=False)
    assert bc.se_dang == 3 and moi_truong["api"].goi == []
    assert hc(b).doc_tat_ca() == truoc and len(hc(b).lan_ghi) == so_lan_ghi
    assert moi_truong["so"].doc() == []
    nk = b.tab("Nhật ký").doc_tat_ca()
    assert nk[-1][nk[0].index("che_do")] == "thu" and nk[-1][nk[0].index("buoc")] == "dang"


def test_chay_thu_dong_ket_khong_bi_danh_dau(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    nguoi_dat(b, "video-thu", "fb_reels", "trang_thai_dang", "dang_tai_len")
    nguoi_dat(b, "video-thu", "fb_reels", "cap_nhat_luc", "2026-11-15 10:00:00")
    bc = moi_truong["chay"](that=False)
    assert bc.kiem_tra == 1 and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "dang_tai_len"


# ---------------------------------------------------------------- dang thật: chống trùng
def test_dang_thanh_cong_va_chay_hai_lan_khong_dang_trung(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    for nt in ("fb_reels", "yt_shorts", "tiktok"):
        duyet(b, "video-thu", nt)
    bc = moi_truong["chay"]()
    assert bc.da_dang == 2 and bc.ban_giao == 1 and len(moi_truong["api"].goi) == 3
    fb = dong(b, "video-thu", "fb_reels")
    assert fb["trang_thai_dang"] == "da_dang" and fb["id_bai"].startswith("id-fb") and fb["link_bai"] and fb["loi"] == ""
    tt = dong(b, "video-thu", "tiktok")
    assert tt["trang_thai_dang"] == "cho_dang_tay" and tt["link_bai"]
    assert fb["duyet"] == "Duyệt"  # máy không đụng cột người
    assert len(moi_truong["so"].doc()) == 3
    moi_truong["chay"]()
    assert len(moi_truong["api"].goi) == 3


def test_ghi_dang_tai_len_truoc_khi_goi_api(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    thay = []
    api = moi_truong["api"]
    goc_cong_cu = api.cong_cu

    def cong_cu():
        cc = goc_cong_cu()
        ham = cc["fb_reels"]
        cc["fb_reels"] = lambda yc: (thay.append(dong(b, "video-thu", "fb_reels")["trang_thai_dang"]), ham(yc))[1]
        return cc
    api.cong_cu = cong_cu
    moi_truong["chay"]()
    assert thay == ["dang_tai_len"]


def test_co_id_bai_thi_khong_bao_gio_dang_lai(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    nguoi_dat(b, "video-thu", "fb_reels", "id_bai", "123")
    bc = moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and bc.bo_qua == 1


def test_so_dang_da_co_thi_dong_bo_sheet_khong_dang_lai(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["so"].ghi({"luc": BAY.isoformat(), "kenh": "kenhthu", "ma_video": "video-thu", "nen_tang": "fb_reels",
                          "id_bai": "999", "link": "https://fb/999", "loai": "dang"})
    moi_truong["chay"]()
    d = dong(b, "video-thu", "fb_reels")
    assert moi_truong["api"].goi == [] and d["id_bai"] == "999" and d["trang_thai_dang"] == "da_dang"


def test_loi_ghi_sheet_sau_khi_dang_lan_sau_khong_dang_lai(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    tab = hc(b)
    ghi_goc = tab.ghi_o
    dem = {"n": 0}

    def ghi_hong(o):
        o = list(o)
        if any(v == "da_dang" for _, _, v in o):
            dem["n"] += 1
            raise ConnectionError("mất mạng khi ghi Sheet")
        ghi_goc(o)
    tab.ghi_o = ghi_hong
    with pytest.raises(ConnectionError):
        moi_truong["chay"]()
    assert len(moi_truong["api"].goi) == 1 and moi_truong["so"].da_xu_ly("video-thu", "fb_reels")
    tab.ghi_o = ghi_goc
    moi_truong["chay"](bay=BAY + timedelta(hours=2))
    assert len(moi_truong["api"].goi) == 1
    assert dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "da_dang"


def test_rut_duyet_ngay_truoc_khi_dang(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    tab = hc(b)
    lan_dau = tab.so_lan_doc

    def nguoi_doi_y(t, lan):
        if lan == lan_dau + 2:  # sau lần đọc lập kế hoạch, trước lần đọc lại
            t.truoc_khi_doc = None
            duyet(b, "video-thu", "fb_reels", "Sửa")
    tab.truoc_khi_doc = nguoi_doi_y
    moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == ""


def test_dong_ket_qua_30_phut_thanh_can_kiem_tra(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    duyet(b, "video-thu", "yt_shorts")
    for nt, luc in (("fb_reels", "2026-11-15 11:20:00"), ("yt_shorts", "2026-11-15 11:45:00")):
        nguoi_dat(b, "video-thu", nt, "trang_thai_dang", "dang_tai_len")
        nguoi_dat(b, "video-thu", nt, "cap_nhat_luc", luc)
    moi_truong["chay"]()
    assert moi_truong["api"].goi == []
    assert dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "can_kiem_tra"
    assert dong(b, "video-thu", "yt_shorts")["trang_thai_dang"] == "dang_tai_len"


# ---------------------------------------------------------------- lỗi giữa chừng
def test_loi_mang_thu_lai_toi_da_2_lan_roi_thanh_cong(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["api"].kich_ban["fb_reels"] = [D.KetQuaDang(False, loai_loi="mang", loi="timeout")] * 2
    moi_truong["chay"]()
    assert len(moi_truong["api"].goi) == 3 and moi_truong["ngu"] == [5, 15]
    assert dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "da_dang"


def test_loi_mang_qua_2_lan_thanh_loi_thu_lai(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["api"].kich_ban["fb_reels"] = [D.KetQuaDang(False, loai_loi="mang", loi="timeout")] * 3
    moi_truong["chay"]()
    d = dong(b, "video-thu", "fb_reels")
    assert len(moi_truong["api"].goi) == 3 and d["trang_thai_dang"] == "loi_thu_lai" and "timeout" in d["loi"]
    moi_truong["chay"](bay=BAY + timedelta(hours=1))  # lần chạy sau được thử lại
    assert len(moi_truong["api"].goi) == 4 and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "da_dang"


@pytest.mark.parametrize("loai", ["quyen", "noi_dung"])
def test_loi_quyen_va_noi_dung_khong_thu_lai(moi_truong, loai):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["api"].kich_ban["fb_reels"] = [D.KetQuaDang(False, loai_loi=loai, loi="HTTP 403")]
    moi_truong["chay"]()
    assert len(moi_truong["api"].goi) == 1 and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "loi"
    moi_truong["chay"](bay=BAY + timedelta(hours=1))
    assert len(moi_truong["api"].goi) == 1


def test_loi_khong_ro_o_buoc_cuoi_can_kiem_tra_va_giu_id(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["api"].kich_ban["fb_reels"] = [D.KetQuaDang(False, id_bai="vid-7", loai_loi="khong_ro", loi="đăng: timeout")]
    moi_truong["chay"]()
    d = dong(b, "video-thu", "fb_reels")
    assert len(moi_truong["api"].goi) == 1 and d["trang_thai_dang"] == "can_kiem_tra" and d["id_bai"] == "vid-7"


def test_ngoai_le_trong_cong_cu_coi_nhu_khong_ro(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "yt_shorts")
    moi_truong["api"].kich_ban["yt_shorts"] = [RuntimeError("bug")]
    moi_truong["chay"]()
    assert dong(b, "video-thu", "yt_shorts")["trang_thai_dang"] == "can_kiem_tra"


def test_youtube_chua_cong_khai_thi_can_kiem_tra(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "yt_shorts")
    moi_truong["api"].kich_ban["yt_shorts"] = [D.KetQuaDang(True, "yt1", "https://youtube/shorts/yt1", "private")]
    moi_truong["chay"]()
    d = dong(b, "video-thu", "yt_shorts")
    assert d["trang_thai_dang"] == "can_kiem_tra" and d["id_bai"] == "yt1" and "private" in d["loi"]
    moi_truong["chay"](bay=BAY + timedelta(hours=1))
    assert len(moi_truong["api"].goi) == 1


# ---------------------------------------------------------------- kiểm tra trước khi đăng
def test_file_doi_sau_khi_vao_hang_cho_thi_khong_dang(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    moi_truong["video"].write_bytes(b"video-khac")
    moi_truong["chay"]()
    d = dong(b, "video-thu", "fb_reels")
    assert moi_truong["api"].goi == [] and d["trang_thai_dang"] == "loi" and "sha1" in d["loi"]


def test_caption_tren_sheet_bi_sua_thanh_cum_tu_cam(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    nguoi_dat(b, "video-thu", "fb_reels", "caption", "Tỉ lệ đỗ cao nhất")
    moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == "loi"


@pytest.mark.parametrize("gio,dang", [("", True), ("11:59", True), ("12:30", False), ("2026-11-15 11:00", True),
                                     ("16/11/2026 08:00", False), ("trưa mai", False)])
def test_gio_dang(moi_truong, gio, dang):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    nguoi_dat(b, "video-thu", "fb_reels", "gio_dang", gio)
    moi_truong["chay"]()
    assert (len(moi_truong["api"].goi) == 1) is dang


def test_gioi_han_24h(moi_truong):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    for i in range(30):
        moi_truong["so"].ghi({"luc": (BAY - timedelta(hours=1)).isoformat(), "kenh": "kenhthu",
                              "ma_video": f"cu-{i}", "nen_tang": "fb_reels", "loai": "dang"})
    bc = moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and any("30 bài/24 giờ" in x for x in bc.dong)
    moi_truong["chay"](bay=BAY + timedelta(hours=24))
    assert len(moi_truong["api"].goi) == 1


def test_thieu_cau_hinh_thi_bo_qua_khong_ghi_sheet(moi_truong, monkeypatch):
    moi_truong["them"]()
    b = moi_truong["bang"]
    duyet(b, "video-thu", "fb_reels")
    monkeypatch.delenv("KT_FB_TOKEN")
    bc = moi_truong["chay"]()
    assert moi_truong["api"].goi == [] and dong(b, "video-thu", "fb_reels")["trang_thai_dang"] == ""
    assert any("KT_FB_TOKEN" in x for x in bc.dong)


def test_khoa_khong_cho_hai_tien_trinh(moi_truong):
    moi_truong["them"]()
    with khoa(moi_truong["goc"] / "projects" / "_may_reels" / "dang.lock"):
        with pytest.raises(LoiDangChay):
            moi_truong["chay"]()


def test_moi_lan_chay_ghi_nhat_ky(moi_truong):
    moi_truong["them"]()
    nk = moi_truong["bang"].tab("Nhật ký")
    truoc = len(nk.doc_tat_ca())
    moi_truong["chay"](that=False)
    moi_truong["chay"]()
    assert len(nk.doc_tat_ca()) == truoc + 2


# ---------------------------------------------------------------- cấu hình kênh
def test_dang_bai_yaml_tu_choi_gia_tri_giong_token(tmp_path):
    p = tmp_path / "brand" / "k"
    p.mkdir(parents=True)
    (p / "dang-bai.yaml").write_text("fb_reels: {page_id: '1', bien_token: 'EAAGabc123'}\n", encoding="utf-8")
    with pytest.raises(LoiCauHinh):
        doc_cau_hinh_dang("k", tmp_path)


def test_cau_hinh_cac_kenh_trong_repo_khong_chua_bi_mat():
    for f in (REPO / "brand").glob("*/dang-bai.yaml"):
        ch = doc_cau_hinh_dang(f.parent.name, REPO)
        assert ch.nen_tang


def test_import_dang_bai_va_publisher_khong_keo_googleapiclient():
    code = ("import sys, may_reels.dang_bai, may_reels.hang_cho, may_reels.drive;"
            "from tools.tool_registry import ToolRegistry; r=ToolRegistry(); r.discover();"
            "print(sorted(t.name for t in r.get_by_capability('publish')), 'googleapiclient' in sys.modules)")
    kq = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert kq.returncode == 0, kq.stderr
    assert kq.stdout.strip() == "['export_bundle', 'facebook_reels', 'tiktok_handoff', 'youtube_shorts'] False"

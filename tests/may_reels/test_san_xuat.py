"""Kế hoạch, cắt cảnh, dựng HTML, sản xuất hàng loạt và sửa: agent và bước dựng đều giả, không gọi mạng."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from may_reels import sheet as S
from may_reels.cot_sheet import CAN_QUAY, HANG_CHO, NHAT_KY, Y_TUONG
from may_reels.dung import canh
from may_reels.dung.hf import Dung
from may_reels.dung.ke_hoach import kiem_tra, tao_artifact
from may_reels.kiem_tra_video import ThongSo
from may_reels.san_xuat import MA_KE_HOACH, MA_OK, MA_THIEU_CANH, san_xuat, so_tiep_theo
from may_reels.sua import sua
from tests.may_reels.sheet_gia import BangGia

REPO = Path(__file__).resolve().parents[2]
SX = yaml.safe_load((REPO / "brand" / "vanxuan" / "san-xuat.yaml").read_text(encoding="utf-8"))
CTA = "Nhắn Zalo 0900 111 222 để nhận bộ câu ôn thi A1."

BRAND = {
    "id": "kenhthu",
    "kenh": {"ten_kenh": "Kênh Thử", "khan_gia": "người học lái"},
    "lien_he": {"zalo": "0900 111 222", "hotline": "0900 111 222", "dia_chi": "Thôn 1"},
    "mau": {"navy": "#0E3970", "xanh_chinh": "#048DD1", "cam_nhan": "#E4661F", "trang": "#FFFFFF"},
    "font": {"files": {"F-ExtraBold.ttf": {}, "F-Bold.ttf": {}}},
    "assets": {},
    "cta": [CTA],
    "hashtags": {"facebook": ["#fb"], "youtube": ["#yt"], "tiktok": ["#tt"]},
    "cam": {"cum_tu_cam": ["bao đỗ"], "cum_tu_cam_du_an": ["tỉ lệ đỗ"]},
    "quyen_hinh": {"da_dong_y": True},
    "chu_de": [{"ma": "cd-a", "tru_cot": "1 phút luật mới", "dinh_dang": "hoi-dap", "chu_de": "A?", "y_chinh": "x"},
               {"ma": "cd-b", "tru_cot": "1 phút luật mới", "dinh_dang": "hoi-dap", "chu_de": "B?", "y_chinh": "y"}],
    "kho_canh": [
        {"ma": f"v{i}", "dung_duoc": True, "loai_file": "video", "doan_dung_duoc": [[0.0, 30.0]], "file_tuong_doi": f"v{i}.mp4",
         "the": ["san-tap"], "mat_nguoi": False, "thoi_luong": 30} for i in range(1, 7)
    ] + [{"ma": "anh1", "dung_duoc": True, "loai_file": "anh", "doan_dung_duoc": [], "file_tuong_doi": "a.jpg",
          "the": [], "mat_nguoi": False},
         {"ma": "bi-loai", "dung_duoc": False, "loai_file": "video", "doan_dung_duoc": [[0, 5]], "file_tuong_doi": "x.mp4",
          "ly_do_loai": ["stock"], "the": []}],
}

NGUON = [{"id": "n1", "van_ban": "Luật Thử số 1/2024", "ten_ngan": "Luật 1/2024", "dieu_khoan": "Điều 1 khoản 2",
          "link": "https://vbpl.vn/x", "ngay_mo": "2026-11-15", "trich_nguyen_van": "Người lái xe phải nhường đường."}]


def ke_hoach(**kw) -> dict:
    kh = {
        "phien_ban": 1, "ma_video": "kt-001-cd-a", "kenh": "kenhthu", "ma_chu_de": "cd-a", "tieu_de": "Ai đi trước?",
        "khung_nhip": "mot-phut-luat-moi", "nguon_luat": copy.deepcopy(NGUON),
        "doan": [
            {"id": "s1", "vai": "hook", "loi": "Ngã tư không đèn, ai đi trước?", "nguon_ids": [],
             "the": {"dong1": "NGÃ TƯ", "dong2": "AI ĐI TRƯỚC?", "mau": "cam", "kieu": "hook"},
             "canh": {"ma": "v1", "vao": 2.0, "mo_ta": "sân"}},
            {"id": "s2", "vai": "than", "loi": "Theo luật, ở nơi giao nhau không có biển báo và cũng không có đèn tín hiệu, xe đi từ bên phải của bạn được ưu tiên đi trước.",
             "nguon_ids": ["n1"], "the": {"dong1": "BÊN PHẢI", "dong2": "được đi trước", "mau": "xanh", "kieu": "wipe"},
             "canh": {"ma": "v2", "vao": 1.0, "mo_ta": "sân"}},
            {"id": "s3", "vai": "than", "loi": "Nếu có biển báo đường ưu tiên thì xe đi trên đường ưu tiên luôn được đi trước, dù xe đó đang ở bên trái hay bên phải của bạn.",
             "nguon_ids": ["n1"], "the": {"dong1": "ĐƯỜNG ƯU TIÊN", "dong2": "đi trước", "mau": "cam", "kieu": "word"},
             "canh": {"ma": "v3", "vao": 0.0, "mo_ta": "sân"}},
            {"id": "s4", "vai": "than", "loi": "Còn xe cứu thương, xe cứu hỏa đang làm nhiệm vụ có tín hiệu ưu tiên thì mọi xe khác đều phải nhường đường cho các xe này đi trước.",
             "nguon_ids": ["n1"], "the": {"dong1": "XE ƯU TIÊN", "dong2": "luôn được nhường", "mau": "xanh", "kieu": "scale"},
             "canh": {"ma": "anh1", "vao": None, "mo_ta": "ảnh"}},
            {"id": "s5", "vai": "chot", "loi": "Nhớ ba điều này là qua ngã tư an toàn hơn nhiều rồi.",
             "nguon_ids": [], "the": {"dong1": "NHỚ 3 ĐIỀU", "dong2": "qua ngã tư an toàn", "mau": "cam", "kieu": "scale"},
             "canh": {"ma": "v4", "vao": 0.0, "mo_ta": "sân"}},
            {"id": "s6", "vai": "cta", "loi": CTA, "nguon_ids": [], "the": None, "canh": None},
        ],
        "caption": {"fb_reels": "Ngã tư không đèn ai đi trước? Nguồn: Luật 1/2024.", "yt_shorts": "Ngã tư không đèn ai đi trước?",
                    "tiktok": "Ai đi trước ở ngã tư?"},
        "thieu_canh": [], "quyet_dinh": [],
    }
    kh.update(kw)
    return kh


def loi_cua(kh):
    return kiem_tra(kh, BRAND, SX)[0]


# ---------------------------------------------------------------- kiểm tra kế hoạch
def test_ke_hoach_hop_le():
    assert loi_cua(ke_hoach()) == []


@pytest.mark.parametrize("sua_kh,tim", [
    (lambda k: k["doan"][0].update(loi="Có bằng A1 lái xe 150 phân khối được không câu trả lời là tùy năm cấp"), "hook"),
    (lambda k: k["doan"][1].update(loi="Học ở đây bao đỗ nhé, ai cũng qua hết luôn, không trượt đâu các bạn ơi."), "cụm từ cấm"),
    (lambda k: k["caption"].update(tiktok="Tỉ lệ đỗ cao"), "cụm từ cấm"),
    (lambda k: k["doan"][1].update(nguon_ids=[]), "thiếu nguồn"),
    (lambda k: k["doan"][-1].update(loi="Nhắn Zalo 0999 999 999 nhé."), "cta"),
    (lambda k: k["doan"][2]["canh"].update(ma="v2", vao=5.0), "hơn một lần"),
    (lambda k: k["doan"][2]["canh"].update(ma="bi-loai", vao=1.0), "bị loại"),
    (lambda k: k["doan"][2]["canh"].update(vao=40.0), "ngoài doan_dung_duoc"),
    (lambda k: k["doan"][2].update(canh=None), "thiếu cảnh"),
    (lambda k: k.update(doan=[k["doan"][0], k["doan"][-1], k["doan"][1], k["doan"][4]]), "id đoạn"),
])
def test_ke_hoach_bi_bat_loi(sua_kh, tim):
    kh = ke_hoach()
    sua_kh(kh)
    assert any(tim in x for x in loi_cua(kh)), loi_cua(kh)


def test_ke_hoach_qua_ngan_hoac_qua_dai():
    kh = ke_hoach()
    kh["doan"] = [kh["doan"][0], kh["doan"][4], kh["doan"][5]]
    for i, d in enumerate(kh["doan"], start=1):
        d["id"] = f"s{i}"
    assert any(("thời lượng" in x) or ("nhịp" in x) or ("schema" in x) for x in loi_cua(kh))


def test_canh_bao_canh_dung_nhieu():
    _, cb = kiem_tra(ke_hoach(), BRAND, SX, so_lan_dung={"v1": 3})
    assert any("v1" in x for x in cb)


def test_tao_artifact_hop_schema():
    from schemas.artifacts import validate_artifact
    brief, script, sp = tao_artifact(ke_hoach(), BRAND, SX)
    for ten, obj in (("brief", brief), ("script", script), ("scene_plan", sp)):
        validate_artifact(ten, obj)
    assert brief["target_platform"] == "generic" and "source_ref" in script["sections"][1]
    assert sp["scenes"][0]["required_assets"][0]["path"] == "kenh:v1.mp4"


# ---------------------------------------------------------------- cắt cảnh
def moc_gia(kh, dai=5.0):
    t, m = 0.0, {}
    for d in kh["doan"]:
        m[d["id"]] = {"id": d["id"], "start": round(t, 2), "end": round(t + dai, 2)}
        t += dai + 0.3
    return m


def test_tinh_cat_lui_diem_vao_va_bao_thieu():
    kh = ke_hoach()
    kh["doan"][0]["canh"]["vao"] = 28.0  # chỉ còn 2s tới hết đoạn dùng được -> lùi về 30 - dài
    cat = canh.tinh_cat(kh, BRAND, SX, moc_gia(kh))
    assert cat[0]["in"] == round(30.0 - cat[0]["dai"], 2) and cat[0]["start"] == 0.0
    assert [c["anh"] for c in cat] == [False, False, False, True, False]
    sx = copy.deepcopy(SX)
    sx["canh"]["tranh_them"] = {"v2": [[0, 30]]}
    with pytest.raises(canh.LoiThieuCanh):
        canh.tinh_cat(kh, BRAND, sx, moc_gia(kh))


# ---------------------------------------------------------------- HTML HyperFrames
def test_dung_html_khong_viet_cung_va_co_nguon(tmp_path):
    kh = ke_hoach()
    goc = tmp_path / "repo"
    (goc / "brand/kenhthu/assets/fonts").mkdir(parents=True)
    for f in ("F-ExtraBold.ttf", "F-Bold.ttf"):
        (goc / "brand/kenhthu/assets/fonts" / f).write_bytes(b"f")
    (goc / "brand/kenhthu/assets/logo.png").write_bytes(b"png")
    P = goc / "projects" / kh["ma_video"]
    (P / "hf/assets/img").mkdir(parents=True)
    (P / "hf/assets/img/c4.jpg").write_bytes(b"j")
    moc = moc_gia(kh)
    cat = canh.tinh_cat(kh, BRAND, SX, moc)
    tu = []
    for d in kh["doan"]:
        for i, w in enumerate(d["loi"].split()):
            tu.append({"doan": d["id"], "text": w, "start": moc[d["id"]]["start"] + 0.15 + i * 0.2,
                       "end": moc[d["id"]]["start"] + 0.3 + i * 0.2})
    sx = copy.deepcopy(SX)
    sx["man_ket"]["logo_chu"] = {"dong1": "KÊNH", "dong2": "THỬ", "dong2_nhan": "NGHIỆM"}
    r = Dung(P, kh, BRAND, sx, cat, tu, {"doan": list(moc.values())}, goc).viet()
    s2 = (P / "hf/compositions/s2.html").read_text(encoding="utf-8")
    assert "Nguồn: Luật 1/2024, Điều 1 khoản 2" in s2
    ket = (P / "hf/compositions/ket.html").read_text(encoding="utf-8")
    assert "0900 111 222" in ket and "Thôn 1" in ket and "NGHIỆM" in ket
    assert 'class="nw"' in ket
    idx = (P / "hf/index.html").read_text(encoding="utf-8")
    assert f'data-duration="{r["tong"]}"' in idx and "assets/img/c4.jpg" in (P / "hf/compositions/s4.html").read_text(encoding="utf-8")
    for f in (P / "hf").rglob("*.html"):
        assert "Vạn Xuân" not in f.read_text(encoding="utf-8")


# ---------------------------------------------------------------- sản xuất hàng loạt
@pytest.fixture()
def nha_may(tmp_path, monkeypatch):
    goc = tmp_path / "repo"
    (goc / "brand/kenhthu").mkdir(parents=True)
    (goc / "projects").mkdir()
    (goc / "brand/kenhthu/brand.json").write_text(json.dumps(BRAND, ensure_ascii=False), encoding="utf-8")
    (goc / "brand/kenhthu/san-xuat.yaml").write_text(yaml.safe_dump(SX, allow_unicode=True), encoding="utf-8")
    (goc / "brand/kenhthu/cau-hinh.yaml").write_text("tien_to_ma_video: kt\n", encoding="utf-8")
    (goc / "projects/kt-004-cu").mkdir()
    monkeypatch.delenv("KENH_GOC_DIR", raising=False)
    monkeypatch.setattr("tools_local.nap_kenh.nap_env", lambda: None)
    xt = tmp_path / "xem-thu"
    xt.mkdir()
    monkeypatch.setenv("MAY_REELS_XEM_THU_DIR", str(xt))
    monkeypatch.setattr("may_reels.hang_cho.do_thong_so", lambda p: ThongSo(1080, 1920, 40.0, 30.0))
    bang = BangGia()
    S.khoi_tao(bang)
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kenhthu", "ma": m, "chu_de": m, "trang_thai_san_xuat": "ý tưởng"}
                                    for m in ("cd-a", "cd-b", "cd-c")])
    yt = bang.tab("Ý tưởng")
    c = yt.doc_tat_ca()[0].index("duyet_chu_de") + 1
    yt.dat(2, c, "Làm")
    yt.dat(3, c, "Làm")
    return goc, bang


def dung_gia(kich_ban: dict):
    """kich_ban[ma_video] = danh sách (mã thoát, tóm tắt) trả lần lượt; tự tạo renders/final.mp4 khi thành công."""
    def ham(ma_video, *, goc, stages=None, giay=None):
        ma, tom = kich_ban[ma_video].pop(0)
        if ma == MA_OK:
            (goc / "projects" / ma_video / "renders").mkdir(parents=True, exist_ok=True)
            (goc / "projects" / ma_video / "renders/final.mp4").write_bytes(b"mp4-" + ma_video.encode())
        return ma, tom
    return ham


def agent_gia(goi: list):
    def ham(prompt, *, du_an, goc):
        goi.append((du_an.name, prompt, json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8"))))
        ma = du_an.name
        cd = ma.split("-", 2)[2]
        (du_an / "ke_hoach.json").write_text(json.dumps(ke_hoach(ma_video=ma, ma_chu_de=cd), ensure_ascii=False),
                                             encoding="utf-8")
        return {"result": "ok", "num_turns": 3, "duration_ms": 1000}
    return ham


def test_so_tiep_theo(nha_may):
    goc, _ = nha_may
    assert so_tiep_theo("kenhthu", goc) == ("kt", 5)


def test_san_xuat_lo_vong_sua_va_job_hong_khong_keo_job_khac(nha_may):
    goc, bang = nha_may
    goi = []
    kb = {"kt-005-cd-a": [(MA_KE_HOACH, {"loi": "hook ước lượng 4.1s"}), (MA_OK, {"diem_qa": 70, "tru_diem": {"x": 30}}),
                          (MA_OK, {"diem_qa": 72}) ],
          "kt-006-cd-b": [(1, {"loi": "hyperframes render lỗi"})]}
    ds = san_xuat(bang, "kenhthu", 3, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None)
    assert [k.ma_video for k in ds] == ["kt-005-cd-a", "kt-006-cd-b"]  # cd-c chưa chọn Làm
    a, b = ds
    assert a.trang_thai == "cho_duyet" and a.diem_qa == 72 and "Dưới ngưỡng" in a.canh_bao and a.vong == 2
    assert a.so_luot_agent == 3 and "hook" in goi[1][2]["phan_hoi"] and "Điểm QA 70" in goi[2][2]["phan_hoi"]
    assert b.trang_thai == "loi" and "render" in b.loi
    hang = S.doc_dong(bang, HANG_CHO)
    assert {(d["ma_video"], d["nen_tang"]) for d in hang} == {("kt-005-cd-a", n) for n in ("fb_reels", "yt_shorts", "tiktok")}
    assert all(d["duyet"] == "Chờ duyệt" and d["diem_qa"] == "72" and "Dưới ngưỡng" in d["canh_bao"] for d in hang)
    assert all(d["link_xem_thu"] == "kt-005-cd-a.mp4" and d["ghi_chu_may"].startswith("Thư mục đăng tay:") for d in hang)
    tt = {d["ma"]: d["trang_thai_san_xuat"] for d in S.doc_dong(bang, Y_TUONG)}
    assert tt == {"cd-a": "chờ duyệt", "cd-b": "lỗi", "cd-c": "ý tưởng"}
    job = json.loads((goc / "projects/kt-005-cd-a/reel_job.json").read_text(encoding="utf-8"))
    assert job["trang_thai"] == "cho_duyet"
    nk = S.doc_dong(bang, NHAT_KY)
    assert [(d["ma"], d["ket_qua"], d["so_luot_tro_ly"]) for d in nk] == [("kt-005-cd-a", "ok", "3"), ("kt-006-cd-b", "loi", "1")]
    # chạy lại: không sản xuất lại chủ đề đã có job
    assert san_xuat(bang, "kenhthu", 3, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None) == []


def test_san_xuat_thieu_canh_ghi_can_quay(nha_may):
    goc, bang = nha_may
    thieu = [{"doan": "s3", "y_can_canh": "xe vào vòng xuyến", "mo_ta_canh": "vòng xuyến thật", "goi_y_quay": "dọc 10s",
              "ly_do": "kho không có vòng xuyến"}]
    kb = {"kt-005-cd-a": [(MA_THIEU_CANH, {"loi": "thiếu", "thieu_canh": thieu})], "kt-006-cd-b": [(MA_OK, {"diem_qa": 90})]}
    ds = san_xuat(bang, "kenhthu", 2, goc=goc, agent=agent_gia([]), dung=dung_gia(kb), log=lambda s: None)
    assert [k.trang_thai for k in ds] == ["cho_quay", "cho_duyet"], [k.loi for k in ds]
    cq = S.doc_dong(bang, CAN_QUAY)
    assert cq[0]["ma_yeu_cau"] == "kenhthu:cd-a:1" and cq[0]["ly_do"] == "kho không có vòng xuyến" and cq[0]["trang_thai_quay"] == ""
    assert {d["ma"]: d["trang_thai_san_xuat"] for d in S.doc_dong(bang, Y_TUONG)}["cd-a"] == "chờ quay"


# ---------------------------------------------------------------- sửa
def test_sua_dua_duyet_ve_cho_duyet_va_chan_khi_co_dong_da_duyet(nha_may):
    goc, bang = nha_may
    san_xuat(bang, "kenhthu", 2, goc=goc, agent=agent_gia([]), log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})], "kt-006-cd-b": [(MA_OK, {"diem_qa": 88})]}))
    hc = bang.tab("Hàng chờ")
    tieu_de = hc.doc_tat_ca()[0]
    cd, cg = tieu_de.index("duyet") + 1, tieu_de.index("ghi_chu_sua") + 1
    hang = hc.doc_tat_ca()
    for r, h in enumerate(hang[1:], start=2):
        if h[0] == "kt-005-cd-a":
            hc.dat(r, cd, "Sửa")
            hc.dat(r, cg, "Đổi câu chốt cho vui hơn")
        if h[0] == "kt-006-cd-b" and h[tieu_de.index("nen_tang")] == "fb_reels":
            hc.dat(r, cd, "Sửa")
            hc.dat(r, cg, "Sửa hook")
        if h[0] == "kt-006-cd-b" and h[tieu_de.index("nen_tang")] == "tiktok":
            hc.dat(r, cd, "Duyệt")

    def agent_sua(prompt, *, du_an, goc):
        kh = json.loads((du_an / "ke_hoach.json").read_text(encoding="utf-8"))
        kh["doan"][4]["loi"] = "Nhớ ba điều này, qua ngã tư vui và an toàn hơn nhé."
        (du_an / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok"}
    kq = sua(bang, goc=goc, agent=agent_sua, log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 93})], "kt-006-cd-b": [(MA_OK, {"diem_qa": 80})]}))
    ket = {k["ma_video"]: k for k in kq}
    assert ket["kt-005-cd-a"]["trang_thai"] == "cho_duyet" and ket["kt-005-cd-a"]["dung_lai"]
    rows = {(d["ma_video"], d["nen_tang"]): d for d in S.doc_dong(bang, HANG_CHO)}
    a = rows[("kt-005-cd-a", "fb_reels")]
    assert a["duyet"] == "Chờ duyệt" and a["diem_qa"] == "93" and "Đã sửa theo ghi chú lần 1" in a["canh_bao"]
    assert a["link_xem_thu"] == "kt-005-cd-a-v2.mp4" and a["ghi_chu_sua"] == "Đổi câu chốt cho vui hơn"
    assert (goc / "projects/kt-005-cd-a/ke_hoach.truoc-sua-1.json").is_file()
    # kt-006: TikTok đã Duyệt -> không thay video, giữ nguyên "Sửa" và ghi lỗi
    assert ket["kt-006-cd-b"]["trang_thai"] == "loi"
    assert rows[("kt-006-cd-b", "fb_reels")]["duyet"] == "Sửa" and rows[("kt-006-cd-b", "tiktok")]["duyet"] == "Duyệt"
    assert "đã được duyệt" in rows[("kt-006-cd-b", "fb_reels")]["loi"]


def test_khong_viet_cung_ten_kenh_trong_may_reels_va_skill():
    for p in list((REPO / "may_reels").rglob("*.py")) + list((REPO / "skills" / "may-reels").rglob("*.md")):
        t = p.read_text(encoding="utf-8").lower()
        assert "vanxuan" not in t and "vạn xuân" not in t, p


# ---------------------------------------------------------------- cảnh tạm (sơ đồ) và thay cảnh thật
SO_DO = {"so_do": {"kieu": "giao_nhau", "xe": [{"tu": "phai", "thu_tu": 1}, {"tu": "duoi", "thu_tu": 2}]},
         "mo_ta": "sơ đồ ngã tư"}
THIEU = [{"doan": "s2", "y_can_canh": "ngã tư thật", "mo_ta_canh": "ngã tư không đèn", "goi_y_quay": "dọc 10s",
          "ly_do": "kho không có ngã tư"}]


def ke_hoach_tam(**kw):
    kh = ke_hoach(**kw)
    kh["doan"][1]["canh"] = copy.deepcopy(SO_DO)
    kh["thieu_canh"] = copy.deepcopy(THIEU)
    return kh


def test_ke_hoach_canh_tam_hop_le_va_canh_bao():
    loi, cb = kiem_tra(ke_hoach_tam(), BRAND, SX)
    assert loi == [] and any("Có cảnh tạm" in x and "s2" in x for x in cb)


@pytest.mark.parametrize("sua_kh,tim", [
    (lambda k: k.update(thieu_canh=[]), "chỉ dùng cho đoạn có trong thieu_canh"),
    (lambda k: k["doan"][1].update(canh={"ma": "v2", "vao": 1.0, "mo_ta": "sân"}), "phải dùng cảnh tạm"),
    (lambda k: k["doan"][1]["canh"]["so_do"].update(xe=[]), "cần danh sách xe"),
    (lambda k: k["thieu_canh"][0].update(doan="s9"), "không tồn tại"),
])
def test_ke_hoach_canh_tam_dung_sai(sua_kh, tim):
    kh = ke_hoach_tam()
    sua_kh(kh)
    assert any(tim in x for x in loi_cua(kh)), loi_cua(kh)


def test_tao_artifact_va_cat_canh_voi_canh_tam():
    from schemas.artifacts import validate_artifact
    kh = ke_hoach_tam()
    _, _, sp = tao_artifact(kh, BRAND, SX)
    validate_artifact("scene_plan", sp)
    assert sp["scenes"][1]["type"] == "diagram"
    cat = canh.tinh_cat(kh, BRAND, SX, moc_gia(kh))
    assert cat[1]["so_do"]["kieu"] == "giao_nhau" and cat[1]["ma"] is None


@pytest.mark.parametrize("so_do", [
    SO_DO["so_do"],
    {"kieu": "vong_xuyen", "xe": [{"tu": "tren", "thu_tu": 1}, {"tu": "phai", "thu_tu": 2}]},
    {"kieu": "the_chu", "chu": "NHƯỜNG BÊN PHẢI"},
    {"kieu": "giao_nhau", "duong_uu_tien": "ngang", "xe": [{"tu": "trai", "thu_tu": 1, "loai": "o_to"},
                                                          {"tu": "tren", "thu_tu": 2, "loai": "uu_tien"}]},
])
def test_html_so_do(tmp_path, so_do):
    kh = ke_hoach_tam()
    kh["doan"][1]["canh"]["so_do"] = so_do
    goc = tmp_path / "repo"
    (goc / "brand/kenhthu/assets/fonts").mkdir(parents=True)
    for f in ("F-ExtraBold.ttf", "F-Bold.ttf"):
        (goc / "brand/kenhthu/assets/fonts" / f).write_bytes(b"f")
    (goc / "brand/kenhthu/assets/logo.png").write_bytes(b"png")
    P = goc / "projects" / kh["ma_video"]
    (P / "hf/assets/img").mkdir(parents=True)
    (P / "hf/assets/img/c4.jpg").write_bytes(b"j")
    moc = moc_gia(kh)
    cat = canh.tinh_cat(kh, BRAND, SX, moc)
    Dung(P, kh, BRAND, SX, cat, [], {"doan": list(moc.values())}, goc).viet()
    h = (P / "hf/compositions/s2.html").read_text(encoding="utf-8")
    assert '<svg id="s2-sd"' in h and "assets/video" not in h
    if so_do["kieu"] != "the_chu":
        assert "s2-xe0" in h and "s2-xe1" in h
    if so_do.get("duong_uu_tien"):
        assert "ĐƯỜNG ƯU TIÊN" in h


def agent_tam(goi: list):
    def ham(prompt, *, du_an, goc):
        goi.append((du_an.name, json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8"))))
        cd = du_an.name.split("-", 2)[2]
        (du_an / "ke_hoach.json").write_text(json.dumps(ke_hoach_tam(ma_video=du_an.name, ma_chu_de=cd), ensure_ascii=False),
                                             encoding="utf-8")
        return {"result": "ok"}
    return ham


def test_san_xuat_canh_tam_vao_hang_cho_va_van_ghi_can_quay(nha_may):
    goc, bang = nha_may
    kb = {"kt-005-cd-a": [(MA_OK, {"diem_qa": 92, "canh_bao": ["Có cảnh tạm (sơ đồ): s2 — chờ cảnh quay thật"]})],
          "kt-006-cd-b": [(MA_OK, {"diem_qa": 95})]}
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_tam([]), dung=dung_gia(kb), log=lambda s: None)
    assert ds[0].trang_thai == "cho_duyet" and ds[0].thieu_canh
    hang = [d for d in S.doc_dong(bang, HANG_CHO) if d["ma_video"] == "kt-005-cd-a"]
    assert len(hang) == 3 and all("Có cảnh tạm" in d["canh_bao"] for d in hang)
    cq = S.doc_dong(bang, CAN_QUAY)
    assert [(d["ma_yeu_cau"], d["ma_video"]) for d in cq] == [("kenhthu:cd-a:1", "kt-005-cd-a")]
    job = json.loads((goc / "projects/kt-005-cd-a/reel_job.json").read_text(encoding="utf-8"))
    assert job["trang_thai"] == "cho_duyet" and job["metadata"]["canh_tam"] == ["s2"]


def test_ca_cho_quay_dung_lai_cung_ma_video(nha_may):
    goc, bang = nha_may
    kb = {"kt-005-cd-a": [(MA_THIEU_CANH, {"loi": "thiếu", "thieu_canh": THIEU}), (MA_OK, {"diem_qa": 90})],
          "kt-006-cd-b": [(MA_OK, {"diem_qa": 95})]}
    goi = []
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None)
    assert json.loads((goc / "projects/kt-005-cd-a/reel_job.json").read_text(encoding="utf-8"))["trang_thai"] == "cho_quay"
    assert san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None)[0].ma_video \
        == "kt-006-cd-b"  # không có cờ: bỏ qua chủ đề đang chờ quay
    ds = san_xuat(bang, "kenhthu", 2, goc=goc, agent=agent_tam(goi), dung=dung_gia(kb), log=lambda s: None, ca_cho_quay=True)
    assert [(k.ma_video, k.trang_thai) for k in ds] == [("kt-005-cd-a", "cho_duyet")]
    assert "cảnh tạm" in goi[-1][1]["phan_hoi"]
    assert not (goc / "projects/kt-007-cd-a").exists()


def test_thay_canh_khi_da_quay(nha_may):
    goc, bang = nha_may
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_tam([]), log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 92})]}))
    cq = bang.tab("Cần quay")
    tieu_de = cq.doc_tat_ca()[0]
    cq.dat(2, tieu_de.index("trang_thai_quay") + 1, "Đã quay")  # người đánh dấu

    def agent_thay(prompt, *, du_an, goc):
        kh = json.loads((du_an / "ke_hoach.json").read_text(encoding="utf-8"))
        kh["doan"][1]["canh"] = {"ma": "v5", "vao": 0.0, "mo_ta": "ngã tư mới quay"}
        kh["thieu_canh"] = []
        (du_an / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok"}
    from may_reels.sua import thay_canh
    kq = thay_canh(bang, goc=goc, agent=agent_thay, log=lambda s: None,
                   dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 98})]}))
    assert kq[0]["trang_thai"] == "cho_duyet" and kq[0]["dung_lai"]
    d = next(x for x in S.doc_dong(bang, HANG_CHO) if x["ma_video"] == "kt-005-cd-a" and x["nen_tang"] == "fb_reels")
    assert d["duyet"] == "Chờ duyệt" and d["diem_qa"] == "98" and d["link_xem_thu"] == "kt-005-cd-a-v2.mp4"
    assert "Đã thay cảnh tạm" in d["canh_bao"]
    assert S.doc_dong(bang, CAN_QUAY)[0]["trang_thai_nap"].startswith("đã thay vào kt-005-cd-a")
    job = json.loads((goc / "projects/kt-005-cd-a/reel_job.json").read_text(encoding="utf-8"))
    assert job["metadata"]["canh_tam"] == []
    # chạy lại: dòng đã nạp -> không làm gì
    assert thay_canh(bang, goc=goc, agent=agent_thay, dung=dung_gia({}), log=lambda s: None) == []


def test_thay_canh_khong_co_canh_moi_thi_giu_so_do(nha_may):
    goc, bang = nha_may
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_tam([]), log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 92})]}))
    cq = bang.tab("Cần quay")
    cq.dat(2, cq.doc_tat_ca()[0].index("trang_thai_quay") + 1, "Đã quay")
    from may_reels.sua import thay_canh
    kq = thay_canh(bang, goc=goc, agent=lambda prompt, *, du_an, goc: {"result": "không có cảnh khớp"},
                   dung=dung_gia({}), log=lambda s: None)
    assert kq[0]["trang_thai"] == "khong_doi" and not kq[0]["dung_lai"]
    assert "chưa thấy cảnh mới" in S.doc_dong(bang, CAN_QUAY)[0]["trang_thai_nap"]

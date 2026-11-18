"""Kho cảnh: nạp cảnh mới quay, quyền hình, số lần dùng, job chờ quay về hàng sản xuất, gợi ý quay.

Agent, chép lời và nap_kenh.py đều giả. Test nạp thật chạy FFmpeg trên một video tổng hợp 3 giây (bỏ qua nếu thiếu FFmpeg).
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from may_reels import kho as K
from may_reels import sheet as S
from may_reels.cot_sheet import CAN_QUAY, QUYEN_HINH, Y_TUONG
from may_reels.goi_y_quay import kiem as kiem_goi_y, thieu, van_ban_zalo
from may_reels.san_xuat import MA_OK, MA_THIEU_CANH, chon_chu_de, san_xuat
from tests.may_reels.sheet_gia import BangGia
from tests.may_reels.test_san_xuat import THIEU, agent_gia, agent_tam, dung_gia, nha_may  # noqa: F401 (fixture)

REPO = Path(__file__).resolve().parents[2]
CO_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")

KENH_YAML = """id: kenhthu
ten_kenh: Kênh thử
# Quyền hình: người dùng sửa tay
quyen_hinh:
  da_dong_y: true
  ngay: "2026-11-10"
  pham_vi: "Mọi file đã nạp tới 2026-11-10"
  ngoai_tru: ["x-1"]   # chú thích giữ nguyên
  bo_sung:
    - ma: "cu-1"   # mục cũ
      ngay: "2026-11-12"
      ghi_chu: "đã đồng ý"

# Liên hệ
hotline: "0900 000 000"
"""


def nhan_dung(**kw) -> dict:
    n = {"loai": "BROLL", "mo_ta": "Xe chạy quanh vòng số 8 trên sân", "dia_diem": "san-tap", "co_canh": "trung",
         "chuyen_dong": "dung-yen", "the": ["san-tap", "vong-so-8"], "doan_dung_duoc": [[0.0, 2.5]],
         "chat_luong": "tot", "ghi_chu": "", "rui_ro": [], "duoc_dung": True, "can_xu_ly": "", "loi_noi": "",
         "mat_nguoi": False}
    n.update(kw)
    return n


# ---------------------------------------------------------------- hàm thuần
def test_ma_file_trung_ma_cua_kho_hien_co():
    # Cùng thuật toán với scripts/nap_canh_quay.py của bộ kit: mã của cảnh cũ trong kho thật không đổi.
    assert K.ma_file("canh-quay/Học Viên Nam_Hạng A_ trung cảnh.mp4") == "hoc-vien-nam-hang-a-trung-canh-78c68e"
    assert K.ma_file("image/Học viên chờ vào thi.jpg") == "hoc-vien-cho-vao-thi-36fdeb"


@pytest.mark.parametrize("w,h,ra", [(480, 854, "chi-khung-anh"), (1080, 1920, "toan-man"), (1920, 2560, "toan-man"),
                                    (1920, 1080, "chi-khung-anh"), (960, 1280, "chi-khung-anh"), (None, 10, "chi-khung-anh")])
def test_dung_cho_theo_footage_policy(w, h, ra):
    assert K.dung_cho(w, h) == ra


def test_kiem_nhan_dien_truong_may_tinh_va_ep_mat_nguoi():
    muc = {"loai_file": "video", "rong": 1080, "cao": 1920, "thoi_luong": 3.0}
    n, loi = K.kiem_nhan(nhan_dung(rui_ro=["mat-hoc-vien"], can_xu_ly="chỉ dùng 0-1 s", mat_nguoi=False), muc)
    assert loi == []
    assert n["mat_nguoi"] is True  # có rủi ro mặt học viên thì coi như có mặt người
    assert (n["nguon"], n["rong_nguon"], n["cao_nguon"], n["dung_cho"]) == ("trung-tam", 1080, 1920, "toan-man")
    assert set(n) == set(K.TRUONG_AGENT) | {"nguon", "rong_nguon", "cao_nguon", "dung_cho"}


@pytest.mark.parametrize("sua,tim", [
    ({"loai": "CLIP"}, "loai="),
    ({"the": ["Sân Tập"]}, "the phải"),
    ({"doan_dung_duoc": [[0, 9]]}, "ngoài 0-3.0s"),
    ({"doan_dung_duoc": [[1, 2], [0, 1.5]]}, "tăng dần"),
    ({"rui_ro": ["bien-so"], "can_xu_ly": ""}, "can_xu_ly"),
    ({"mat_nguoi": "khong"}, "mat_nguoi phải"),
    ({"rui_ro": ["mat-nguoi-la"]}, "rui_ro chỉ gồm"),
])
def test_kiem_nhan_bat_loi(sua, tim):
    _, loi = K.kiem_nhan(nhan_dung(**sua), {"loai_file": "video", "rong": 720, "cao": 1280, "thoi_luong": 3.0})
    assert any(tim in x for x in loi), loi


def test_them_bo_sung_yaml_giu_chu_thich_va_chi_them_muc_moi():
    moi = K.them_bo_sung_yaml(KENH_YAML, [{"ma": "moi-1", "ngay": "2026-11-17", "ghi_chu": "Đồng ý trên Sheet: \"A\""},
                                          {"ma": "cu-1", "ngay": "2026-11-17", "ghi_chu": "trùng, bỏ qua"}])
    assert "# chú thích giữ nguyên" in moi and "# mục cũ" in moi and "# Liên hệ" in moi
    d = yaml.safe_load(moi)
    assert [b["ma"] for b in d["quyen_hinh"]["bo_sung"]] == ["cu-1", "moi-1"]
    assert d["quyen_hinh"]["bo_sung"][1]["ghi_chu"] == "Đồng ý trên Sheet: \"A\""
    assert d["hotline"] == "0900 000 000" and d["quyen_hinh"]["ngoai_tru"] == ["x-1"]
    assert K.them_bo_sung_yaml(moi, [{"ma": "moi-1", "ngay": "x", "ghi_chu": "x"}]) == moi  # chạy lại: không đổi


@pytest.mark.parametrize("khoi", ["quyen_hinh:\n  da_dong_y: true\n  ngay: 2026-11-10\n\nkhac: 1\n",
                                  "quyen_hinh:\n  da_dong_y: true\n  bo_sung: []\nkhac: 1\n"])
def test_them_bo_sung_yaml_khi_chua_co_hoac_rong(khoi):
    d = yaml.safe_load(K.them_bo_sung_yaml(khoi, [{"ma": "m", "ngay": "2026-11-17", "ghi_chu": "g"}]))
    assert d["quyen_hinh"]["bo_sung"] == [{"ma": "m", "ngay": "2026-11-17", "ghi_chu": "g"}] and d["khac"] == 1


def test_them_bo_sung_yaml_tu_choi_khi_chua_co_quyen_hinh():
    with pytest.raises(ValueError, match="chưa có khối quyen_hinh"):
        K.them_bo_sung_yaml("id: a\n", [{"ma": "m", "ngay": "x", "ghi_chu": "g"}])


# ---------------------------------------------------------------- nap_kenh.py: quyền hình chỉ áp cho cảnh có mặt người
def _nap_kenh_mod():
    spec = importlib.util.spec_from_file_location("nap_kenh_kho_test", REPO / "tools_local" / "nap_kenh.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_nap_kenh_canh_moi_khong_mat_dung_ngay_co_mat_cho_xac_nhan(tmp_path):
    mod = _nap_kenh_mod()
    for f in ("a.mp4", "b.mp4", "c.mp4", "d.mp4"):
        (tmp_path / f).write_bytes(b"v")
    index = {  # dấu mtime cũ (2023) nhưng ngay_nap thật là hôm nay: phải tin ngay_nap
        "a.mp4": {"ma": "a", "dau": "1-1700000000", "ngay_nap": "2026-11-17"},
        "b.mp4": {"ma": "b", "dau": "1-1700000000", "ngay_nap": "2026-11-17"},
        "c.mp4": {"ma": "c", "dau": "1-1700000000", "ngay_nap": "2026-11-17"},
        "d.mp4": {"ma": "d", "dau": "1-1700000000"},  # cảnh cũ, không có ngay_nap: theo mtime như trước
    }
    nhan = {m: {"duoc_dung": True, "mat_nguoi": mn} for m, mn in (("a", False), ("b", True), ("c", True), ("d", True))}
    qh = {"da_dong_y": True, "ngay": "2026-11-10", "bo_sung": [{"ma": "c"}]}
    kq = {c["ma"]: c for c in mod.doc_kho(tmp_path, index, nhan, qh)}
    assert kq["a"]["dung_duoc"] and kq["a"]["ngay_nap"] == "2026-11-17"
    assert not kq["b"]["dung_duoc"] and "chờ xác nhận quyền hình" in kq["b"]["ly_do_loai"][0]
    assert kq["c"]["dung_duoc"]  # đã có trong quyen_hinh.bo_sung
    assert kq["d"]["dung_duoc"]  # nạp 2023 <= hạn: giữ nguyên hành vi cũ
    nhan["a"].pop("mat_nguoi")  # thiếu nhãn mat_nguoi: coi như có mặt người
    assert not {c["ma"]: c for c in mod.doc_kho(tmp_path, index, nhan, qh)}["a"]["dung_duoc"]


# ---------------------------------------------------------------- lệnh kho nap (FFmpeg thật, agent giả)
@pytest.fixture()
def kenh(tmp_path):
    goc = tmp_path / "repo"
    (goc / "brand/kenhthu").mkdir(parents=True)
    (goc / "projects").mkdir()
    k = tmp_path / "kenh-goc" / "kenhthu"
    (k / "canh-quay/_kho").mkdir(parents=True)
    (k / "canh-quay/moi-quay/2026-11-17").mkdir(parents=True)
    (k / "channel.yaml").write_text(KENH_YAML, encoding="utf-8")
    (k / "canh-quay/_kho/index.json").write_text(json.dumps(
        {"canh-quay/cu.mp4": {"ma": "cu-1", "file": "canh-quay/cu.mp4", "dau": "1-1"}}), encoding="utf-8")
    (k / "canh-quay/_kho/nhan.json").write_text(json.dumps({"cu-1": nhan_dung()}, ensure_ascii=False), encoding="utf-8")
    bang = BangGia()
    S.khoi_tao(bang)
    return goc, k, bang


def tao_video(p: Path, giay: float = 3.0, co_tieng: bool = True) -> None:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=360x640:rate=30:duration={giay}"]
    if co_tieng:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}", "-c:a", "aac"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(p)], check=True)


def agent_nhan(goi: list, mat: dict[str, bool] | None = None):
    def ham(prompt, *, du_an, goc):
        yc = json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8"))
        assert (du_an / "khung.jpg").is_file()
        goi.append(yc)
        co_mat = (mat or {}).get(Path(yc["file"]).name, False)
        n = nhan_dung(loai="ANH" if yc["loai_file"] == "anh" else "BROLL", mat_nguoi=co_mat,
                      doan_dung_duoc=[] if yc["loai_file"] == "anh" else [[0.0, 2.5]],
                      rui_ro=["mat-hoc-vien"] if co_mat else [], can_xu_ly="cần xin phép" if co_mat else "")
        (du_an / "nhan.json").write_text(json.dumps(n, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 500}
    return ham


def chep_gia(goi: list):
    def ham(p, ra):
        goi.append(p.name)
        return {"model": "gia", "doan": [{"start": 0.2, "end": 1.8, "text": "xin chào các bạn học viên"}],
                "so_tu": 6, "giay_co_loi": 1.6, "van_ban": "xin chào các bạn học viên"}
    return ham


@pytest.mark.skipif(not CO_FFMPEG, reason="cần FFmpeg")
def test_kho_nap_tu_phan_tich_gan_nhan_va_giu_dinh_dang(kenh):
    goc, k, bang = kenh
    moi = k / "canh-quay/moi-quay/2026-11-17"
    tao_video(moi / "BROLL tay ga_1.mp4")
    tao_video(moi / "NOI có mặt.mp4")
    from PIL import Image
    Image.new("RGB", (300, 400), "white").save(moi / "anh san.jpg")
    goi_nhan, goi_chep, goi_nap = [], [], []
    kq = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, agent=agent_nhan(goi_nhan, {"NOI có mặt.mp4": True}),
               chep=chep_gia(goi_chep), nap_kenh=lambda kenh, goc: goi_nap.append(kenh), log=lambda s: None)
    assert kq.loi == [], kq.loi
    assert len(kq.moi) == len(kq.nhan) == 3 and goi_nap == ["kenhthu"]
    assert sorted(goi_chep) == ["BROLL tay ga_1.mp4", "NOI có mặt.mp4"]  # ảnh không chép lời
    index = json.loads((k / "canh-quay/_kho/index.json").read_text(encoding="utf-8"))
    rel = "canh-quay/moi-quay/2026-11-17/BROLL tay ga_1.mp4"
    v = index[rel]
    assert v["ma"] == K.ma_file(rel) and v["file"] == rel
    assert {"ma", "file", "dau", "loai_file", "rong", "cao", "huong", "fps", "thoi_luong", "co_am_thanh",
            "chuyen_canh", "lufs", "loi_noi", "ngay_nap", "nap_luc", "nap_boi"} <= set(v)
    assert (v["loai_file"], v["rong"], v["cao"], v["huong"]) == ("video", 360, 640, "doc")
    assert 2.5 <= v["thoi_luong"] <= 3.5 and v["co_am_thanh"] is True and isinstance(v["chuyen_canh"], list)
    assert v["loi_noi"]["co_loi"] is True and v["loi_noi"]["so_tu"] == 6
    assert (k / "canh-quay/_kho" / v["ma"] / "khung.jpg").is_file()
    assert "xin chào" in (k / "canh-quay/_kho" / v["ma"] / "loi-thoai.srt").read_text(encoding="utf-8")
    a = index["canh-quay/moi-quay/2026-11-17/anh san.jpg"]
    assert (a["loai_file"], a["rong"], a["cao"], a["huong"]) == ("anh", 300, 400, "doc")
    # Thư mục mới quay chỉ còn đúng file của người: không có khung hình hay file tạm rơi vào.
    assert sorted(p.name for p in moi.iterdir()) == ["BROLL tay ga_1.mp4", "NOI có mặt.mp4", "anh san.jpg"]
    nhan = json.loads((k / "canh-quay/_kho/nhan.json").read_text(encoding="utf-8"))
    assert nhan["cu-1"] == nhan_dung()  # nhãn cũ giữ nguyên
    assert nhan[v["ma"]]["nguon"] == "trung-tam" and nhan[v["ma"]]["dung_cho"] == "chi-khung-anh"
    assert "the_da_co" in goi_nhan[0] and "vong-so-8" in goi_nhan[0]["the_da_co"]
    # Cảnh có mặt người -> tab Quyền hình, chờ người.
    qh = S.doc_dong(bang, QUYEN_HINH)
    assert [d["ma_canh"] for d in qh] == kq.cho_quyen == [K.ma_file("canh-quay/moi-quay/2026-11-17/NOI có mặt.mp4")]
    assert qh[0]["xac_nhan_quyen"] == "" and qh[0]["khung_hinh"].endswith("/khung.jpg")
    # Chạy lại: không có gì mới, không gọi agent.
    kq2 = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, agent=agent_nhan(goi_nhan), chep=chep_gia(goi_chep),
                nap_kenh=lambda kenh, goc: None, log=lambda s: None)
    assert kq2.moi == [] and kq2.nhan == [] and len(goi_nhan) == 3


@pytest.mark.skipif(not CO_FFMPEG, reason="cần FFmpeg")
def test_kho_nap_nhan_sai_khong_vao_kho_va_lan_sau_gan_lai(kenh):
    goc, k, bang = kenh
    tao_video(k / "canh-quay/moi-quay/a.mp4", co_tieng=False)

    def agent_sai(prompt, *, du_an, goc):
        (du_an / "nhan.json").write_text(json.dumps(nhan_dung(dia_diem="san-bong")), encoding="utf-8")
        return {"result": "ok"}
    kq = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, agent=agent_sai, chep=chep_gia([]),
               nap_kenh=lambda kenh, goc: None, log=lambda s: None)
    assert kq.moi and not kq.nhan and "dia_diem" in kq.loi[0]
    assert "a-" not in json.dumps(json.loads((k / "canh-quay/_kho/nhan.json").read_text(encoding="utf-8")))
    goi = []
    kq = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, agent=agent_nhan(goi), chep=chep_gia([]),
               nap_kenh=lambda kenh, goc: None, log=lambda s: None)
    assert kq.moi == [] and len(kq.nhan) == 1 and len(goi) == 1  # không phân tích lại, chỉ gắn lại nhãn


def test_kho_nap_nhan_file_script_cu_da_lap_index(kenh):
    # Script cũ của bộ kit đã lập index cho file trong thư mục mới quay (không có ngay_nap): kho nap nhận về,
    # ghi ngày nạp thật và gắn nhãn, không phân tích lại.
    goc, k, bang = kenh
    rel = "canh-quay/moi-quay/b.mp4"
    (k / rel).write_bytes(b"v")
    (k / "canh-quay/_kho/b-1").mkdir()
    from PIL import Image
    Image.new("RGB", (60, 100)).save(k / "canh-quay/_kho/b-1/khung.jpg")
    idx = json.loads((k / "canh-quay/_kho/index.json").read_text(encoding="utf-8"))
    idx[rel] = {"ma": "b-1", "file": rel, "dau": "1-1700000000", "loai_file": "video", "rong": 720, "cao": 1280,
                "thoi_luong": 3.0}
    (k / "canh-quay/_kho/index.json").write_text(json.dumps(idx), encoding="utf-8")
    goi = []
    kq = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, agent=agent_nhan(goi), chep=chep_gia([]),
               nap_kenh=lambda kenh, goc: None, log=lambda s: None)
    assert kq.moi == [] and kq.nhan == ["b-1"]
    m = json.loads((k / "canh-quay/_kho/index.json").read_text(encoding="utf-8"))[rel]
    assert m["ngay_nap"] == K.hom_nay() and m["nap_boi"] == "kho-nap"
    assert "ngay_nap" not in json.loads((k / "canh-quay/_kho/index.json").read_text(encoding="utf-8"))["canh-quay/cu.mp4"]


def test_kho_nap_che_do_thu_khong_ghi(kenh):
    goc, k, bang = kenh
    (k / "canh-quay/moi-quay/a.mp4").write_bytes(b"v")
    truoc = (k / "canh-quay/_kho/index.json").read_text(encoding="utf-8")
    kq = K.nap(bang, "kenhthu", goc=goc, thu_muc_kenh=k, thu=True, agent=None, chep=None,
               nap_kenh=lambda kenh, goc: pytest.fail("chạy thử không được gọi nap_kenh"), log=lambda s: None)
    assert kq.moi == [] and (k / "canh-quay/_kho/index.json").read_text(encoding="utf-8") == truoc


def test_xac_nhan_quyen_hinh_chep_vao_channel_yaml(kenh):
    goc, k, bang = kenh
    K.ghi_quyen_hinh(bang, "kenhthu", [("moi-1", {"file": "canh-quay/moi-quay/a.mp4"}, nhan_dung(rui_ro=["mat-hoc-vien"])),
                                       ("moi-2", {"file": "canh-quay/moi-quay/b.mp4"}, nhan_dung(mat_nguoi=True))])
    t = bang.tab("Quyền hình")
    c = t.doc_tat_ca()[0].index("xac_nhan_quyen") + 1
    t.dat(2, c, "Đồng ý")
    t.dat(3, c, "Không")
    tm = K.thu_muc("kenhthu", goc, k)
    assert K.ap_dung_quyen_hinh(bang, "kenhthu", tm, log=lambda s: None) == ["moi-1"]
    d = yaml.safe_load((k / "channel.yaml").read_text(encoding="utf-8"))
    assert [b["ma"] for b in d["quyen_hinh"]["bo_sung"]] == ["cu-1", "moi-1"]
    assert list(k.glob("channel.yaml.bak-*"))
    ap = {r["ma_canh"]: r["trang_thai_ap_dung"] for r in S.doc_dong(bang, QUYEN_HINH)}
    assert ap["moi-1"].startswith("đã chép") and ap["moi-2"].startswith("không dùng")
    assert K.ap_dung_quyen_hinh(bang, "kenhthu", tm, log=lambda s: None) == []  # đã áp dụng: không làm lại


# ---------------------------------------------------------------- số lần dùng cảnh
def _du_an(goc: Path, ten: str, canh: list[str], trang_thai: str | None, luc: str = "2026-11-15T10:00:00+07:00",
           kenh: str = "kenhthu") -> None:
    P = goc / "projects" / ten
    P.mkdir(parents=True)
    (P / "ke_hoach.json").write_text(json.dumps({"kenh": kenh, "doan": [{"canh": {"ma": m}} for m in canh]
                                                 + [{"canh": None}]}), encoding="utf-8")
    if trang_thai:
        (P / "reel_job.json").write_text(json.dumps({"trang_thai": trang_thai, "lich_su": [
            {"den": "dang_san_xuat", "luc": "2026-11-01T00:00:00+07:00"}, {"den": trang_thai, "luc": luc}]}),
            encoding="utf-8")


def test_thong_ke_chi_tinh_video_da_dung_xong(tmp_path):
    _du_an(tmp_path, "kt-1", ["a", "b"], "cho_duyet", "2026-11-15T10:00:00+07:00")
    _du_an(tmp_path, "kt-2", ["a"], "da_dang", "2026-11-16T09:00:00+07:00")
    _du_an(tmp_path, "kt-3", ["a", "c"], "loi")        # lỗi: không tính
    _du_an(tmp_path, "kt-4", ["c"], "cho_quay")       # chưa dựng: không tính
    _du_an(tmp_path, "kt-5", ["c"], None)             # không có job, không có final.mp4: không tính
    _du_an(tmp_path, "kk-1", ["a"], "cho_duyet", kenh="kenhkhac")
    tk = K.thong_ke_dung_canh(tmp_path, "kenhthu")
    assert tk["a"]["so_lan"] == 2 and tk["a"]["ngay_gan_nhat"] == "2026-11-16" and tk["b"]["so_lan"] == 1
    assert "c" not in tk
    assert K.thong_ke_dung_canh(tmp_path, "kenhthu", tru="kt-2")["a"]["so_lan"] == 1
    index = {"x.mp4": {"ma": "a"}, "y.mp4": {"ma": "z", "so_lan_dung": 4, "ngay_dung_gan_nhat": "2026-01-01"}}
    assert K.ap_thong_ke_vao_index(index, tk) == 2
    assert index["x.mp4"]["so_lan_dung"] == 2 and index["x.mp4"]["ngay_dung_gan_nhat"] == "2026-11-16"
    assert index["y.mp4"]["so_lan_dung"] == 0 and index["y.mp4"]["ngay_dung_gan_nhat"] is None
    assert K.ap_thong_ke_vao_index(index, tk) == 0


def test_san_xuat_ghi_so_lan_dung_vao_index_va_gui_ngay_cho_agent(nha_may, tmp_path, monkeypatch):
    goc, bang = nha_may
    k = tmp_path / "kenh-goc" / "kenhthu"
    (k / "canh-quay/_kho").mkdir(parents=True)
    (k / "canh-quay/_kho/index.json").write_text(json.dumps({"v1.mp4": {"ma": "v1"}, "v2.mp4": {"ma": "v2"}}),
                                                 encoding="utf-8")
    monkeypatch.setenv("KENH_GOC_DIR", str(tmp_path / "kenh-goc"))
    goi = []
    kb = {"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})], "kt-006-cd-b": [(MA_OK, {"diem_qa": 90})]}
    san_xuat(bang, "kenhthu", 2, goc=goc, agent=agent_gia(goi), dung=dung_gia(kb), log=lambda s: None)
    index = json.loads((k / "canh-quay/_kho/index.json").read_text(encoding="utf-8"))
    dung = {m["ma"]: m.get("so_lan_dung") for m in index.values()}
    assert dung["v1"] == 2  # cả hai video dùng v1 (ke_hoach mẫu của test_san_xuat)
    assert goi[1][2]["so_lan_dung_canh"]["v1"] == 1 and goi[1][2]["ngay_dung_canh_gan_nhat"]["v1"]


# ---------------------------------------------------------------- job chờ quay -> hàng sản xuất
def _danh_dau(bang, ma_yeu_cau: str, gia_tri: str = "Đã quay") -> None:
    t = bang.tab("Cần quay")
    hang = t.doc_tat_ca()
    i = next(n for n, h in enumerate(hang, 1) if h[0] == ma_yeu_cau)
    t.dat(i, hang[0].index("trang_thai_quay") + 1, gia_tri)


def test_job_cho_quay_du_canh_tu_ve_hang_san_xuat(nha_may):
    goc, bang = nha_may
    thieu2 = THIEU + [{**THIEU[0], "doan": "s3", "mo_ta_canh": "cận tay ga"}]
    kb = {"kt-005-cd-a": [(MA_THIEU_CANH, {"loi": "thiếu", "thieu_canh": thieu2}), (MA_OK, {"diem_qa": 90})]}
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), dung=dung_gia(kb), log=lambda s: None)
    jf = goc / "projects/kt-005-cd-a/reel_job.json"
    assert json.loads(jf.read_text(encoding="utf-8"))["trang_thai"] == "cho_quay"
    tao = S.doc_dong(bang, CAN_QUAY)[0]["tao_luc"]
    index = {"m.mp4": {"ma": "moi-1", "nap_luc": "2999-01-01T00:00:00+07:00"}}

    _danh_dau(bang, "kenhthu:cd-a:1")  # mới quay một trong hai cảnh
    assert K.tra_ve_san_xuat(bang, "kenhthu", index, goc=goc, log=lambda s: None) == []
    _danh_dau(bang, "kenhthu:cd-a:2")
    assert K.tra_ve_san_xuat(bang, "kenhthu", {"m.mp4": {"ma": "c", "nap_luc": tao[:10] + "T00:00:00+07:00"}},
                             goc=goc, log=lambda s: None) == []  # file nạp TRƯỚC yêu cầu: chưa tính
    assert K.tra_ve_san_xuat(bang, "kenhthu", index, goc=goc, log=lambda s: None) == ["kt-005-cd-a"]
    job = json.loads(jf.read_text(encoding="utf-8"))
    assert job["trang_thai"] == "cho_quay" and job["metadata"]["san_sang_san_xuat_lai"]["canh_moi"] == ["moi-1"]
    assert all("quay về hàng sản xuất" in d["trang_thai_nap"] for d in S.doc_dong(bang, CAN_QUAY))
    # san-xuat lấy job này dù không có --ca-cho-quay, rồi bỏ cờ.
    assert [r["ma"] for r in chon_chu_de(bang, "kenhthu", 5, goc)] == ["cd-a", "cd-b"]
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), dung=dung_gia(kb), log=lambda s: None)
    assert [(k.ma_video, k.trang_thai) for k in ds] == [("kt-005-cd-a", "cho_duyet")]
    assert "san_sang_san_xuat_lai" not in json.loads(jf.read_text(encoding="utf-8")).get("metadata", {})


def test_goi_y_da_quay_dap_ung_yeu_cau_cua_job(nha_may):
    goc, bang = nha_may
    kb = {"kt-005-cd-a": [(MA_THIEU_CANH, {"loi": "thiếu", "thieu_canh": THIEU})]}
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), dung=dung_gia(kb), log=lambda s: None)
    S.ghi_theo_khoa(bang, CAN_QUAY, [{"ma_yeu_cau": "kenhthu:goi-y:vong-xuyen", "kenh": "kenhthu",
                                      "gop_yeu_cau": "kenhthu:cd-a:1", "tao_luc": "2026-01-01T00:00:00+07:00"}])
    _danh_dau(bang, "kenhthu:goi-y:vong-xuyen")  # người quay đánh dấu dòng trong danh sách gộp, không phải dòng của job
    index = {"m.mp4": {"ma": "moi-1", "nap_luc": "2999-01-01T00:00:00+07:00"}}
    assert K.tra_ve_san_xuat(bang, "kenhthu", index, goc=goc, log=lambda s: None) == ["kt-005-cd-a"]
    nap = {d["ma_yeu_cau"]: d["trang_thai_nap"] for d in S.doc_dong(bang, CAN_QUAY)}
    assert nap["kenhthu:goi-y:vong-xuyen"].startswith("đã nạp 1 cảnh mới")


def test_canh_tam_cho_duyet_de_cho_thay_canh(nha_may):
    goc, bang = nha_may
    san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_tam([]), log=lambda s: None,
             dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 92})]}))
    _danh_dau(bang, "kenhthu:cd-a:1")
    index = {"m.mp4": {"ma": "moi-1", "nap_luc": "2999-01-01T00:00:00+07:00"}}
    assert K.tra_ve_san_xuat(bang, "kenhthu", index, goc=goc, log=lambda s: None) == []
    assert S.doc_dong(bang, CAN_QUAY)[0]["trang_thai_nap"] == ""  # thay-canh còn nhận dòng này


# ---------------------------------------------------------------- kho thieu
def goi_y_mau(**kw) -> dict:
    c = {"ma": "can-xi-nhan", "loai": "BROLL", "mo_ta": "Cận tay bật xi-nhan trái", "goc_may": "Ngang tay lái, cận",
         "cam_doc": True, "thoi_luong_giay": [3, 6], "loi_thoai": None, "anh_sang": "7-9h, xuôi nắng",
         "tieng_on": "để tiếng thật", "xin_phep": "Quay tay, không thấy mặt", "phuc_vu_chu_de": ["cd-a", "cd-b"],
         "gop_yeu_cau": [], "uu_tien": 1, "ly_do": "kho chưa có cận xi-nhan"}
    c.update(kw)
    noi = {**c, "ma": "noi-hook-cd-a", "loai": "NOI", "mo_ta": "Thầy nói hook", "loi_thoai": "Vào vòng xuyến nhường ai?",
           "phuc_vu_chu_de": ["cd-a"], "uu_tien": 2}
    return {"buoi": [{"ten": "Sân tập buổi sáng", "dia_diem": "san-tap", "thoi_diem": "7-9h", "canh": [c, noi]}],
            "ghi_chu_chung": "Mang mic cài áo"}


def test_kiem_goi_y_va_van_ban_zalo():
    vao = {"chu_de": [{"ma": "cd-a", "chu_de": "A?"}, {"ma": "cd-b", "chu_de": "B?"}],
           "yeu_cau_dang_mo": [{"ma_yeu_cau": "kt:cd-a:1"}]}
    canh, loi = kiem_goi_y(goi_y_mau(), vao)
    assert loi == [] and len(canh) == 2
    txt = van_ban_zalo("Kênh Thử", goi_y_mau(), canh, "2026-11-17")
    assert "Cầm máy DỌC" in txt and "1. [BROLL] Cận tay bật xi-nhan trái" in txt and "Vào vòng xuyến nhường ai?" in txt
    assert "|" not in txt and "**" not in txt  # dán Zalo: không bảng, không markdown
    for sua, tim in (({"loai": "VLOG"}, "loai"), ({"phuc_vu_chu_de": ["cd-z"]}, "cd-z"), ({"xin_phep": ""}, "xin_phep"),
                     ({"gop_yeu_cau": ["kt:x:9"]}, "kt:x:9"), ({"ma": "Xi Nhan"}, "mã cảnh"),
                     ({"cam_doc": False}, "cam_doc"), ({"thoi_luong_giay": 5}, "thoi_luong")):
        assert any(tim in x for x in kiem_goi_y(goi_y_mau(**sua), vao)[1]), sua
    g = goi_y_mau()
    g["buoi"][0]["canh"][1]["loi_thoai"] = ""
    assert any("loi_thoai" in x for x in kiem_goi_y(g, vao)[1])


def test_kho_thieu_ghi_can_quay_va_khong_de_dong_da_quay(nha_may):
    goc, bang = nha_may
    goi = []

    def agent(prompt, *, du_an, goc):
        vao = json.loads((du_an / "goi_y_quay.yeu_cau.json").read_text(encoding="utf-8"))
        goi.append(vao)
        (du_an / "goi_y_quay.json").write_text(json.dumps(goi_y_mau(), ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 100}
    kq = thieu(bang, "kenhthu", goc=goc, agent=agent, log=lambda s: None)
    assert kq["loi"] == [] and kq["file_zalo"].is_file()
    assert [c["ma"] for c in goi[0]["chu_de"]] == ["cd-a", "cd-b"]  # chỉ chủ đề đã chọn Làm
    assert "hoi-nhanh-dap-dung" in goi[0]["thu_vien_dinh_dang"] and goi[0]["kho_canh"][0]["so_lan_dung"] == 0
    d = {r["ma_yeu_cau"]: r for r in S.doc_dong(bang, CAN_QUAY)}
    r = d["kenhthu:goi-y:can-xi-nhan"]
    assert r["ma_chu_de"] == "cd-a, cd-b" and r["goi_y_quay"].startswith("Cầm dọc 9:16") and r["buoi"].startswith("Sân tập")
    assert d["kenhthu:goi-y:noi-hook-cd-a"]["loi_thoai"] == "Vào vòng xuyến nhường ai?"
    _danh_dau(bang, "kenhthu:goi-y:can-xi-nhan")
    sua_o = bang.tab("Cần quay").lan_ghi.__len__()

    def agent2(prompt, *, du_an, goc):
        g = goi_y_mau(mo_ta="MÔ TẢ MỚI")
        g["buoi"][0]["canh"] = g["buoi"][0]["canh"][:1]  # bỏ cảnh NOI khỏi gợi ý mới
        (du_an / "goi_y_quay.json").write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok"}
    thieu(bang, "kenhthu", goc=goc, agent=agent2, log=lambda s: None)
    d = {r["ma_yeu_cau"]: r for r in S.doc_dong(bang, CAN_QUAY)}
    assert d["kenhthu:goi-y:can-xi-nhan"]["mo_ta_canh"] == "Cận tay bật xi-nhan trái"  # đã quay: không ghi đè
    assert d["kenhthu:goi-y:noi-hook-cd-a"]["ly_do"].startswith("Không còn trong gợi ý")
    assert len(bang.tab("Cần quay").lan_ghi) > sua_o
    assert len(S.doc_dong(bang, CAN_QUAY)) == 2  # không nhân đôi dòng


def test_kho_thieu_tu_choi_goi_y_sai_khong_ghi_sheet(nha_may):
    goc, bang = nha_may

    def agent(prompt, *, du_an, goc):
        (du_an / "goi_y_quay.json").write_text(json.dumps(goi_y_mau(phuc_vu_chu_de=["cd-khong-co"])), encoding="utf-8")
        return {"result": "ok"}
    kq = thieu(bang, "kenhthu", goc=goc, agent=agent, log=lambda s: None)
    assert kq["loi"] and S.doc_dong(bang, CAN_QUAY) == []

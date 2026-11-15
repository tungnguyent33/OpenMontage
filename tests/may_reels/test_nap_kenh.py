"""tools_local/nap_kenh.py: không lộ đường dẫn tuyệt đối, không viết cứng giá trị của một kênh."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
NAP = REPO / "tools_local" / "nap_kenh.py"

CHU_DE = """| Mã | Trụ cột | Định dạng | Chủ đề | Ý chính | Nguồn | Trend |
|---|---|---|---|---|---|---|
| chu-de-a | t1 | hoi-dap | Chủ đề A | ý | nguồn | - |
| chu-de-b | t1 | giai-thich | Chủ đề B | ý | nguồn | - |
"""


@pytest.fixture()
def nap(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("nap_kenh_test", NAP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root = tmp_path / "repo"
    (root / "brand").mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", root)  # .env và đường dẫn tương đối tính theo repo giả
    monkeypatch.delenv(mod.BIEN_KENH_GOC, raising=False)
    return mod, root


def tao_kenh(goc: Path, ma: str = "kenhthu") -> Path:
    k = goc / "channels" / ma
    (k / "context").mkdir(parents=True)
    (k / "image").mkdir()
    (k / "fonts").mkdir()
    (k / "canh-quay" / "_kho").mkdir(parents=True)
    (k / "channel.yaml").write_text(f"id: {ma}\nten_kenh: Kênh thử\nquyen_hinh:\n  da_dong_y: true\n  ngay: '2030-01-01'\n",
                                    encoding="utf-8")
    (k / "context" / "business.md").write_text("# Bí mật kinh doanh\n- Hotline: 0900 000 000\nNỘI-DUNG-RIÊNG-TƯ\n",
                                               encoding="utf-8")
    (k / "chu-de.md").write_text(CHU_DE, encoding="utf-8")
    (k / "image" / "san.jpg").write_bytes(b"x")
    (k / "fonts" / "FontThu-Bold.ttf").write_bytes(b"font")
    (k / "canh-quay" / "a.mp4").write_bytes(b"v")
    (k / "canh-quay" / "_kho" / "index.json").write_text(
        json.dumps({"a.mp4": {"ma": "a-1", "dau": "x-1700000000", "loai_file": "video"}}), encoding="utf-8")
    (k / "canh-quay" / "_kho" / "nhan.json").write_text(json.dumps({"a-1": {"duoc_dung": True}}), encoding="utf-8")
    (k / "canh-quay" / "_kho" / "KHO.md").write_text("kho", encoding="utf-8")
    videos = goc / "videos"
    videos.mkdir()
    (videos / "kt-001-chu-de-a").mkdir()
    (videos / "vx-002-chu-de-b").mkdir()  # tiền tố của kênh khác: không được tính
    return k


def doc_brand(root: Path, ma: str = "kenhthu") -> tuple[str, dict]:
    raw = (root / "brand" / ma / "brand.json").read_text(encoding="utf-8")
    return raw, json.loads(raw)


def test_brand_json_khong_co_duong_dan_tuyet_doi_va_context(nap, tmp_path):
    mod, root = nap
    kenh = tao_kenh(tmp_path)
    assert mod.main([str(kenh), "--out", str(root / "brand")]) == 0
    raw, b = doc_brand(root)
    for chuoi in (str(tmp_path), tmp_path.as_posix(), str(tmp_path).replace("\\", "\\\\")):
        assert chuoi not in raw
    assert "NỘI-DUNG-RIÊNG-TƯ" not in raw
    assert b["context"]["business"]["file_tuong_doi"] == "context/business.md"
    ban_local = root / b["context"]["business"]["ban_local"]
    assert "NỘI-DUNG-RIÊNG-TƯ" in ban_local.read_text(encoding="utf-8")
    assert ban_local.is_relative_to(root / "brand" / "kenhthu" / mod.THU_MUC_LOCAL)
    assert b["anh_that"] == ["image/san.jpg"]
    assert b["kho_md"] == "canh-quay/_kho/KHO.md"
    assert all("duong_dan" not in c for c in b["kho_canh"])
    assert b["kho_canh"][0]["file_tuong_doi"] == "a.mp4"
    assert b["nguon_kenh"]["bien_moi_truong"] == mod.BIEN_KENH_GOC


def test_tien_to_va_font_doc_tu_cau_hinh_kenh(nap, tmp_path):
    mod, root = nap
    kenh = tao_kenh(tmp_path)
    out = root / "brand" / "kenhthu"
    out.mkdir(parents=True)
    (out / "cau-hinh.yaml").write_text(
        "tien_to_ma_video: kt\nthu_muc_video: ../../videos\nfonts: [FontThu-Bold.ttf]\n", encoding="utf-8")
    assert mod.main([str(kenh), "--out", str(root / "brand")]) == 0
    _, b = doc_brand(root)
    da_lam = {r["ma"]: r["da_lam"] for r in b["chu_de"]}
    assert da_lam == {"chu-de-a": True, "chu-de-b": False}
    assert list(b["font"]["files"]) == ["FontThu-Bold.ttf"]
    assert (out / "assets" / "fonts" / "FontThu-Bold.ttf").is_file()
    assert b["canh_bao"] == []


def test_thieu_cau_hinh_thi_canh_bao_khong_doan(nap, tmp_path):
    mod, root = nap
    kenh = tao_kenh(tmp_path)
    assert mod.main([str(kenh), "--out", str(root / "brand")]) == 0
    _, b = doc_brand(root)
    assert not any(r["da_lam"] for r in b["chu_de"])
    assert b["font"]["files"] == {}
    assert len(b["canh_bao"]) == 2


def test_doc_thu_muc_kenh_tu_bien_moi_truong(nap, tmp_path, monkeypatch):
    mod, root = nap
    tao_kenh(tmp_path)
    assert mod.main(["--id", "kenhthu", "--out", str(root / "brand")]) == 2  # chưa đặt biến
    monkeypatch.setenv(mod.BIEN_KENH_GOC, str(tmp_path / "channels"))
    assert mod.main(["--id", "kenhthu", "--out", str(root / "brand")]) == 0
    assert (root / "brand" / "kenhthu" / "brand.json").is_file()


def test_nap_kenh_khong_viet_cung_gia_tri_mot_kenh():
    src = NAP.read_text(encoding="utf-8")
    for cam in ("vanxuan", "vx-", "BeVietnam"):
        assert cam not in src, cam


@pytest.mark.skipif(shutil.which("git") is None, reason="không có git")
@pytest.mark.parametrize("duong_dan", [".env", "secrets/khoa.json", "brand/kenhbatky/_local/context/business.md"])
def test_gitignore_chan_bi_mat_va_noi_dung_kenh(duong_dan):
    kq = subprocess.run(["git", "check-ignore", "-q", "--no-index", duong_dan], cwd=REPO)
    assert kq.returncode == 0, f"{duong_dan} chưa bị gitignore"


def test_brand_json_da_commit_khong_co_duong_dan_tuyet_doi():
    for f in (REPO / "brand").glob("*/brand.json"):
        raw = f.read_text(encoding="utf-8")
        assert ":\\\\" not in raw and ":/" not in raw.replace("://", ""), f

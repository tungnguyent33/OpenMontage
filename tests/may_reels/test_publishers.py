"""Ba publisher Máy Reels với HTTP/dịch vụ giả: không gọi mạng."""
from __future__ import annotations

from pathlib import Path

import pytest

from schemas.artifacts import validate_artifact
from tools.publishers.facebook_reels import FacebookReels
from tools.publishers.tiktok_handoff import TiktokHandoff
from tools.publishers.youtube_shorts import YoutubeShorts


@pytest.fixture()
def video(tmp_path):
    p = tmp_path / "v.mp4"
    p.write_bytes(b"0123456789")
    return p


def hop_le(res):
    validate_artifact("publish_log", res.data["publish_log"])
    return res.data["publish_log"]["entries"][0]


# ---------------------------------------------------------------- Facebook
class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._b = body
        self.text = str(body)

    def json(self):
        return self._b


class HttpGia:
    def __init__(self, tra_ve):
        self.tra_ve = list(tra_ve)
        self.goi = []

    def _tra(self, method, url, kw):
        self.goi.append((method, url, kw))
        r = self.tra_ve.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, **kw):
        return self._tra("POST", url, kw)

    def get(self, url, **kw):
        return self._tra("GET", url, kw)


def fb_vao(video, **kw):
    return {"video_path": str(video), "page_id": "1234", "token_env": "KT_FB", "description": "mô tả", **kw}


def test_fb_mac_dinh_chay_thu_khong_goi_mang(video, monkeypatch):
    monkeypatch.setenv("KT_FB", "tok")
    http = HttpGia([])
    res = FacebookReels(http=http).execute(fb_vao(video))
    assert res.success and http.goi == [] and hop_le(res)["status"] == "pending_review"


def test_fb_dang_dung_ba_buoc(video, monkeypatch):
    monkeypatch.setenv("KT_FB", "tok")
    http = HttpGia([Resp(200, {"video_id": "v1", "upload_url": "u"}), Resp(200, {"success": True}),
                    Resp(200, {"success": True}), Resp(200, {"permalink_url": "/reel/v1", "status": {}})])
    res = FacebookReels(http=http).execute(fb_vao(video, that=True))
    e = hop_le(res)
    assert res.success and e["status"] == "published" and e["video_id"] == "v1"
    assert e["url"] == "https://www.facebook.com/reel/v1"
    (m1, u1, k1), (m2, u2, k2), (m3, u3, k3), (m4, u4, k4) = http.goi
    assert u1.endswith("/v27.0/1234/video_reels") and k1["data"]["upload_phase"] == "start"
    assert u2.endswith("/video-upload/v27.0/v1") and k2["headers"]["file_size"] == "10"
    assert k2["headers"]["Authorization"] == "OAuth tok" and k2["data"] == b"0123456789"
    assert k3["data"]["upload_phase"] == "finish" and k3["data"]["video_state"] == "PUBLISHED"
    assert m4 == "GET"


@pytest.mark.parametrize("tra_ve,loai", [
    ([Resp(403, {"error": {"code": 200, "message": "no"}})], "quyen"),
    ([Resp(400, {"error": {"code": 1363040, "message": "ratio"}})], "noi_dung"),
    ([Resp(503, {})], "mang"),
    ([ConnectionError("x")], "mang"),
    ([Resp(429, {})], "gioi_han"),
])
def test_fb_phan_loai_loi_buoc_dau(video, monkeypatch, tra_ve, loai):
    monkeypatch.setenv("KT_FB", "tok")
    res = FacebookReels(http=HttpGia(tra_ve)).execute(fb_vao(video, that=True))
    assert not res.success and res.data["loai_loi"] == loai and hop_le(res)["status"] == "failed"


@pytest.mark.parametrize("loi_cuoi", [ConnectionError("mất mạng"), Resp(502, {})])
def test_fb_loi_mang_o_buoc_dang_la_khong_ro(video, monkeypatch, loi_cuoi):
    monkeypatch.setenv("KT_FB", "tok")
    http = HttpGia([Resp(200, {"video_id": "v1"}), Resp(200, {"success": True}), loi_cuoi])
    res = FacebookReels(http=http).execute(fb_vao(video, that=True))
    assert res.data["loai_loi"] == "khong_ro" and hop_le(res)["video_id"] == "v1"


def test_fb_thieu_token(video, monkeypatch):
    monkeypatch.delenv("KT_FB", raising=False)
    http = HttpGia([])
    res = FacebookReels(http=http).execute(fb_vao(video, that=True))
    assert res.data["loai_loi"] == "quyen" and http.goi == []


# ---------------------------------------------------------------- YouTube
class Exec:
    def __init__(self, v):
        self.v = v

    def execute(self):
        if isinstance(self.v, Exception):
            raise self.v
        return self.v


class InsertGia:
    def __init__(self, ket_qua):
        self.k = list(ket_qua)

    def next_chunk(self):
        r = self.k.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class Tien:
    def __init__(self, n):
        self.resumable_progress = n


class YtGia:
    def __init__(self, kenh=("UCk",), chunk=None, privacy="public"):
        self.kenh = kenh
        self.chunk = chunk if chunk is not None else [(Tien(5), None), (None, {"id": "yt1"})]
        self.privacy = privacy
        self.body = None
        self.goi = []

    def channels(self):
        return self

    def videos(self):
        return self

    def list(self, **kw):
        self.goi.append(("list", kw))
        if kw.get("mine"):
            return Exec({"items": [{"id": k} for k in self.kenh]})
        return Exec({"items": [{"status": {"privacyStatus": self.privacy}}]})

    def insert(self, **kw):
        self.goi.append(("insert", kw))
        self.body = kw["body"]
        return InsertGia(self.chunk)


def yt_vao(video, **kw):
    return {"video_path": str(video), "title": "Tiêu đề", "description": "d", "channel_id": "UCk",
            "token_file_env": "KT_YT", **kw}


def test_yt_mac_dinh_chay_thu(video):
    dv = YtGia()
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video))
    assert res.success and dv.goi == [] and hop_le(res)["status"] == "pending_review"


def test_yt_tai_len_cong_khai_va_doc_lai(video):
    dv = YtGia()
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video, that=True, made_for_kids=False))
    e = hop_le(res)
    assert res.success and e["video_id"] == "yt1" and e["visibility"] == "public"
    assert dv.body["status"]["privacyStatus"] == "public" and dv.body["status"]["selfDeclaredMadeForKids"] is False
    assert "containsSyntheticMedia" not in dv.body["status"]
    assert [g[0] for g in dv.goi] == ["list", "insert", "list"]


def test_yt_sai_kenh_thi_khong_tai(video):
    dv = YtGia(kenh=("UCkhac",))
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video, that=True))
    assert res.data["loai_loi"] == "quyen" and [g[0] for g in dv.goi] == ["list"]


def test_yt_rieng_tu_sau_khi_tai(video):
    dv = YtGia(privacy="private")
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video, that=True))
    assert res.success and hop_le(res)["visibility"] == "private"


def test_yt_loi_mang_sau_khi_gui_het_la_khong_ro(video):
    dv = YtGia(chunk=[(Tien(10), None), ConnectionError("mất")])
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video, that=True))
    assert res.data["loai_loi"] == "khong_ro"


def test_yt_loi_mang_giua_chung_duoc_thu_lai(video):
    dv = YtGia(chunk=[(Tien(5), None), ConnectionError("mất")])
    res = YoutubeShorts(dich_vu=dv, media_upload=lambda p: object()).execute(yt_vao(video, that=True))
    assert res.data["loai_loi"] == "mang"


# ---------------------------------------------------------------- TikTok bàn giao
def test_tiktok_handoff_chep_video_va_caption(video):
    class Drive:
        def __init__(self):
            self.tai = []

        def thu_muc(self, ten, cha=None):
            return {"id": f"id-{ten}", "webViewLink": f"https://drive/{ten}"}

        def tai_len(self, p, ten, tm, mime):
            self.tai.append((ten, tm, mime, Path(p).read_bytes()))
            return {"id": ten}

    d = Drive()
    assert TiktokHandoff(drive=d).execute({"video_path": str(video), "ma_video": "m1", "caption": "Chào"}).data["chay_thu"]
    assert d.tai == []
    res = TiktokHandoff(drive=d).execute({"video_path": str(video), "ma_video": "m1", "caption": "Chào #tag", "that": True})
    e = hop_le(res)
    assert res.success and e["status"] == "exported" and res.data["link_thu_muc"] == "https://drive/m1"
    assert [(t[0], t[1]) for t in d.tai] == [("m1.mp4", "id-m1"), ("caption.txt", "id-m1")]
    assert d.tai[1][3].decode("utf-8").strip() == "Chào #tag"


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="không có ffmpeg")
def test_do_thong_so_video_that(tmp_path):
    import subprocess
    from may_reels.kiem_tra_video import do_thong_so, loi_thong_so
    p = tmp_path / "doc 9x16.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=540x960:r=30:d=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)
    ts = do_thong_so(p)
    assert (ts.rong, ts.cao) == (540, 960) and abs(ts.fps - 30) < 0.01 and abs(ts.giay - 4) < 0.2
    assert loi_thong_so(ts, "fb_reels") == [] and loi_thong_so(ts, "tiktok") == []
    ngang = tmp_path / "ngang.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=960x540:r=20:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(ngang)], check=True)
    loi = loi_thong_so(do_thong_so(ngang), "fb_reels")
    assert any("9:16" in x for x in loi) and any("fps" in x for x in loi) and any("ngắn hơn 3" in x for x in loi)

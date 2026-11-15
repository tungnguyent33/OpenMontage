"""Tải Short lên YouTube bằng YouTube Data API (videos.insert), OAuth của chủ kênh.

Tóm tắt API và ngày đọc tài liệu: docs/may-reels/API-DANG-BAI.md mục 2.
- Mặc định CHẠY THỬ: phải truyền `that: true`.
- Refresh token nằm trong file ở secrets/; tên biến môi trường chứa đường dẫn file được
  truyền qua `token_file_env` (khai trong brand/<kenh>/dang-bai.yaml).
- Trước khi tải: kiểm tra token đúng kênh `channel_id`. Sau khi tải: đọc lại privacyStatus.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile, ToolResult, ToolRuntime, ToolStability, ToolTier,
)
from tools.publishers._dang_chung import KHONG_RO, MANG, NOI_DUNG, QUYEN, bay_gio_utc, loai_theo_http, publish_log

CHUNK = 8 * 1024 * 1024
DO_DAI_TIEU_DE = 100  # giới hạn tiêu đề YouTube: chưa xác minh trong tài liệu đã đọc, cắt cho an toàn


def _ma_http(e) -> int | None:
    resp = getattr(e, "resp", None)
    st = getattr(resp, "status", None)
    try:
        return int(st) if st is not None else None
    except (TypeError, ValueError):
        return None


class YoutubeShorts(BaseTool):
    name = "youtube_shorts"
    version = "0.1.0"
    tier = ToolTier.PUBLISH
    capability = "publish"
    provider = "youtube"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["python:googleapiclient", "python:google_auth_oauthlib"]
    install_instructions = "pip install -r may_reels/requirements.txt; tạo OAuth client: docs/may-reels/CAI-DAT-DANG-BAI.md"
    agent_skills = []
    capabilities = ["publish_short"]
    supports = {"uploads": True, "dry_run_default": True}
    best_for = ["tải Short 9:16 tới 3 phút lên kênh YouTube sau khi người đã duyệt trên Sheet"]
    not_good_for = ["video dài trên 3 phút (sẽ không thành Shorts)"]

    input_schema = {
        "type": "object",
        "required": ["video_path", "title", "channel_id", "token_file_env"],
        "properties": {
            "video_path": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "channel_id": {"type": "string", "description": "ID kênh (UC...) phải khớp với token"},
            "token_file_env": {"type": "string", "description": "TÊN biến môi trường chứa đường dẫn file token"},
            "category_id": {"type": "string"},
            "made_for_kids": {"type": "boolean"},
            "contains_synthetic_media": {"type": "boolean"},
            "that": {"type": "boolean", "default": False},
        },
    }
    output_schema = {"type": "object", "properties": {"publish_log": {"type": "object"}, "loai_loi": {"type": "string"}}}
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=0, network_required=True)
    side_effects = ["tải công khai một video lên kênh YouTube (khi that=true)"]
    user_visible_verification = ["Mở link_bai trên Sheet, kiểm tra video công khai và hiện trong tab Shorts"]

    def __init__(self, dich_vu=None, media_upload=None) -> None:
        self._dv = dich_vu
        self._media = media_upload

    def _dich_vu(self, token_file: Path):
        if self._dv is None:
            from googleapiclient.discovery import build
            from may_reels.google_oauth import PHAM_VI_YOUTUBE, nap_creds
            self._dv = build("youtube", "v3", credentials=nap_creds(token_file, PHAM_VI_YOUTUBE), cache_discovery=False)
        return self._dv

    def _media_upload(self, path: Path):
        if self._media is not None:
            return self._media(path)
        from googleapiclient.http import MediaFileUpload
        return MediaFileUpload(str(path), mimetype="video/mp4", chunksize=CHUNK, resumable=True)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        video = Path(inputs["video_path"])
        tieu_de = (inputs.get("title") or "").strip()[:DO_DAI_TIEU_DE]
        mo_ta = inputs.get("description", "")
        entry: dict[str, Any] = {
            "platform": "youtube_shorts", "timestamp": bay_gio_utc(),
            "metadata_used": {"title": tieu_de, "description": mo_ta, "hashtags": list(inputs.get("hashtags") or [])},
        }

        def that_bai(loai: str, msg: str, video_id: str | None = None) -> ToolResult:
            entry.update(status="failed", error=msg)
            if video_id:
                entry["video_id"] = video_id
            return ToolResult(success=False, error=msg, data={"publish_log": publish_log(entry), "loai_loi": loai})

        if not video.is_file():
            return that_bai(NOI_DUNG, f"không thấy file {video.name}")
        if not tieu_de:
            return that_bai(NOI_DUNG, "thiếu tiêu đề")
        if not inputs.get("that"):
            entry["status"] = "pending_review"
            return ToolResult(success=True, data={"publish_log": publish_log(entry), "chay_thu": True})

        ten_bien = inputs["token_file_env"]
        v = os.environ.get(ten_bien, "").strip().strip('"').strip("'")
        if not v and self._dv is None:
            return that_bai(QUYEN, f"chưa đặt biến môi trường {ten_bien}")
        token_file = Path(v) if Path(v).is_absolute() else Path(__file__).resolve().parents[2] / v

        try:
            yt = self._dich_vu(token_file)
        except Exception as e:
            return that_bai(QUYEN, f"không mở được phiên YouTube: {e}")

        # 1. Đúng kênh chưa? (1 đơn vị quota)
        try:
            kq = yt.channels().list(part="id", mine=True).execute()
        except Exception as e:
            ma = _ma_http(e)
            return that_bai(loai_theo_http(ma) if ma else MANG, f"kiểm tra kênh: {e}")
        cac_kenh = [c.get("id") for c in kq.get("items", [])]
        if inputs["channel_id"] not in cac_kenh:
            return that_bai(QUYEN, f"token thuộc kênh {cac_kenh}, không phải {inputs['channel_id']}")

        # 2. Tải lên (resumable). Lỗi mạng khi đã gửi hết dữ liệu thì video CÓ THỂ đã tạo -> khong_ro.
        status = {"privacyStatus": "public"}
        if inputs.get("made_for_kids") is not None:
            status["selfDeclaredMadeForKids"] = bool(inputs["made_for_kids"])
        if inputs.get("contains_synthetic_media") is not None:
            status["containsSyntheticMedia"] = bool(inputs["contains_synthetic_media"])
        snippet = {"title": tieu_de, "description": mo_ta}
        if inputs.get("category_id"):
            snippet["categoryId"] = str(inputs["category_id"])
        tong = video.stat().st_size
        da_gui = 0
        phan_hoi = None
        try:
            yeu_cau = yt.videos().insert(part="snippet,status", body={"snippet": snippet, "status": status},
                                         media_body=self._media_upload(video))
            while phan_hoi is None:
                tien_do, phan_hoi = yeu_cau.next_chunk()
                if tien_do is not None:
                    da_gui = int(getattr(tien_do, "resumable_progress", da_gui) or da_gui)
        except Exception as e:
            ma = _ma_http(e)
            loai = loai_theo_http(ma)
            if loai == MANG and da_gui >= tong:
                loai = KHONG_RO
            return that_bai(loai, f"tải lên: {e}")
        video_id = (phan_hoi or {}).get("id")
        if not video_id:
            return that_bai(KHONG_RO, f"tải lên xong nhưng không có id ({phan_hoi})")

        # 3. Đọc lại privacyStatus.
        try:
            kq = yt.videos().list(part="status", id=video_id).execute()
            items = kq.get("items") or []
            rieng_tu = (items[0].get("status") or {}).get("privacyStatus") if items else None
        except Exception:
            rieng_tu = None
        url = f"https://www.youtube.com/shorts/{video_id}"
        entry.update(status="published", video_id=video_id, url=url)
        if rieng_tu in ("public", "private", "unlisted"):
            entry["visibility"] = rieng_tu
        return ToolResult(success=True, data={"publish_log": publish_log(entry), "privacy_status": rieng_tu})

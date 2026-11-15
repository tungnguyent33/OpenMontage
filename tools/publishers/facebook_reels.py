"""Đăng Reel lên Facebook Page qua Graph API (Reels Publishing API).

Tóm tắt API và ngày đọc tài liệu: docs/may-reels/API-DANG-BAI.md mục 1.
Mặc định CHẠY THỬ: phải truyền `that: true` mới gọi mạng. Token đọc từ biến môi trường
có tên trong `token_env` (khai trong brand/<kenh>/dang-bai.yaml), không truyền token trực tiếp.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile, ToolResult, ToolRuntime, ToolStability, ToolTier,
)
from tools.publishers._dang_chung import KHONG_RO, MANG, NOI_DUNG, QUYEN, LoiDang, bay_gio_utc, loai_theo_http, publish_log

GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com/video-upload"
PHIEN_BAN = "v27.0"
TIMEOUT = (15, 600)


class FacebookReels(BaseTool):
    name = "facebook_reels"
    version = "0.1.0"
    tier = ToolTier.PUBLISH
    capability = "publish"
    provider = "facebook"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["python:requests"]
    install_instructions = "Tạo app Meta và Page access token: docs/may-reels/CAI-DAT-DANG-BAI.md"
    agent_skills = []
    capabilities = ["publish_reel"]
    supports = {"uploads": True, "dry_run_default": True}
    best_for = ["đăng Reel 9:16 lên Facebook Page của kênh sau khi người đã duyệt trên Sheet"]
    not_good_for = ["trang cá nhân (API chỉ hỗ trợ Page)", "video ngoài 3-90 giây"]

    input_schema = {
        "type": "object",
        "required": ["video_path", "page_id", "token_env"],
        "properties": {
            "video_path": {"type": "string"},
            "page_id": {"type": "string", "description": "ID số của Page"},
            "token_env": {"type": "string", "description": "TÊN biến môi trường chứa Page access token"},
            "description": {"type": "string"},
            "title": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "is_ai_generated": {"type": "boolean"},
            "that": {"type": "boolean", "default": False, "description": "true = đăng thật; mặc định chạy thử"},
        },
    }
    output_schema = {"type": "object", "properties": {"publish_log": {"type": "object"}, "loai_loi": {"type": "string"}}}
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=0, network_required=True)
    side_effects = ["đăng công khai một Reel lên Facebook Page (khi that=true)"]
    user_visible_verification = ["Mở link_bai trên Sheet và xem Reel trên Page"]

    def __init__(self, http=None) -> None:
        self._http = http

    def _h(self):
        if self._http is None:
            import requests
            self._http = requests
        return self._http

    @staticmethod
    def _kiem(resp, buoc: str, loai_khi_mang: str = MANG) -> dict:
        if resp.status_code >= 400:
            try:
                err = resp.json().get("error", {})
                msg = f"{err.get('code', '')} {err.get('message', '')}".strip()
            except Exception:
                msg = (resp.text or "")[:300]
            loai = loai_theo_http(resp.status_code)
            if loai == MANG:
                loai = loai_khi_mang
            raise LoiDang(loai, f"{buoc}: HTTP {resp.status_code} {msg}")
        try:
            return resp.json()
        except Exception:
            return {}

    def _goi(self, ham, url, buoc, loai_khi_mang=MANG, **kw):
        try:
            resp = ham(url, timeout=TIMEOUT, **kw)
        except Exception as e:  # lỗi kết nối/timeout của requests
            raise LoiDang(loai_khi_mang, f"{buoc}: {type(e).__name__}: {e}") from e
        return self._kiem(resp, buoc, loai_khi_mang)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        video = Path(inputs["video_path"])
        mo_ta = inputs.get("description", "")
        entry: dict[str, Any] = {
            "platform": "facebook_reels", "timestamp": bay_gio_utc(),
            "metadata_used": {"title": inputs.get("title", ""), "description": mo_ta,
                              "hashtags": list(inputs.get("hashtags") or [])},
        }
        if not video.is_file():
            entry.update(status="failed", error=f"không thấy file {video.name}")
            return ToolResult(success=False, error=entry["error"], data={"publish_log": publish_log(entry), "loai_loi": NOI_DUNG})
        if not inputs.get("that"):
            entry["status"] = "pending_review"
            return ToolResult(success=True, data={"publish_log": publish_log(entry), "chay_thu": True})
        token = os.environ.get(inputs["token_env"], "").strip()
        if not token:
            entry.update(status="failed", error=f"chưa đặt biến môi trường {inputs['token_env']}")
            return ToolResult(success=False, error=entry["error"], data={"publish_log": publish_log(entry), "loai_loi": QUYEN})

        h = self._h()
        page = inputs["page_id"]
        video_id = None
        try:
            r = self._goi(h.post, f"{GRAPH}/{PHIEN_BAN}/{page}/video_reels", "khởi tạo",
                          data={"upload_phase": "start", "access_token": token})
            video_id = r.get("video_id")
            if not video_id:
                raise LoiDang(NOI_DUNG, f"khởi tạo: không nhận được video_id ({r})")
            du_lieu = video.read_bytes()
            r = self._goi(h.post, f"{RUPLOAD}/{PHIEN_BAN}/{video_id}", "tải file",
                          headers={"Authorization": f"OAuth {token}", "offset": "0",
                                   "file_size": str(len(du_lieu)), "Content-Type": "application/octet-stream"},
                          data=du_lieu)
            if not r.get("success"):
                raise LoiDang(MANG, f"tải file: phản hồi không thành công ({r})")
            # Bước cuối: lỗi mạng/5xx ở đây thì bài CÓ THỂ đã đăng -> khong_ro, không thử lại.
            tham_so = {"access_token": token, "video_id": video_id, "upload_phase": "finish",
                       "video_state": "PUBLISHED", "description": mo_ta}
            if inputs.get("title"):
                tham_so["title"] = inputs["title"]
            if "is_ai_generated" in inputs and inputs["is_ai_generated"] is not None:
                tham_so["is_ai_generated"] = "true" if inputs["is_ai_generated"] else "false"
            r = self._goi(h.post, f"{GRAPH}/{PHIEN_BAN}/{page}/video_reels", "đăng", loai_khi_mang=KHONG_RO, data=tham_so)
            if not r.get("success"):
                raise LoiDang(KHONG_RO, f"đăng: phản hồi không rõ ({r})")
        except LoiDang as e:
            entry.update(status="failed", error=str(e))
            if video_id:
                entry["video_id"] = str(video_id)
            return ToolResult(success=False, error=str(e), data={"publish_log": publish_log(entry), "loai_loi": e.loai})

        url = ""
        trang_thai = {}
        try:  # đọc lại trạng thái và link; lỗi ở đây không làm hỏng việc đăng
            r = self._goi(h.get, f"{GRAPH}/{PHIEN_BAN}/{video_id}", "đọc trạng thái",
                          params={"fields": "status,permalink_url", "access_token": token})
            trang_thai = r.get("status") or {}
            url = r.get("permalink_url") or ""
            if url.startswith("/"):
                url = "https://www.facebook.com" + url
        except LoiDang:
            pass
        entry.update(status="published", video_id=str(video_id), visibility="public")
        if url:
            entry["url"] = url
        return ToolResult(success=True, data={"publish_log": publish_log(entry), "trang_thai_fb": trang_thai})

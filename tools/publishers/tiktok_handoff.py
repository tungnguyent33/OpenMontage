"""Bàn giao video cho người đăng tay lên TikTok (chưa dùng TikTok API).

Chép video và caption.txt vào Google Drive: "Chờ đăng TikTok/<ma_video>/".
Điều kiện để chuyển sang API: docs/may-reels/API-DANG-BAI.md mục 3.
Mặc định CHẠY THỬ: phải truyền `that: true`.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile, ToolResult, ToolRuntime, ToolStability, ToolTier,
)
from tools.publishers._dang_chung import MANG, NOI_DUNG, QUYEN, bay_gio_utc, loai_theo_http, publish_log


class TiktokHandoff(BaseTool):
    name = "tiktok_handoff"
    version = "0.1.0"
    tier = ToolTier.PUBLISH
    capability = "publish"
    provider = "tiktok_handoff"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = ["python:googleapiclient", "python:google_auth_oauthlib"]
    install_instructions = "pip install -r may_reels/requirements.txt; đăng nhập Drive: docs/may-reels/CAI-DAT-DANG-BAI.md"
    agent_skills = []
    capabilities = ["handoff_manual_post"]
    supports = {"uploads": False, "dry_run_default": True}
    best_for = ["chuẩn bị video và caption để người đăng tay lên TikTok"]
    not_good_for = ["đăng tự động lên TikTok (chưa có app TikTok được kiểm định)"]

    input_schema = {
        "type": "object",
        "required": ["video_path", "ma_video", "caption"],
        "properties": {
            "video_path": {"type": "string"},
            "ma_video": {"type": "string"},
            "caption": {"type": "string", "description": "caption kèm hashtag, ghi vào caption.txt"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "that": {"type": "boolean", "default": False},
        },
    }
    output_schema = {"type": "object", "properties": {"publish_log": {"type": "object"}, "link_thu_muc": {"type": "string"}}}
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=0, network_required=True)
    side_effects = ["tạo thư mục và tải file lên Google Drive của người dùng (khi that=true)"]
    user_visible_verification = ["Mở link thư mục trên Sheet, tải video về điện thoại và đăng tay"]

    def __init__(self, drive=None) -> None:
        self._drive = drive

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        from may_reels.drive import THU_MUC_TIKTOK
        video = Path(inputs["video_path"])
        entry: dict[str, Any] = {
            "platform": "tiktok", "timestamp": bay_gio_utc(),
            "metadata_used": {"description": inputs["caption"], "hashtags": list(inputs.get("hashtags") or [])},
        }
        if not video.is_file():
            entry.update(status="failed", error=f"không thấy file {video.name}")
            return ToolResult(success=False, error=entry["error"], data={"publish_log": publish_log(entry), "loai_loi": NOI_DUNG})
        if not inputs.get("that"):
            entry["status"] = "pending_review"
            return ToolResult(success=True, data={"publish_log": publish_log(entry), "chay_thu": True})
        try:
            if self._drive is None:
                from may_reels.drive import DriveGoogle
                self._drive = DriveGoogle.mo()
        except Exception as e:
            entry.update(status="failed", error=f"không mở được Drive: {e}")
            return ToolResult(success=False, error=entry["error"], data={"publish_log": publish_log(entry), "loai_loi": QUYEN})
        try:
            goc = self._drive.thu_muc(THU_MUC_TIKTOK)
            tm = self._drive.thu_muc(inputs["ma_video"], cha=goc["id"])
            self._drive.tai_len(video, f"{inputs['ma_video']}{video.suffix or '.mp4'}", tm["id"], "video/mp4")
            with tempfile.TemporaryDirectory() as d:
                cap = Path(d) / "caption.txt"
                cap.write_text(inputs["caption"].rstrip() + "\n", encoding="utf-8")
                self._drive.tai_len(cap, "caption.txt", tm["id"], "text/plain")
        except Exception as e:
            ma = getattr(getattr(e, "resp", None), "status", None)
            loai = loai_theo_http(int(ma)) if ma else MANG
            entry.update(status="failed", error=f"Drive: {e}")
            return ToolResult(success=False, error=entry["error"], data={"publish_log": publish_log(entry), "loai_loi": loai})
        link = tm.get("webViewLink") or f"https://drive.google.com/drive/folders/{tm['id']}"
        entry.update(status="exported", export_path=link)
        return ToolResult(success=True, data={"publish_log": publish_log(entry), "link_thu_muc": link, "thu_muc_id": tm["id"]})

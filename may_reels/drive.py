"""Google Drive qua OAuth của người dùng (service account không có dung lượng Drive).

Scope drive.file: máy chỉ thấy file và thư mục do chính Máy Reels tạo.
"""
from __future__ import annotations

from pathlib import Path

from may_reels.google_oauth import BIEN_DRIVE_TOKEN, PHAM_VI_DRIVE, duong_dan_tu_bien, nap_creds

MIME_THU_MUC = "application/vnd.google-apps.folder"
THU_MUC_XEM_THU = "Máy Reels - Xem thử"
THU_MUC_TIKTOK = "Chờ đăng TikTok"
TOKEN_MAC_DINH = "secrets/google-drive-token.json"


def _thoat(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


class DriveGoogle:
    def __init__(self, dich_vu) -> None:
        self._s = dich_vu

    @classmethod
    def mo(cls) -> "DriveGoogle":
        from googleapiclient.discovery import build
        creds = nap_creds(duong_dan_tu_bien(BIEN_DRIVE_TOKEN, TOKEN_MAC_DINH), PHAM_VI_DRIVE)
        return cls(build("drive", "v3", credentials=creds, cache_discovery=False))

    def thu_muc(self, ten: str, cha: str | None = None) -> dict:
        """Tìm thư mục theo tên (trong `cha` nếu có), không có thì tạo. Trả về {id, webViewLink}."""
        q = f"name = '{_thoat(ten)}' and mimeType = '{MIME_THU_MUC}' and trashed = false"
        if cha:
            q += f" and '{cha}' in parents"
        kq = self._s.files().list(q=q, fields="files(id, webViewLink)", pageSize=10).execute()
        if kq.get("files"):
            return kq["files"][0]
        body = {"name": ten, "mimeType": MIME_THU_MUC}
        if cha:
            body["parents"] = [cha]
        return self._s.files().create(body=body, fields="id, webViewLink").execute()

    def tai_len(self, duong_dan: Path, ten: str, thu_muc_id: str, mime: str) -> dict:
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(str(duong_dan), mimetype=mime, resumable=True)
        return self._s.files().create(body={"name": ten, "parents": [thu_muc_id]}, media_body=media,
                                      fields="id, webViewLink").execute()

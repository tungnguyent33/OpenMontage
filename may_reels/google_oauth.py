"""OAuth Google của NGƯỜI DÙNG (không phải service account) cho YouTube và Drive.

- Đăng nhập một lần bằng trình duyệt: `python -m may_reels dang-nhap youtube --kenh <mã>`
  hoặc `python -m may_reels dang-nhap drive`. Token (có refresh token) lưu vào file trong secrets/.
- Các lần sau máy tự làm mới access token từ file đó.
Thư viện Google chỉ import trong hàm.
"""
from __future__ import annotations

import os
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
BIEN_CLIENT_SECRET = "MAY_REELS_GOOGLE_CLIENT_SECRET"
BIEN_DRIVE_TOKEN = "MAY_REELS_DRIVE_TOKEN"

PHAM_VI_YOUTUBE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  # đọc lại privacyStatus và kiểm tra đúng kênh
]
PHAM_VI_DRIVE = ["https://www.googleapis.com/auth/drive.file"]  # chỉ file/thư mục do Máy Reels tạo


class LoiOAuth(RuntimeError):
    pass


def duong_dan_tu_bien(ten_bien: str, mac_dinh: str | None = None) -> Path:
    v = os.environ.get(ten_bien, "").strip().strip('"').strip("'") or (mac_dinh or "")
    if not v:
        raise LoiOAuth(f"Chưa đặt biến môi trường {ten_bien}")
    p = Path(v)
    return p if p.is_absolute() else GOC / p


def dang_nhap(token_file: Path, pham_vi: list[str]) -> Path:
    """Mở trình duyệt để người dùng đồng ý, rồi lưu token. Chỉ người dùng tự chạy."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    client = duong_dan_tu_bien(BIEN_CLIENT_SECRET)
    if not client.is_file():
        raise LoiOAuth(f"Không thấy file OAuth client: {client} (xem CAI-DAT-DANG-BAI.md)")
    flow = InstalledAppFlow.from_client_secrets_file(str(client), pham_vi)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return token_file


def nap_creds(token_file: Path, pham_vi: list[str]):
    """Đọc token đã lưu, làm mới nếu hết hạn, ghi lại file. Không mở trình duyệt."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not token_file.is_file():
        raise LoiOAuth(f"Chưa đăng nhập: không thấy {token_file.name}. Chạy lệnh dang-nhap trước.")
    creds = Credentials.from_authorized_user_file(str(token_file), pham_vi)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise LoiOAuth(f"Token trong {token_file.name} không dùng được. Chạy lại lệnh dang-nhap.")
    return creds

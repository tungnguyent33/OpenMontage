"""Đưa một video có sẵn vào tab Hàng chờ: `python -m may_reels hang-cho them ...`.

- Kiểm tra video (9:16, thời lượng, fps theo từng nền tảng) và caption (cụm từ cấm của kênh).
- Tải bản xem thử lên Drive "Máy Reels - Xem thử" (OAuth của người dùng).
- Lưu bản ghi local projects/_may_reels/hang_cho/<ma_video>.json (đường dẫn file, sha1).
- Tạo mỗi nền tảng một dòng. Cột `duyet` để TRỐNG (= Chờ duyệt): máy không ghi cột của người.
- Không đổi nội dung của dòng đã được người xử lý (duyet khác trống/Chờ duyệt, hoặc đã có trạng thái đăng).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from may_reels.cau_hinh_dang import doc_cau_hinh_dang
from may_reels.chu_de import doc_brand
from may_reels.cot_sheet import HANG_CHO
from may_reels.kiem_tra_video import cum_tu_cam, do_thong_so, loi_thong_so, tim_cum_tu_cam
from may_reels.sheet import BangNguon, chuan, doc_dong, ghi_theo_khoa

GOC = Path(__file__).resolve().parent.parent
MA_VIDEO = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
KHOA_HASHTAG = {"fb_reels": "facebook", "yt_shorts": "youtube", "tiktok": "tiktok"}
CANH_BAO_CO_SAN = "Video có sẵn, chưa qua chấm điểm QA"
DUYET_CHO = {"", "Chờ duyệt"}


class LoiHangCho(ValueError):
    pass


def thu_muc_ban_ghi(goc: Path | None = None) -> Path:
    return (goc or GOC) / "projects" / "_may_reels" / "hang_cho"


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def tao_ma(ten: str) -> str:
    s = unicodedata.normalize("NFD", ten).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def hashtag_cua(brand: dict, nen_tang: str) -> list[str]:
    return [h for h in (brand.get("hashtags") or {}).get(KHOA_HASHTAG[nen_tang], []) if h]


def doc_ban_ghi(ma_video: str, goc: Path | None = None) -> dict | None:
    p = thu_muc_ban_ghi(goc) / f"{ma_video}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


@dataclass
class KetQuaThem:
    ma_video: str
    nen_tang: list[str]
    link_xem_thu: str = ""
    loi: list[str] = field(default_factory=list)
    them: int = 0
    cap_nhat: int = 0
    giu_nguyen: int = 0


def them_video(bang: BangNguon, *, video: Path, kenh: str, caption_file: Path, ma: str | None = None,
               nen_tang: list[str] | None = None, thu: bool = False, drive=None, goc: Path | None = None,
               do=do_thong_so) -> KetQuaThem:
    goc = goc or GOC
    video = Path(video).resolve()
    if not video.is_file():
        raise LoiHangCho(f"Không thấy video: {video}")
    if not Path(caption_file).is_file():
        raise LoiHangCho(f"Không thấy file caption: {caption_file}")
    brand = doc_brand(kenh, goc)
    ch = doc_cau_hinh_dang(kenh, goc)
    nt = list(nen_tang or ch.nen_tang)
    ma_video = ma or tao_ma(video.stem)
    if not MA_VIDEO.fullmatch(ma_video or ""):
        raise LoiHangCho(f"Mã video không hợp lệ: {ma_video!r} (dùng --ma)")
    caption = unicodedata.normalize("NFC", Path(caption_file).read_text(encoding="utf-8")).strip()
    if not caption:
        raise LoiHangCho("Caption trống")
    kq = KetQuaThem(ma_video, nt)

    # Kiểm tra trước, không ghi gì nếu có lỗi.
    ts = do(video)
    for x in nt:
        kq.loi += loi_thong_so(ts, x)
    cam = cum_tu_cam(brand)
    for x in nt:
        trung = tim_cum_tu_cam(caption + "\n" + " ".join(hashtag_cua(brand, x)), cam)
        if trung:
            kq.loi.append(f"{x}: caption/hashtag chứa cụm từ cấm {trung}")
    sha = sha1_file(video)
    cu = doc_ban_ghi(ma_video, goc)
    if cu and cu.get("sha1") != sha:
        kq.loi.append(f"Mã {ma_video} đã dùng cho một file khác (sha1 {cu.get('sha1')[:10]}). Dùng --ma khác.")
    da_xu_ly = []
    for d in doc_dong(bang, HANG_CHO):
        if d.get("ma_video") == ma_video and d.get("nen_tang") in nt:
            if chuan(d.get("duyet")) not in DUYET_CHO or chuan(d.get("trang_thai_dang")):
                da_xu_ly.append(d["nen_tang"])
    if da_xu_ly:
        kq.loi.append(f"Dòng {ma_video} trên {da_xu_ly} đã được duyệt hoặc đã xử lý: không đổi nội dung nữa")
    if kq.loi:
        return kq

    dong = []
    for x in nt:
        dong.append({"ma_video": ma_video, "kenh": kenh, "nen_tang": x, "caption": caption,
                     "hashtag": " ".join(hashtag_cua(brand, x)), "canh_bao": CANH_BAO_CO_SAN})
    if thu:
        kq.link_xem_thu = "(chạy thử: chưa tải lên Drive)"
        kgt = ghi_theo_khoa(bang, HANG_CHO, dong, thu=True)
        kq.them, kq.cap_nhat, kq.giu_nguyen = len(kgt.them), len(kgt.cap_nhat), len(kgt.giu_nguyen)
        return kq

    if cu and cu.get("drive_id") and cu.get("link_xem_thu"):
        kq.link_xem_thu = cu["link_xem_thu"]
    else:
        if drive is None:
            from may_reels.drive import DriveGoogle
            drive = DriveGoogle.mo()
        from may_reels.drive import THU_MUC_XEM_THU
        tm = drive.thu_muc(THU_MUC_XEM_THU)
        f = drive.tai_len(video, f"{ma_video}{video.suffix or '.mp4'}", tm["id"], "video/mp4")
        kq.link_xem_thu = f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view"
        cu = {"drive_id": f["id"]}
    ban_ghi = {"ma_video": ma_video, "kenh": kenh, "video": str(video), "sha1": sha,
               "caption_file": str(Path(caption_file).resolve()), "nen_tang": nt,
               "drive_id": cu.get("drive_id"), "link_xem_thu": kq.link_xem_thu,
               "thong_so": {"rong": ts.rong, "cao": ts.cao, "giay": ts.giay, "fps": ts.fps}}
    p = thu_muc_ban_ghi(goc) / f"{ma_video}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ban_ghi, ensure_ascii=False, indent=2), encoding="utf-8")
    for d in dong:
        d["link_xem_thu"] = kq.link_xem_thu
    kgt = ghi_theo_khoa(bang, HANG_CHO, dong)
    kq.them, kq.cap_nhat, kq.giu_nguyen = len(kgt.them), len(kgt.cap_nhat), len(kgt.giu_nguyen)
    return kq

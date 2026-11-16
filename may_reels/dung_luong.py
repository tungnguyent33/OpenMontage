"""Đo dung lượng media của Máy Reels trên máy và trong thư mục xem thử (Drive).

    python -m may_reels dung-luong [--cache]

- Theo dự án (projects/<mã>) và theo loại: renders, exports, hf/assets/video, assets/audio, review, phần còn lại.
- File hard link (exports/*/video trỏ tới renders/final.mp4) chỉ đếm MỘT lần, ở loại đứng trước trong LOAI.
- Thư mục xem thử: MAY_REELS_XEM_THU_DIR (thư mục đồng bộ Google Drive for desktop).
- --cache: thêm các cache dùng chung (model Hugging Face, torch, HyperFrames, npm/npx). Chỉ báo, không xóa.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
# Thứ tự = thứ tự ưu tiên khi một file có nhiều hard link (renders trước exports).
LOAI = ["renders", "exports", "hf/assets/video", "assets/audio", "review", "con_lai"]
NHAN_LOAI = {"renders": "renders", "exports": "exports", "hf/assets/video": "hf/vid", "assets/audio": "audio",
             "review": "review", "con_lai": "còn lại"}
MB = 1024 * 1024


def loai_cua(rel: str) -> str:
    """rel: đường dẫn posix tương đối so với thư mục dự án."""
    for k in LOAI[:-1]:
        if rel == k or rel.startswith(k + "/"):
            return k
    return "con_lai"


def _cac_file(thu_muc: Path):
    for goc, _dirs, files in os.walk(thu_muc):
        for f in files:
            p = Path(goc) / f
            try:
                st = p.stat(follow_symlinks=False)
            except OSError:
                continue
            yield p, st


class DemMotLan:
    """Đếm mỗi file thật (dev, inode) một lần. Hệ tệp không có inode (st_ino == 0) thì đếm mọi file."""

    def __init__(self) -> None:
        self.da_thay: set[tuple[int, int]] = set()

    def moi(self, st: os.stat_result) -> bool:
        if not st.st_ino:
            return True
        k = (st.st_dev, st.st_ino)
        if k in self.da_thay:
            return False
        self.da_thay.add(k)
        return True


@dataclass
class DoDuAn:
    ma: str
    theo_loai: dict[str, int] = field(default_factory=lambda: {k: 0 for k in LOAI})

    @property
    def tong(self) -> int:
        return sum(self.theo_loai.values())


def do_du_an(P: Path, dem: DemMotLan | None = None) -> DoDuAn:
    dem = dem or DemMotLan()
    kq = DoDuAn(P.name)
    ds = [(loai_cua(p.relative_to(P).as_posix()), p, st) for p, st in _cac_file(P)]
    ds.sort(key=lambda x: LOAI.index(x[0]))
    for loai, _p, st in ds:
        if dem.moi(st):
            kq.theo_loai[loai] += st.st_size
    return kq


def do_thu_muc(d: Path, dem: DemMotLan | None = None) -> tuple[int, int]:
    """(tổng byte, số file)."""
    dem = dem or DemMotLan()
    tong = so = 0
    for _p, st in _cac_file(d):
        if dem.moi(st):
            tong += st.st_size
            so += 1
    return tong, so


def thu_muc_xem_thu() -> Path | None:
    v = os.environ.get("MAY_REELS_XEM_THU_DIR", "").strip().strip('"').strip("'")
    return Path(v) if v else None


def _npm_cache() -> Path | None:
    try:
        r = subprocess.run(["npm", "config", "get", "cache"], capture_output=True, text=True, shell=os.name == "nt",
                           timeout=30)
        p = Path(r.stdout.strip())
        return p if r.returncode == 0 and p.is_dir() else None
    except (OSError, subprocess.SubprocessError):
        return None


def cache_dung_chung() -> list[tuple[str, Path, str]]:
    """(nhãn, đường dẫn, cách dọn an toàn). Chỉ để báo."""
    nha = Path.home()
    hf = Path(os.environ.get("HF_HOME") or nha / ".cache" / "huggingface") / "hub"
    ds = [
        ("PhoWhisper (nghe lại giọng)", hf / "models--kiendt--PhoWhisper-large-ct2",
         "ĐANG DÙNG (san-xuat.yaml giong.nghe_lai). Xóa thì lần sinh giọng sau tải lại ~3 GB."),
        ("VieNeu-TTS v3 Turbo (giọng)", hf / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo",
         "ĐANG DÙNG. Xóa thì lần sinh giọng sau tải lại."),
        ("MOSS Audio Tokenizer (VieNeu dùng kèm)", hf / "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX",
         "Có thể VieNeu cần: chưa xác minh, không xóa."),
        ("faster-whisper large-v3", hf / "models--Systran--faster-whisper-large-v3",
         "Máy Reels không dùng (dùng PhoWhisper). Xóa được nếu tool transcriber của OpenMontage không cần: "
         "`hf cache delete` hoặc xóa thư mục."),
        ("wav2vec2 tiếng Việt", hf / "models--nguyenvulebinh--wav2vec2-base-vietnamese-250h",
         "Máy Reels không dùng. Xóa được (thư mục riêng của model)."),
        ("whisper-tiny", hf / "models--openai--whisper-tiny", "Nhỏ, bỏ qua."),
        ("Hugging Face (toàn bộ hub)", hf, "Dọn từng model bằng `hf cache delete` (chọn model), không xóa cả hub."),
        ("torch hub", nha / ".cache" / "torch", "Máy Reels không gọi torch hub. Xóa được, tool khác cần sẽ tự tải lại."),
        ("HyperFrames (Chrome + font)", nha / ".cache" / "hyperframes",
         "ĐANG DÙNG để render. Xóa thì lần render sau tải lại Chrome (~270 MB). history/ xóa được."),
    ]
    npm = _npm_cache()
    if npm:
        ds.append(("npx (gói chạy tạm, có hyperframes)", npm / "_npx",
                   "Xóa được khi không có render nào đang chạy; lần sau npx tải lại đúng phiên bản."))
        ds.append(("npm cache (toàn bộ)", npm, "Dọn an toàn bằng `npm cache clean --force` (không đụng dự án)."))
    return ds


def bao_cao(goc: Path = GOC, cache: bool = False, in_ra=print) -> dict:
    proj = goc / "projects"
    dem = DemMotLan()
    du_an = [do_du_an(P, dem) for P in sorted(proj.iterdir()) if P.is_dir()] if proj.is_dir() else []
    cot = "".join(f"{NHAN_LOAI[k]:>9}" for k in LOAI)
    in_ra(f"{'Dự án':<36}{cot}{'TỔNG':>10}   (MB, hard link đếm 1 lần)")
    tong_loai = {k: 0 for k in LOAI}
    for d in du_an:
        in_ra(f"{d.ma[:35]:<36}" + "".join(f"{d.theo_loai[k] / MB:9.1f}" for k in LOAI) + f"{d.tong / MB:10.1f}")
        for k in LOAI:
            tong_loai[k] += d.theo_loai[k]
    tong = sum(tong_loai.values())
    in_ra(f"{'CỘNG':<36}" + "".join(f"{tong_loai[k] / MB:9.1f}" for k in LOAI) + f"{tong / MB:10.1f}")
    kq = {"du_an": {d.ma: d.theo_loai | {"tong": d.tong} for d in du_an}, "tong_may": tong, "theo_loai": tong_loai}
    xt = thu_muc_xem_thu()
    if xt and xt.is_dir():
        b, n = do_thu_muc(xt)
        in_ra(f"Thư mục xem thử ({xt}): {b / MB:.1f} MB, {n} file")
        kq["xem_thu"] = b
    else:
        in_ra("Thư mục xem thử: chưa đặt MAY_REELS_XEM_THU_DIR hoặc không tồn tại")
    if cache:
        in_ra("\nCache dùng chung (chỉ báo, không xóa):")
        kq["cache"] = {}
        for nhan, p, cach in cache_dung_chung():
            b = do_thu_muc(p)[0] if p.is_dir() else 0
            kq["cache"][nhan] = b
            in_ra(f"  {nhan:<40}{b / MB:10.1f} MB  {p}")
            in_ra(f"      {cach}")
    return kq

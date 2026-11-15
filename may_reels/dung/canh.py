"""Cảnh: tính đoạn cắt theo mốc giọng thật, rồi cắt từ kho kênh (chỉ ĐỌC) bằng FFmpeg.

- Cảnh sN bắt đầu khi giọng sN bắt đầu (+LEAD), kéo tới khi giọng đoạn sau bắt đầu.
- Điểm vào lấy từ kế hoạch; thiếu độ dài thì lùi điểm vào, nhưng KHÔNG ra ngoài doan_dung_duoc và không chạm
  khoảng cần tránh (san-xuat.yaml canh.tranh_them). Không vừa -> LoiThieuCanh (ghi tab Cần quay).
- File gốc: $KENH_GOC_DIR/<kênh>/<file_tuong_doi> (brand.json không có đường dẫn tuyệt đối).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

LEAD = 0.15
VF = ("scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},unsharp=5:5:0.6,"
      "fps={fps},format=yuv420p")


class LoiThieuCanh(RuntimeError):
    def __init__(self, doan: str, ma: str, ly_do: str) -> None:
        super().__init__(f"{doan}: {ma}: {ly_do}")
        self.doan, self.ma, self.ly_do = doan, ma, ly_do


def _gop(khoang: list) -> list[list[float]]:
    out: list[list[float]] = []
    for x, y in sorted(khoang):
        if out and x <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], y)
        else:
            out.append([x, y])
    return out


def tinh_cat(ke_hoach: dict, brand: dict, sx: dict, moc: dict) -> list[dict]:
    kho = {k["ma"]: k for k in brand.get("kho_canh") or []}
    tranh_them = (sx.get("canh") or {}).get("tranh_them") or {}
    ids = [d["id"] for d in ke_hoach["doan"]]
    ra = []
    for k_idx, d in enumerate(ke_hoach["doan"]):
        c = d["canh"]
        if c is None:
            continue
        a = 0.0 if k_idx == 0 else round(moc[d["id"]]["start"] + LEAD, 2)
        b = round(moc[ids[k_idx + 1]]["start"] + LEAD, 2)
        dai = round(b - a, 2)
        k = kho[c["ma"]]
        vao = None
        if k.get("loai_file") == "video":
            vao = float(c["vao"])
            tranh = tranh_them.get(c["ma"], [])
            chon = None
            khoang = k.get("doan_dung_duoc") or [[0.0, float(k.get("thoi_luong") or 0)]]
            for x, y in _gop(khoang):
                if not (x - 1e-6 <= vao <= y + 1e-6):
                    continue
                v = vao if vao + dai <= y + 1e-6 else round(y - dai, 2)
                if v >= x - 1e-6 and all(v + dai <= tx or v >= ty for tx, ty in tranh):
                    chon = v
                break
            if chon is None:
                raise LoiThieuCanh(d["id"], c["ma"], f"cần {dai}s quanh {vao}s trong {khoang} (tránh {tranh})")
            vao = chon
        ra.append({"id": "c" + d["id"][1:], "doan": d["id"], "ma": c["ma"], "start": a, "dai": dai, "in": vao,
                   "anh": k.get("loai_file") != "video"})
    return ra


def chuan_bi(cat: list[dict], brand: dict, sx: dict, du_an: Path, goc_kenh: Path) -> None:
    kh = sx.get("khung_hinh") or {}
    w, h, fps = int(kh.get("rong", 1080)), int(kh.get("cao", 1920)), int(kh.get("fps", 30))
    kho = {k["ma"]: k for k in brand.get("kho_canh") or []}
    vdir, idir = du_an / "hf" / "assets" / "video", du_an / "hf" / "assets" / "img"
    vdir.mkdir(parents=True, exist_ok=True)
    idir.mkdir(parents=True, exist_ok=True)
    for c in cat:
        src = goc_kenh / kho[c["ma"]]["file_tuong_doi"]
        if not src.is_file():
            raise LoiThieuCanh(c["doan"], c["ma"], f"không thấy file gốc {kho[c['ma']]['file_tuong_doi']}")
        if c["anh"]:
            shutil.copyfile(src, idir / f"{c['id']}{src.suffix.lower() or '.jpg'}")
            continue
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(c["in"]), "-i", str(src), "-t", str(c["dai"]), "-an",
                        "-vf", VF.format(w=w, h=h, fps=fps), "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                        str(vdir / f"{c['id']}.mp4")], check=True)

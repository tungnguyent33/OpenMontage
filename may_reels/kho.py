"""Kho cảnh của kênh: nạp cảnh mới quay, thống kê số lần dùng, đưa job chờ quay về hàng sản xuất.

    python -m may_reels kho nap --kenh <mã> [--thu]

Người quay thả file vào `<thư mục kênh gốc>/canh-quay/moi-quay/` (đổi bằng `thu_muc_moi_quay` trong
brand/<kênh>/cau-hinh.yaml). File nằm yên tại chỗ sau khi nạp. Với mỗi file chưa có trong `canh-quay/_kho/index.json`:
  1. Đo thông số và tách cảnh bằng tool có sẵn: audio_probe, scene_detect, frame_sampler (tools/analysis/).
     Không dùng nguyên hàm lib/source_media_review.review_source_media: hàm đó ghi khung hình vào ngay thư mục chứa
     file gốc (tức thư mục mới quay) và đọc khóa "text" mà transcriber không trả về.
  2. Có tiếng thì chép lời bằng tool transcriber (may_reels/kho_chep_loi.py, chạy bằng MAY_REELS_PY_GIONG).
  3. Agent (claude -p, skills/may-reels/gan-nhan-canh.md) xem lưới khung hình, ghi nhãn. Python kiểm nhãn rồi mới
     thêm vào nhan.json (không sửa nhãn đã có).
  4. Cảnh có mặt người: chưa dùng được cho tới khi người chọn "Đồng ý" ở tab Quyền hình. Lần `kho nap` sau chép
     xác nhận vào quyen_hinh.bo_sung của channel.yaml (sao lưu trước).
  5. Ghi số lần dùng và ngày dùng gần nhất của từng cảnh vào index.json, viết lại KHO.md (may_reels/kho_md.py),
     chạy tools_local/nap_kenh.py.
  6. Job đang cho_quay có đủ yêu cầu ở tab Cần quay là "Đã quay" và có file nạp sau yêu cầu: đánh dấu
     san_sang_san_xuat_lai, lệnh `san-xuat` lần sau tự lấy job đó.
Định dạng bản ghi index.json và nhan.json giữ đúng như scripts/nap_canh_quay.py và subagent phan-loai-canh của bộ
kit kênh; chỉ thêm khóa: ngay_nap, nap_luc, nap_boi (index.json), so_lan_dung, ngay_dung_gan_nhat (index.json).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import CAN_QUAY, NHAT_KY, QUYEN_HINH
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky

GOC = Path(__file__).resolve().parent.parent
TZ_VN = timezone(timedelta(hours=7))
VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".mts", ".3gp", ".webm"}
ANH = {".jpg", ".jpeg", ".png", ".webp"}
THU_MUC_MOI_MAC_DINH = "canh-quay/moi-quay"
KHO_REL = "canh-quay/_kho"
SKILL_NHAN = "skills/may-reels/gan-nhan-canh.md"
BIEN_PY = "MAY_REELS_PY_GIONG"
GIAY_CHEP_LOI = int(os.environ.get("MAY_REELS_GIAY_CHEP_LOI", "900"))
TRANG_THAI_CO_VIDEO = ("cho_duyet", "da_duyet", "da_dang")
TU_TOI_THIEU_CO_LOI = 4  # như nap_canh_quay.py: dưới 4 từ coi như Whisper nghe nhầm tiếng nền

# Giá trị hợp lệ của nhãn (subagent phan-loai-canh của bộ kit kênh)
LOAI = ("NOI", "BROLL", "THAO", "ANH")
DIA_DIEM = ("san-tap", "phong-hoc", "duong-thuc", "van-phong", "khac")
CO_CANH = ("rong", "trung", "trung-can", "can", "chi-tiet")
CHUYEN_DONG = ("dung-yen", "lia", "theo-sau", "tien-lai", "rung")
CHAT_LUONG = ("tot", "dung-duoc", "kem")
RUI_RO = ("mat-hoc-vien", "bien-so", "giay-to", "ten-nguoi", "nguoi-ngoai")
RUI_RO_MAT = ("mat-hoc-vien", "nguoi-ngoai")
TRUONG_AGENT = ("loai", "mo_ta", "dia_diem", "co_canh", "chuyen_dong", "the", "doan_dung_duoc", "chat_luong",
                "ghi_chu", "rui_ro", "duoc_dung", "can_xu_ly", "loi_noi", "mat_nguoi")
XAC_NHAN_DONG_Y, XAC_NHAN_KHONG = "Đồng ý", "Không"


def hom_nay() -> str:
    return datetime.now(TZ_VN).date().isoformat()


# ---------------------------------------------------------------- mã và dấu file (giống nap_canh_quay.py)
def ma_file(rel: str) -> str:
    khong_dau = unicodedata.normalize("NFD", Path(rel).stem.lower().replace("đ", "d"))
    khong_dau = "".join(c for c in khong_dau if unicodedata.category(c) != "Mn")
    stem = re.sub(r"[^a-z0-9]+", "-", khong_dau).strip("-")[:30] or "canh"
    return f"{stem}-{hashlib.md5(rel.encode('utf-8')).hexdigest()[:6]}"


def dau_file(p: Path) -> str:
    st = p.stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def huong(w: int | None, h: int | None) -> str:
    return "doc" if w and h and h > w else "ngang" if w and h and w > h else "vuong"


def dung_cho(w: int | None, h: int | None) -> str:
    """footage-policy mục 3: s = max(1080/rong, 1920/cao) ở zoom 1; rong_hieu_dung = 1080/s; >= 1080 thì toàn màn."""
    if not w or not h:
        return "chi-khung-anh"
    s = max(1080 / w, 1920 / h)
    return "toan-man" if 1080 / s >= 1080 - 1e-6 else "chi-khung-anh"


# ---------------------------------------------------------------- đọc/ghi file kho
def doc_json(p: Path, mac_dinh):
    if not p.is_file():
        return mac_dinh
    return json.loads(p.read_text(encoding="utf-8"))  # lỗi cú pháp thì ném ra: không ghi đè file của người


def ghi_json(p: Path, data) -> None:
    """Ghi file tạm rồi thay, để máy chết giữa chừng không để lại index.json cụt."""
    tam = p.with_name(p.name + ".dang-ghi")
    tam.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tam, p)


@dataclass
class ThuMuc:
    kenh: Path      # thư mục kênh gốc
    moi: Path       # thư mục mới quay
    kho: Path       # canh-quay/_kho
    tam: Path       # projects/_may_reels/kho/<kenh>/ (trong repo, agent đọc/ghi ở đây)


def thu_muc(kenh: str, goc: Path = GOC, thu_muc_kenh: Path | None = None) -> ThuMuc:
    if thu_muc_kenh is None:
        from tools_local.nap_kenh import nap_env, thu_muc_kenh as tmk
        nap_env()
        thu_muc_kenh = tmk(kenh)
    if not thu_muc_kenh or not thu_muc_kenh.is_dir():
        raise RuntimeError(f"Không thấy thư mục kênh gốc của {kenh} (KENH_GOC_DIR trong .env)")
    import yaml
    f = goc / "brand" / kenh / "cau-hinh.yaml"
    cfg = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.is_file() else {}
    moi = cfg.get("thu_muc_moi_quay") or THU_MUC_MOI_MAC_DINH
    return ThuMuc(thu_muc_kenh, thu_muc_kenh / moi, thu_muc_kenh / KHO_REL, goc / "projects" / "_may_reels" / "kho" / kenh)


# ---------------------------------------------------------------- phân tích kỹ thuật (tools/analysis)
def _ffprobe_hinh(p: Path) -> dict:
    """Kích thước hiển thị (tính cả cờ xoay của điện thoại) và fps. audio_probe không đo phần hình."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:stream_side_data=rotation:stream_tags=rotate",
                        "-of", "json", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    v = (json.loads(r.stdout or "{}").get("streams") or [{}])[0]
    w, h = v.get("width"), v.get("height")
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = rot or int((v.get("tags") or {}).get("rotate", 0) or 0)
    if w and h and abs(rot) % 180 == 90:
        w, h = h, w
    num, _, den = (v.get("r_frame_rate") or "0/1").partition("/")
    fps = round(float(num) / float(den or 1), 2) if float(den or 1) else None
    return {"rong": w, "cao": h, "fps": fps}


def _lufs(p: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(p), "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def luoi_khung(khung: list[tuple[Path, float]], ra: Path, cot: int = 6, rong_o: int = 270) -> None:
    """Ghép khung thành một lưới, in mốc giây ở góc mỗi ô (agent đọc mốc để ghi doan_dung_duoc)."""
    from PIL import Image, ImageDraw, ImageFont
    anh = [(Image.open(p).convert("RGB"), t) for p, t in khung]
    if not anh:
        raise RuntimeError("không trích được khung hình nào")
    cao_o = max(1, round(rong_o * anh[0][0].height / anh[0][0].width))
    hang = (len(anh) + cot - 1) // cot
    luoi = Image.new("RGB", (cot * rong_o, hang * cao_o), "black")
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (im, t) in enumerate(anh):
        o = im.resize((rong_o, cao_o))
        d = ImageDraw.Draw(o)
        nhan = f"{t:.1f}s"
        d.rectangle((0, 0, 12 + 13 * len(nhan), 30), fill="black")
        d.text((6, 3), nhan, fill="yellow", font=font)
        luoi.paste(o, ((i % cot) * rong_o, (i // cot) * cao_o))
    ra.parent.mkdir(parents=True, exist_ok=True)
    luoi.save(ra, quality=88)


def phan_tich_anh(p: Path, ra_khung: Path) -> dict:
    from PIL import Image, ImageOps
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        ra_khung.parent.mkdir(parents=True, exist_ok=True)
        im.resize((540, max(1, round(540 * h / w)))).save(ra_khung, quality=88)
    return {"loai_file": "anh", "rong": w, "cao": h, "huong": huong(w, h)}


def phan_tich_video(p: Path, ra_khung: Path, tam: Path) -> dict:
    from tools.analysis.audio_probe import AudioProbe
    from tools.analysis.frame_sampler import FrameSampler
    from tools.analysis.scene_detect import SceneDetect
    hinh = _ffprobe_hinh(p)
    am = AudioProbe().execute({"input_path": str(p)})
    if not am.success:
        raise RuntimeError(f"audio_probe: {am.error}")
    dur = float(am.data.get("duration_seconds") or 0) or 0.1
    muc = {"loai_file": "video", "rong": hinh["rong"], "cao": hinh["cao"], "huong": huong(hinh["rong"], hinh["cao"]),
           "fps": hinh["fps"], "thoi_luong": round(dur, 2), "co_am_thanh": bool(am.data.get("audio"))}
    cd = SceneDetect().execute({"input_path": str(p), "output_path": str(tam / "scenes.json")})
    if not cd.success:
        raise RuntimeError(f"scene_detect: {cd.error}")
    muc["chuyen_canh"] = [round(float(s["start_seconds"]), 2) for s in cd.data["scenes"][1:]]
    n = 6 if dur <= 20 else 12
    moc = [round(dur * (k + 0.5) / n, 2) for k in range(n)]
    fs = FrameSampler().execute({"input_path": str(p), "strategy": "timestamps", "timestamps": moc,
                                 "output_dir": str(tam / "khung_le"), "format": "jpg"})
    if not fs.success:
        raise RuntimeError(f"frame_sampler: {fs.error}")
    luoi_khung([(Path(f["path"]), float(f.get("timestamp_seconds", t)))
                for f, t in zip(fs.data["frames"], moc)], ra_khung)
    if muc["co_am_thanh"]:
        muc["lufs"] = _lufs(p)
    return muc


def _srt(doan: list[dict]) -> str:
    def t(x: float) -> str:
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i}\n{t(d['start'])} --> {t(d['end'])}\n{d['text']}\n" for i, d in enumerate(doan, 1))


def chep_loi_mac_dinh(p: Path, ra_json: Path, goc: Path = GOC) -> dict:
    py = os.environ.get(BIEN_PY, "python")
    r = subprocess.run([py, "-m", "may_reels.kho_chep_loi", str(p), str(ra_json)], cwd=goc, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=GIAY_CHEP_LOI,
                       env={**os.environ, "PYTHONUTF8": "1", "HF_HUB_OFFLINE": "1"})
    if r.returncode != 0 or not ra_json.is_file():
        raise RuntimeError(f"chép lời lỗi: {r.stderr.strip()[-400:]}")
    return json.loads(ra_json.read_text(encoding="utf-8"))


def loi_noi_tu_chep(kq: dict, thu_muc_canh: Path) -> dict:
    thu_muc_canh.mkdir(parents=True, exist_ok=True)
    (thu_muc_canh / "loi-thoai.txt").write_text(kq.get("van_ban") or "(không nhận ra lời nói)", encoding="utf-8")
    (thu_muc_canh / "loi-thoai.srt").write_text(_srt(kq.get("doan") or []), encoding="utf-8")
    so_tu = int(kq.get("so_tu") or 0)
    return {"so_tu": so_tu, "giay_co_loi": kq.get("giay_co_loi") or 0, "co_loi": so_tu >= TU_TOI_THIEU_CO_LOI,
            "trich": (kq.get("van_ban") or "(không nhận ra lời nói)")[:300], "model": kq.get("model")}


# ---------------------------------------------------------------- nhãn: agent đề xuất, Python kiểm
def kiem_nhan(raw: dict, muc: dict) -> tuple[dict, list[str]]:
    """Kiểm nhãn agent ghi. Trả về (nhãn đủ khóa như nhan.json, lỗi). Có lỗi thì không đưa vào nhan.json."""
    loi = []
    n = {k: raw.get(k) for k in TRUONG_AGENT}

    def chon(k, hop_le):
        if n[k] not in hop_le:
            loi.append(f"{k}={n[k]!r} không thuộc {list(hop_le)}")
    chon("loai", LOAI)
    chon("dia_diem", DIA_DIEM)
    chon("co_canh", CO_CANH)
    chon("chuyen_dong", CHUYEN_DONG)
    chon("chat_luong", CHAT_LUONG)
    if muc.get("loai_file") == "anh" and n["loai"] not in (None, "ANH"):
        loi.append("ảnh tĩnh phải có loai = ANH")
    if not str(n["mo_ta"] or "").strip():
        loi.append("thiếu mo_ta")
    the = n["the"] or []
    if not isinstance(the, list) or not the or any(not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(x)) for x in the):
        loi.append("the phải là danh sách từ khóa không dấu, nối bằng gạch ngang")
    rr = n["rui_ro"] or []
    if not isinstance(rr, list) or any(x not in RUI_RO for x in rr):
        loi.append(f"rui_ro chỉ gồm {list(RUI_RO)}")
        rr = [x for x in rr if x in RUI_RO] if isinstance(rr, list) else []
    n["rui_ro"] = rr
    for k in ("duoc_dung", "mat_nguoi"):
        if not isinstance(n[k], bool):
            loi.append(f"{k} phải là true/false")
    dd = n["doan_dung_duoc"] or []
    dur = float(muc.get("thoi_luong") or 0)
    if muc.get("loai_file") == "anh":
        dd = []
    elif not isinstance(dd, list) or any(not (isinstance(x, list) and len(x) == 2) for x in dd):
        loi.append("doan_dung_duoc phải là danh sách [giây vào, giây ra]")
        dd = []
    else:
        dd = [[round(float(a), 1), round(float(b), 1)] for a, b in dd]
        for a, b in dd:
            if not (0 <= a < b <= dur + 0.5):
                loi.append(f"doan_dung_duoc [{a}, {b}] ngoài 0-{dur}s")
        if dd != sorted(dd) or any(dd[i][1] > dd[i + 1][0] for i in range(len(dd) - 1)):
            loi.append("doan_dung_duoc phải tăng dần, không chồng nhau")
    n["doan_dung_duoc"] = dd
    if (rr or n["mat_nguoi"]) and not str(n["can_xu_ly"] or "").strip():
        loi.append("có rủi ro / mặt người thì phải ghi can_xu_ly")
    for k in ("ghi_chu", "can_xu_ly", "loi_noi"):
        n[k] = str(n[k] or "")
    # Python tự điền: không để agent đoán những thứ tính được.
    if any(x in rr for x in RUI_RO_MAT):
        n["mat_nguoi"] = True  # có rủi ro mặt người thì coi như có mặt người, kể cả khi agent ghi false
    n["nguon"] = "trung-tam"  # thư mục mới quay chỉ chứa cảnh trung tâm tự quay (stock để riêng ở canh-quay/stock/)
    n["rong_nguon"], n["cao_nguon"] = muc.get("rong"), muc.get("cao")
    n["dung_cho"] = dung_cho(muc.get("rong"), muc.get("cao"))
    return n, loi


def goi_agent_nhan(prompt: str, *, du_an: Path, goc: Path) -> dict:
    from may_reels.san_xuat import goi_agent
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=("nhan.json",), web=False, giay=600,
                     he_thong=("Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi. Chỉ làm theo "
                               f"{SKILL_NHAN}. Chỉ ghi đúng một file nhan.json trong thư mục được giao."))


def gan_nhan(ma: str, muc: dict, khung: Path, the_da_co: list[str], tm: ThuMuc, *, goc: Path,
             agent: Callable[..., dict]) -> tuple[dict | None, list[str], dict]:
    d = tm.tam / ma
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(khung, d / "khung.jpg")
    srt = tm.kho / ma / "loi-thoai.srt"
    yc = {"ma": ma, **{k: muc.get(k) for k in ("file", "loai_file", "rong", "cao", "huong", "fps", "thoi_luong",
                                                 "chuyen_canh", "co_am_thanh", "lufs", "loi_noi")},
          "loi_thoai_srt": srt.read_text(encoding="utf-8") if srt.is_file() else "",
          "the_da_co": the_da_co}
    (d / "yeu_cau.json").write_text(json.dumps(yc, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "nhan.json").unlink(missing_ok=True)
    rel = d.relative_to(goc).as_posix()
    r = agent(f"Đọc và làm đúng theo {SKILL_NHAN}. Đọc {rel}/yeu_cau.json và xem {rel}/khung.jpg, rồi ghi {rel}/nhan.json.",
              du_an=d, goc=goc)
    if r.get("is_error") or not (d / "nhan.json").is_file():
        return None, [f"agent lỗi: {str(r.get('result'))[:200]}"], r
    try:
        raw = json.loads((d / "nhan.json").read_text(encoding="utf-8"))
    except ValueError as e:
        return None, [f"nhan.json của agent sai cú pháp: {e}"], r
    n, loi = kiem_nhan(raw, muc)
    return (None if loi else n), loi, r


# ---------------------------------------------------------------- số lần dùng cảnh (cho agent sản xuất tránh lặp)
def thong_ke_dung_canh(goc: Path, kenh: str, tru: str | None = None) -> dict[str, dict]:
    """Mỗi cảnh: số video đã dùng và ngày gần nhất. Chỉ tính video đã dựng xong (job ở cho_duyet trở đi, hoặc dự án
    không có job nhưng có renders/final.mp4). Đọc lại từ projects/*/ke_hoach.json mỗi lần, nên dựng lại hay sửa
    video không làm đếm trùng."""
    tk: dict[str, dict] = {}
    for f in sorted((goc / "projects").glob("*/ke_hoach.json")):
        P = f.parent
        if tru and P.name == tru:
            continue
        try:
            kh = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if kh.get("kenh") != kenh:
            continue
        ngay = None
        jf = P / "reel_job.json"
        if jf.is_file():
            try:
                job = json.loads(jf.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if job.get("trang_thai") not in TRANG_THAI_CO_VIDEO:
                continue
            # Lần gần nhất video ở trạng thái có video (vào Hàng chờ, được duyệt, được đăng): đăng là lúc người xem thấy.
            luc = [b["luc"] for b in job.get("lich_su") or [] if b.get("den") in TRANG_THAI_CO_VIDEO]
            ngay = (luc[-1] if luc else job.get("cap_nhat_luc") or "")[:10] or None
        elif (P / "renders" / "final.mp4").is_file():
            ngay = datetime.fromtimestamp((P / "renders" / "final.mp4").stat().st_mtime, TZ_VN).date().isoformat()
        else:
            continue
        for m in {d["canh"].get("ma") for d in kh.get("doan", []) if d.get("canh") and d["canh"].get("ma")}:
            t = tk.setdefault(m, {"so_lan": 0, "ngay_gan_nhat": None, "video": []})
            t["so_lan"] += 1
            t["video"].append(P.name)
            if ngay and (t["ngay_gan_nhat"] is None or ngay > t["ngay_gan_nhat"]):
                t["ngay_gan_nhat"] = ngay
    return tk


def ap_thong_ke_vao_index(index: dict, tk: dict[str, dict]) -> int:
    """Ghi so_lan_dung, ngay_dung_gan_nhat vào bản ghi index.json. Trả về số bản ghi đổi."""
    doi = 0
    for muc in index.values():
        t = tk.get(muc.get("ma"), {})
        moi = (t.get("so_lan", 0), t.get("ngay_gan_nhat"))
        if "so_lan_dung" not in muc or (muc.get("so_lan_dung"), muc.get("ngay_dung_gan_nhat")) != moi:
            muc["so_lan_dung"], muc["ngay_dung_gan_nhat"] = moi
            doi += 1
    return doi


def cap_nhat_su_dung(kenh: str, goc: Path = GOC, thu_muc_kenh: Path | None = None) -> int:
    """Gọi sau mỗi video vào Hàng chờ. Chưa đặt KENH_GOC_DIR hoặc chưa có index.json thì bỏ qua (trả về 0)."""
    try:
        tm = thu_muc(kenh, goc, thu_muc_kenh)
    except RuntimeError:
        return 0
    f = tm.kho / "index.json"
    if not f.is_file():
        return 0
    index = doc_json(f, {})
    doi = ap_thong_ke_vao_index(index, thong_ke_dung_canh(goc, kenh))
    if doi:
        ghi_json(f, index)
    return doi


# ---------------------------------------------------------------- quyền hình: Sheet -> channel.yaml
def them_bo_sung_yaml(text: str, muc: list[dict]) -> str:
    """Thêm mục vào quyen_hinh.bo_sung của channel.yaml, giữ nguyên chú thích và phần còn lại của file.
    Kiểm bằng yaml.safe_load: kết quả phải bằng bản cũ cộng đúng các mục mới, không thì ném lỗi."""
    import yaml
    cu = yaml.safe_load(text) or {}
    qh = cu.get("quyen_hinh")
    if not isinstance(qh, dict):
        raise ValueError("channel.yaml chưa có khối quyen_hinh: thêm tay trước (máy không tự tạo quyền hình)")
    da_co = {b.get("ma") for b in qh.get("bo_sung") or []}
    muc = [m for m in muc if m["ma"] not in da_co]
    if not muc:
        return text
    dong = text.split("\n")
    i_qh = next(i for i, d in enumerate(dong) if re.match(r"^quyen_hinh:\s*(#.*)?$", d))
    ket_thuc = next((i for i in range(i_qh + 1, len(dong)) if dong[i].strip() and not dong[i].startswith((" ", "\t"))
                     and not dong[i].lstrip().startswith("#")), len(dong))
    i_bs = next((i for i in range(i_qh + 1, ket_thuc) if re.match(r"^\s+bo_sung:", dong[i])), None)

    def khoi(thut: str) -> list[str]:
        out = []
        for m in muc:
            out.append(f"{thut}- ma: {json.dumps(m['ma'], ensure_ascii=False)}")
            for k in ("ngay", "ghi_chu"):
                out.append(f"{thut}  {k}: {json.dumps(m[k], ensure_ascii=False)}")
        return out
    if i_bs is None:
        thut_qh = re.match(r"^(\s+)", next(d for d in dong[i_qh + 1:ket_thuc] if d.strip())).group(1)
        chen = ket_thuc
        while chen > i_qh + 1 and not dong[chen - 1].strip():
            chen -= 1
        dong[chen:chen] = [f"{thut_qh}bo_sung:"] + khoi(thut_qh + "  ")
    else:
        thut_bs = re.match(r"^(\s+)", dong[i_bs]).group(1)
        if re.match(r"^\s+bo_sung:\s*\[\s*\]\s*(#.*)?$", dong[i_bs]):
            dong[i_bs] = f"{thut_bs}bo_sung:"
        cuoi = i_bs
        thut_muc = thut_bs + "  "
        for i in range(i_bs + 1, ket_thuc):
            d = dong[i]
            if not d.strip():
                continue
            t = len(d) - len(d.lstrip())
            if t <= len(thut_bs):
                break
            if d.lstrip().startswith("- "):
                thut_muc = d[:t]
            cuoi = i
        dong[cuoi + 1:cuoi + 1] = khoi(thut_muc)
    moi_text = "\n".join(dong)
    moi = yaml.safe_load(moi_text)
    mong = json.loads(json.dumps(cu, default=str))
    mong["quyen_hinh"]["bo_sung"] = list(qh.get("bo_sung") or []) + muc
    if json.loads(json.dumps(moi, default=str)) != json.loads(json.dumps(mong, default=str)):
        raise ValueError("chèn quyen_hinh.bo_sung làm đổi phần khác của channel.yaml: dừng, không ghi")
    return moi_text


def ap_dung_quyen_hinh(bang: BangNguon, kenh: str, tm: ThuMuc, *, thu: bool = False,
                       log: Callable[[str], None] = print) -> list[str]:
    """Dòng Quyền hình có xác nhận mà chưa áp dụng: Đồng ý -> quyen_hinh.bo_sung; Không -> chỉ ghi lại.
    Trả về mã cảnh vừa được đồng ý."""
    dong = [d for d in doc_dong(bang, QUYEN_HINH)
            if d.get("kenh") == kenh and not chuan(d.get("trang_thai_ap_dung"))
            and chuan(d.get("xac_nhan_quyen")) in (XAC_NHAN_DONG_Y, XAC_NHAN_KHONG)]
    if not dong:
        return []
    dong_y = [d for d in dong if chuan(d.get("xac_nhan_quyen")) == XAC_NHAN_DONG_Y]
    luc = bay_gio_vn()
    if dong_y:
        f = tm.kenh / "channel.yaml"
        text = f.read_bytes().decode("utf-8")
        moi = them_bo_sung_yaml(text, [{"ma": d["ma_canh"], "ngay": hom_nay(),
                                        "ghi_chu": ("Người dùng chọn Đồng ý ở tab Quyền hình (" + luc + ")"
                                                    + (f": {d['ghi_chu_nguoi']}" if d.get("ghi_chu_nguoi") else ""))}
                                       for d in dong_y])
        for d in dong_y:
            log(f"{'[thử] ' if thu else ''}Quyền hình: {d['ma_canh']} Đồng ý -> quyen_hinh.bo_sung")
        if not thu and moi != text:
            shutil.copy2(f, f.with_name(f"channel.yaml.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"))
            f.write_bytes(moi.encode("utf-8"))
    for d in dong:
        if chuan(d.get("xac_nhan_quyen")) == XAC_NHAN_KHONG:
            log(f"Quyền hình: {d['ma_canh']} Không -> giữ ngoài kho dùng được")
    if not thu:
        ghi_theo_khoa(bang, QUYEN_HINH, [{
            "kenh": kenh, "ma_canh": d["ma_canh"],
            "trang_thai_ap_dung": (f"đã chép vào quyen_hinh.bo_sung ({luc})" if d in dong_y
                                   else f"không dùng: người chọn Không ({luc})")} for d in dong])
    return [d["ma_canh"] for d in dong_y]


def ghi_quyen_hinh(bang: BangNguon, kenh: str, ds: list[tuple[str, dict, dict]]) -> None:
    """ds: [(ma, muc index, nhãn)] của cảnh có mặt người. Không đè dòng đã có (giữ tao_luc)."""
    if not ds:
        return
    luc = bay_gio_vn()
    ghi_theo_khoa(bang, QUYEN_HINH, [{
        "kenh": kenh, "ma_canh": ma, "file": muc.get("file"), "khung_hinh": f"{KHO_REL}/{ma}/khung.jpg",
        "mo_ta": n.get("mo_ta"), "rui_ro": ", ".join(n.get("rui_ro") or []) or "mat-nguoi",
        "can_xu_ly": n.get("can_xu_ly"), "tao_luc": luc} for ma, muc, n in ds], chi_khi_trong={"tao_luc"})


# ---------------------------------------------------------------- job chờ quay -> hàng sản xuất
def _thoi_diem(s: str | None) -> datetime | None:
    """Đọc cả "2026-11-17 16:43:00" (Sheet) lẫn ISO có múi giờ (job). Không có múi giờ thì hiểu là giờ Việt Nam."""
    try:
        t = datetime.fromisoformat(str(s).strip())
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=TZ_VN)


def _nap_sau(index: dict, moc: str) -> list[str]:
    """Mã cảnh nạp bằng `kho nap` sau thời điểm moc. Cảnh nạp theo cách cũ không có nap_luc: không tính.
    moc không đọc được (ô trống) thì mọi cảnh có nap_luc đều tính."""
    m0 = _thoi_diem(moc)
    out = []
    for m in index.values():
        t = _thoi_diem(m.get("nap_luc"))
        if t and (m0 is None or t > m0):
            out.append(m["ma"])
    return out


def da_quay(dong: dict, goi_y: list[dict]) -> bool:
    """Yêu cầu đã quay: chính dòng đó "Đã quay", hoặc một dòng gợi ý quay gộp nó (gop_yeu_cau) đã "Đã quay"."""
    if chuan(dong.get("trang_thai_quay")) == "Đã quay":
        return True
    return any(chuan(g.get("trang_thai_quay")) == "Đã quay"
               and dong["ma_yeu_cau"] in [x.strip() for x in (g.get("gop_yeu_cau") or "").split(",")] for g in goi_y)


def tra_ve_san_xuat(bang: BangNguon, kenh: str, index: dict, *, goc: Path = GOC, thu: bool = False,
                    log: Callable[[str], None] = print) -> list[str]:
    """Job cho_quay đủ cảnh (mọi yêu cầu Đã quay, có file nạp sau yêu cầu): metadata.san_sang_san_xuat_lai,
    ghi trang_thai_nap. Dòng gợi ý quay đã quay và có file mới: ghi trang_thai_nap. Trả về mã video được trả về."""
    from may_reels.job import kiem_tra as kiem_job
    rows = [d for d in doc_dong(bang, CAN_QUAY) if d.get("kenh") == kenh]
    goi_y = [d for d in rows if ":goi-y:" in d.get("ma_yeu_cau", "")]
    theo_video: dict[str, list[dict]] = {}
    for d in rows:
        if d.get("ma_video"):
            theo_video.setdefault(d["ma_video"], []).append(d)
    luc = bay_gio_vn()
    ghi, tra = [], []
    for ma_video, ds in theo_video.items():
        jf = goc / "projects" / ma_video / "reel_job.json"
        if not jf.is_file():
            continue
        job = json.loads(jf.read_text(encoding="utf-8"))
        if job.get("trang_thai") != "cho_quay" or (job.get("metadata") or {}).get("san_sang_san_xuat_lai"):
            continue
        if not all(da_quay(d, goi_y) for d in ds):
            continue
        moc = [t for t in (_thoi_diem(d.get("tao_luc")) for d in ds) if t]
        moi = _nap_sau(index, max(moc).isoformat() if moc else "")
        if not moi:
            log(f"{ma_video}: mọi yêu cầu đã quay nhưng chưa có file nào nạp sau yêu cầu, chưa trả về sản xuất")
            continue
        tra.append(ma_video)
        log(f"{'[thử] ' if thu else ''}{ma_video}: đủ cảnh đã quay ({len(moi)} cảnh mới) -> hàng sản xuất")
        if thu:
            continue
        job.setdefault("metadata", {})["san_sang_san_xuat_lai"] = {"luc": luc, "canh_moi": moi}
        kiem_job(job)
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        ghi += [{"ma_yeu_cau": d["ma_yeu_cau"],
                 "trang_thai_nap": f"đã nạp; {ma_video} quay về hàng sản xuất, chạy san-xuat ({luc})"} for d in ds]
    for g in goi_y:
        if chuan(g.get("trang_thai_quay")) == "Đã quay" and not chuan(g.get("trang_thai_nap")):
            moi = _nap_sau(index, g.get("tao_luc") or "")
            if moi:
                ghi.append({"ma_yeu_cau": g["ma_yeu_cau"], "trang_thai_nap": f"đã nạp {len(moi)} cảnh mới ({luc})"})
    if ghi and not thu:
        ghi_theo_khoa(bang, CAN_QUAY, ghi)
    return tra


# ---------------------------------------------------------------- lệnh kho nap
@dataclass
class KetQuaNap:
    moi: list[str] = field(default_factory=list)            # mã cảnh đã phân tích
    nhan: list[str] = field(default_factory=list)           # mã cảnh đã gắn nhãn
    cho_quyen: list[str] = field(default_factory=list)      # mã cảnh có mặt người, chờ xác nhận
    dong_y: list[str] = field(default_factory=list)         # mã cảnh vừa được đồng ý trên Sheet
    tra_ve: list[str] = field(default_factory=list)         # mã video trả về hàng sản xuất
    loi: list[str] = field(default_factory=list)
    giay_agent: float = 0.0
    so_luot_agent: int = 0


def nap(bang: BangNguon, kenh: str, *, goc: Path = GOC, thu_muc_kenh: Path | None = None, thu: bool = False,
        agent: Callable[..., dict] = goi_agent_nhan, chep: Callable[[Path, Path], dict] | None = None,
        nap_kenh: Callable[[str, Path], None] | None = None, log: Callable[[str], None] = print) -> KetQuaNap:
    from may_reels.khoa_tien_trinh import khoa
    t0 = time.monotonic()
    kq = KetQuaNap()
    tm = thu_muc(kenh, goc, thu_muc_kenh)
    if nap_kenh is None:
        from may_reels.nguon_luat import chay_nap_kenh as nap_kenh
    chep = chep or (lambda p, ra: chep_loi_mac_dinh(p, ra, goc))
    with khoa(goc / "projects" / "_may_reels" / f"kho-{kenh}.lock"):
        if not thu:
            tm.moi.mkdir(parents=True, exist_ok=True)
            tm.kho.mkdir(parents=True, exist_ok=True)
        f_index, f_nhan = tm.kho / "index.json", tm.kho / "nhan.json"
        index, nhan = doc_json(f_index, {}), doc_json(f_nhan, {})

        # 1. Xác nhận quyền hình trên Sheet (để lần nap_kenh cuối lượt đã tính).
        kq.dong_y = ap_dung_quyen_hinh(bang, kenh, tm, thu=thu, log=log)

        # 2. File mới trong thư mục mới quay; file đã có trong index (do lượt trước nạp) mà chưa có nhãn thì gắn lại.
        tep = sorted(p for p in (tm.moi.rglob("*") if tm.moi.is_dir() else [])
                     if p.is_file() and p.suffix.lower() in VIDEO | ANH)
        moi = [p for p in tep if p.relative_to(tm.kenh).as_posix() not in index]
        # File trong thư mục mới quay đã được script cũ của bộ kit (nap_canh_quay.py) lập index: nhận về, ghi ngày nạp
        # thật (không thì nap_kenh.py suy ngày từ mtime, cảnh có mặt người có thể lọt phạm vi quyen_hinh cũ).
        rel_moi = tm.moi.relative_to(tm.kenh).as_posix().rstrip("/") + "/"
        for rel, m in index.items():
            if rel.startswith(rel_moi) and not m.get("nap_boi") and not thu:
                m.update(ngay_nap=hom_nay(), nap_luc=bay_gio_vn(), nap_boi="kho-nap")
                ghi_json(f_index, index)
        chua_nhan = [rel for rel, m in index.items()
                     if m.get("nap_boi") == "kho-nap" and m["ma"] not in nhan and (tm.kenh / rel).is_file()]
        log(f"Thư mục mới quay: {tm.moi} | {len(tep)} file, {len(moi)} file mới, {len(chua_nhan)} file chờ gắn lại nhãn")
        if thu:
            for p in moi:
                log(f"  [thử] sẽ nạp {p.relative_to(tm.kenh).as_posix()}")
        for p in ([] if thu else moi):
            rel = p.relative_to(tm.kenh).as_posix()
            ma = ma_file(rel)
            if any(m.get("ma") == ma for m in index.values()):
                kq.loi.append(f"{rel}: mã {ma} đã có trong index với file khác, bỏ qua")
                continue
            log(f"  phân tích {rel}")
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    muc = {"ma": ma, "file": rel, "dau": dau_file(p)}
                    if p.suffix.lower() in ANH:
                        muc.update(phan_tich_anh(p, tm.kho / ma / "khung.jpg"))
                    else:
                        muc.update(phan_tich_video(p, tm.kho / ma / "khung.jpg", Path(tmp)))
                        if muc["co_am_thanh"]:
                            muc["loi_noi"] = loi_noi_tu_chep(chep(p, Path(tmp) / "chep.json"), tm.kho / ma)
                muc.update(ngay_nap=hom_nay(), nap_luc=bay_gio_vn(), nap_boi="kho-nap")
            except Exception as e:  # file hỏng không làm dừng file khác
                kq.loi.append(f"{rel}: {type(e).__name__}: {e}"[:300])
                continue
            index[rel] = muc
            ghi_json(f_index, index)
            kq.moi.append(ma)
            chua_nhan.append(rel)

        # 3. Gắn nhãn (agent) và kiểm (Python).
        the_da_co = sorted({t for v in nhan.values() for t in v.get("the") or []})
        cho_quyen = []
        for rel in ([] if thu else chua_nhan):
            muc = index[rel]
            ma = muc["ma"]
            log(f"  gắn nhãn {ma}")
            n, loi, r = gan_nhan(ma, muc, tm.kho / ma / "khung.jpg", the_da_co, tm, goc=goc, agent=agent)
            kq.so_luot_agent += 1
            kq.giay_agent += (r.get("duration_ms") or 0) / 1000
            if loi:
                kq.loi.append(f"{ma}: nhãn chưa đạt, chưa đưa vào kho ({'; '.join(loi)})"[:400])
                continue
            nhan[ma] = n
            ghi_json(f_nhan, nhan)
            kq.nhan.append(ma)
            the_da_co = sorted(set(the_da_co) | set(n["the"]))
            if n["mat_nguoi"]:
                cho_quyen.append((ma, muc, n))
        kq.cho_quyen = [m for m, *_ in cho_quyen]
        if cho_quyen:
            ghi_quyen_hinh(bang, kenh, cho_quyen)

        # 4. Số lần dùng cảnh.
        if not thu and f_index.is_file():
            if ap_thong_ke_vao_index(index, thong_ke_dung_canh(goc, kenh)):
                ghi_json(f_index, index)

        # 5. Viết lại KHO.md (mục 1-2 từ dữ liệu, giữ mục 3-4 của agent). Lỗi ở đây không chặn các bước sau.
        if not thu and f_index.is_file():
            from may_reels.kho_md import cap_nhat as cap_nhat_kho_md
            try:
                cap_nhat_kho_md(kenh, tm.kenh, goc, index, nhan, bay_gio=bay_gio_vn(), dung_cho_fn=dung_cho)
            except Exception as e:
                kq.loi.append(f"KHO.md: {type(e).__name__}: {e}"[:300])

        # 6. Sinh lại brand.json, rồi trả job chờ quay đủ cảnh về hàng sản xuất.
        if not thu:
            nap_kenh(kenh, goc)
        kq.tra_ve = tra_ve_san_xuat(bang, kenh, index, goc=goc, thu=thu, log=log)

    if not thu:
        try:
            them_nhat_ky(bang, NHAT_KY, [{
                "thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": "", "buoc": "kho_nap", "che_do": "that",
                "ket_qua": "loi" if kq.loi else "ok",
                "chi_tiet": (f"mới {len(kq.moi)}, gắn nhãn {len(kq.nhan)}, chờ quyền hình {len(kq.cho_quyen)}, "
                             f"đồng ý {len(kq.dong_y)}, trả về sản xuất {kq.tra_ve}; " + "; ".join(kq.loi))[:500],
                "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(round(time.monotonic() - t0, 1)),
                "so_luot_tro_ly": str(kq.so_luot_agent)}])
        except Exception:  # pragma: no cover
            pass
    return kq

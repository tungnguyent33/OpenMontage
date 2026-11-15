"""Giọng đọc tiếng Việt có kiểm tra bằng tai máy: sinh bằng VieNeu, nghe lại bằng PhoWhisper, chọn bản đúng.

VieNeu sinh mỗi lần một khác và đôi khi nuốt số hoặc đọc sai thanh. Vì vậy mỗi đoạn được sinh tối đa
`so_lan` lần; mỗi lần PhoWhisper nghe lại, so với lời cần đọc (đã viết số thành chữ). Lấy bản có đúng
số âm tiết và giống nhất; không bản nào đạt ngưỡng thì báo lỗi, không dùng bản sai.

Chạy bằng Python có cài `vieneu`, `faster_whisper`, `soundfile`, `numpy` (trên máy này: `python` hệ thống).
Các thư viện nặng chỉ import trong hàm. Phần chữ (doc_so, chuan_hoa_doc, am_tiet, do_khop) không cần thư viện nào.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _hai_so(n: int, day_du: bool) -> str:
    """0..99. day_du: đang đứng sau hàng trăm (cần 'linh')."""
    c, d = divmod(n, 10)
    if c == 0:
        return ("linh " + CHU_SO[d]) if day_du and d else (CHU_SO[d] if not day_du else "")
    if c == 1:
        dv = {0: "", 5: "lăm"}.get(d, CHU_SO[d])
        return ("mười " + dv).strip()
    dv = {0: "", 1: "mốt", 4: "tư", 5: "lăm"}.get(d, CHU_SO[d])
    return (CHU_SO[c] + " mươi " + dv).strip()


def _ba_so(n: int, day_du: bool) -> str:
    t, r = divmod(n, 100)
    if t == 0 and not day_du:
        return _hai_so(r, False)
    dau = CHU_SO[t] + " trăm"
    return (dau + " " + _hai_so(r, True)).strip() if r else dau


def doc_so(n: int) -> str:
    """Đọc số nguyên không âm kiểu tiếng Việt: 2025 -> 'hai nghìn không trăm hai mươi lăm'."""
    if n == 0:
        return "không"
    hang = ["", "nghìn", "triệu", "tỷ"]
    nhom = []
    while n:
        n, r = divmod(n, 1000)
        nhom.append(r)
    phan = []
    for i in range(len(nhom) - 1, -1, -1):
        g = nhom[i]
        if g == 0:
            continue
        chu = _ba_so(g, i < len(nhom) - 1)
        phan.append((chu + " " + hang[i]).strip())
    return " ".join(phan)


DIEN_THOAI = re.compile(r"\b0\d{2,3}(?:[ .]\d{3,4}){1,2}\b")


def co_dien_thoai(van_ban: str) -> bool:
    return bool(DIEN_THOAI.search(van_ban))


def _doc_dien_thoai(m: re.Match) -> str:
    """'0823 279 999' -> 'không tám hai ba, hai bảy chín, chín chín chín' (đọc từng chữ số theo nhóm)."""
    return ", ".join(" ".join(CHU_SO[int(c)] for c in nhom) for nhom in re.split(r"[ .]", m.group(0)))


THAY_THE = [
    (DIEN_THOAI, _doc_dien_thoai),
    (re.compile(r"\bZalo\b"), "Za lô"),
    (re.compile(r"\bkW\b"), "ki lô oát"),
    (re.compile(r"\bcm³|\bcm3\b"), "phân khối"),
    (re.compile(r"\b([A-Z])(\d)\b"), lambda m: f"{m.group(1)} {doc_so(int(m.group(2)))}"),  # A1 -> A một
]


def chuan_hoa_doc(van_ban: str) -> str:
    """Viết lại để TTS đọc chắc chắn: ký hiệu, mã hạng bằng, rồi mọi con số thành chữ."""
    s = van_ban
    for mau, thay in THAY_THE:
        s = mau.sub(thay, s)
    return re.sub(r"\d+", lambda m: doc_so(int(m.group(0))), s)


def am_tiet(van_ban: str) -> list[str]:
    s = unicodedata.normalize("NFC", van_ban).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return s.split()


# Cách Whisper hay viết tên riêng khác với lời đọc; quy về một dạng trước khi so.
BIET_DANH = [(re.compile(r"(?:za|da|sa|gia)\s?l[oô]"), "zalo")]


def _chuoi(am: list[str]) -> str:
    s = " ".join(am)
    for mau, thay in BIET_DANH:
        s = mau.sub(thay, s)
    return s.replace(" ", "")


def do_khop(can: list[str], nghe: list[str]) -> float:
    """Giống nhau theo ký tự, bỏ dấu cách (Whisper có thể viết 'za lô' thành 'zalo').

    Whisper hay bịa thêm chữ ở đoạn im lặng cuối file: chỉ so phần đầu của `nghe` dài xấp xỉ `can`.
    """
    a = _chuoi(can)
    b = _chuoi(nghe)
    tot = difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()
    for k in range(len(nghe), 0, -1):
        bk = _chuoi(nghe[:k])
        if len(bk) < len(a) * 0.9:
            break
        tot = max(tot, difflib.SequenceMatcher(a=a, b=bk, autojunk=False).ratio())
    return tot


def am_so(n: int) -> int:
    """Số âm tiết khi đọc số n (khớp doc_so)."""
    return len(doc_so(int(n)).split())


DOC_RIENG = {"kW": 3, "A1": 2, "Zalo": 1}


def so_am_hien_thi(tok: str, dien_thoai: bool = False) -> int:
    """Số chữ Whisper sẽ trả về cho một từ HIỂN THỊ trên phụ đề (dùng để khớp mốc phụ đề)."""
    t = re.sub(r"[^\wÀ-ỹ/]", "", tok)
    if t in DOC_RIENG:
        return DOC_RIENG[t]
    if t.isdigit():
        return len(t) if dien_thoai else am_so(int(t))
    return 1


DUOI_THUA_TOI_DA = 0.4  # giây


def duoi_thua_giay(tu: list[dict], so_tu: int) -> float:
    """Độ dài (giây) của phần chữ Whisper nghe được SAU số chữ cần có.

    Chữ bịa của Whisper dồn vào vài phần trăm giây ở cuối file; nếu phần thừa kéo dài hơn DUOI_THUA_TOI_DA
    thì đó là tiếng đọc thật (TTS đọc lặp) -> bản này không dùng được.
    """
    du = tu[so_tu:]
    if not du:
        return 0.0
    return max(0.0, du[-1]["e"] - du[0]["s"])


@dataclass
class KetQuaDoan:
    id: str
    doc: str
    wav: object
    sample_rate: int
    tu: list[dict]
    khop: float
    so_lan: int
    cac_lan: list[dict] = field(default_factory=list)


def sinh_va_kiem(doan: list[tuple[str, str, int]], *, giong: str = "Hải Đăng", so_lan: int = 10, nguong: float = 0.95,
                 whisper_model: str = "kiendt/PhoWhisper-large-ct2", log=print, cache_dir=None) -> list[KetQuaDoan]:
    """doan: [(id, lời cần đọc đã chuẩn hóa, số chữ Whisper tối thiểu để khớp phụ đề)].

    Một lần sinh đạt khi Whisper trả về ít nhất `so_tu` chữ và độ khớp ký tự >= nguong.
    Trả về bản khớp nhất của từng đoạn, hoặc RuntimeError nếu có đoạn không đạt.
    cache_dir: đoạn đã đạt được lưu ở đây (wav + json) và dùng lại nếu lời đọc không đổi.
    """
    import os
    import tempfile

    import numpy as np
    import soundfile as sf
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from faster_whisper import WhisperModel
    from vieneu import Vieneu

    tts = Vieneu(backend="onnx", device="cpu")
    v = tts.get_preset_voice(giong)
    sr = getattr(tts, "sample_rate", 48000)
    wm = WhisperModel(whisper_model, device="cpu", compute_type="int8")
    ket_qua, hong = [], []
    with tempfile.TemporaryDirectory() as tmp:
        import json
        from pathlib import Path
        cache = Path(cache_dir) if cache_dir else None
        if cache:
            cache.mkdir(parents=True, exist_ok=True)
        for sid, txt, so_tu in doan:
            can = am_tiet(txt)
            if cache and (cache / f"{sid}.json").is_file() and (cache / f"{sid}.wav").is_file():
                c = json.loads((cache / f"{sid}.json").read_text(encoding="utf-8"))
                if c.get("doc") == txt and c.get("khop", 0) >= nguong and c.get("so_tu_can") == so_tu:
                    w, sr_c = sf.read(str(cache / f"{sid}.wav"), dtype="float32")
                    ket_qua.append(KetQuaDoan(sid, txt, w, sr_c, c["tu"], c["khop"], c["so_lan"], c.get("cac_lan", [])))
                    log(f"   {sid}: dùng lại bản đã đạt (khớp {c['khop']})")
                    continue
            tot = None
            lan_thu = []
            for lan in range(1, so_lan + 1):
                w = np.asarray(tts.infer(txt, voice=v), dtype=np.float32).flatten()
                f = os.path.join(tmp, f"{sid}-{lan}.wav")
                sf.write(f, w, sr)
                # VAD + không nối ngữ cảnh: giảm chữ Whisper bịa ở đoạn lặng cuối file (và giảm thời gian nghe).
                segs, _ = wm.transcribe(f, language="vi", word_timestamps=True, beam_size=5, vad_filter=True,
                                        condition_on_previous_text=False)
                tu = [{"w": x.word.strip(), "s": round(x.start, 3), "e": round(x.end, 3)} for sg in segs for x in sg.words]
                nghe = am_tiet(" ".join(x["w"] for x in tu))
                k = do_khop(can, nghe)
                du_am = len(tu) >= so_tu and duoi_thua_giay(tu, so_tu) <= DUOI_THUA_TOI_DA
                lan_thu.append({"lan": lan, "khop": round(k, 3), "so_tu": len(tu), "can": so_tu,
                                "nghe": " ".join(nghe)})
                log(f"   {sid} lần {lan}: khớp {k:.3f}, {len(tu)}/{so_tu} chữ")
                if du_am and (tot is None or k > tot.khop):
                    tot = KetQuaDoan(sid, txt, w, sr, tu, round(k, 3), lan)
                if du_am and k >= 0.995:
                    break
            if tot is None or tot.khop < nguong:
                hong.append(f"{sid}: tốt nhất {tot.khop if tot else 0:.3f} sau {so_lan} lần ({lan_thu[-1]['nghe']})")
            else:
                tot.cac_lan = lan_thu
                ket_qua.append(tot)
                if cache:
                    sf.write(str(cache / f"{sid}.wav"), tot.wav, sr)
                    (cache / f"{sid}.json").write_text(json.dumps(
                        {"doc": txt, "khop": tot.khop, "so_lan": tot.so_lan, "so_tu_can": so_tu, "tu": tot.tu,
                         "cac_lan": lan_thu}, ensure_ascii=False), encoding="utf-8")
    if hong:
        raise RuntimeError("Giọng đọc không đạt: " + "; ".join(hong))
    return ket_qua

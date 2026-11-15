"""Sinh giọng + mốc phụ đề cho một dự án. Chạy bằng Python có vieneu/faster_whisper (trên máy này: `python`):

    python -m may_reels.dung.giong_chay <thư mục dự án> --giong "Hải Đăng" --so-lan 10 --nguong 0.95 --nghi 0.3

Đọc <dự án>/ke_hoach.json. Ghi vào <dự án>/assets/audio/: sN.wav, giong_tho.wav, moc_giong.json, tu_whisper.json,
kiem_giong.json, tu_phu_de.json. Đoạn đã đạt được lưu ở assets/audio/_da_dat/ và dùng lại khi lời không đổi.
Chỉ import thư viện chuẩn + numpy/soundfile + may_reels.giong (không cần jsonschema, yaml, gspread).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LEAD = 0.15  # giọng bắt đầu sau 0,15 s trong video (khớp hf.py)


def khop_phu_de(ke_hoach: dict, moc: dict, wh: dict) -> list[dict]:
    """Gán mốc thời gian PhoWhisper cho từng chữ HIỂN THỊ (đúng văn bản kế hoạch)."""
    from may_reels.giong import co_dien_thoai, so_am_hien_thi
    ra = []
    for d in ke_hoach["doan"]:
        sid = d["id"]
        dt = co_dien_thoai(d["loi"])
        toks = d["loi"].split()
        w = wh[sid]
        can = sum(so_am_hien_thi(t, dien_thoai=dt) for t in toks)
        if len(w) < can:
            raise RuntimeError(f"{sid}: Whisper nghe {len(w)} chữ, cần {can} để khớp phụ đề")
        i = 0
        for t in toks:
            k = so_am_hien_thi(t, dien_thoai=dt)
            seg = w[i:i + k]
            i += k
            g0 = LEAD + moc[sid]["start"]
            ra.append({"doan": sid, "text": t, "start": round(g0 + seg[0]["s"], 3), "end": round(g0 + seg[-1]["e"], 3),
                       "nghe": " ".join(x["w"] for x in seg)})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("du_an")
    ap.add_argument("--giong", default="Hải Đăng")
    ap.add_argument("--so-lan", type=int, default=10)
    ap.add_argument("--nguong", type=float, default=0.95)
    ap.add_argument("--nghi", type=float, default=0.30)
    a = ap.parse_args(argv)
    import numpy as np
    import soundfile as sf
    from may_reels.giong import chuan_hoa_doc, co_dien_thoai, sinh_va_kiem, so_am_hien_thi

    P = Path(a.du_an)
    kh = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
    doan = []
    for d in kh["doan"]:
        dt = co_dien_thoai(d["loi"])
        so_tu = sum(so_am_hien_thi(t, dien_thoai=dt) for t in d["loi"].split())
        doan.append((d["id"], chuan_hoa_doc(d.get("doc_rieng") or d["loi"]), so_tu))
    out = P / "assets" / "audio"
    out.mkdir(parents=True, exist_ok=True)
    kq = sinh_va_kiem(doan, giong=a.giong, so_lan=a.so_lan, nguong=a.nguong, cache_dir=out / "_da_dat")
    moc, ghep, t0, tu, kiem = [], [], 0.0, {}, {}
    for r in kq:
        sf.write(str(out / f"{r.id}.wav"), r.wav, r.sample_rate)
        d = len(r.wav) / r.sample_rate
        moc.append({"id": r.id, "doc": r.doc, "start": round(t0, 3), "end": round(t0 + d, 3)})
        ghep += [r.wav, np.zeros(int(a.nghi * r.sample_rate), np.float32)]
        t0 += d + a.nghi
        tu[r.id] = r.tu
        kiem[r.id] = {"khop": r.khop, "chon_lan": r.so_lan, "so_lan_thu": len(r.cac_lan) or r.so_lan}
        print(r.id, f"{d:.2f}s", f"khớp {r.khop}", f"(lần {r.so_lan})")
    sf.write(str(out / "giong_tho.wav"), np.concatenate(ghep), kq[0].sample_rate)
    moc_d = {"sample_rate": kq[0].sample_rate, "nghi": a.nghi, "doan": moc, "tong": round(t0 - a.nghi, 3)}
    (out / "moc_giong.json").write_text(json.dumps(moc_d, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "tu_whisper.json").write_text(json.dumps(tu, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "kiem_giong.json").write_text(json.dumps(kiem, ensure_ascii=False, indent=1), encoding="utf-8")
    pd = khop_phu_de(kh, {m["id"]: m for m in moc}, tu)
    (out / "tu_phu_de.json").write_text(json.dumps(pd, ensure_ascii=False, indent=1), encoding="utf-8")
    print("tong", moc_d["tong"])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

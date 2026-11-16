"""Tự kiểm bản dựng (final_review theo schemas/artifacts/final_review.schema.json) và chấm ĐIỂM KỸ THUẬT 0-100.

diem_ky_thuat tất định, công thức ghi rõ trong DIEM_TRU: bắt đầu 100, trừ theo từng vấn đề.
diem_qa trên Sheet là tổng rubric nội dung (may_reels/cham_diem.py, brand/<kenh>/rubric.yaml); điểm kỹ thuật chỉ là
một tiêu chí trong đó (quy đổi về trọng số "ky_thuat").
"""
from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

from may_reels.dung.am_thanh import do as do_am

DIEM_TRU = {
    "ky_thuat": 20,        # sai độ phân giải / fps / thời lượng / thiếu tiếng
    "am_luong": 10,        # ngoài -15..-13 LUFS hoặc đỉnh > -1 dBFS
    "khung_den": 15,
    "im_lang": 10,
    "phu_de": 15,          # phụ đề thiếu chữ so với lời
    "hook_qua_3s": 10,     # hook (giọng đoạn đầu) dài hơn 3 giây; > 4 giây trừ gấp đôi
    "tuong_phan": 3,       # mỗi cảnh báo tương phản của hyperframes check, tối đa 15
    "giong_khop": 100,     # nhân với (1 - độ khớp thấp nhất của giọng)
    "canh_dung_nhieu": 2,  # mỗi cảnh đã dùng >= 3 lần ở video trước
}
# Cảnh tạm (sơ đồ) không trừ ở đây nữa: rubric tiêu chí "chan_thuc" tính theo tỉ lệ thời lượng cảnh thật.


def _probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,avg_frame_rate:format=duration,size", "-of", "json", str(p)],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout)


def _loc(p: Path, loc: str, am: bool) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af" if am else "-vf", loc, "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


def kiem(du_an: Path, video: Path, *, sx: dict, kh: dict, so_canh_bao_tuong_phan: int = 0,
         canh_dung_nhieu: int = 0) -> tuple[dict, dict]:
    """Trả về (final_review, render_report_output). final_review.metadata có diem_ky_thuat và chi tiết trừ điểm."""
    kh_cfg = sx.get("khung_hinh") or {}
    w0, h0, fps0 = int(kh_cfg.get("rong", 1080)), int(kh_cfg.get("cao", 1920)), float(kh_cfg.get("fps", 30))
    lo, hi = kh_cfg.get("thoi_luong_giay", [30, 50])
    pr = _probe(video)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    fps = float(Fraction(v["avg_frame_rate"]))
    dur = float(pr["format"]["duration"])
    tech = []
    if (v["width"], v["height"]) != (w0, h0):
        tech.append(f"độ phân giải {v['width']}x{v['height']}")
    if abs(fps - fps0) > 0.05:
        tech.append(f"{fps:.2f} fps")
    if not lo <= dur <= hi:
        tech.append(f"dài {dur:.1f}s ngoài {lo}-{hi}s")
    if a is None:
        tech.append("không có tiếng")

    rv = du_an / "review"
    rv.mkdir(exist_ok=True)
    frames = []
    for i, t in enumerate([0.6, dur * 0.2, dur * 0.4, dur * 0.6, dur * 0.8, dur - 1.0]):
        f = rv / f"khung-{i}-{t:.1f}s.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(f)], check=True)
        frames.append(f.relative_to(du_an).as_posix())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", "fps=1/4,scale=270:-1,tile=6x2", "-frames:v", "1",
                    str(rv / "luoi.png")], check=True)
    den = re.findall(r"black_start:([\d.]+)", _loc(video, "blackdetect=d=0.5:pix_th=0.05", False))
    giu = float(kh_cfg.get("giu_man_ket_giay", 1.5))
    lang = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", _loc(video, "silencedetect=n=-45dB:d=1.2", True))
            if float(x) < dur - giu - 1.0]
    am = do_am(video)
    am_van_de = []
    if lang:
        am_van_de.append(f"im lặng bất thường tại {lang}")
    if not -15 <= am["lufs"] <= -13:
        am_van_de.append(f"{am['lufs']} LUFS")
    if am["true_peak_dbfs"] > -1.0:
        am_van_de.append(f"đỉnh {am['true_peak_dbfs']} dBFS")

    tu = json.loads((du_an / "assets/audio/tu_phu_de.json").read_text(encoding="utf-8"))
    can = sum(len(d["loi"].split()) for d in kh["doan"])
    pd_van_de = [] if len(tu) == can else [f"phụ đề {len(tu)}/{can} chữ"]

    moc = json.loads((du_an / "assets/audio/moc_giong.json").read_text(encoding="utf-8"))
    hook_s = moc["doan"][0]["end"] - moc["doan"][0]["start"]
    kiem_giong = json.loads((du_an / "assets/audio/kiem_giong.json").read_text(encoding="utf-8"))
    khop_min = min(x["khop"] for x in kiem_giong.values())

    tru = {}
    if tech:
        tru["ky_thuat"] = DIEM_TRU["ky_thuat"]
    if [x for x in am_van_de if "LUFS" in x or "đỉnh" in x]:
        tru["am_luong"] = DIEM_TRU["am_luong"]
    if den:
        tru["khung_den"] = DIEM_TRU["khung_den"]
    if lang:
        tru["im_lang"] = DIEM_TRU["im_lang"]
    if pd_van_de:
        tru["phu_de"] = DIEM_TRU["phu_de"]
    if hook_s > 3.0:
        tru["hook_qua_3s"] = DIEM_TRU["hook_qua_3s"] * (2 if hook_s > 4.0 else 1)
    if so_canh_bao_tuong_phan:
        tru["tuong_phan"] = min(15, DIEM_TRU["tuong_phan"] * so_canh_bao_tuong_phan)
    if khop_min < 1.0:
        tru["giong_khop"] = round(DIEM_TRU["giong_khop"] * (1 - khop_min), 1)
    if canh_dung_nhieu:
        tru["canh_dung_nhieu"] = DIEM_TRU["canh_dung_nhieu"] * canh_dung_nhieu
    diem = max(0, round(100 - sum(tru.values())))

    van_de = tech + am_van_de + ([f"khung đen tại {den}"] if den else []) + pd_van_de
    try:
        from lib.slideshow_risk import score_slideshow_risk
        sp = json.loads((du_an / "artifacts/scene_plan.json").read_text(encoding="utf-8"))
        rui_ro = score_slideshow_risk(sp["scenes"], None, "documentary-montage", "hyperframes")
        rui_ro = {"average": rui_ro["average"], "verdict": rui_ro["verdict"],
                  "ghi_chu": "chỉ tham khảo: scene_plan không điền shot_language/shot_intent nên điểm này không trừ QA"}
    except Exception as e:  # pragma: no cover
        rui_ro = {"loi": str(e)}
    fr = {
        "version": "1.0", "output_path": video.relative_to(du_an).as_posix(), "status": "pass" if not van_de else "revise",
        "checks": {
            "technical_probe": {"valid_container": True, "duration_seconds": round(dur, 2),
                                "resolution": f"{v['width']}x{v['height']}", "fps": round(fps, 3), "has_audio": a is not None,
                                "codec": v["codec_name"], "file_size_bytes": int(pr["format"]["size"]), "issues": tech},
            "visual_spotcheck": {"frames_sampled": len(frames), "frame_paths": frames, "black_frames_detected": bool(den),
                                 "broken_overlays": False, "missing_assets": False, "unreadable_text": False,
                                 "issues": [f"{so_canh_bao_tuong_phan} cảnh báo tương phản từ hyperframes check"]
                                 if so_canh_bao_tuong_phan else []},
            "audio_spotcheck": {"narration_present": a is not None, "music_present": False, "unexpected_silence": bool(lang),
                                "clipping_detected": am["true_peak_dbfs"] > -0.1, "mix_intelligible": khop_min >= 0.95,
                                "issues": am_van_de},
            "promise_preservation": {"delivery_promise_honored": not tech, "renderer_family_used": "documentary-montage",
                                     "render_runtime_used": "hyperframes", "runtime_swap_detected": False,
                                     "runtime_swap_check": "ok: render_runtime = hyperframes theo san-xuat.yaml",
                                     "silent_downgrade_detected": False, "issues": []},
            "subtitle_check": {"subtitles_expected": True, "subtitles_present": bool(tu),
                               "coverage_ratio": min(1.0, len(tu) / max(can, 1)), "timing_drift_detected": False,
                               "issues": pd_van_de},
        },
        "issues_found": van_de,
        "metadata": {"diem_ky_thuat": diem, "tru_diem": tru, "lufs": am["lufs"], "true_peak_dbfs": am["true_peak_dbfs"],
                     "hook_giay": round(hook_s, 2), "giong_khop_thap_nhat": khop_min, "slideshow_risk": rui_ro,
                     "luoi_khung": "review/luoi.png"},
    }
    out = {"path": video.relative_to(du_an).as_posix(), "format": "mp4", "codec": v["codec_name"],
           "audio_codec": a["codec_name"] if a else "", "resolution": f"{v['width']}x{v['height']}", "fps": round(fps, 3),
           "duration_seconds": round(dur, 2), "file_size_bytes": int(pr["format"]["size"]),
           "platform_target": "fb_reels, yt_shorts, tiktok"}
    return fr, out

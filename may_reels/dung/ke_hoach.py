"""Kiểm tra ke_hoach.json và sinh brief / script / scene_plan.

Mọi lỗi ở đây là lỗi KẾ HOẠCH (nội dung, nguồn, cảnh, nhịp): báo về để agent sửa, không dựng.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from may_reels.giong import am_tiet, chuan_hoa_doc
from may_reels.kiem_tra_video import cum_tu_cam, tim_cum_tu_cam

GOC = Path(__file__).resolve().parents[2]
SCHEMA = GOC / "schemas" / "may-reels" / "ke_hoach_video.schema.json"
NHAN_VAI = {"hook": "Hook", "than": "Thân", "chot": "Chốt", "cta": "CTA"}


def doc_brand(kenh: str, goc: Path | None = None) -> dict:
    return json.loads(((goc or GOC) / "brand" / kenh / "brand.json").read_text(encoding="utf-8"))


def doc_san_xuat(kenh: str, goc: Path | None = None) -> dict:
    p = (goc or GOC) / "brand" / kenh / "san-xuat.yaml"
    if not p.is_file():
        raise FileNotFoundError(f"Chưa có brand/{kenh}/san-xuat.yaml (quyết định sản xuất của kênh)")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def giay_uoc_luong(loi: str, am_moi_giay: float) -> float:
    return len(am_tiet(chuan_hoa_doc(loi))) / am_moi_giay


def kiem_tra(kh: dict, brand: dict, sx: dict, *, so_lan_dung: dict[str, int] | None = None) -> tuple[list[str], list[str]]:
    """Trả về (lỗi, cảnh báo). Có lỗi thì không được dựng."""
    import jsonschema
    loi, canh_bao = [], []
    try:
        jsonschema.validate(kh, json.loads(SCHEMA.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as e:
        return [f"sai schema ke_hoach: {e.message} tại {list(e.absolute_path)}"], []

    doan = kh["doan"]
    ids = [d["id"] for d in doan]
    if ids != [f"s{i}" for i in range(1, len(doan) + 1)]:
        loi.append(f"id đoạn phải là s1..s{len(doan)} theo thứ tự: {ids}")
    vai = [d["vai"] for d in doan]
    if vai[0] != "hook" or vai[-1] != "cta" or vai.count("hook") != 1 or vai.count("cta") != 1 or "chot" not in vai:
        loi.append(f"nhịp phải là hook, thân..., chốt, cta: {vai}")
    khung = (sx.get("khung_nhip") or {}).get(kh["khung_nhip"])
    if not khung:
        loi.append(f"khung_nhip {kh['khung_nhip']!r} không có trong san-xuat.yaml")

    aps = float(sx.get("am_tiet_moi_giay", 4.45))
    nghi = float((sx.get("giong") or {}).get("nghi_giua_doan_giay", 0.3))
    giay = {d["id"]: giay_uoc_luong(d.get("doc_rieng") or d["loi"], aps) for d in doan}
    tong = sum(giay.values()) + nghi * (len(doan) - 1) + float((sx.get("khung_hinh") or {}).get("giu_man_ket_giay", 1.5))
    lo, hi = (sx.get("khung_hinh") or {}).get("thoi_luong_giay", [30, 50])
    if not lo <= tong <= hi:
        loi.append(f"thời lượng ước lượng {tong:.1f}s ngoài {lo}-{hi}s")
    if giay[ids[0]] > 3.0:
        loi.append(f"hook ước lượng {giay[ids[0]]:.1f}s, phải trong 3 giây (rút gọn câu hook)")

    # Cụm từ cấm: lời, thẻ chữ, caption
    cam = cum_tu_cam(brand)
    van_ban = [(d["id"], d["loi"]) for d in doan] + [(d["id"] + ".the", f"{d['the']['dong1']} {d['the']['dong2']}")
                                                    for d in doan if d["the"]]
    van_ban += [(f"caption.{k}", v) for k, v in kh["caption"].items()] + [("tieu_de", kh["tieu_de"])]
    for noi, t in van_ban:
        trung = tim_cum_tu_cam(t, cam)
        if trung:
            loi.append(f"{noi}: cụm từ cấm {trung}")

    # Nguồn luật
    nguon = {n["id"]: n for n in kh["nguon_luat"]}
    luat = (sx.get("khung_nhip") or {}).get(kh["khung_nhip"], {}).get("tru_cot") == "1 phút luật mới"
    for d in doan:
        for nid in d["nguon_ids"]:
            if nid not in nguon:
                loi.append(f"{d['id']}: nguon_ids {nid} không có trong nguon_luat")
        if luat and d["vai"] == "than" and not d["nguon_ids"]:
            loi.append(f"{d['id']}: đoạn luật thiếu nguồn")
        if re.search(r"\b(Điều|Nghị định|Thông tư|Luật)\b", d["loi"]) and not d["nguon_ids"]:
            loi.append(f"{d['id']}: nhắc tới văn bản luật mà không có nguồn")

    # CTA: phải là một câu CTA của kênh (giữ đúng số điện thoại)
    cta = doan[-1]
    if cta["loi"] not in (brand.get("cta") or []):
        loi.append(f"đoạn cta phải là nguyên văn một câu trong brand.json cta: {cta['loi']!r}")
    if cta["canh"] is not None or cta["the"] is not None:
        loi.append("đoạn cta dùng màn kết: canh và the phải là null")

    # Cảnh
    kho = {k["ma"]: k for k in brand.get("kho_canh") or []}
    csx = sx.get("canh") or {}
    lap_duoc = set(csx.get("lap_duoc_neu_the") or [])
    dung = []
    thieu = {t["doan"] for t in kh["thieu_canh"]}
    tam = []
    for d in doan[:-1]:
        c = d["canh"]
        if c is None:
            loi.append(f"{d['id']}: thiếu cảnh (thiếu cảnh thật thì ghi vào thieu_canh và dùng cảnh tạm so_do)")
            continue
        if "so_do" in c:
            if d["id"] not in thieu:
                loi.append(f"{d['id']}: cảnh tạm so_do chỉ dùng cho đoạn có trong thieu_canh")
            sd = c["so_do"]
            if sd["kieu"] in ("giao_nhau", "vong_xuyen") and not sd.get("xe"):
                loi.append(f"{d['id']}: sơ đồ {sd['kieu']} cần danh sách xe")
            if sd["kieu"] == "the_chu" and not sd.get("chu"):
                loi.append(f"{d['id']}: sơ đồ the_chu cần 'chu'")
            tam.append(d["id"])
            continue
        if d["id"] in thieu:
            loi.append(f"{d['id']}: đoạn có trong thieu_canh phải dùng cảnh tạm so_do, không lấp bằng cảnh kho không khớp")
        k = kho.get(c["ma"])
        if not k:
            loi.append(f"{d['id']}: cảnh {c['ma']} không có trong kho kênh")
            continue
        if not k.get("dung_duoc"):
            loi.append(f"{d['id']}: cảnh {c['ma']} bị loại ({'; '.join(k.get('ly_do_loai') or [])})")
        if k.get("mat_nguoi") and not (brand.get("quyen_hinh") or {}).get("da_dong_y"):
            loi.append(f"{d['id']}: cảnh có mặt người mà quyen_hinh chưa đồng ý")
        if k.get("loai_file") == "video":
            if c.get("vao") is None:
                loi.append(f"{d['id']}: cảnh video phải có 'vao' (giây trong file gốc)")
            elif k.get("doan_dung_duoc") and not any(x <= c["vao"] < y for x, y in k["doan_dung_duoc"]):
                loi.append(f"{d['id']}: vao={c['vao']} ngoài doan_dung_duoc {k['doan_dung_duoc']}")
        if not lap_duoc & set(k.get("the") or []):
            dung.append(c["ma"])
        if so_lan_dung and so_lan_dung.get(c["ma"], 0) >= 3:
            canh_bao.append(f"{d['id']}: cảnh {c['ma']} đã dùng {so_lan_dung[c['ma']]} lần ở video trước")
    if tam:
        canh_bao.append(f"Có cảnh tạm (sơ đồ): {', '.join(tam)} — chờ cảnh quay thật")
    for t in kh["thieu_canh"]:
        if t["doan"] not in {d["id"] for d in doan}:
            loi.append(f"thieu_canh: đoạn {t['doan']} không tồn tại")
    lap = sorted({m for m in dung if dung.count(m) > 1})
    if csx.get("khong_lap_trong_video", True) and lap:
        loi.append(f"dùng một cảnh hơn một lần trong video: {lap}")
    return loi, canh_bao


def tao_artifact(kh: dict, brand: dict, sx: dict) -> tuple[dict, dict, dict]:
    """brief, script, scene_plan theo schema OpenMontage. Thời gian là ước lượng; mốc thật lấy sau khi sinh giọng."""
    aps = float(sx.get("am_tiet_moi_giay", 4.45))
    nghi = float((sx.get("giong") or {}).get("nghi_giua_doan_giay", 0.3))
    nguon = {n["id"]: n for n in kh["nguon_luat"]}
    kho = {k["ma"]: k for k in brand.get("kho_canh") or []}
    t, sections, scenes = 0.0, [], []
    for d in kh["doan"]:
        dur = round(giay_uoc_luong(d.get("doc_rieng") or d["loi"], aps), 2)
        a, b = round(t, 2), round(t + dur, 2)
        t += dur + nghi
        sec = {"id": d["id"], "label": NHAN_VAI[d["vai"]], "text": d["loi"], "start_seconds": a, "end_seconds": b,
               "speaker_directions": f"Giọng {(sx.get('giong') or {}).get('ten', '')}, nhịp vừa, rõ số"}
        if d["nguon_ids"]:
            sec["source_ref"] = "; ".join(f"{nguon[i]['van_ban']}, {nguon[i]['dieu_khoan']} — {nguon[i]['link']}"
                                          for i in d["nguon_ids"])
        sections.append(sec)
        c = d["canh"]
        if c and "so_do" in c:
            ra = {"type": "diagram", "description": f"Cảnh tạm (sơ đồ {c['so_do']['kieu']}): {c['mo_ta']}",
                  "source": "generate", "so_do": c["so_do"],
                  "generation_summary": "Vẽ bằng code (SVG + GSAP trong HyperFrames), không dùng AI, không stock"}
        elif c:
            k = kho[c["ma"]]
            ra = {"type": "video" if k.get("loai_file") == "video" else "image", "ma_kho": c["ma"],
                  "description": c["mo_ta"], "source": "provided", "path": f"kenh:{k['file_tuong_doi']}",
                  "in_out": [c["vao"], None] if c.get("vao") is not None else None}
        else:
            ra = {"type": "image", "description": "Màn kết: logo + CTA + Zalo + địa chỉ", "source": "provided",
                  "path": f"brand/{kh['kenh']}/assets/logo.png"}
        the = d["the"]
        scenes.append({"id": "c" + d["id"][1:], "type": ("diagram" if "so_do" in c else "broll") if c else "text_card",
                       "description": c["mo_ta"] if c else "Màn kết", "start_seconds": a, "end_seconds": b,
                       "script_section_id": d["id"], "framing": "9:16 1080x1920",
                       "overlay_notes": (f"Thẻ: {the['dong1']} / {the['dong2']}" if the else "Màn kết") +
                                        (" | Dòng nguồn: " + "; ".join(nguon[i]["dieu_khoan"] for i in d["nguon_ids"])
                                         if d["nguon_ids"] else ""),
                       "required_assets": [ra]})
    total = round(t - nghi, 2)
    meta = {"ma_video": kh["ma_video"], "kenh": kh["kenh"], "ma_chu_de": kh["ma_chu_de"], "khung_nhip": kh["khung_nhip"],
            "nen_tang": ["fb_reels", "yt_shorts", "tiktok"], "nguon_luat": kh["nguon_luat"],
            "anchor_medium": "narration_led_graphics", "fallback_policy": "Không AI sinh hình, không stock nước ngoài"}
    brief = {"version": "1.0", "title": kh["tieu_de"], "hook": kh["doan"][0]["loi"],
             "key_points": [d["loi"] for d in kh["doan"] if d["vai"] == "than"],
             "cta": kh["doan"][-1]["loi"], "tone": "Thân thiện, thẳng thắn, xưng mình gọi bạn",
             "style": f"Thương hiệu kênh (brand/{kh['kenh']}/brand.json)",
             "target_audience": (brand.get("kenh") or {}).get("khan_gia", ""), "target_platform": "generic",
             "target_duration_seconds": total, "reference_material": [n["link"] for n in kh["nguon_luat"]],
             "metadata": meta}
    script = {"version": "1.0", "title": kh["tieu_de"], "total_duration_seconds": total, "sections": sections,
              "metadata": {"uoc_luong": True, "nguon_luat": kh["nguon_luat"]}}
    scene_plan = {"version": "1.0", "scenes": scenes,
                  "metadata": {"anchor_rules": "Cảnh kho chỉ dùng trong doan_dung_duoc; không lặp cảnh; không stock"}}
    return brief, script, scene_plan

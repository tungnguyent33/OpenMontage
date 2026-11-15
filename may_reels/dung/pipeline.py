"""Chạy pipeline may-reels cho một dự án có ke_hoach.json: mỗi stage một checkpoint (lib/checkpoint.py), đo thời gian.

    python -m may_reels dung --du-an <ma_video> [--stage idea script ...]

Cổng người:
  idea    : human_approved=True CHỈ khi tab Ý tưởng có duyet_chu_de = "Làm" cho (kênh, mã chủ đề). Ghi tham chiếu dòng.
  publish : đóng gói bằng export_bundle, ghi awaiting_human. Không đăng.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

GOC = Path(__file__).resolve().parents[2]
PIPELINE = "may-reels"
STAGES = ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"]
TZ_VN = timezone(timedelta(hours=7))
BIEN_PY_GIONG = "MAY_REELS_PY_GIONG"  # Python có vieneu + faster_whisper; mặc định "python"


class LoiKeHoach(RuntimeError):
    """Kế hoạch sai (nội dung, nguồn, cảnh, nhịp): agent phải sửa ke_hoach.json."""


class LoiCongDuyet(RuntimeError):
    """Chủ đề chưa được chọn "Làm" trên Sheet."""


class LoiThieuCanhDung(RuntimeError):
    """Không có cảnh thật phù hợp: ghi tab Cần quay, job sang cho_quay."""

    def __init__(self, thieu: list[dict]) -> None:
        super().__init__("; ".join(f"{x['doan']}: {x['ly_do']}" for x in thieu))
        self.thieu = thieu


class LoiQA(RuntimeError):
    """Bản dựng không qua final_review."""


@dataclass
class KetQuaDung:
    du_an: Path
    video: Path | None = None
    diem_qa: int | None = None
    canh_bao: list[str] = field(default_factory=list)
    thoi_gian: dict = field(default_factory=dict)


def bay_gio() -> str:
    return datetime.now(TZ_VN).isoformat(timespec="seconds")


def doc_cong_sheet(kenh: str, ma_chu_de: str) -> dict:
    """Đọc dòng tab Ý tưởng. Trả về tham chiếu nếu duyet_chu_de == 'Làm', ngược lại LoiCongDuyet."""
    from may_reels.cot_sheet import Y_TUONG
    from may_reels.sheet import chuan, doc_dong, mo_tu_env
    d = next((r for r in doc_dong(mo_tu_env(), Y_TUONG) if r.get("kenh") == kenh and r.get("ma") == ma_chu_de), None)
    if not d or chuan(d.get("duyet_chu_de")) != "Làm":
        raise LoiCongDuyet(f"tab Ý tưởng chưa có duyet_chu_de = 'Làm' cho {kenh}/{ma_chu_de}")
    return {"tab": Y_TUONG.ten, "khoa": {"kenh": kenh, "ma": ma_chu_de}, "duyet_chu_de": d["duyet_chu_de"], "doc_luc": bay_gio()}


def so_lan_dung_canh(goc: Path, kenh: str, tru: str | None = None) -> dict[str, int]:
    """Đếm số video trước đã dùng mỗi cảnh (đọc projects/*/ke_hoach.json của cùng kênh)."""
    dem: dict[str, int] = {}
    for f in (goc / "projects").glob("*/ke_hoach.json"):
        if tru and f.parent.name == tru:
            continue
        try:
            kh = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if kh.get("kenh") != kenh:
            continue
        for m in {d["canh"].get("ma") for d in kh.get("doan", []) if d.get("canh") and d["canh"].get("ma")}:
            dem[m] = dem.get(m, 0) + 1
    return dem


class Pipeline:
    def __init__(self, ma_video: str, *, goc: Path = GOC, cong: Callable[[str, str], dict] = doc_cong_sheet,
                 log: Callable[[str], None] = print) -> None:
        from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat
        self.goc, self.log, self.cong = goc, log, cong
        self.P = goc / "projects" / ma_video
        self.kh = json.loads((self.P / "ke_hoach.json").read_text(encoding="utf-8"))
        self.kenh = self.kh["kenh"]
        self.brand = doc_brand(self.kenh, goc)
        self.sx = doc_san_xuat(self.kenh, goc)
        self.A = self.P / "artifacts"
        self.kq = KetQuaDung(self.P)

    # ---------- tiện ích ----------
    def _ck(self, stage: str, status: str, artifacts: dict, **kw) -> None:
        from lib.checkpoint import write_checkpoint
        write_checkpoint(self.goc / "projects", self.P.name, stage, status, artifacts, pipeline_type=PIPELINE, **kw)
        self.log(f"  checkpoint {stage}: {status}")

    def _ghi(self, ten: str, obj: dict) -> None:
        self.A.mkdir(parents=True, exist_ok=True)
        (self.A / f"{ten}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def _doc(self, ten: str) -> dict:
        return json.loads((self.A / f"{ten}.json").read_text(encoding="utf-8"))

    def _kiem_ke_hoach(self) -> list[str]:
        from may_reels.dung.ke_hoach import kiem_tra
        loi, canh_bao = kiem_tra(self.kh, self.brand, self.sx, so_lan_dung=so_lan_dung_canh(self.goc, self.kenh, self.P.name))
        if loi:
            raise LoiKeHoach("; ".join(loi))
        return canh_bao

    # ---------- stage ----------
    def idea(self) -> None:
        from lib.checkpoint import init_project
        from may_reels.dung.ke_hoach import tao_artifact
        the_sheet = self.cong(self.kenh, self.kh["ma_chu_de"])
        # Thiếu cảnh thật: kế hoạch phải dùng cảnh tạm (so_do) cho đúng các đoạn đó; kiem_tra bắt lỗi nếu không.
        self.kq.canh_bao += self._kiem_ke_hoach()
        init_project(self.P.name, title=self.kh["tieu_de"], pipeline_type=PIPELINE, series=self.kenh,
                     pipeline_dir=self.goc / "projects")
        brief, script, scene_plan = tao_artifact(self.kh, self.brand, self.sx)
        for ten, obj in (("brief", brief), ("script", script), ("scene_plan", scene_plan)):
            self._ghi(ten, obj)
        sx = self.sx
        dl = {"version": "1.0", "project_id": self.P.name, "decisions": [
            {"decision_id": "d-001", "stage": "idea", "category": "render_runtime_selection", "subject": "Runtime dựng",
             "options_considered": [
                 {"option_id": "hyperframes", "label": "HyperFrames", "score": 0.9, "reason": "Chốt trong san-xuat.yaml"},
                 {"option_id": "remotion", "label": "Remotion", "score": 0.5, "reason": "Có trong manifest",
                  "rejected_because": "Kênh đã chốt HyperFrames (san-xuat.yaml)"}],
             "selected": sx.get("runtime", "hyperframes"), "reason": "Đã chốt theo cấu hình kênh", "user_visible": True,
             "user_approved": True},
            {"decision_id": "d-002", "stage": "idea", "category": "voice_selection", "subject": "Giọng đọc",
             "options_considered": [{"option_id": "vieneu", "label": (sx.get("giong") or {}).get("ten", ""), "score": 1.0,
                                     "reason": "Chốt trong san-xuat.yaml"}],
             "selected": "vieneu", "reason": "Đã chốt theo cấu hình kênh", "user_visible": True, "user_approved": True},
            {"decision_id": "d-003", "stage": "idea", "category": "music_source", "subject": "Nhạc nền",
             "options_considered": [{"option_id": "khong", "label": "Không nhạc", "score": 1.0, "reason": "san-xuat.yaml"}],
             "selected": "khong", "reason": "Đã chốt theo cấu hình kênh", "user_visible": True, "user_approved": True},
        ]}
        for i, q in enumerate(self.kh.get("quyet_dinh") or [], start=4):
            dl["decisions"].append({"decision_id": f"d-{i:03d}", "stage": "idea", "category": q["category"],
                                    "subject": q["subject"], "options_considered": q.get("options_considered") or [],
                                    "selected": q["selected"], "reason": q["reason"], "user_visible": True,
                                    "user_approved": False})
        self._ck("idea", "completed", {"brief": brief, "decision_log": dl}, human_approval_required=True,
                 human_approved=True, metadata={"duyet_tu_sheet": the_sheet})

    def script(self) -> None:
        self._kiem_ke_hoach()
        self._ck("script", "completed", {"script": self._doc("script")},
                 review={"reviewer": "may_reels.dung.ke_hoach", "ket_luan": "đạt",
                         "da_kiem": ["cụm từ cấm", "nguồn luật", "CTA nguyên văn", "nhịp hook/thân/chốt/cta", "thời lượng"]})

    def scene_plan(self) -> None:
        self._ck("scene_plan", "completed", {"scene_plan": self._doc("scene_plan")},
                 review={"reviewer": "may_reels.dung.ke_hoach", "ket_luan": "đạt",
                         "da_kiem": ["dung_duoc", "doan_dung_duoc", "quyen_hinh", "không lặp cảnh"]})

    def assets(self) -> None:
        from may_reels.dung import am_thanh, canh
        from tools_local.nap_kenh import nap_env, thu_muc_kenh
        g = self.sx.get("giong") or {}
        py = os.environ.get(BIEN_PY_GIONG, "python")
        r = subprocess.run([py, "-m", "may_reels.dung.giong_chay", str(self.P), "--giong", g.get("ten", "Hải Đăng"),
                            "--so-lan", str(g.get("so_lan_thu", 10)), "--nguong", str(g.get("nguong_khop", 0.95)),
                            "--nghi", str(g.get("nghi_giua_doan_giay", 0.3))],
                           cwd=self.goc, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONUTF8": "1"})
        self.log(r.stdout.strip()[-1500:])
        if r.returncode != 0:
            raise RuntimeError(f"sinh giọng lỗi: {r.stderr.strip()[-1500:]}")
        moc = json.loads((self.P / "assets/audio/moc_giong.json").read_text(encoding="utf-8"))
        try:
            cat = canh.tinh_cat(self.kh, self.brand, self.sx, {m["id"]: m for m in moc["doan"]})
        except canh.LoiThieuCanh as e:
            raise LoiThieuCanhDung([self._thieu(e.doan, e.ma, e.ly_do)]) from e
        (self.P / "cat_canh.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
        nap_env()
        goc_kenh = thu_muc_kenh(self.kenh)
        if not goc_kenh or not goc_kenh.is_dir():
            raise RuntimeError("Chưa đặt KENH_GOC_DIR trong .env hoặc thư mục kênh không tồn tại")
        try:
            canh.chuan_bi(cat, self.brand, self.sx, self.P, goc_kenh)
        except canh.LoiThieuCanh as e:
            raise LoiThieuCanhDung([self._thieu(e.doan, e.ma, e.ly_do)]) from e
        a = self.sx.get("am_thanh") or {}
        am = am_thanh.chuan_hoa_wav(self.P / "assets/audio/giong_tho.wav", self.P / "hf/assets/audio/vo.wav",
                                   float(a.get("lufs", -14)), float(a.get("dinh_dbtp", -1.0)))
        assets = [{"id": f"vo-{m['id']}", "type": "narration", "path": f"assets/audio/{m['id']}.wav", "source_tool": "vieneu",
                   "scene_id": "c" + m["id"][1:], "provider": "vieneu", "cost_usd": 0,
                   "duration_seconds": round(m["end"] - m["start"], 3)} for m in moc["doan"]]
        assets.append({"id": "vo", "type": "narration", "path": "hf/assets/audio/vo.wav", "source_tool": "ffmpeg",
                       "scene_id": "all", "cost_usd": 0, "generation_summary": f"loudnorm {am}"})
        assets.append({"id": "phu-de", "type": "subtitle", "path": "assets/audio/tu_phu_de.json", "source_tool": "faster_whisper",
                       "scene_id": "all", "cost_usd": 0})
        for c in cat:
            if c.get("so_do"):
                assets.append({"id": c["id"], "type": "diagram", "path": f"hf/compositions/{c['doan']}.html",
                               "source_tool": "hyperframes", "scene_id": c["id"], "subtype": "canh-tam", "cost_usd": 0,
                               "generation_summary": f"Cảnh tạm: sơ đồ {c['so_do']['kieu']} (thay bằng cảnh quay thật sau)"})
                continue
            p = (f"hf/assets/img/{next((f.name for f in (self.P / 'hf/assets/img').glob(c['id'] + '.*')), c['id'] + '.jpg')}"
                 if c["anh"] else f"hf/assets/video/{c['id']}.mp4")
            assets.append({"id": c["id"], "type": "image" if c["anh"] else "video", "path": p, "source_tool": "ffmpeg",
                           "scene_id": c["id"], "provider": "kho-kenh", "subtype": "kho-kenh", "cost_usd": 0,
                           "generation_summary": f"{c['ma']} vào {c['in']}s dài {c['dai']}s"})
        thieu = [x["path"] for x in assets if x.get("subtype") != "canh-tam" and not (self.P / x["path"]).is_file()]
        if thieu:
            raise RuntimeError(f"thiếu file asset: {thieu}")
        self._ck("assets", "completed", {"asset_manifest": {"version": "1.0", "assets": assets,
                                                             "metadata": {"do_am": am, "tong_chi_phi_usd": 0}}},
                 cost_snapshot={"total_spent_usd": 0})

    def _thieu(self, doan: str, ma: str, ly_do: str) -> dict:
        d = next(x for x in self.kh["doan"] if x["id"] == doan)
        return {"doan": doan, "y_can_canh": d["loi"], "mo_ta_canh": (d.get("canh") or {}).get("mo_ta", ""),
                "goi_y_quay": "Quay dọc 9:16, ít nhất 10 giây liền, không thấy mặt học viên và biển số",
                "ly_do": f"Cảnh {ma} không đủ đoạn dùng được: {ly_do}"}

    def edit(self) -> None:
        cat = json.loads((self.P / "cat_canh.json").read_text(encoding="utf-8"))
        moc = json.loads((self.P / "assets/audio/moc_giong.json").read_text(encoding="utf-8"))
        cuts = [{"id": c["id"], "source": c["id"], "in_seconds": 0 if (c["anh"] or c.get("so_do")) else c["in"],
                 "out_seconds": round((0 if (c["anh"] or c.get("so_do")) else c["in"]) + c["dai"], 2), "layer": "primary",
                 **({"transform": {"animation": "ken-burns-slow-zoom"}} if c["anh"] else {})} for c in cat]
        ed = {"version": "1.0", "render_runtime": self.sx.get("runtime", "hyperframes"),
              "renderer_family": "documentary-montage", "cuts": cuts,
              "audio": {"narration": {"segments": [{"asset_id": f"vo-{m['id']}", "start_seconds": round(m["start"] + 0.15, 3),
                                                    "end_seconds": round(m["end"] + 0.15, 3)} for m in moc["doan"]]}},
              "metadata": {"nhac": "không"}}
        self._ck("edit", "completed", {"edit_decisions": ed})

    def compose(self) -> None:
        from may_reels.dung import am_thanh
        from may_reels.dung.hf import Dung
        from may_reels.dung.kiem_tra import kiem
        t0 = time.monotonic()
        cat = json.loads((self.P / "cat_canh.json").read_text(encoding="utf-8"))
        moc = json.loads((self.P / "assets/audio/moc_giong.json").read_text(encoding="utf-8"))
        tu = json.loads((self.P / "assets/audio/tu_phu_de.json").read_text(encoding="utf-8"))
        Dung(self.P, self.kh, self.brand, self.sx, cat, tu, moc, self.goc).viet()
        cli = ["npx", "--yes", f"hyperframes@{self.sx.get('hyperframes_phien_ban', '0.9.46')}"]
        r = subprocess.run(cli + ["check"], cwd=self.P / "hf", capture_output=True, text=True, encoding="utf-8",
                           errors="replace", shell=True)
        if r.returncode != 0:
            raise RuntimeError(f"hyperframes check lỗi: {(r.stdout + r.stderr)[-2000:]}")
        tuong_phan = len(re.findall(r"✗ #\S+ [\d.]+:1", r.stdout))
        tho, out = self.P / "renders/final_tho.mp4", self.P / "renders/final.mp4"
        out.parent.mkdir(exist_ok=True)
        r = subprocess.run(cli + ["render", "-o", str(tho), "--quiet"], cwd=self.P / "hf", capture_output=True, text=True,
                           encoding="utf-8", errors="replace", shell=True)
        if r.returncode != 0 or not tho.is_file():
            raise RuntimeError(f"hyperframes render lỗi: {(r.stdout + r.stderr)[-2000:]}")
        a = self.sx.get("am_thanh") or {}
        am_thanh.chuan_hoa_mp4(tho, out, float(a.get("lufs", -14)), float(a.get("dinh_dbtp", -1.0)))
        tho.unlink()
        render_s = round(time.monotonic() - t0, 1)
        dung_nhieu = sum(1 for m, n in so_lan_dung_canh(self.goc, self.kenh, self.P.name).items()
                         if n >= 3 and any((d.get("canh") or {}).get("ma") == m for d in self.kh["doan"]))
        so_canh_tam = sum(1 for d in self.kh["doan"] if (d.get("canh") or {}).get("so_do"))
        fr, o = kiem(self.P, out, sx=self.sx, kh=self.kh, so_canh_bao_tuong_phan=tuong_phan, canh_dung_nhieu=dung_nhieu,
                     so_canh_tam=so_canh_tam)
        rr = {"version": "1.0", "outputs": [o], "render_time_seconds": render_s, "render_grammar": "documentary-montage",
              "verification_notes": [f"diem_qa {fr['metadata']['diem_qa']}", f"trừ {fr['metadata']['tru_diem']}"]}
        self.kq.video, self.kq.diem_qa = out, fr["metadata"]["diem_qa"]
        if fr["status"] != "pass":
            self._ck("compose", "failed", {"render_report": rr, "final_review": fr}, error="; ".join(fr["issues_found"]))
            raise LoiQA("; ".join(fr["issues_found"]))
        self._ck("compose", "completed", {"render_report": rr, "final_review": fr},
                 review={"reviewer": "may_reels.dung.kiem_tra", "ket_luan": fr["status"],
                         "diem_qa": fr["metadata"]["diem_qa"]})

    def publish(self) -> None:
        from tools.publishers.export_bundle import ExportBundle
        from may_reels.hang_cho import go_lien_ket_cu
        go_lien_ket_cu(self.P / "exports", self.P / "renders/final.mp4")
        tags = self.brand.get("hashtags") or {}
        res = ExportBundle().execute({
            "video_path": str(self.P / "renders/final.mp4"), "title": self.kh["tieu_de"], "project_name": self.P.name,
            "export_dir": str(self.P / "exports"), "description": self.kh["caption"]["fb_reels"],
            "hashtags": sorted(set(sum(tags.values(), []))), "platform": "local"})
        if not res.success:
            raise RuntimeError(f"export_bundle lỗi: {res.error}")
        from may_reels.hang_cho import lien_ket_video
        lien_ket_video(self.P / "exports", self.P / "renders/final.mp4")
        self._ck("publish", "awaiting_human", {"publish_log": res.data["publish_log"]},
                 metadata={"cho_duyet": "tab Hàng chờ, cột duyet (cổng B). Chưa đăng nền tảng nào."})

    # ---------- chạy ----------
    def chay(self, stages: list[str] | None = None) -> KetQuaDung:
        from lib.checkpoint import get_completed_stages
        xong = set(get_completed_stages(self.goc / "projects", self.P.name, PIPELINE)) if (self.P / "project.json").exists() else set()
        tg_file = self.P / "thoi-gian.json"
        tg = json.loads(tg_file.read_text(encoding="utf-8")) if tg_file.exists() else {}
        for s in stages or [s for s in STAGES if s not in xong or s == "publish"]:
            self.log(f"== {s} ({bay_gio()})")
            t = time.monotonic()
            getattr(self, s)()
            tg[s] = {"giay": round(time.monotonic() - t, 1), "xong_luc": bay_gio()}
            tg_file.write_text(json.dumps(tg, ensure_ascii=False, indent=1), encoding="utf-8")
        if self.kq.diem_qa is None and (self.P / "checkpoint_compose.json").exists():
            c = json.loads((self.P / "checkpoint_compose.json").read_text(encoding="utf-8"))
            self.kq.diem_qa = c["artifacts"]["final_review"]["metadata"].get("diem_qa")
            self.kq.video = self.P / "renders/final.mp4"
        self.kq.thoi_gian = tg
        return self.kq

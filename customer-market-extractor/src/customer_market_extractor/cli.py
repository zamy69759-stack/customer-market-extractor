from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .core import discover, load_config, parse_file, result_dict, safe_relative, validate_card


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def require_config(cfg: dict) -> bool:
    missing = [key for key in ("source_root", "knowledge_root", "work_root") if not cfg.get(key)]
    if missing:
        print("尚未完成首次路径配置。请由用户运行 python run.py configure 并亲自指定三个根目录。", file=sys.stderr)
        return False
    return True


def _atomic_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def cmd_status(args) -> int:
    cfg = load_config(skill_dir())
    states = {
        k: {
            "path": v,
            "configured": bool(v),
            "exists": bool(v) and Path(v).exists(),
            "readable": bool(v) and os.access(v, os.R_OK),
        }
        for k, v in cfg.items() if k.endswith("_root")
    }
    optional = {}
    for module in ("docx", "openpyxl", "pypdf", "pptx", "extract_msg"):
        try:
            __import__(module); optional[module] = True
        except ImportError:
            optional[module] = False
    print(json.dumps({"paths": states, "optional_parsers": optional, "ocr": "未配置", "transcription": "未配置"}, ensure_ascii=False, indent=2))
    return 0 if all(x["configured"] and x["exists"] and x["readable"] for x in states.values()) else 2


def cmd_configure(args) -> int:
    current = load_config(skill_dir())
    prompts = [("source_root", "原始语料库根目录"), ("knowledge_root", "企业知识库根目录"), ("work_root", "工具工作目录")]
    for key, label in prompts:
        old = current.get(key) or ""
        value = input(f"{label} [{old}]: ").strip()
        if value:
            current[key] = str(Path(value).expanduser().resolve())
        elif not old:
            print(f"必须由用户提供：{label}，未保存。", file=sys.stderr); return 2
    for key, _ in prompts:
        p = Path(current[key])
        if not p.exists():
            print(f"路径不存在，未保存: {p}", file=sys.stderr); return 2
    _atomic_json(skill_dir() / "config.json", current)
    print("配置已保存")
    return 0


def cmd_scan(args) -> int:
    cfg = load_config(skill_dir())
    if not require_config(cfg):
        return 2
    source_root = Path(cfg["source_root"])
    target = safe_relative(source_root, args.relative_path)
    work = Path(cfg["work_root"])
    work.mkdir(parents=True, exist_ok=True)
    manifest_path = work / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    files = {}
    report = []
    for path in discover(target):
        rel = path.relative_to(source_root).as_posix()
        result = parse_file(path, rel)
        record = result_dict(result)
        record["changed"] = old.get("files", {}).get(rel, {}).get("sha256") != result.sha256
        files[rel] = record
        report.append(record)
    data = {"generated_at": datetime.now().astimezone().isoformat(), "source": args.relative_path, "files": files}
    _atomic_json(manifest_path, data)
    report_path = work / "parse-report.json"
    _atomic_json(report_path, report)
    counts = {s: sum(1 for r in report if r["status"] == s) for s in ("成功", "部分成功", "失败")}
    print(json.dumps({"files": len(report), "counts": counts, "manifest": str(manifest_path), "report": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if not counts["失败"] else 1


def cmd_validate(args) -> int:
    cfg = load_config(skill_dir())
    if not require_config(cfg):
        return 2
    root = Path(cfg["knowledge_root"]) / cfg.get("knowledge_category", "客户与市场")
    if not root.exists():
        print(f"知识分类目录不存在: {root}", file=sys.stderr); return 2
    issues = {str(p): e for p in root.rglob("MKT_*.md") if (e := validate_card(p))}
    print(json.dumps({"cards": len(list(root.rglob('MKT_*.md'))), "issues": issues}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="customer-market-extractor")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("configure").set_defaults(func=cmd_configure)
    scan = sub.add_parser("scan"); scan.add_argument("relative_path"); scan.set_defaults(func=cmd_scan)
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    args = parser.parse_args(argv)
    return args.func(args)

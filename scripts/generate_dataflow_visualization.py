#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.config import Config
from dashagent.dataflow_visualizer import build_html_report, build_markdown_report, build_mermaid_graph, load_trajectory


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mermaid/Markdown/HTML dataflow visualization from a trajectory.")
    parser.add_argument("trajectory", help="Path to trajectory.json")
    parser.add_argument("--out-dir", default=None, help="Output directory. Defaults to outputs/demo_dataflow.")
    parser.add_argument("--format", choices=["mmd", "md", "html", "all"], default="all")
    args = parser.parse_args()
    config = Config.from_env(ROOT)
    out_dir = Path(args.out_dir) if args.out_dir else config.outputs_dir / "demo_dataflow"
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectory = load_trajectory(args.trajectory)
    written = []
    if args.format in {"mmd", "all"}:
        path = out_dir / "dataflow.mmd"
        path.write_text(build_mermaid_graph(trajectory), encoding="utf-8")
        written.append(str(path))
    if args.format in {"md", "all"}:
        path = out_dir / "dataflow.md"
        path.write_text(build_markdown_report(trajectory), encoding="utf-8")
        written.append(str(path))
    if args.format in {"html", "all"}:
        path = out_dir / "dataflow.html"
        path.write_text(build_html_report(trajectory), encoding="utf-8")
        written.append(str(path))
    mmdc = shutil.which("mmdc")
    svg_path = None
    if args.format == "all" and mmdc:
        mmd_path = out_dir / "dataflow.mmd"
        svg_path = out_dir / "dataflow.svg"
        try:
            subprocess.run([mmdc, "-i", str(mmd_path), "-o", str(svg_path)], check=False, capture_output=True, text=True)
            if svg_path.exists():
                written.append(str(svg_path))
        except Exception:
            svg_path = None
    print(json.dumps({"trajectory": args.trajectory, "out_dir": str(out_dir), "written": written, "mermaid_cli": bool(mmdc), "svg": str(svg_path) if svg_path and svg_path.exists() else None}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

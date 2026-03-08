#!/usr/bin/env python3
"""
arc_task.py — ArcGIS Pro Automation CLI

Submit a map generation task via ArcPy (ArcGIS Pro) or fall back to
simulation mode (geopandas/matplotlib) when ArcGIS Pro is not available.

Usage:
    python arc_task.py --input data/parcels.shp --style blue_fill --output output/map.png
    python arc_task.py --input data/sample.geojson --style red_fill --output output/map.pdf --format pdf
    python arc_task.py --input data/parcels.shp --style blue_fill --output output/map.png --queue
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Try to import ArcPy (requires ArcGIS Pro + license) ──────────────────────
try:
    import arcpy
    ARCPY_AVAILABLE = True
    print("[info] ArcPy detected — using ArcGIS Pro rendering engine")
except ImportError:
    ARCPY_AVAILABLE = False
    print("[info] ArcPy not available — using simulation mode (geopandas/matplotlib)")

# ── Style presets ─────────────────────────────────────────────────────────────
STYLES_DIR = Path(__file__).parent / "styles"
STYLES = {
    "blue_fill": {"fill_color": [0, 112, 255], "outline_color": [0, 0, 0], "outline_width": 0.5},
    "red_fill":  {"fill_color": [255, 0, 0],   "outline_color": [80, 0, 0], "outline_width": 0.5},
    "outline_only": {"fill_color": None,        "outline_color": [0, 0, 0], "outline_width": 1.0},
    "heat_map":  {"type": "graduated", "field": None, "color_ramp": "YlOrRd"},
}


def load_style(style_name: str) -> dict:
    """Load style from JSON file or built-in presets."""
    style_file = STYLES_DIR / f"{style_name}.json"
    if style_file.exists():
        with open(style_file) as f:
            return json.load(f)
    if style_name in STYLES:
        return STYLES[style_name]
    raise ValueError(f"Unknown style: '{style_name}'. Available: {list(STYLES.keys())}")


def run_arcpy_task(input_path: str, style_name: str, output_path: str, fmt: str = "png") -> dict:
    """
    Run a mapping task using ArcPy (requires ArcGIS Pro license).

    arcpy.mp workflow:
    1. Open or create an ArcGIS Pro project (.aprx)
    2. Access the map and add a layer
    3. Apply symbology
    4. Export the layout to PNG/PDF
    """
    import arcpy
    from arcpy import mp as arcpy_mp

    style = load_style(style_name)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # ── Use a blank project template or existing .aprx ────────────────────────
    aprx_path = Path(__file__).parent / "template.aprx"
    if aprx_path.exists():
        aprx = arcpy_mp.ArcGISProject(str(aprx_path))
    else:
        # Create a new project in memory (ArcGIS Pro 2.7+)
        aprx = arcpy_mp.ArcGISProject("CURRENT")

    # ── Get the first map ─────────────────────────────────────────────────────
    m = aprx.listMaps()[0]

    # ── Add data layer ────────────────────────────────────────────────────────
    layer = m.addDataFromPath(str(Path(input_path).resolve()))
    print(f"[arcpy] Added layer: {layer.name}")

    # ── Apply symbology ───────────────────────────────────────────────────────
    sym = layer.symbology
    if hasattr(sym, "renderer"):
        renderer = sym.renderer
        renderer.symbol.color = {
            "RGB": style.get("fill_color", [128, 128, 128]) + [100]
        }
        renderer.symbol.outlineColor = {
            "RGB": style.get("outline_color", [0, 0, 0]) + [100]
        }
        layer.symbology = sym
    print(f"[arcpy] Applied style: {style_name}")

    # ── Export layout ─────────────────────────────────────────────────────────
    layout = aprx.listLayouts()[0] if aprx.listLayouts() else None
    if layout is None:
        # No layout — export map frame directly
        m.defaultView.exportToPNG(str(output), resolution=150)
    else:
        if fmt.lower() == "pdf":
            layout.exportToPDF(str(output))
        else:
            layout.exportToPNG(str(output), resolution=150)

    print(f"[arcpy] Exported map to: {output}")
    return {"output": str(output), "engine": "arcpy", "style": style_name}


def run_simulation_task(input_path: str, style_name: str, output_path: str, fmt: str = "png") -> dict:
    """
    Simulate ArcPy map export using geopandas + matplotlib.
    Produces the same output structure without an ArcGIS Pro license.
    """
    try:
        import geopandas as gpd
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError as e:
        raise ImportError(
            f"Simulation mode requires: pip install geopandas matplotlib shapely fiona\n{e}"
        )

    style = load_style(style_name)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    gdf = gpd.read_file(input_path)
    print(f"[sim] Loaded {len(gdf)} features from {input_path}")

    # ── Build matplotlib color args ───────────────────────────────────────────
    fill = style.get("fill_color")
    if fill:
        facecolor = [c / 255.0 for c in fill] + [0.7]
    else:
        facecolor = "none"

    edge = style.get("outline_color", [0, 0, 0])
    edgecolor = [c / 255.0 for c in edge]
    linewidth = style.get("outline_width", 0.5)

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    gdf.plot(ax=ax, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth)

    ax.set_title(f"arcgis-map-tasks — {Path(input_path).stem} ({style_name})", pad=12)
    ax.set_axis_off()

    # Legend
    patch = mpatches.Patch(facecolor=facecolor if fill else "white",
                            edgecolor=edgecolor, label=style_name)
    ax.legend(handles=[patch], loc="lower right")

    # ── Save ──────────────────────────────────────────────────────────────────
    if fmt.lower() == "pdf":
        fig.savefig(str(output), format="pdf", bbox_inches="tight", dpi=150)
    else:
        fig.savefig(str(output), format="png", bbox_inches="tight", dpi=150)

    plt.close(fig)
    print(f"[sim] Exported map to: {output}")
    return {"output": str(output), "engine": "simulation", "style": style_name}


def queue_task(input_path: str, style_name: str, output_path: str, fmt: str = "png") -> dict:
    """Add task to the JSON queue for background processing."""
    from task_queue import TaskQueue
    q = TaskQueue()
    task_id = q.enqueue(input_path, style_name, output_path, fmt)
    print(f"[queue] Task queued: {task_id}")
    return {"task_id": task_id, "status": "queued"}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="arcgis-map-tasks — ArcGIS Pro automation prototype"
    )
    parser.add_argument("--input",  required=True,  help="Path to input shapefile or GeoJSON")
    parser.add_argument("--style",  required=True,  help="Style preset name (blue_fill, red_fill, ...)")
    parser.add_argument("--output", required=True,  help="Output file path (.png or .pdf)")
    parser.add_argument("--format", default="png",  choices=["png", "pdf"], help="Output format")
    parser.add_argument("--queue",  action="store_true", help="Queue task instead of running immediately")
    parser.add_argument("--sim",    action="store_true", help="Force simulation mode (skip ArcPy)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"[error] Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.queue:
        result = queue_task(args.input, args.style, args.output, args.format)
    elif ARCPY_AVAILABLE and not args.sim:
        result = run_arcpy_task(args.input, args.style, args.output, args.format)
    else:
        result = run_simulation_task(args.input, args.style, args.output, args.format)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

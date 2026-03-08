#!/usr/bin/env python3
"""
arc_task_sim.py — Simulation Mode (no ArcGIS Pro required)

Demonstrates the same interface as arc_task.py using open-source tools.
Useful for development, testing, and cross-platform use (macOS/Linux).

Dependencies: geopandas, matplotlib, shapely, fiona
    pip install geopandas matplotlib shapely fiona

Usage:
    python arc_task_sim.py --input data/sample.geojson --style blue_fill --output output/map.png
    python arc_task_sim.py --input data/sample.geojson --style red_fill --output output/map.pdf --format pdf
"""

import argparse
import json
import sys
from pathlib import Path


STYLES = {
    "blue_fill":    {"fill_color": [0, 112, 255],  "outline_color": [0, 0, 0],  "outline_width": 0.5},
    "red_fill":     {"fill_color": [255, 0, 0],    "outline_color": [80, 0, 0], "outline_width": 0.5},
    "outline_only": {"fill_color": None,            "outline_color": [0, 0, 0],  "outline_width": 1.0},
    "heat_map":     {"fill_color": [255, 165, 0],  "outline_color": [0, 0, 0],  "outline_width": 0.3},
}


def run(input_path: str, style_name: str, output_path: str, fmt: str = "png") -> dict:
    try:
        import geopandas as gpd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("[error] Install dependencies: pip install geopandas matplotlib shapely fiona", file=sys.stderr)
        sys.exit(1)

    # Load style
    style_file = Path(__file__).parent / "styles" / f"{style_name}.json"
    if style_file.exists():
        style = json.loads(style_file.read_text())
    elif style_name in STYLES:
        style = STYLES[style_name]
    else:
        print(f"[error] Unknown style: '{style_name}'. Options: {list(STYLES)}", file=sys.stderr)
        sys.exit(1)

    # Load data
    if not Path(input_path).exists():
        print(f"[error] Input not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    gdf = gpd.read_file(input_path)
    print(f"[sim] Loaded {len(gdf)} features | CRS: {gdf.crs}")

    # Colors
    fill = style.get("fill_color")
    facecolor = [c / 255.0 for c in fill] + [0.7] if fill else "none"
    edge = style.get("outline_color", [0, 0, 0])
    edgecolor = [c / 255.0 for c in edge]
    linewidth = style.get("outline_width", 0.5)

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(11, 8.5))
    gdf.plot(ax=ax, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth)

    # Title and legend
    stem = Path(input_path).stem
    ax.set_title(
        f"arcgis-map-tasks (sim) — {stem}\nStyle: {style_name}",
        fontsize=13, pad=14
    )
    ax.set_xlabel("Longitude" if gdf.crs and gdf.crs.is_geographic else "X")
    ax.set_ylabel("Latitude" if gdf.crs and gdf.crs.is_geographic else "Y")

    legend_patch = mpatches.Patch(
        facecolor=facecolor if fill else "white",
        edgecolor=edgecolor,
        linewidth=linewidth,
        label=style_name
    )
    ax.legend(handles=[legend_patch], loc="lower right", fontsize=9)
    fig.tight_layout()

    # Export
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output), format=fmt.lower(), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[sim] ✅ Exported: {output.resolve()}")

    return {
        "output":  str(output.resolve()),
        "engine":  "simulation (geopandas/matplotlib)",
        "style":   style_name,
        "features": len(gdf),
    }


def main():
    parser = argparse.ArgumentParser(
        description="arc_task_sim — ArcGIS Pro automation demo (no license required)"
    )
    parser.add_argument("--input",  required=True,  help="Shapefile or GeoJSON input path")
    parser.add_argument("--style",  required=True,  help="Style name: " + ", ".join(STYLES))
    parser.add_argument("--output", required=True,  help="Output path (.png or .pdf)")
    parser.add_argument("--format", default="png",  choices=["png", "pdf"])
    args = parser.parse_args()

    result = run(args.input, args.style, args.output, args.format)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

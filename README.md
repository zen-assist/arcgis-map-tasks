# arcgis-map-tasks

A prototype CLI tool for automating ArcGIS Pro map generation tasks using ArcPy — the ESRI counterpart to [qgis-map-tasks](https://github.com/zen-assist/qgis-map-tasks).

---

## Architecture Overview

```
┌────────────────────────────────────────────┐
│              CLI Interface                 │
│        arc_task.py --input ... --output    │
└────────────────────┬───────────────────────┘
                     │
              ┌──────▼──────┐
              │  Task Queue  │  (JSON file / SQLite)
              │  tasks.json  │
              └──────┬───────┘
                     │
         ┌───────────▼────────────┐
         │   ArcPy Worker Process  │
         │  (ArcGIS Pro conda env) │
         └───────────┬────────────┘
                     │
        ┌────────────▼───────────┐
        │    arcpy.mp Module      │
        │  (ArcGIS Mapping API)   │
        └────────────┬────────────┘
                     │
          ┌──────────▼─────────┐
          │  Output: PNG / PDF  │
          └────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| CLI entry point | `arc_task.py` | Submit and run mapping tasks |
| Task queue | `task_queue.py` | Manage job queue (JSON/SQLite) |
| Map renderer | `arc_renderer.py` | Core ArcPy rendering logic |
| Style presets | `styles/` | Predefined symbology configs |
| Sample data | `data/` | Example shapefiles/GeoJSON |

---

## How ArcPy Automation Works (vs PyQGIS)

### ArcPy

ArcPy is ESRI's Python library bundled with ArcGIS Pro. Key characteristics:

- **Environment**: Runs inside ArcGIS Pro's bundled **conda** environment (`arcgispro-py3`)
- **Invocation**: Must be called via the ArcGIS Pro Python interpreter, not system Python
- **Modules**: 
  - `arcpy` — geoprocessing tools
  - `arcpy.mp` — mapping and layout automation (the primary module for our use case)
  - `arcpy.da` — data access (cursors, feature classes)
  - `arcpy.sharing` — web map publishing

### PyQGIS (QGIS)

- **Environment**: System Python or QGIS's bundled Python
- **Invocation**: `qgis_process` CLI or PyQGIS standalone script
- **API**: `qgis.core`, `qgis.analysis`
- **License**: Open source (GPL)

### Key Differences

| Aspect | ArcGIS Pro / ArcPy | QGIS / PyQGIS |
|--------|---------------------|----------------|
| **License** | Commercial (~$1,500/yr) | Free & open source |
| **Python env** | ArcGIS conda (`arcgispro-py3`) | System Python or QGIS Python |
| **Headless** | Background geoprocessing (limited) | Full headless via `qgis_process` |
| **Mapping API** | `arcpy.mp` | `qgis.core.QgsLayoutExporter` |
| **Data formats** | ESRI formats + OGC | Full OGC + ESRI |
| **Conda** | Required (managed by ESRI) | Optional |
| **CLI** | No native CLI (script-based) | `qgis_process` CLI |

### Headless Execution

ArcGIS Pro supports "background geoprocessing" but does **not** fully support headless rendering (exporting maps without a UI) on all platforms. The workaround:

1. Use `arcpy.mp` to load `.aprx` project files programmatically
2. Export layouts via `layout.exportToPNG()` / `layout.exportToPDF()`
3. Run the script via the ArcGIS Pro Python interpreter in the background

**Windows only**: ArcGIS Pro is Windows-only software. The Python environment and ArcPy cannot be installed on macOS or Linux.

---

## Licensing Considerations

| Requirement | Details |
|-------------|---------|
| **ArcGIS Pro license** | Required. ~$1,500/yr (Named User or Single Use) |
| **License type** | Named User (Esri cloud auth) or concurrent |
| **Offline use** | Requires license borrowing from ArcGIS License Manager |
| **Python only** | ArcPy requires a licensed ArcGIS Pro installation — no standalone pip install |
| **Platform** | **Windows only** (ArcGIS Pro does not run on macOS/Linux) |
| **Alternative** | ArcGIS API for Python (`arcgis` package) — works on all platforms, cloud-based, free tier available |

> ⚠️ **Important**: Unlike QGIS/PyQGIS which can be installed freely, ArcPy requires a paid ArcGIS Pro license and is Windows-only. For cross-platform automation, consider the [ArcGIS API for Python](https://developers.arcgis.com/python/) instead.

---

## Proposed Task Queue Design

```
tasks.json (or SQLite tasks.db)
{
  "queue": [
    {
      "id": "uuid",
      "status": "pending|running|done|failed",
      "input": "data/parcels.shp",
      "style": "blue_fill",
      "output": "output/map.png",
      "created_at": "2026-03-08T14:00:00Z",
      "completed_at": null,
      "error": null
    }
  ]
}
```

**Worker loop**:
1. Poll queue for `pending` tasks
2. Mark task as `running`
3. Load `.aprx` template or create programmatically
4. Add data layer, apply symbology
5. Export to output path
6. Mark `done` or `failed` with error message

---

## Usage

> ⚠️ Requires ArcGIS Pro installed on Windows with valid license. For simulation/demo on other platforms, see `arc_task_sim.py`.

### Run a task

```bash
# Windows (ArcGIS Pro Python)
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" arc_task.py \
  --input data/parcels.shp \
  --style blue_fill \
  --output output/map.png

# Or via the queue
python arc_queue_worker.py &
python arc_task.py --input data/parcels.shp --style blue_fill --output output/map.png --queue
```

### Styles available

| Style name | Description |
|------------|-------------|
| `blue_fill` | Solid blue fill, dark outline |
| `red_fill` | Solid red fill |
| `heat_map` | Graduated colors by attribute |
| `outline_only` | No fill, black outline |

---

## Setup

### ArcGIS Pro Environment (Windows)

```bash
# Activate ArcGIS Pro conda env
conda activate arcgispro-py3

# ArcPy is pre-installed — no pip install needed
python -c "import arcpy; print(arcpy.GetInstallInfo()['Version'])"
```

### Simulation Mode (macOS/Linux)

```bash
# Install simulation dependencies
pip install geopandas matplotlib shapely fiona

# Run in simulation mode (no ArcGIS Pro required)
python arc_task_sim.py --input data/sample.geojson --style blue_fill --output output/map.png
```

---

## Files

```
arcgis-map-tasks/
├── README.md                 # This file
├── arc_task.py               # CLI entry point (ArcPy / real)
├── arc_task_sim.py           # Simulation mode (geopandas/matplotlib)
├── arc_renderer.py           # Core ArcPy rendering logic
├── task_queue.py             # Task queue manager
├── arc_queue_worker.py       # Background worker
├── styles/
│   ├── blue_fill.json        # Style definition
│   └── red_fill.json
├── data/
│   └── sample.geojson        # Sample data for testing
└── output/                   # Map exports (gitignored)
```

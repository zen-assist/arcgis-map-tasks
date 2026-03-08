"""
arc_renderer.py — Core ArcPy rendering logic

Provides a clean interface for ArcGIS Pro map generation tasks.
Handles project management, layer loading, symbology, and export.

ArcPy Reference:
  arcpy.mp.ArcGISProject  — manage .aprx project files
  arcpy.mp.Layer          — add/remove/configure map layers
  layout.exportToPNG()    — export to raster
  layout.exportToPDF()    — export to vector PDF
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class ArcMapRenderer:
    """
    Renders map tasks using arcpy.mp (ArcGIS Pro Mapping module).

    Workflow:
        renderer = ArcMapRenderer("template.aprx")
        renderer.load_data("parcels.shp")
        renderer.apply_style("blue_fill")
        renderer.export("output/map.png", fmt="png")
        renderer.close()
    """

    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize with an optional .aprx project file.
        
        Args:
            project_path: Path to existing .aprx, or None to use "CURRENT"
                          (only valid when running inside ArcGIS Pro).
        """
        try:
            import arcpy
            from arcpy import mp as arcpy_mp
            self._arcpy = arcpy
            self._mp = arcpy_mp
        except ImportError:
            raise EnvironmentError(
                "ArcPy is not available. Ensure ArcGIS Pro is installed and "
                "you are using the ArcGIS Pro conda Python environment.\n"
                "Expected: C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe"
            )

        if project_path and Path(project_path).exists():
            self._aprx = arcpy_mp.ArcGISProject(str(project_path))
            logger.info(f"Opened project: {project_path}")
        else:
            self._aprx = arcpy_mp.ArcGISProject("CURRENT")
            logger.info("Using current ArcGIS Pro project")

        self._map = self._aprx.listMaps()[0]
        self._layer = None

    def load_data(self, input_path: str) -> "ArcMapRenderer":
        """
        Load a data source (shapefile, GeoJSON, File Geodatabase, feature class).
        
        Args:
            input_path: Path to the data source.
        
        Returns:
            self (for chaining)
        """
        resolved = str(Path(input_path).resolve())
        self._layer = self._map.addDataFromPath(resolved)
        logger.info(f"Loaded layer: {self._layer.name} from {resolved}")
        return self

    def apply_style(self, style_name: str, style_config: Optional[dict] = None) -> "ArcMapRenderer":
        """
        Apply symbology to the loaded layer.
        
        Args:
            style_name: Name of the style preset.
            style_config: Optional override dict with keys:
                          fill_color, outline_color, outline_width
        
        Returns:
            self (for chaining)
        """
        if self._layer is None:
            raise RuntimeError("No layer loaded. Call load_data() first.")

        config = style_config or self._load_style_config(style_name)
        sym = self._layer.symbology

        if not hasattr(sym, "renderer"):
            logger.warning("Layer does not support symbology renderer modification")
            return self

        renderer = sym.renderer

        # Apply fill color
        fill = config.get("fill_color")
        if fill:
            renderer.symbol.color = {"RGB": fill + [100]}

        # Apply outline
        outline = config.get("outline_color", [0, 0, 0])
        renderer.symbol.outlineColor = {"RGB": outline + [100]}
        renderer.symbol.outlineWidth = config.get("outline_width", 0.5)

        self._layer.symbology = sym
        logger.info(f"Applied style: {style_name}")
        return self

    def export(self, output_path: str, fmt: str = "png", resolution: int = 150) -> str:
        """
        Export the map to an image or PDF.
        
        Args:
            output_path: Destination file path.
            fmt: 'png' or 'pdf'
            resolution: DPI for raster exports (default 150).
        
        Returns:
            Absolute path to the exported file.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        layouts = self._aprx.listLayouts()
        if layouts:
            layout = layouts[0]
            if fmt.lower() == "pdf":
                layout.exportToPDF(str(output))
            else:
                layout.exportToPNG(str(output), resolution=resolution)
        else:
            # No layout — export directly from the map view
            logger.warning("No layout found; exporting from default map view")
            if fmt.lower() == "pdf":
                self._map.defaultView.exportToPDF(str(output))
            else:
                self._map.defaultView.exportToPNG(str(output), resolution=resolution)

        logger.info(f"Exported: {output.resolve()}")
        return str(output.resolve())

    def close(self):
        """Release the project reference."""
        del self._aprx
        self._aprx = None
        logger.info("Project closed")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _load_style_config(style_name: str) -> dict:
        style_file = Path(__file__).parent / "styles" / f"{style_name}.json"
        if style_file.exists():
            with open(style_file) as f:
                return json.load(f)
        # Inline defaults
        defaults = {
            "blue_fill":    {"fill_color": [0, 112, 255],  "outline_color": [0, 0, 0],    "outline_width": 0.5},
            "red_fill":     {"fill_color": [255, 0, 0],    "outline_color": [80, 0, 0],   "outline_width": 0.5},
            "outline_only": {"fill_color": None,            "outline_color": [0, 0, 0],    "outline_width": 1.0},
        }
        if style_name not in defaults:
            raise ValueError(f"Unknown style: '{style_name}'. Known: {list(defaults)}")
        return defaults[style_name]


# ── ArcGIS API for Python (cross-platform alternative) ───────────────────────

class AGOLRenderer:
    """
    Cross-platform alternative using the ArcGIS API for Python.
    Works on macOS/Linux without ArcGIS Pro.
    Requires: pip install arcgis

    Uses ArcGIS Online or ArcGIS Enterprise for rendering.
    """

    def __init__(self, username: str, password: str, url: str = "https://www.arcgis.com"):
        try:
            from arcgis.gis import GIS
            from arcgis.mapping import WebMap
        except ImportError:
            raise EnvironmentError("Install ArcGIS API: pip install arcgis")

        from arcgis.gis import GIS
        self._gis = GIS(url, username, password)
        logger.info(f"Connected to ArcGIS Online as: {self._gis.users.me.username}")

    def publish_and_export(self, input_path: str, output_path: str) -> str:
        """Publish data to AGOL and export a static map."""
        # Implementation would involve:
        # 1. Upload shapefile/GeoJSON as hosted feature layer
        # 2. Create a WebMap with the layer
        # 3. Export via arcgis.mapping or print service
        raise NotImplementedError("AGOL publishing not yet implemented in prototype")

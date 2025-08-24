"""
UI Extractor for Power BI Files

Extracts user interface components including pages, visualizations, bookmarks, and layout information.
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


class UIExtractor:
    """
    Extracts UI structure from PBIX files.

    This class handles extraction of:
    - Report pages and their properties
    - Visualizations and their configurations
    - Custom visuals
    - Bookmarks and navigation
    - Page layouts and themes
    """

    # Visual type mapping for better readability
    VISUAL_TYPE_MAP = {
        "actionButton": "Action Button",
        "card": "Card",
        "columnChart": "Column Chart",
        "barChart": "Bar Chart",
        "lineChart": "Line Chart",
        "areaChart": "Area Chart",
        "pieChart": "Pie Chart",
        "donutChart": "Donut Chart",
        "tableEx": "Table",
        "matrix": "Matrix",
        "slicer": "Slicer",
        "gauge": "Gauge",
        "scatterChart": "Scatter Chart",
        "map": "Map",
        "filledMap": "Filled Map",
        "treemap": "Treemap",
        "waterfallChart": "Waterfall Chart",
        "funnelChart": "Funnel Chart",
        "textbox": "Text Box",
        "shape": "Shape",
        "image": "Image",
        "decompositionTreeVisual": "Decomposition Tree",
        "keyDriversVisual": "Key Influencers",
        "qnaVisual": "Q&A Visual",
        "esriVisual": "ArcGIS Map",
    }

    def __init__(self, pbix_path: Path):
        """
        Initialize the UI extractor.

        Args:
            pbix_path: Path to the PBIX file
        """
        self.pbix_path = Path(pbix_path)
        self.logger = logging.getLogger(f"{__name__}.{self.pbix_path.stem}")

    def extract_ui_structure(self) -> Dict[str, Any]:
        """
        Extract complete UI structure from PBIX file.

        Returns:
            Dictionary containing pages, visualizations, and UI metadata
        """
        self.logger.info("Starting UI structure extraction")

        ui_data = {
            "pages": [],
            "visualizations": [],
            "visual_summary": {},
            "custom_visuals": [],
            "bookmarks": [],
            "themes": {},
            "raw_layouts": {},
            "extraction_info": {
                "method": "Direct PBIX parsing",
                "extracted_files": [],
                "total_pages": 0,
                "total_visuals": 0,
            },
        }

        try:
            with zipfile.ZipFile(self.pbix_path, "r") as pbix_zip:
                file_list = pbix_zip.namelist()

                # Extract Layout files (contains report structure)
                layout_files = [f for f in file_list if "Layout" in f]

                for layout_file in layout_files:
                    ui_data["extraction_info"]["extracted_files"].append(layout_file)
                    layout_data = self._extract_layout_file(pbix_zip, layout_file)

                    if layout_data:
                        ui_data["raw_layouts"][layout_file] = layout_data

                        # Parse pages and visualizations
                        pages = self._parse_report_pages(layout_data)
                        ui_data["pages"].extend(pages)

                        visuals = self._parse_visualizations(layout_data)
                        ui_data["visualizations"].extend(visuals)

                # Extract custom visual information
                visual_files = [
                    f for f in file_list if "CustomVisuals" in f and f.endswith(".json")
                ]
                for visual_file in visual_files:
                    custom_visual = self._extract_custom_visual(pbix_zip, visual_file)
                    if custom_visual:
                        ui_data["custom_visuals"].append(custom_visual)

                # Extract themes if present
                theme_files = [f for f in file_list if "Theme" in f and f.endswith(".json")]
                for theme_file in theme_files:
                    theme_data = self._extract_theme_file(pbix_zip, theme_file)
                    if theme_data:
                        ui_data["themes"][theme_file] = theme_data

            # Create visual type summary
            visual_types = {}
            for visual in ui_data["visualizations"]:
                vtype = visual.get("enhanced_type", visual.get("type", "unknown"))
                visual_types[vtype] = visual_types.get(vtype, 0) + 1
            ui_data["visual_summary"] = visual_types

            # Update extraction info
            ui_data["extraction_info"]["total_pages"] = len(ui_data["pages"])
            ui_data["extraction_info"]["total_visuals"] = len(ui_data["visualizations"])

            self.logger.info(
                f"UI structure extraction complete: {ui_data['extraction_info']['total_pages']} pages, {ui_data['extraction_info']['total_visuals']} visuals"
            )
            return ui_data

        except Exception as e:
            self.logger.error(f"UI structure extraction failed: {e}")
            ui_data["error"] = str(e)
            return ui_data

    def _extract_layout_file(self, pbix_zip: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """Extract and parse layout JSON file."""
        try:
            with pbix_zip.open(file_path) as file:
                content = file.read()

                # Try different encodings
                for encoding in ["utf-16le", "utf-8", "utf-16"]:
                    try:
                        text_content = content.decode(encoding)
                        if text_content.strip():
                            return json.loads(text_content)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
        except Exception as e:
            self.logger.warning(f"Could not extract layout file {file_path}: {e}")

        return None

    def _parse_report_pages(self, layout_data: Dict) -> List[Dict[str, Any]]:
        """Parse report pages from layout data."""
        pages = []

        def find_pages(data, path=""):
            if isinstance(data, dict):
                # Look for sections which typically contain pages
                if "sections" in data and isinstance(data["sections"], list):
                    for i, section in enumerate(data["sections"]):
                        page = self._parse_single_page(section, i)
                        if page:
                            pages.append(page)

                # Also check for direct page data
                if self._is_page_like(data):
                    page = self._parse_single_page(data)
                    if page:
                        pages.append(page)

                # Recurse through nested structures
                for key, value in data.items():
                    if key not in ["sections"]:  # Avoid double processing
                        find_pages(value, f"{path}.{key}" if path else key)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_pages(item, f"{path}[{i}]")

        find_pages(layout_data)
        return pages

    def _is_page_like(self, data: Dict) -> bool:
        """Check if data looks like a page definition."""
        page_indicators = ["name", "ordinal", "width", "height", "visualContainers"]
        return isinstance(data, dict) and any(key in data for key in page_indicators)

    def _parse_single_page(
        self, page_data: Dict, ordinal: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse a single report page."""
        if not isinstance(page_data, dict):
            return None

        # Extract page name
        page_name = page_data.get(
            "name",
            f"Page_{ordinal if ordinal is not None else page_data.get('ordinal', 'Unknown')}",
        )
        display_name = page_data.get("displayName", self._clean_page_name(page_name))

        page_info = {
            "name": page_name,
            "display_name": display_name,
            "ordinal": ordinal if ordinal is not None else page_data.get("ordinal", 0),
            "width": page_data.get("width", 1280),
            "height": page_data.get("height", 720),
            "visual_count": 0,
            "background": page_data.get("background", {}),
            "filters": page_data.get("filters", []),
            "visibility": page_data.get("visibility", "Visible"),
            "raw_data": page_data,
        }

        # Count visualizations
        visual_containers = page_data.get("visualContainers", [])
        if isinstance(visual_containers, list):
            page_info["visual_count"] = len(visual_containers)

        return page_info

    def _parse_visualizations(self, layout_data: Dict) -> List[Dict[str, Any]]:
        """Parse visualizations from layout data."""
        visuals = []

        def find_visuals(data, path="", page_context=None):
            if isinstance(data, dict):
                # Look for visual containers
                if "visualContainers" in data and isinstance(data["visualContainers"], list):
                    for visual in data["visualContainers"]:
                        parsed_visual = self._parse_single_visual(visual, path, page_context)
                        if parsed_visual:
                            visuals.append(parsed_visual)

                # Look for direct visual configuration
                if "config" in data and isinstance(data.get("config"), str):
                    parsed_visual = self._parse_single_visual(data, path, page_context)
                    if parsed_visual:
                        visuals.append(parsed_visual)

                # Update page context if we find page info
                if self._is_page_like(data):
                    page_context = data.get("name", page_context)

                # Recurse through nested structures
                for key, value in data.items():
                    if key not in ["visualContainers"]:  # Avoid double processing
                        find_visuals(value, f"{path}.{key}" if path else key, page_context)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_visuals(item, f"{path}[{i}]", page_context)

        find_visuals(layout_data)
        return visuals

    def _parse_single_visual(
        self, visual_data: Dict, path: str, page_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse a single visualization."""
        if not isinstance(visual_data, dict):
            return None

        try:
            # Extract basic position and size
            position_info = {
                "x": round(visual_data.get("x", 0), 1),
                "y": round(visual_data.get("y", 0), 1),
                "width": round(visual_data.get("width", 0), 1),
                "height": round(visual_data.get("height", 0), 1),
                "z_order": visual_data.get("z", visual_data.get("zOrder", 0)),
            }

            # Parse configuration
            config_str = visual_data.get("config", "{}")
            visual_type = "unknown"
            text_content = None
            data_roles_count = 0
            bookmark_action = None

            try:
                if isinstance(config_str, str) and config_str.strip():
                    config = json.loads(config_str)

                    # Extract visual type
                    if "singleVisual" in config:
                        single_visual = config["singleVisual"]
                        visual_type = single_visual.get("visualType", "unknown")

                        # Extract data roles count
                        if "projections" in single_visual:
                            projections = single_visual["projections"]
                            data_roles_count = sum(
                                len(v) for v in projections.values() if isinstance(v, list)
                            )

                        # Extract text content
                        if "objects" in single_visual:
                            text_content = self._extract_text_from_objects(single_visual["objects"])

                    # Extract bookmark actions
                    if "vcObjects" in config.get("singleVisual", {}):
                        vc_objects = config["singleVisual"]["vcObjects"]
                        bookmark_action = self._extract_bookmark_action(vc_objects)

            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Could not parse visual config: {e}")

            # Get human-readable visual type
            enhanced_type = self.VISUAL_TYPE_MAP.get(
                visual_type, visual_type.title() if visual_type else "Unknown"
            )

            return {
                "id": visual_data.get("id"),
                "type": visual_type,
                "enhanced_type": enhanced_type,
                "page_context": page_context,
                "position": position_info,
                "text_content": text_content,
                "data_roles_count": data_roles_count,
                "bookmark_action": bookmark_action,
                "config_size": len(config_str),
                "path": path,
                "raw_config": config if "config" in locals() else {},
            }

        except Exception as e:
            self.logger.warning(f"Could not parse visual: {e}")
            return None

    def _extract_text_from_objects(self, objects: Dict) -> Optional[str]:
        """Extract text content from visual objects."""
        try:
            if "text" in objects:
                for text_config in objects["text"]:
                    if "properties" in text_config and "text" in text_config["properties"]:
                        text_expr = text_config["properties"]["text"]
                        if "expr" in text_expr and "Literal" in text_expr["expr"]:
                            return text_expr["expr"]["Literal"]["Value"].strip("'")
        except Exception:
            pass
        return None

    def _extract_bookmark_action(self, vc_objects: Dict) -> Optional[str]:
        """Extract bookmark action information."""
        try:
            if "visualLink" in vc_objects:
                for link_config in vc_objects["visualLink"]:
                    if "properties" in link_config:
                        props = link_config["properties"]
                        if "bookmark" in props and "expr" in props["bookmark"]:
                            return props["bookmark"]["expr"]["Literal"]["Value"].strip("'")
        except Exception:
            pass
        return None

    def _clean_page_name(self, name: str) -> str:
        """Convert technical page names to more readable format."""
        if name.startswith("ReportSection"):
            if len(name) > 20:  # Likely a UUID-style name
                return f"Page {name[-4:]}"
            else:
                return name.replace("ReportSection", "Page ")
        return name

    def _extract_custom_visual(
        self, pbix_zip: zipfile.ZipFile, visual_file: str
    ) -> Optional[Dict[str, Any]]:
        """Extract custom visual information."""
        try:
            with pbix_zip.open(visual_file) as f:
                content = f.read().decode("utf-8")
                visual_data = json.loads(content)

                return {
                    "file": visual_file,
                    "name": visual_data.get("name", "Unknown"),
                    "version": visual_data.get("version", "Unknown"),
                    "description": visual_data.get("description", ""),
                    "config": visual_data,
                }
        except Exception as e:
            self.logger.warning(f"Could not parse custom visual {visual_file}: {e}")
            return {"file": visual_file, "error": str(e)}

    def _extract_theme_file(self, pbix_zip: zipfile.ZipFile, theme_file: str) -> Optional[Dict]:
        """Extract theme information."""
        try:
            with pbix_zip.open(theme_file) as f:
                content = f.read().decode("utf-8")
                return json.loads(content)
        except Exception as e:
            self.logger.warning(f"Could not parse theme file {theme_file}: {e}")
            return None

    def get_ui_summary(self) -> Dict[str, Any]:
        """Get a quick summary of UI components."""
        try:
            ui_data = self.extract_ui_structure()

            return {
                "total_pages": len(ui_data.get("pages", [])),
                "total_visuals": len(ui_data.get("visualizations", [])),
                "visual_types": ui_data.get("visual_summary", {}),
                "custom_visuals": len(ui_data.get("custom_visuals", [])),
                "has_themes": len(ui_data.get("themes", {})) > 0,
            }
        except Exception as e:
            self.logger.error(f"Could not get UI summary: {e}")
            return {"error": str(e)}

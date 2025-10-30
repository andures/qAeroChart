# -*- coding: utf-8 -*-
"""
LayerManager - Manages memory layers for aeronautical profile charts

This module handles the creation, configuration, and management of memory layers
used for ICAO aeronautical profile charts. It creates 5 specialized layers following
ICAO Annex 14 and Doc 8697 standards.

v2.0: Integrated with ProfileChartGeometry for cartesian calculations.
"""

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsProject,
    QgsLayerTreeGroup,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    Qgis
)

from .profile_chart_geometry import ProfileChartGeometry


class LayerManager:
    """
    Manager for creating and handling aeronautical profile chart layers.
    
    Creates and manages 5 memory layers:
    1. profile_point_symbol - Point symbols for profile points (MAPt, FAF, IF, etc.)
    2. profile_carto_label - Cartographic labels for profile points
    3. profile_line - Profile line connecting points
    4. profile_dist - Distance markers and annotations
    5. profile_MOCA - Minimum Obstacle Clearance Altitude indicators
    
    All layers are organized under a "MAP 03 - Profile" group in the layer tree.
    """
    
    # Layer names constants
    LAYER_POINT_SYMBOL = "profile_point_symbol"
    LAYER_CARTO_LABEL = "profile_carto_label"
    LAYER_LINE = "profile_line"
    LAYER_LINE_FINAL = "profile_line_final"
    LAYER_LINE_RUNWAY = "profile_line_runway"
    LAYER_DIST = "profile_dist"
    LAYER_MOCA = "profile_MOCA"
    LAYER_BASELINE = "profile_baseline"
    LAYER_GRID = "profile_grid"
    LAYER_KEY_VLINES = "profile_key_verticals"
    
    # Group name
    GROUP_NAME = "MAP 03 - Profile"
    
    def __init__(self, iface, crs=None):
        """
        Initialize the LayerManager.
        
        Args:
            iface (QgisInterface): The QGIS interface object
            crs (QgsCoordinateReferenceSystem): CRS for layers (default: project CRS)
        """
        self.iface = iface
        self.project = QgsProject.instance()
        
        # Use project CRS if not specified
        if crs is None:
            self.crs = self.project.crs()
        else:
            self.crs = crs
        
        # Debug flag (can be overridden by config in create_all_layers)
        self.debug = True

        # Dictionary to store created layers
        self.layers = {}
        
        # Group reference
        self.layer_group = None
        
        print(f"PLUGIN qAeroChart: LayerManager initialized with CRS: {self.crs.authid()}")

    # ------------- Internal helpers -------------
    def _log(self, message, level="INFO"):
        try:
            print(f"[qAeroChart][{level}] {message}")
        except Exception:
            # best-effort logging to avoid breaking flows
            pass

    def _dbg(self, message):
        if self.debug:
            self._log(message, level="DEBUG")

    def _crs_guard(self):
        """Warn if using a geographic CRS (degrees) which breaks metric profile drawing."""
        try:
            if self.crs.isGeographic():
                msg = (
                    f"Project CRS {self.crs.authid()} is geographic (degrees). "
                    "Use a projected CRS (meters) for correct distances/altitudes."
                )
                self._log(msg, level="WARN")
                try:
                    if self.iface:
                        self.iface.messageBar().pushMessage(
                            "qAeroChart", msg, level=Qgis.Warning, duration=6
                        )
                except Exception:
                    pass
        except Exception as e:
            self._log(f"CRS guard check failed: {e}", level="WARN")
    
    def create_all_layers(self, config=None):
        """
        Create all 5 profile chart layers and organize them in a group.
        
        Args:
            config (dict): Optional configuration with style parameters
        
        Returns:
            dict: Dictionary with layer names as keys and QgsVectorLayer objects as values
        """
        # Configure debug mode
        try:
            if config and isinstance(config, dict):
                self.debug = bool(config.get('debug', True))
        except Exception:
            pass

        self._dbg("Starting create_all_layers()")
        print("PLUGIN qAeroChart: Creating all profile layers...")
        self._crs_guard()
        
        # Create group first
        self._create_layer_group()
        
        # Create each layer
        self.layers[self.LAYER_POINT_SYMBOL] = self._create_point_symbol_layer()
        self.layers[self.LAYER_CARTO_LABEL] = self._create_carto_label_layer()
        self.layers[self.LAYER_LINE] = self._create_line_layer()
        # Additional simple line layers to guarantee visibility
        self.layers[self.LAYER_LINE_FINAL] = self._create_named_line_layer(self.LAYER_LINE_FINAL)
        self.layers[self.LAYER_LINE_RUNWAY] = self._create_named_line_layer(self.LAYER_LINE_RUNWAY)
        # New supportive layers: horizontal baseline and vertical grid
        self.layers[self.LAYER_BASELINE] = self._create_named_line_layer(self.LAYER_BASELINE)
        self.layers[self.LAYER_GRID] = self._create_dist_layer_for_grid()
        self.layers[self.LAYER_KEY_VLINES] = self._create_named_line_layer(self.LAYER_KEY_VLINES)
        self.layers[self.LAYER_DIST] = self._create_dist_layer()
        self.layers[self.LAYER_MOCA] = self._create_moca_layer()

        # Emit validity and field diagnostics
        for k, lyr in self.layers.items():
            try:
                self._dbg(f"Layer '{k}': valid={lyr.isValid()} CRS={lyr.crs().authid()} fields={[f.name() for f in lyr.fields()]}")
            except Exception as e:
                self._log(f"Diag failed for layer '{k}': {e}", level="WARN")
        
        # Add layers to group and apply styles
        self._add_layers_to_group(config)
        
        print(f"PLUGIN qAeroChart: Created {len(self.layers)} layers in group '{self.GROUP_NAME}'")
        self._dbg("Finished create_all_layers()")
        
        return self.layers
    
    def _create_layer_group(self):
        """Create or get the layer group for profile charts."""
        root = self.project.layerTreeRoot()
        
        # Check if group already exists
        existing_group = root.findGroup(self.GROUP_NAME)
        
        if existing_group:
            self.layer_group = existing_group
            print(f"PLUGIN qAeroChart: Using existing group '{self.GROUP_NAME}'")
        else:
            self.layer_group = root.addGroup(self.GROUP_NAME)
            print(f"PLUGIN qAeroChart: Created new group '{self.GROUP_NAME}'")
        try:
            self._dbg(f"Group '{self.GROUP_NAME}' child count: {len(self.layer_group.children())}")
        except Exception:
            pass

        # Try to move the group to the very top of the TOC so it always renders above the basemap
        try:
            parent = root
            children = list(parent.children())
            idx = children.index(self.layer_group) if self.layer_group in children else -1
            if idx > 0:
                node = parent.takeChild(idx)
                if node is not None:
                    parent.insertChildNode(0, node)
                    self._dbg("Moved group to the top of the layer tree")
        except Exception as e:
            self._log(f"Could not move group to top: {e}", level="WARN")
    
    def _create_point_symbol_layer(self):
        """
        Create the profile_point_symbol layer for point symbols.
        
        Fields:
        - point_name: Name/identifier (MAPt, FAF, IF, etc.)
        - point_type: Type of point (fix, navaid, threshold, etc.)
        - distance: Distance from reference point (NM)
        - elevation: Elevation above MSL (ft)
        - notes: Additional notes
        
        Returns:
            QgsVectorLayer: The created layer
        """
        # Create memory layer
        uri = f"Point?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, self.LAYER_POINT_SYMBOL, "memory")
        
        # Add fields
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("point_name", QVariant.String, len=50),
            QgsField("point_type", QVariant.String, len=30),
            QgsField("distance", QVariant.Double),
            QgsField("elevation", QVariant.Double),
            QgsField("notes", QVariant.String, len=255)
        ])
        layer.updateFields()
        
        print(f"PLUGIN qAeroChart: Created layer '{self.LAYER_POINT_SYMBOL}' with {layer.fields().count()} fields")
        
        return layer
    
    def _create_carto_label_layer(self):
        """
        Create the profile_carto_label layer for cartographic labels.
        
        Fields:
        - label_text: Text to display
        - label_type: Type of label (point_name, elevation, distance, etc.)
        - rotation: Text rotation angle
        - font_size: Font size
        
        Returns:
            QgsVectorLayer: The created layer
        """
        uri = f"Point?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, self.LAYER_CARTO_LABEL, "memory")
        
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("label_text", QVariant.String, len=100),
            QgsField("label_type", QVariant.String, len=30),
            QgsField("rotation", QVariant.Double),
            QgsField("font_size", QVariant.Int)
        ])
        layer.updateFields()
        
        print(f"PLUGIN qAeroChart: Created layer '{self.LAYER_CARTO_LABEL}' with {layer.fields().count()} fields")
        
        return layer
    
    def _create_line_layer(self):
        """
        Create the profile_line layer for the main profile line.
        
        Fields:
        - line_type: Type of line (profile, approach, etc.)
        - segment_name: Name of the segment
        - gradient: Gradient/slope of the segment
        
        Returns:
            QgsVectorLayer: The created layer
        """
        uri = f"LineString?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, self.LAYER_LINE, "memory")
        
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("line_type", QVariant.String, len=30),
            QgsField("segment_name", QVariant.String, len=50),
            QgsField("gradient", QVariant.Double)
        ])
        layer.updateFields()
        
        print(f"PLUGIN qAeroChart: Created layer '{self.LAYER_LINE}' with {layer.fields().count()} fields")
        
        return layer

    def _create_named_line_layer(self, name):
        """Create a generic line layer with standard fields using the given name."""
        uri = f"LineString?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("line_type", QVariant.String, len=30),
            QgsField("segment_name", QVariant.String, len=50),
            QgsField("gradient", QVariant.Double)
        ])
        layer.updateFields()
        return layer
    
    def _create_dist_layer(self):
        """
        Create the profile_dist layer for distance markers (tick lines).
        
        Notes:
        - Use LineString geometry so each marker is a small vertical segment (tick)
        - This makes the scale visually clear as en el gráfico 2D (distancia vs altitud)
        
        Fields:
        - distance: Distance value (NM)
        - from_point: Origin point name
        - marker_type: Type of marker (tick, label, etc.)
        
        Returns:
            QgsVectorLayer: The created layer
        """
        uri = f"LineString?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, self.LAYER_DIST, "memory")
        
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("distance", QVariant.Double),
            QgsField("from_point", QVariant.String, len=50),
            QgsField("marker_type", QVariant.String, len=30)
        ])
        layer.updateFields()
        
        print(f"PLUGIN qAeroChart: Created layer '{self.LAYER_DIST}' with {layer.fields().count()} fields (LineString)")
        
        return layer

    def _create_dist_layer_for_grid(self):
        """Create a LineString layer to hold full-height vertical gridlines."""
        uri = f"LineString?crs={self.crs.authid()}"
        layer = QgsVectorLayer(uri, self.LAYER_GRID, "memory")
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("distance", QVariant.Double),
            QgsField("marker_type", QVariant.String, len=30)
        ])
        layer.updateFields()
        return layer
    
    def _create_moca_layer(self):
        """
        Create the profile_MOCA layer for Minimum Obstacle Clearance Altitude.
        
        Uses Polygon geometry to display MOCA areas with diagonal hatching.
        
        Fields:
        - moca: MOCA value (ft)
        - segment_name: Associated segment
        - clearance: Clearance above obstacles (ft)
        
        Returns:
            QgsVectorLayer: The created layer
        """
        uri = f"Polygon?crs={self.crs.authid()}"  # Changed from LineString to Polygon
        layer = QgsVectorLayer(uri, self.LAYER_MOCA, "memory")
        
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("moca", QVariant.Double),
            QgsField("segment_name", QVariant.String, len=50),
            QgsField("clearance", QVariant.Double)
        ])
        layer.updateFields()
        
        print(f"PLUGIN qAeroChart: Created layer '{self.LAYER_MOCA}' with {layer.fields().count()} fields")
        
        return layer
    
    def _add_layers_to_group(self, config=None):
        """
        Add all created layers to the layer group and apply styles.
        
        Args:
            config (dict): Optional configuration with style parameters
        """
        if not self.layer_group:
            print("PLUGIN qAeroChart ERROR: Layer group not found")
            return
        
        # Add layers to project and group in specific order
        # Order layers so the profile line is above MOCA for visibility
        layer_order = [
            self.LAYER_CARTO_LABEL,
            self.LAYER_POINT_SYMBOL,
            self.LAYER_GRID,
            self.LAYER_BASELINE,
            self.LAYER_KEY_VLINES,
            self.LAYER_DIST,
            self.LAYER_LINE,
            self.LAYER_MOCA
        ]
        
        for layer_name in layer_order:
            if layer_name in self.layers:
                layer = self.layers[layer_name]
                # Add to project
                self.project.addMapLayer(layer, False)
                # Add to group
                self.layer_group.addLayer(layer)
                print(f"PLUGIN qAeroChart: Added '{layer_name}' to group")
                try:
                    self._dbg(f"  -> layer '{layer_name}' valid={layer.isValid()} count={layer.featureCount()} extent={[layer.extent().xMinimum(), layer.extent().yMinimum(), layer.extent().xMaximum(), layer.extent().yMaximum()]}")
                except Exception:
                    pass

        # Create a subgroup for simple line layers (final/runway) to mirror other plugins' structure
        simple_group = self.layer_group.addGroup("profile_line")
        for name in [self.LAYER_LINE_FINAL, self.LAYER_LINE_RUNWAY]:
            lyr = self.layers.get(name)
            if lyr:
                # add to project if not already
                if lyr not in self.project.mapLayers().values():
                    self.project.addMapLayer(lyr, False)
                simple_group.addLayer(lyr)
                print(f"PLUGIN qAeroChart: Added '{name}' into subgroup 'profile_line'")
                try:
                    self._dbg(f"  -> subgroup '{name}' valid={lyr.isValid()} count={lyr.featureCount()}")
                except Exception:
                    pass
        
        # Apply basic styles to make features visible
        self._apply_basic_styles(config)

        # Move group to the top again (after new nodes were inserted)
        try:
            self._create_layer_group()  # will reuse existing and perform the move-to-top safety
        except Exception:
            pass

        # Optionally promote render order so these layers are drawn above others
        try:
            root = self.project.layerTreeRoot()
            # Build preferred order: our layers first (leaves only), then the rest
            preferred = []
            for name in [self.LAYER_MOCA, self.LAYER_GRID, self.LAYER_BASELINE, self.LAYER_KEY_VLINES, self.LAYER_DIST, self.LAYER_LINE_RUNWAY, self.LAYER_LINE_FINAL, self.LAYER_LINE, self.LAYER_POINT_SYMBOL, self.LAYER_CARTO_LABEL]:
                lyr = self.layers.get(name)
                if lyr:
                    preferred.append(lyr)
            current = [l for l in self.project.mapLayers().values() if l not in preferred]
            new_order = preferred + current
            # Methods differ slightly across QGIS versions; try both styles
            try:
                root.setCustomLayerOrder(new_order)
                root.setHasCustomLayerOrder(True)
                self._dbg("Applied custom layer order: profile group on top")
            except Exception:
                try:
                    self.project.setCustomLayerOrder(new_order)
                    self.project.setTopologicalEditing(False)  # harmless no-op hint for some versions
                    self._dbg("Applied project custom layer order fallback")
                except Exception:
                    pass
        except Exception as e:
            self._log(f"Could not promote custom layer order: {e}", level="WARN")
    
    def _apply_basic_styles(self, config=None):
        """
        Apply basic symbology to layers to make them visible.
        
        Args:
            config (dict): Optional configuration with style parameters
        """
        from qgis.core import (
            QgsSymbol,
            QgsSimpleLineSymbolLayer,
            QgsSimpleMarkerSymbolLayer,
            QgsTextFormat,
            QgsPalLayerSettings,
            QgsVectorLayerSimpleLabeling,
            QgsUnitTypes,
            QgsLineSymbol,
            QgsSingleSymbolRenderer,
            QgsProperty,
            Qgis,
        )
        from qgis.PyQt.QtGui import QColor, QFont
        from qgis.PyQt.QtCore import Qt
        
        # Get style parameters from config or use defaults
        style = config.get('style', {}) if config else {}
        line_width = style.get('line_width_mm', 2.0)
        use_map_units = bool(style.get('use_map_units', False))
        line_width_mu = float(style.get('line_width_mu', 30.0))  # meters
        dist_width_mu = float(style.get('dist_width_mu', 10.0))  # meters for tick lines if map units enabled
        runway_width_mu = float(style.get('runway_width_mu', max(line_width_mu, 50.0)))
        moca_border_width = style.get('moca_border_width_mm', 1.0)
        point_size = style.get('point_size_mm', 5.0)
        line_color = style.get('line_color', '#000000')
        moca_fill = style.get('moca_fill_color', '#6464FF64')
        moca_hatch = style.get('moca_hatch_color', '#000000')
        
        # Style for PROFILE_LINE - Black solid line, configurable width
        line_layer = self.layers.get(self.LAYER_LINE)
        if line_layer:
            # Build a double-line symbol (white casing + black core) for strong contrast
            core = QgsSimpleLineSymbolLayer()
            core.setColor(QColor(line_color))
            casing = QgsSimpleLineSymbolLayer()
            casing.setColor(QColor(255, 255, 255))
            # Make edges look straight, not rounded
            try:
                core.setCapStyle(Qt.FlatCap)
                core.setJoinStyle(Qt.MiterJoin)
                casing.setCapStyle(Qt.FlatCap)
                casing.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                core.setWidth(line_width_mu)
                core.setWidthUnit(QgsUnitTypes.RenderMapUnits)
                casing.setWidth(line_width_mu * 1.8)
                casing.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                core.setWidth(line_width)
                core.setWidthUnit(QgsUnitTypes.RenderMillimeters)
                casing.setWidth(line_width * 1.8)
                casing.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            symbol = QgsLineSymbol()
            symbol.appendSymbolLayer(casing)
            symbol.appendSymbolLayer(core)
            # Always use a fresh single symbol renderer to avoid invalid renderer state
            line_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
            line_layer.triggerRepaint()
            unit_txt = f"{line_width_mu}m (map units)" if use_map_units else f"{line_width}mm"
            print(f"PLUGIN qAeroChart: Applied style to profile_line ({line_color}, {unit_txt})")

        # Style for simple 'final' line layer
        final_layer = self.layers.get(self.LAYER_LINE_FINAL)
        if final_layer:
            core = QgsSimpleLineSymbolLayer()
            core.setColor(QColor(line_color))
            casing = QgsSimpleLineSymbolLayer()
            casing.setColor(QColor(255, 255, 255))
            try:
                core.setCapStyle(Qt.FlatCap)
                core.setJoinStyle(Qt.MiterJoin)
                casing.setCapStyle(Qt.FlatCap)
                casing.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                core.setWidth(line_width_mu)
                core.setWidthUnit(QgsUnitTypes.RenderMapUnits)
                casing.setWidth(line_width_mu * 1.6)
                casing.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                core.setWidth(line_width)
                core.setWidthUnit(QgsUnitTypes.RenderMillimeters)
                casing.setWidth(line_width * 1.6)
                casing.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            symbol = QgsLineSymbol()
            symbol.appendSymbolLayer(casing)
            symbol.appendSymbolLayer(core)
            final_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
            final_layer.triggerRepaint()
            unit_txt = f"{line_width_mu}m (map units)" if use_map_units else f"{line_width}mm"
            print(f"PLUGIN qAeroChart: Applied style to {self.LAYER_LINE_FINAL} ({line_color}, {unit_txt})")

        # Style for simple 'runway' line layer (slightly thicker)
        runway_layer_simple = self.layers.get(self.LAYER_LINE_RUNWAY)
        if runway_layer_simple:
            core = QgsSimpleLineSymbolLayer()
            core.setColor(QColor(line_color))
            casing = QgsSimpleLineSymbolLayer()
            casing.setColor(QColor(255, 255, 255))
            try:
                core.setCapStyle(Qt.FlatCap)
                core.setJoinStyle(Qt.MiterJoin)
                casing.setCapStyle(Qt.FlatCap)
                casing.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                core.setWidth(runway_width_mu)
                core.setWidthUnit(QgsUnitTypes.RenderMapUnits)
                casing.setWidth(runway_width_mu * 1.6)
                casing.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                core.setWidth(max(line_width, 3.0))
                core.setWidthUnit(QgsUnitTypes.RenderMillimeters)
                casing.setWidth(max(line_width, 3.0) * 1.6)
                casing.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            symbol = QgsLineSymbol()
            symbol.appendSymbolLayer(casing)
            symbol.appendSymbolLayer(core)
            runway_layer_simple.setRenderer(QgsSingleSymbolRenderer(symbol))
            runway_layer_simple.triggerRepaint()
            unit_txt = f"{runway_width_mu}m (map units)" if use_map_units else f"{max(line_width,3.0)}mm"
            print(f"PLUGIN qAeroChart: Applied style to {self.LAYER_LINE_RUNWAY} ({line_color}, {unit_txt})")
        
        # Style for PROFILE_POINT_SYMBOL - Red circles, configurable size
        point_layer = self.layers.get(self.LAYER_POINT_SYMBOL)
        if point_layer:
            symbol = QgsSymbol.defaultSymbol(point_layer.geometryType())
            symbol.setColor(QColor(255, 0, 0))  # Red
            symbol.setSize(point_size)
            symbol.setSizeUnit(QgsUnitTypes.RenderMillimeters)
            point_layer.renderer().setSymbol(symbol)
            point_layer.triggerRepaint()
            print(f"PLUGIN qAeroChart: Applied style to profile_point_symbol (red, {point_size}mm)")
        
        # Style for PROFILE_DIST - Gray tick lines, 0.3 mm
        dist_layer = self.layers.get(self.LAYER_DIST)
        if dist_layer:
            symbol = QgsSymbol.defaultSymbol(dist_layer.geometryType())
            symbol.setColor(QColor(128, 128, 128))  # Gray
            # For line symbols, configure width in millimeters
            try:
                if use_map_units:
                    symbol.setWidth(dist_width_mu)
                    from qgis.core import QgsUnitTypes
                    symbol.setWidthUnit(QgsUnitTypes.RenderMapUnits)
                else:
                    symbol.setWidth(0.3)
                    from qgis.core import QgsUnitTypes
                    symbol.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            except Exception:
                pass
            dist_layer.renderer().setSymbol(symbol)
            dist_layer.triggerRepaint()
            unit_txt = f"{dist_width_mu}m (map units)" if use_map_units else "0.3mm"
            print(f"PLUGIN qAeroChart: Applied style to profile_dist (gray tick lines, {unit_txt})")
            # eAIP style: no 'N NM' labels on vertical ticks; axis labels below baseline are used instead.
            try:
                dist_layer.setLabelsEnabled(False)
            except Exception:
                pass
        
        # Style for PROFILE_MOCA - Configurable hatching pattern
        moca_layer = self.layers.get(self.LAYER_MOCA)
        if moca_layer:
            from qgis.core import QgsFillSymbol, QgsLinePatternFillSymbolLayer, QgsSimpleFillSymbolLayer
            
            try:
                # Parse colors from hex
                moca_color_str = moca_fill.lstrip('#')
                if len(moca_color_str) == 8:  # RRGGBBAA
                    r, g, b, a = int(moca_color_str[0:2], 16), int(moca_color_str[2:4], 16), int(moca_color_str[4:6], 16), int(moca_color_str[6:8], 16)
                    color_str = f'{r},{g},{b},{a}'
                else:  # RGB
                    color_str = f'{int(moca_color_str[0:2], 16)},{int(moca_color_str[2:4], 16)},{int(moca_color_str[4:6], 16)},100'
                
                # Create fill symbol with configurable parameters
                symbol = QgsFillSymbol.createSimple({
                    'color': color_str,
                    'outline_color': moca_hatch,
                    'outline_width': str(moca_border_width),
                    'outline_width_unit': 'MM',
                    'outline_style': 'solid'
                })
                
                # Try to add diagonal line pattern
                line_pattern = QgsLinePatternFillSymbolLayer()
                line_pattern.setDistance(2.0)  # 2mm spacing
                line_pattern.setDistanceUnit(QgsUnitTypes.RenderMillimeters)
                line_pattern.setLineAngle(45)  # 45 degree diagonal
                
                # Configure line style
                line_symbol = line_pattern.subSymbol()
                if line_symbol:
                    line_symbol.setColor(QColor(moca_hatch))
                    line_symbol.setWidth(0.5)  # 0.5mm lines
                    line_symbol.setWidthUnit(QgsUnitTypes.RenderMillimeters)
                
                symbol.appendSymbolLayer(line_pattern)
                
            except Exception as e:
                # Fallback to simple fill if pattern fails
                print(f"PLUGIN qAeroChart WARNING: Could not create hatching pattern: {e}")
                symbol = QgsFillSymbol.createSimple({
                    'color': '100,100,255,150',
                    'outline_color': 'black',
                    'outline_width': str(moca_border_width),
                    'outline_width_unit': 'MM'
                })
            
            moca_layer.renderer().setSymbol(symbol)
            moca_layer.triggerRepaint()
            print(f"PLUGIN qAeroChart: Applied style to profile_MOCA (border: {moca_border_width}mm)")

        # Style for BASELINE - thick, solid black flat-capped line
        baseline_layer = self.layers.get(self.LAYER_BASELINE)
        if baseline_layer:
            bl_core = QgsSimpleLineSymbolLayer()
            bl_core.setColor(QColor(0, 0, 0))
            try:
                bl_core.setCapStyle(Qt.FlatCap)
                bl_core.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                bl_core.setWidth(max(line_width_mu, 40.0))
                bl_core.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                bl_core.setWidth(max(line_width, 2.5))
                bl_core.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            bl_symbol = QgsLineSymbol()
            bl_symbol.appendSymbolLayer(bl_core)
            baseline_layer.setRenderer(QgsSingleSymbolRenderer(bl_symbol))
            baseline_layer.triggerRepaint()
            print("PLUGIN qAeroChart: Applied style to profile_baseline (solid black)")

        # Style for GRID - light gray dashed verticals
        grid_layer = self.layers.get(self.LAYER_GRID)
        if grid_layer:
            gl = QgsSimpleLineSymbolLayer()
            gl.setColor(QColor(180, 180, 180))
            try:
                gl.setCapStyle(Qt.FlatCap)
                gl.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                gl.setWidth(10.0)
                gl.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                gl.setWidth(0.3)
                gl.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            try:
                # Simple dashed appearance
                from qgis.PyQt.QtCore import Qt as QtCoreQt
                gl.setPenStyle(QtCoreQt.DashLine)
            except Exception:
                pass
            grid_symbol = QgsLineSymbol()
            grid_symbol.appendSymbolLayer(gl)
            grid_layer.setRenderer(QgsSingleSymbolRenderer(grid_symbol))
            grid_layer.triggerRepaint()
            print("PLUGIN qAeroChart: Applied style to profile_grid (dashed gray verticals)")
        
        
        # Style for CARTO_LABEL - Configure text labels
        label_layer = self.layers.get(self.LAYER_CARTO_LABEL)
        if label_layer:
            # Make point symbols invisible (we only want text labels)
            symbol = QgsSymbol.defaultSymbol(label_layer.geometryType())
            symbol.setColor(QColor(0, 0, 0, 0))  # Transparent
            symbol.setSize(0.5)  # Very small
            label_layer.renderer().setSymbol(symbol)
            
            # Configure text format for labels
            text_format = QgsTextFormat()
            text_format.setFont(QFont("Arial", 10, QFont.Bold))
            text_format.setSize(10)
            text_format.setColor(QColor(0, 0, 0))  # Black text
            
            # Optional: Add text buffer (white outline) for better visibility
            from qgis.core import QgsTextBufferSettings
            buffer = QgsTextBufferSettings()
            buffer.setEnabled(True)
            buffer.setSize(1.0)
            buffer.setColor(QColor(255, 255, 255))  # White buffer
            text_format.setBuffer(buffer)
            
            # Create label settings
            label_settings = QgsPalLayerSettings()
            label_settings.fieldName = 'label_text'  # Field containing the text to display
            label_settings.enabled = True
            label_settings.setFormat(text_format)
            
            # Position labels slightly above the point (QGIS 3.40+ uses Qgis.LabelPlacement enum)
            label_settings.placement = Qgis.LabelPlacement.OverPoint
            label_settings.yOffset = 0.0

            # Data-defined rotation from attribute 'rotation' when provided (e.g., slope labels)
            try:
                label_settings.setDataDefinedProperty(QgsPalLayerSettings.Rotation, QgsProperty.fromField('rotation'))
            except Exception:
                pass
            
            # Apply labeling to layer
            labeling = QgsVectorLayerSimpleLabeling(label_settings)
            label_layer.setLabeling(labeling)
            label_layer.setLabelsEnabled(True)
            
            print("PLUGIN qAeroChart: Applied labeling to profile_carto_label (black text with white buffer)")

        # Style for KEY VERTICALS - darker dashed lines
        key_v_layer = self.layers.get(self.LAYER_KEY_VLINES)
        if key_v_layer:
            kv = QgsSimpleLineSymbolLayer()
            kv.setColor(QColor(60, 60, 60))
            try:
                kv.setCapStyle(Qt.FlatCap)
                kv.setJoinStyle(Qt.MiterJoin)
            except Exception:
                pass
            if use_map_units:
                kv.setWidth(12.0)
                kv.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            else:
                kv.setWidth(0.6)
                kv.setWidthUnit(QgsUnitTypes.RenderMillimeters)
            try:
                from qgis.PyQt.QtCore import Qt as QtCoreQt
                kv.setPenStyle(QtCoreQt.DashLine)
            except Exception:
                pass
            key_symbol = QgsLineSymbol()
            key_symbol.appendSymbolLayer(kv)
            key_v_layer.setRenderer(QgsSingleSymbolRenderer(key_symbol))
            key_v_layer.triggerRepaint()
            print("PLUGIN qAeroChart: Applied style to profile_key_verticals (dashed dark)")
    
    def add_point_feature(self, point, point_name, point_type="fix", 
                         distance=0.0, elevation=0.0, notes=""):
        """
        Add a point feature to the profile_point_symbol layer.
        
        Args:
            point (QgsPointXY): Point coordinates
            point_name (str): Name/identifier of the point
            point_type (str): Type of point (fix, navaid, threshold, etc.)
            distance (float): Distance from reference (NM)
            elevation (float): Elevation above MSL (ft)
            notes (str): Additional notes
        
        Returns:
            bool: True if feature was added successfully
        """
        layer = self.layers.get(self.LAYER_POINT_SYMBOL)
        if not layer:
            print("PLUGIN qAeroChart ERROR: Point symbol layer not found")
            return False
        
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttributes([point_name, point_type, distance, elevation, notes])
        
        layer.startEditing()
        success = layer.addFeature(feature)
        layer.commitChanges()
        
        if success:
            layer.triggerRepaint()  # Force visual refresh
            print(f"PLUGIN qAeroChart: Added point '{point_name}' at ({point.x():.2f}, {point.y():.2f})")
        
        return success
    
    def add_label_feature(self, point, label_text, label_type="point_name", 
                         rotation=0.0, font_size=10):
        """
        Add a label feature to the profile_carto_label layer.
        
        Args:
            point (QgsPointXY): Label position
            label_text (str): Text to display
            label_type (str): Type of label
            rotation (float): Text rotation angle
            font_size (int): Font size
        
        Returns:
            bool: True if feature was added successfully
        """
        layer = self.layers.get(self.LAYER_CARTO_LABEL)
        if not layer:
            print("PLUGIN qAeroChart ERROR: Carto label layer not found")
            return False
        
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature.setAttributes([label_text, label_type, rotation, font_size])
        
        layer.startEditing()
        success = layer.addFeature(feature)
        layer.commitChanges()
        
        if success:
            layer.triggerRepaint()  # Force visual refresh
            print(f"PLUGIN qAeroChart: Added label '{label_text}' at ({point.x():.2f}, {point.y():.2f})")
        
        return success
    
    def add_line_feature(self, points, line_type="profile", segment_name="", gradient=0.0):
        """
        Add a line feature to the profile_line layer.
        
        Args:
            points (list): List of QgsPointXY defining the line
            line_type (str): Type of line
            segment_name (str): Name of the segment
            gradient (float): Gradient/slope
        
        Returns:
            bool: True if feature was added successfully
        """
        layer = self.layers.get(self.LAYER_LINE)
        if not layer:
            print("PLUGIN qAeroChart ERROR: Line layer not found")
            return False
        
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPolylineXY(points))
        feature.setAttributes([line_type, segment_name, gradient])
        
        layer.startEditing()
        success = layer.addFeature(feature)
        layer.commitChanges()
        
        if success:
            layer.triggerRepaint()  # Force visual refresh
            print(f"PLUGIN qAeroChart: Added line segment '{segment_name}' with {len(points)} points")
        
        return success
    
    def clear_all_layers(self):
        """Clear all features from all managed layers."""
        for layer_name, layer in self.layers.items():
            if layer:
                layer.startEditing()
                layer.deleteFeatures(layer.allFeatureIds())
                layer.commitChanges()
                print(f"PLUGIN qAeroChart: Cleared layer '{layer_name}'")
    
    def remove_all_layers(self):
        """Remove all managed layers from the project."""
        for layer_name, layer in self.layers.items():
            if layer:
                self.project.removeMapLayer(layer.id())
                print(f"PLUGIN qAeroChart: Removed layer '{layer_name}'")
        
        # Remove group if empty
        if self.layer_group:
            root = self.project.layerTreeRoot()
            if len(self.layer_group.children()) == 0:
                root.removeChildNode(self.layer_group)
                print(f"PLUGIN qAeroChart: Removed empty group '{self.GROUP_NAME}'")
        
        self.layers.clear()
        self.layer_group = None
    
    def get_layer(self, layer_name):
        """
        Get a specific layer by name.
        
        Args:
            layer_name (str): Name of the layer
        
        Returns:
            QgsVectorLayer: The layer or None if not found
        """
        return self.layers.get(layer_name)
    
    def layer_exists(self, layer_name):
        """
        Check if a layer exists.
        
        Args:
            layer_name (str): Name of the layer
        
        Returns:
            bool: True if layer exists
        """
        return layer_name in self.layers and self.layers[layer_name] is not None
    
    def populate_layers_from_config(self, config):
        """
        Populate all layers with profile data from configuration.
        Uses ProfileChartGeometry for cartesian calculations.
        
        Args:
            config (dict): Configuration dictionary with origin_point, runway, and profile_points
        
        Returns:
            bool: True if successful
        """
        self._dbg("Starting populate_layers_from_config()")
        print("PLUGIN qAeroChart: Populating layers from config v2.0...")
        print(f"PLUGIN qAeroChart: Config keys: {list(config.keys())}")
        self._crs_guard()
        
        # Extract origin point (v2.0 uses "origin_point", v1.0 uses "reference_point")
        origin_data = config.get('origin_point', config.get('reference_point', {}))
        if not origin_data or 'x' not in origin_data or 'y' not in origin_data:
            print("PLUGIN qAeroChart ERROR: No origin point in configuration")
            print(f"PLUGIN qAeroChart ERROR: origin_data = {origin_data}")
            return False
        
        origin_point = QgsPointXY(origin_data['x'], origin_data['y'])
        print(f"PLUGIN qAeroChart: *** ORIGIN POINT SET TO: X={origin_point.x():.2f}, Y={origin_point.y():.2f} ***")
        
        # Extract profile points and runway parameters
        profile_points = config.get('profile_points', [])
        if not profile_points:
            print("PLUGIN qAeroChart WARNING: No profile points in configuration")
            return False
        
        runway = config.get('runway', {})
        runway_length = float(runway.get('length', 0))
        tch = float(runway.get('tch_rdh', 0))
        self._dbg(f"Runway params -> length={runway_length}m, TCH={tch}m; profile_points={len(profile_points)}")
        
        # Initialize geometry calculator in CARTESIAN mode (no heading needed)
        geometry = ProfileChartGeometry(origin_point)
        
        # BATCH OPERATIONS: Collect all features first, then add in bulk
        point_features = []
        label_features = []
        line_features = []
        simple_final_features = []
        simple_runway_features = []
        dist_features = []
        moca_features = []
        baseline_features = []
        key_vertical_features = []
        
        # Get layer references
        layer_point = self.layers.get(self.LAYER_POINT_SYMBOL)
        layer_label = self.layers.get(self.LAYER_CARTO_LABEL)
        layer_line = self.layers.get(self.LAYER_LINE)
        layer_final_simple = self.layers.get(self.LAYER_LINE_FINAL)
        layer_runway_simple = self.layers.get(self.LAYER_LINE_RUNWAY)
        layer_dist = self.layers.get(self.LAYER_DIST)
        layer_moca = self.layers.get(self.LAYER_MOCA)
        
        # 1. Prepare ORIGIN marker
        if layer_point:
            feat = QgsFeature(layer_point.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(origin_point))
            feat.setAttributes(["ORIGIN", "origin", 0.0, 0.0, "Origin point - WHERE the profile is drawn"])
            point_features.append(feat)
        
        if layer_label:
            feat = QgsFeature(layer_label.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(origin_point))
            feat.setAttributes(["ORIGIN", "origin", 0.0, 12])
            label_features.append(feat)
        
        print(f"PLUGIN qAeroChart: Prepared ORIGIN marker at X={origin_point.x():.2f}, Y={origin_point.y():.2f}")
        
        # 2. Prepare profile line
        if len(profile_points) >= 2:
            print(f"PLUGIN qAeroChart: === CREATING PROFILE LINE ===")
            print(f"PLUGIN qAeroChart: Number of profile points: {len(profile_points)}")
            
            line_points = geometry.create_profile_line(profile_points)
            
            print(f"PLUGIN qAeroChart: Profile line returned {len(line_points) if line_points else 0} points")
            
            if line_points and layer_line:
                # Debug: Print all line points
                for i, pt in enumerate(line_points):
                    print(f"PLUGIN qAeroChart:   Point {i}: X={pt.x():.2f}, Y={pt.y():.2f}")
                
                feat = QgsFeature(layer_line.fields())
                geom = QgsGeometry.fromPolylineXY(line_points)
                
                # Validate geometry
                if geom.isGeosValid():
                    print(f"PLUGIN qAeroChart: ✅ Profile line geometry is VALID")
                else:
                    print(f"PLUGIN qAeroChart: ❌ Profile line geometry is INVALID: {geom.lastError()}")
                
                print(f"PLUGIN qAeroChart: Geometry type: {geom.type()}, WKT length: {len(geom.asWkt())}")
                
                feat.setGeometry(geom)
                feat.setAttributes(["profile", "Main Profile", 0.0])
                line_features.append(feat)
                print(f"PLUGIN qAeroChart: ✅ Profile line feature added to batch")
                # Slope labels per segment
                try:
                    sorted_pts = sorted(profile_points, key=lambda p: float(p.get('distance_nm', 0)))
                    for i in range(len(sorted_pts)-1):
                        p1 = sorted_pts[i]
                        p2 = sorted_pts[i+1]
                        grad_percent = geometry.calculate_gradient((float(p1.get('distance_nm',0)), float(p1.get('elevation_ft',0))),
                                                                   (float(p2.get('distance_nm',0)), float(p2.get('elevation_ft',0))))
                        import math
                        deg = math.degrees(math.atan(grad_percent/100.0))
                        text = f"{deg:.1f}° ({grad_percent:.1f}%)"
                        mid_nm = (float(p1.get('distance_nm',0)) + float(p2.get('distance_nm',0)))/2.0
                        mid_ft = (float(p1.get('elevation_ft',0)) + float(p2.get('elevation_ft',0)))/2.0 + 80.0
                        pos = geometry.calculate_profile_point(mid_nm, mid_ft)
                        if layer_label:
                            lf = QgsFeature(layer_label.fields())
                            lf.setGeometry(QgsGeometry.fromPointXY(pos))
                            lf.setAttributes([text, "slope", deg, 9])
                            label_features.append(lf)
                except Exception as e:
                    print(f"PLUGIN qAeroChart WARNING: Could not create slope labels: {e}")
                # also prepare feature for simple final layer
                if layer_final_simple:
                    feat_final = QgsFeature(layer_final_simple.fields())
                    feat_final.setGeometry(QgsGeometry.fromPolylineXY(line_points))
                    feat_final.setAttributes(["final", "Main Profile", 0.0])
                    simple_final_features.append(feat_final)
            else:
                print(f"PLUGIN qAeroChart: ❌ Profile line NOT created (line_points={bool(line_points)}, layer_line={bool(layer_line)})")
        else:
            print(f"PLUGIN qAeroChart: ❌ Not enough points for profile line ({len(profile_points)} points)")
        
        # 3. Prepare runway line
        if runway_length > 0:
            print(f"PLUGIN qAeroChart: === CREATING RUNWAY LINE ===")
            print(f"PLUGIN qAeroChart: Runway length: {runway_length}m, TCH: {tch}m")
            
            runway_points = geometry.create_runway_line(runway_length, tch)
            
            if runway_points and layer_line:
                # Debug: Print runway points
                for i, pt in enumerate(runway_points):
                    print(f"PLUGIN qAeroChart:   Runway point {i}: X={pt.x():.2f}, Y={pt.y():.2f}")
                
                feat = QgsFeature(layer_line.fields())
                geom = QgsGeometry.fromPolylineXY(runway_points)
                
                # Validate geometry
                if geom.isGeosValid():
                    print(f"PLUGIN qAeroChart: ✅ Runway geometry is VALID")
                else:
                    print(f"PLUGIN qAeroChart: ❌ Runway geometry is INVALID: {geom.lastError()}")
                
                feat.setGeometry(geom)
                feat.setAttributes(["runway", "Runway", 0.0])
                line_features.append(feat)
                print(f"PLUGIN qAeroChart: ✅ Runway line feature added to batch")
                # also prepare feature for simple runway layer
                if layer_runway_simple:
                    feat_rwy = QgsFeature(layer_runway_simple.fields())
                    feat_rwy.setGeometry(QgsGeometry.fromPolylineXY(runway_points))
                    feat_rwy.setAttributes(["runway", "Runway", 0.0])
                    simple_runway_features.append(feat_rwy)
            else:
                print(f"PLUGIN qAeroChart: ❌ Runway line NOT created")
        else:
            print(f"PLUGIN qAeroChart: ⚠️ Runway length is 0, skipping runway line")
        
        # 4. Prepare profile points with symbols and labels
        for point_data in profile_points:
            try:
                distance_nm = float(point_data.get('distance_nm', 0))
                elevation_ft = float(point_data.get('elevation_ft', 0))
                point_name = point_data.get('point_name', 'Unknown')
                moca_ft = point_data.get('moca_ft', '')
                notes = point_data.get('notes', '')
                
                # Calculate cartesian position
                point_xy = geometry.calculate_profile_point(distance_nm, elevation_ft)
                
                # Prepare point symbol
                if layer_point:
                    feat = QgsFeature(layer_point.fields())
                    feat.setGeometry(QgsGeometry.fromPointXY(point_xy))
                    feat.setAttributes([point_name, "fix", distance_nm, elevation_ft, notes])
                    point_features.append(feat)
                
                # Prepare label
                if layer_label:
                    feat = QgsFeature(layer_label.fields())
                    feat.setGeometry(QgsGeometry.fromPointXY(point_xy))
                    feat.setAttributes([point_name, "point_name", 0.0, 10])
                    label_features.append(feat)

                # Add key verticals for known names (FAF/IF/MAPT)
                if point_name.strip().upper() in {"FAF", "IF", "MAPT", "MAP"}:
                    try:
                        bottom = geometry.calculate_profile_point(distance_nm, 0.0)
                        # full height approx: 3000 m
                        topm = 3000.0
                        top = QgsPointXY(bottom.x(), bottom.y() + topm)
                        if self.layers.get(self.LAYER_KEY_VLINES):
                            lyr = self.layers[self.LAYER_KEY_VLINES]
                            feat_v = QgsFeature(lyr.fields())
                            feat_v.setGeometry(QgsGeometry.fromPolylineXY([bottom, top]))
                            feat_v.setAttributes(["key", point_name, 0.0]) if len(lyr.fields())>=3 else None
                            key_vertical_features.append(feat_v)
                    except Exception as e:
                        print(f"PLUGIN qAeroChart WARNING: could not create key vertical for {point_name}: {e}")
                
                print(f"PLUGIN qAeroChart: Prepared point '{point_name}' at {distance_nm} NM / {elevation_ft} ft")
                
            except (ValueError, TypeError) as e:
                print(f"PLUGIN qAeroChart WARNING: Could not process point {point_data.get('point_name', 'unknown')}: {e}")
                continue
        
        # 5. Prepare distance markers (tick line segments)
        if profile_points:
            max_distance_nm = max(float(p.get('distance_nm', 0)) for p in profile_points)
            markers = geometry.create_distance_markers(max_distance_nm, marker_height_m=200)
            # Additionally, prepare full-height gridlines at each NM
            grid_markers = geometry.create_distance_markers(max_distance_nm, marker_height_m=3000)

            # Prepare baseline feature (horizontal at y=0 from 0..max distance)
            baseline_layer = self.layers.get(self.LAYER_BASELINE)
            if baseline_layer:
                try:
                    p0 = geometry.calculate_profile_point(0.0, 0.0)
                    p1 = geometry.calculate_profile_point(max_distance_nm, 0.0)
                    feat = QgsFeature(baseline_layer.fields())
                    feat.setGeometry(QgsGeometry.fromPolylineXY([p0, p1]))
                    feat.setAttributes(["baseline", "Baseline", 0.0])
                    baseline_features.append(feat)
                except Exception as e:
                    print(f"PLUGIN qAeroChart WARNING: Could not prepare baseline: {e}")
            
            if layer_dist:
                for marker in markers:
                    # marker['geometry'] contains [bottom, top] points
                    bottom, top = marker['geometry']
                    feat = QgsFeature(layer_dist.fields())
                    feat.setGeometry(QgsGeometry.fromPolylineXY([bottom, top]))
                    feat.setAttributes([marker['distance'], 'Origin', 'tick'])
                    dist_features.append(feat)
                
                print(f"PLUGIN qAeroChart: Prepared {len(markers)} distance markers")

            # Axis labels under baseline at each NM
            if layer_label:
                try:
                    style = config.get('style', {}) if config else {}
                    reverse_axis = bool(style.get('axis_reverse_labels', False))
                    for i in range(int(max_distance_nm) + 1):
                        # place slightly below baseline (~60 ft)
                        pos = geometry.calculate_profile_point(i, -60.0)
                        feat = QgsFeature(layer_label.fields())
                        feat.setGeometry(QgsGeometry.fromPointXY(pos))
                        label_txt = str(int(max_distance_nm) - i) if reverse_axis else str(i)
                        feat.setAttributes([label_txt, "axis", 0.0, 9])
                        label_features.append(feat)
                    print(f"PLUGIN qAeroChart: Prepared {int(max_distance_nm)+1} axis labels")
                except Exception as e:
                    print(f"PLUGIN qAeroChart WARNING: Could not create axis labels: {e}")
            # Prepare count for GRID (full-height verticals); features will be added in batch section
            print(f"PLUGIN qAeroChart: Prepared {len(grid_markers)} grid lines")
        
    # 6. Prepare MOCA polygons
        print(f"PLUGIN qAeroChart: === CREATING MOCA POLYGONS ===")
        # First, handle OCA coverage rectangles if provided (added to same layer for hatch styling)
        try:
            oca_single = config.get('oca') if config else None
            if oca_single and self.layers.get(self.LAYER_MOCA):
                d1 = float(oca_single.get('from_nm', 0))
                d2 = float(oca_single.get('to_nm', 0))
                hft = float(oca_single.get('oca_ft', oca_single.get('height_ft', 0)))
                poly = geometry.create_oca_box(d1, d2, hft)
                feat = QgsFeature(layer_moca.fields())
                feat.setGeometry(QgsGeometry.fromPolygonXY([poly]))
                feat.setAttributes([hft, f"OCA {d1}-{d2}NM", 0.0])
                moca_features.append(feat)
                print(f"PLUGIN qAeroChart: Added OCA polygon {d1}-{d2} NM @ {hft} ft")
        except Exception as e:
            print(f"PLUGIN qAeroChart WARNING: OCA single processing failed: {e}")
        try:
            oca_segments = config.get('oca_segments', []) if config else []
            if oca_segments and self.layers.get(self.LAYER_MOCA):
                print(f"PLUGIN qAeroChart: Processing OCA segments: {len(oca_segments)}")
                for seg in oca_segments:
                    try:
                        d1 = float(seg.get('from_nm', seg.get('from', 0)))
                        d2 = float(seg.get('to_nm', seg.get('to', 0)))
                        hft = float(seg.get('oca_ft', seg.get('height_ft', 0)))
                        poly = geometry.create_oca_box(d1, d2, hft)
                        feat = QgsFeature(layer_moca.fields())
                        feat.setGeometry(QgsGeometry.fromPolygonXY([poly]))
                        feat.setAttributes([hft, f"OCA {d1}-{d2}NM", 0.0])
                        moca_features.append(feat)
                    except Exception as e:
                        print(f"PLUGIN qAeroChart WARNING: Skipping OCA segment {seg}: {e}")
        except Exception as e:
            print(f"PLUGIN qAeroChart WARNING: OCA segments processing failed: {e}")
        # If explicit MOCA segments are provided, prefer them and skip per-point MOCA to avoid duplicates
        has_explicit_moca = False
        try:
            has_explicit_moca = bool(config.get('moca_segments'))
        except Exception:
            has_explicit_moca = False
        if not has_explicit_moca:
            print(f"PLUGIN qAeroChart: Processing {len(profile_points)-1} possible MOCA segments (per-point)")
        else:
            print("PLUGIN qAeroChart: Explicit MOCA segments present → skipping per-point MOCA")
        
        for i in range(len(profile_points) - 1):
            if has_explicit_moca:
                break
            point1 = profile_points[i]
            point2 = profile_points[i + 1]
            
            moca_ft = point1.get('moca_ft', '')
            print(f"PLUGIN qAeroChart: Segment {i}: {point1.get('point_name','')} → {point2.get('point_name','')}, MOCA={moca_ft}")
            
            if moca_ft and moca_ft.strip():
                try:
                    moca_value = float(moca_ft)
                    dist1_nm = float(point1.get('distance_nm', 0))
                    dist2_nm = float(point2.get('distance_nm', 0))
                    
                    print(f"PLUGIN qAeroChart:   Creating MOCA: {dist1_nm}NM to {dist2_nm}NM at {moca_value}ft")
                    
                    # create_oca_box returns 5 points (closed polygon) for hatched area
                    moca_polygon = geometry.create_oca_box(dist1_nm, dist2_nm, moca_value)
                    
                    print(f"PLUGIN qAeroChart:   MOCA polygon has {len(moca_polygon)} points")
                    
                    # Debug: Print polygon vertices
                    for j, pt in enumerate(moca_polygon):
                        print(f"PLUGIN qAeroChart:     Vertex {j}: X={pt.x():.2f}, Y={pt.y():.2f}")
                    
                    if layer_moca:
                        feat = QgsFeature(layer_moca.fields())
                        
                        # Create polygon geometry
                        geom = QgsGeometry.fromPolygonXY([moca_polygon])
                        
                        # Validate geometry
                        if geom.isGeosValid():
                            print(f"PLUGIN qAeroChart:   ✅ MOCA polygon geometry is VALID")
                        else:
                            print(f"PLUGIN qAeroChart:   ❌ MOCA polygon geometry is INVALID: {geom.lastError()}")
                        
                        print(f"PLUGIN qAeroChart:   Geometry type: {geom.type()}, Area: {geom.area():.2f}")
                        
                        feat.setGeometry(geom)
                        feat.setAttributes([moca_value, f"{point1.get('point_name', '')} - {point2.get('point_name', '')}", 0.0])
                        moca_features.append(feat)
                        print(f"PLUGIN qAeroChart:   ✅ MOCA feature added to batch")
                    else:
                        print(f"PLUGIN qAeroChart:   ❌ layer_moca is None!")
                        
                except (ValueError, TypeError) as e:
                    print(f"PLUGIN qAeroChart: ❌ Could not create MOCA for segment: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            else:
                print(f"PLUGIN qAeroChart:   ⚠️ No MOCA value for this segment")

        # Optional explicit MOCA segments (more control than per-point moca_ft)
        try:
            explicit_moca = config.get('moca_segments', [])
            if explicit_moca and layer_moca:
                print(f"PLUGIN qAeroChart: Processing explicit MOCA segments: {len(explicit_moca)}")
                for seg in explicit_moca:
                    try:
                        d1 = float(seg.get('from_nm', seg.get('from', 0)))
                        d2 = float(seg.get('to_nm', seg.get('to', 0)))
                        hft = float(seg.get('moca_ft', seg.get('height_ft', 0)))
                        poly = geometry.create_oca_box(d1, d2, hft)
                        feat = QgsFeature(layer_moca.fields())
                        feat.setGeometry(QgsGeometry.fromPolygonXY([poly]))
                        feat.setAttributes([hft, f"{d1}-{d2}NM", 0.0])
                        moca_features.append(feat)
                    except Exception as e:
                        print(f"PLUGIN qAeroChart WARNING: Skipping explicit MOCA segment {seg}: {e}")
        except Exception as e:
            print(f"PLUGIN qAeroChart WARNING: explicit MOCA processing failed: {e}")
        
        # BATCH ADD: Add all features in bulk (single edit cycle per layer)
        print(f"PLUGIN qAeroChart: === BATCH ADDING FEATURES ===")
        print(f"PLUGIN qAeroChart: Features to add - Points: {len(point_features)}, Labels: {len(label_features)}, Lines: {len(line_features)}, SimpleFinal: {len(simple_final_features)}, SimpleRunway: {len(simple_runway_features)}, Dist: {len(dist_features)}, MOCA: {len(moca_features)}")
        
        if point_features and layer_point:
            layer_point.startEditing()
            success = layer_point.addFeatures(point_features)
            layer_point.commitChanges()
            layer_point.updateExtents()
            layer_point.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(point_features)} point features (success={success})")
            self._dbg(f"Point layer now has {layer_point.featureCount()} features")
        
        if label_features and layer_label:
            layer_label.startEditing()
            success = layer_label.addFeatures(label_features)
            layer_label.commitChanges()
            layer_label.updateExtents()
            layer_label.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(label_features)} label features (success={success})")
            self._dbg(f"Label layer now has {layer_label.featureCount()} features")

        if line_features and layer_line:
            print(f"PLUGIN qAeroChart: === ADDING LINE FEATURES ===")
            print(f"PLUGIN qAeroChart: Layer valid: {layer_line.isValid()}")
            print(f"PLUGIN qAeroChart: Layer CRS: {layer_line.crs().authid()}")
            print(f"PLUGIN qAeroChart: Features in batch: {len(line_features)}")

            for idx, feat in enumerate(line_features):
                geom = feat.geometry()
                print(f"PLUGIN qAeroChart:   Line {idx}: Valid={geom.isGeosValid()}, Type={geom.type()}, Empty={geom.isEmpty()}, WKT={geom.asWkt()[:100]}...")

            layer_line.startEditing()
            success = layer_line.addFeatures(line_features)
            commit_success = layer_line.commitChanges()

            if not commit_success:
                errors = layer_line.commitErrors()
                print(f"PLUGIN qAeroChart: ❌ LINE COMMIT FAILED! Errors: {errors}")

            layer_line.updateExtents()
            layer_line.triggerRepaint()

            # Debug: Print extent and feature count
            extent = layer_line.extent()
            feature_count = layer_line.featureCount()
            print(f"PLUGIN qAeroChart: ✅ Added {len(line_features)} line features (addFeatures={success}, commit={commit_success})")
            print(f"PLUGIN qAeroChart: Line layer extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
            print(f"PLUGIN qAeroChart: Line layer feature count: {feature_count}")

            # Fallback: if for any reason no line features present, attempt to rebuild once
            if feature_count == 0:
                try:
                    rebuild_points = geometry.create_profile_line(profile_points)
                    if rebuild_points:
                        f = QgsFeature(layer_line.fields())
                        f.setGeometry(QgsGeometry.fromPolylineXY(rebuild_points))
                        f.setAttributes(["profile", "Main Profile (rebuild)", 0.0])
                        layer_line.startEditing()
                        ok_add = layer_line.addFeature(f)
                        ok_commit = layer_line.commitChanges()
                        layer_line.updateExtents()
                        layer_line.triggerRepaint()
                        print(f"PLUGIN qAeroChart: Fallback rebuild line -> add={ok_add}, commit={ok_commit}")
                        try:
                            if self.iface:
                                self.iface.messageBar().pushMessage(
                                    "qAeroChart",
                                    "Profile line rebuilt due to empty layer after first pass.",
                                    level=Qgis.Info,
                                    duration=4
                                )
                        except Exception:
                            pass
                except Exception as e:
                    print(f"PLUGIN qAeroChart WARNING: Fallback rebuild failed: {e}")

        if dist_features and layer_dist:
            layer_dist.startEditing()
            success = layer_dist.addFeatures(dist_features)
            layer_dist.commitChanges()
            layer_dist.updateExtents()
            layer_dist.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(dist_features)} distance markers (success={success})")
            self._dbg(f"Dist layer now has {layer_dist.featureCount()} features")

        # Add GRID features (full-height dashed verticals)
        layer_grid = self.layers.get(self.LAYER_GRID)
        if layer_grid:
            # Rebuild grid features to ensure we didn't just prepare without adding
            if profile_points:
                max_distance_nm = max(float(p.get('distance_nm', 0)) for p in profile_points)
                grid_markers = geometry.create_distance_markers(max_distance_nm, marker_height_m=3000)
                grid_features = []
                for marker in grid_markers:
                    bottom, top = marker['geometry']
                    feat = QgsFeature(layer_grid.fields())
                    feat.setGeometry(QgsGeometry.fromPolylineXY([bottom, top]))
                    feat.setAttributes([marker['distance'], 'grid'])
                    grid_features.append(feat)
                if grid_features:
                    layer_grid.startEditing()
                    success = layer_grid.addFeatures(grid_features)
                    layer_grid.commitChanges()
                    layer_grid.updateExtents()
                    layer_grid.triggerRepaint()
                    print(f"PLUGIN qAeroChart: ✅ Added {len(grid_features)} grid lines")

        # Add simple line layers as a robust visual fallback and to match expected structure
        if simple_final_features and layer_final_simple:
            layer_final_simple.startEditing()
            success = layer_final_simple.addFeatures(simple_final_features)
            layer_final_simple.commitChanges()
            layer_final_simple.updateExtents()
            layer_final_simple.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(simple_final_features)} features to {self.LAYER_LINE_FINAL}")
            self._dbg(f"{self.LAYER_LINE_FINAL} now has {layer_final_simple.featureCount()} features")

        if simple_runway_features and layer_runway_simple:
            layer_runway_simple.startEditing()
            success = layer_runway_simple.addFeatures(simple_runway_features)
            layer_runway_simple.commitChanges()
            layer_runway_simple.updateExtents()
            layer_runway_simple.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(simple_runway_features)} features to {self.LAYER_LINE_RUNWAY}")
            self._dbg(f"{self.LAYER_LINE_RUNWAY} now has {layer_runway_simple.featureCount()} features")

        # Add KEY VERTICALS features
        key_v_layer = self.layers.get(self.LAYER_KEY_VLINES)
        if key_vertical_features and key_v_layer:
            key_v_layer.startEditing()
            success = key_v_layer.addFeatures(key_vertical_features)
            key_v_layer.commitChanges()
            key_v_layer.updateExtents()
            key_v_layer.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added {len(key_vertical_features)} key verticals")

        if moca_features and layer_moca:
            print(f"PLUGIN qAeroChart: === ADDING MOCA FEATURES ===")
            print(f"PLUGIN qAeroChart: Layer valid: {layer_moca.isValid()}")
            print(f"PLUGIN qAeroChart: Layer CRS: {layer_moca.crs().authid()}")
            print(f"PLUGIN qAeroChart: Features in batch: {len(moca_features)}")

            for idx, feat in enumerate(moca_features):
                geom = feat.geometry()
                print(f"PLUGIN qAeroChart:   MOCA {idx}: Valid={geom.isGeosValid()}, Type={geom.type()}, Area={geom.area():.2f}, Empty={geom.isEmpty()}")

            layer_moca.startEditing()
            success = layer_moca.addFeatures(moca_features)
            commit_success = layer_moca.commitChanges()

            if not commit_success:
                errors = layer_moca.commitErrors()
                print(f"PLUGIN qAeroChart: ❌ MOCA COMMIT FAILED! Errors: {errors}")

            layer_moca.updateExtents()
            layer_moca.triggerRepaint()

            # Debug: Print extent and feature count
            extent = layer_moca.extent()
            feature_count = layer_moca.featureCount()
            print(f"PLUGIN qAeroChart: ✅ Added {len(moca_features)} MOCA features (addFeatures={success}, commit={commit_success})")
            print(f"PLUGIN qAeroChart: MOCA layer extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
            print(f"PLUGIN qAeroChart: MOCA layer feature count: {feature_count}")

        # Add BASELINE feature
        baseline_layer = self.layers.get(self.LAYER_BASELINE)
        if baseline_features and baseline_layer:
            baseline_layer.startEditing()
            success = baseline_layer.addFeatures(baseline_features)
            baseline_layer.commitChanges()
            baseline_layer.updateExtents()
            baseline_layer.triggerRepaint()
            print(f"PLUGIN qAeroChart: ✅ Added baseline feature(s): {len(baseline_features)}")

        # Force refresh of canvas
        if self.iface:
            self.iface.mapCanvas().refresh()
            print(f"PLUGIN qAeroChart: ✅ Canvas refreshed")

        # Auto-zoom to profile extent
        if layer_line and layer_line.featureCount() > 0:
            extent = layer_line.extent()
            # Add 20% buffer around the profile
            extent.scale(1.2)
            self.iface.mapCanvas().setExtent(extent)
            self.iface.mapCanvas().refresh()
            print(f"PLUGIN qAeroChart: ✅ Auto-zoomed to profile extent")

            # Optional: Normalize canvas scale for consistent visibility (inspired by qOLS/TOFPA)
            try:
                canvas = self.iface.mapCanvas()
                current_scale = canvas.scale()
                style = config.get('style', {}) if config else {}
                # View scale hint can be customized via JSON; default chosen for comfortable view of small profiles
                view_scale_hint = float(style.get('view_scale_hint', 12000))
                enforce_view_scale = bool(style.get('enforce_view_scale', True))

                if enforce_view_scale and current_scale > view_scale_hint:
                    canvas.zoomScale(view_scale_hint)
                    print(f"PLUGIN qAeroChart: 🔎 Applied view scale hint to {view_scale_hint}")
            except Exception as e:
                print(f"PLUGIN qAeroChart WARNING: Could not apply view scale hint: {e}")

        print("PLUGIN qAeroChart: === LAYER POPULATION COMPLETE ===")
        self._dbg("Finished populate_layers_from_config()")

        return True

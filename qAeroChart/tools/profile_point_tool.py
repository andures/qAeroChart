# -*- coding: utf-8 -*-
"""
ProfilePointTool - Map tool for selecting origin points on the map

This tool allows users to click on the map canvas to select an origin point
(the location WHERE the profile chart will be drawn). It provides visual 
feedback using a rubber band and emits signals to communicate with the 
ProfileCreationDialog.
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal, QPointF, QSizeF
from qgis.PyQt.QtGui import QColor, QTextDocument, QFont
from qgis.core import QgsPointXY, QgsWkbTypes, QgsCoordinateTransform, QgsProject, QgsGeometry, QgsTextAnnotation
from qgis.gui import QgsMapTool, QgsRubberBand, QgsMapCanvasAnnotationItem


class ProfilePointTool(QgsMapTool):
    """
    Map tool for selecting profile origin points.
    
    This tool allows users to click on the map to select an origin point
    (WHERE to draw the profile chart). It provides visual feedback with a 
    temporary marker and emits the selected point coordinates when clicked.
    
    Signals:
        originSelected(QgsPointXY): Emitted when user clicks on the map with the origin point coordinates
        deactivated(): Emitted when the tool is deactivated
    """
    
    # Signals
    originSelected = pyqtSignal(QgsPointXY)  # Renamed from pointSelected
    deactivated = pyqtSignal()
    
    def __init__(self, canvas):
        """
        Initialize the ProfilePointTool.
        
        Args:
            canvas (QgsMapCanvas): The QGIS map canvas
        """
        super(ProfilePointTool, self).__init__(canvas)
        self.canvas = canvas
        self.rubber_band = None
        self.preview_band = None
        self.preview_ticks_band = None
        self.preview_baseline_band = None
        self.preview_grid_band = None
        self._preview_generator = None  # Callable taking QgsPointXY -> dict with polylines
        self.preview_label_items = []
        self.cursor = Qt.CrossCursor
        self._last_hover_point = None
        
        # Initialize rubber band for visual feedback
        self._init_rubber_band()
        
        print("PLUGIN qAeroChart: ProfilePointTool initialized")
    
    def _init_rubber_band(self):
        """Initialize the rubber band for visual feedback."""
        # Create rubber band for point visualization
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        
        # Set appearance
        self.rubber_band.setColor(QColor(255, 0, 0, 180))  # Red with transparency
        self.rubber_band.setWidth(3)
        self.rubber_band.setIcon(QgsRubberBand.ICON_CIRCLE)
        self.rubber_band.setIconSize(15)
        
        # Create rubber band for profile preview (line)
        self.preview_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.preview_band.setColor(QColor(0, 120, 215, 180))  # Blue-ish
        self.preview_band.setWidth(2)
        self.preview_band.hide()
        
        # Create rubber band for tick preview (line)
        self.preview_ticks_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.preview_ticks_band.setColor(QColor(128, 128, 128, 160))  # Gray
        self.preview_ticks_band.setWidth(1)
        self.preview_ticks_band.hide()

        # Baseline (horizontal axis) preview
        self.preview_baseline_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.preview_baseline_band.setColor(QColor(0, 0, 0, 220))  # Black
        self.preview_baseline_band.setWidth(3)
        self.preview_baseline_band.hide()

        # Grid (full verticals) preview
        self.preview_grid_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.preview_grid_band.setColor(QColor(170, 170, 170, 140))
        self.preview_grid_band.setWidth(1)
        self.preview_grid_band.hide()
        
        # Hide initially
        self.rubber_band.hide()
    
    def canvasPressEvent(self, event):
        """
        Handle mouse press event on canvas.
        
        Args:
            event (QgsMapMouseEvent): The mouse event
        """
        # We'll handle the click on release, but we can use press for other interactions
        pass
    
    def canvasReleaseEvent(self, event):
        """
        Handle mouse release event on canvas.
        This is where we capture the point selection.
        
        Args:
            event (QgsMapMouseEvent): The mouse event
        """
        # Only respond to left-click
        if event.button() != Qt.LeftButton:
            return
        
        # Get the clicked point in map coordinates
        point = self.toMapCoordinates(event.pos())
        
        print(f"PLUGIN qAeroChart: Origin point selected at X={point.x():.2f}, Y={point.y():.2f}")
        
        # Show visual feedback
        self._show_point_feedback(point)
        
        # Emit signal with the selected origin point
        self.originSelected.emit(point)
    
    def canvasMoveEvent(self, event):
        """
        Handle mouse move event on canvas.
        Can be used for hover effects or preview.
        
        Args:
            event (QgsMapMouseEvent): The mouse event
        """
        # Live preview of profile at the hovered origin point
        try:
            if not self._preview_generator:
                return
            point = self.toMapCoordinates(event.pos())
            # Track last hovered map point for potential fallback if user doesn't click
            try:
                self._last_hover_point = QgsPointXY(point.x(), point.y())
            except Exception:
                self._last_hover_point = point
            preview = self._preview_generator(point)
            
            # Expecting preview dict with optional keys 'profile_line' (list[QgsPointXY])
            # and 'tick_segments' (list[list[QgsPointXY]] with two points each)
            # Update main profile preview
            self.preview_band.reset(QgsWkbTypes.LineGeometry)
            profile_pts = preview.get('profile_line', [])
            if profile_pts:
                geom = QgsGeometry.fromPolylineXY(profile_pts)
                self.preview_band.setToGeometry(geom, None)
                self.preview_band.show()
            else:
                self.preview_band.hide()

            # Update baseline
            self.preview_baseline_band.reset(QgsWkbTypes.LineGeometry)
            baseline_pts = preview.get('baseline', [])
            if baseline_pts:
                geom = QgsGeometry.fromPolylineXY(baseline_pts)
                self.preview_baseline_band.setToGeometry(geom, None)
                self.preview_baseline_band.show()
            else:
                self.preview_baseline_band.hide()
            
            # Update ticks preview (as multi-segment)
            self.preview_ticks_band.reset(QgsWkbTypes.LineGeometry)
            tick_segments = preview.get('tick_segments', [])
            if tick_segments:
                # Aggregate as multiLineString
                # Build one big geometry by adding each small segment
                for seg in tick_segments:
                    if len(seg) >= 2:
                        geom = QgsGeometry.fromPolylineXY(seg)
                        # RubberBand can't append multiple geometries at once; draw sequentially
                        self.preview_ticks_band.addGeometry(geom, None)
                self.preview_ticks_band.show()
            else:
                self.preview_ticks_band.hide()

            # Update grid preview
            self.preview_grid_band.reset(QgsWkbTypes.LineGeometry)
            grid_segments = preview.get('grid_segments', [])
            if grid_segments:
                for seg in grid_segments:
                    if len(seg) >= 2:
                        geom = QgsGeometry.fromPolylineXY(seg)
                        self.preview_grid_band.addGeometry(geom, None)
                self.preview_grid_band.show()
            else:
                self.preview_grid_band.hide()

            # Update tick labels (text annotations)
            self._clear_preview_labels()
            tick_labels = preview.get('tick_labels', [])
            if tick_labels:
                for entry in tick_labels:
                    pos = entry.get('pos')
                    text = str(entry.get('text', ''))
                    if not isinstance(pos, QgsPointXY) or text == '':
                        continue
                    try:
                        ann = QgsTextAnnotation()
                        doc = QTextDocument()
                        doc.setPlainText(text)
                        font = QFont()
                        font.setPointSize(8)
                        doc.setDefaultFont(font)
                        ann.setDocument(doc)
                        ann.setMapPosition(pos)
                        # Ensure annotation uses the canvas destination CRS
                        try:
                            ann.setMapPositionCrs(self.canvas.mapSettings().destinationCrs())
                        except Exception:
                            pass
                        # Slight upward offset in pixels to avoid overlapping the axis line
                        ann.setFrameOffsetFromReferencePoint(QPointF(-6, -14))
                        ann.setFrameSize(QSizeF(18, 12))
                        item = QgsMapCanvasAnnotationItem(ann, self.canvas)
                        self.preview_label_items.append(item)
                    except Exception as e:
                        # Skip label on error, keep preview responsive
                        print(f"PLUGIN qAeroChart WARNING: label creation failed: {e}")
        except Exception as e:
            # Fail silently to avoid interrupting user interaction
            print(f"PLUGIN qAeroChart WARNING: preview failed: {e}")

    def get_last_hover_point(self):
        """Return the last hovered map point (QgsPointXY) or None."""
        return self._last_hover_point
    
    def _show_point_feedback(self, point):
        """
        Show visual feedback at the selected point location.
        
        Args:
            point (QgsPointXY): The point to highlight
        """
        if self.rubber_band:
            # Clear previous rubber band
            self.rubber_band.reset(QgsWkbTypes.PointGeometry)
            
            # Add the point
            self.rubber_band.addPoint(point)
            
            # Show the rubber band
            self.rubber_band.show()
            
            print("PLUGIN qAeroChart: Visual feedback displayed at point")
    
    def clear_feedback(self):
        """Clear the visual feedback rubber band."""
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.PointGeometry)
            self.rubber_band.hide()
            print("PLUGIN qAeroChart: Visual feedback cleared")
        if self.preview_band:
            self.preview_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_band.hide()
        if self.preview_ticks_band:
            self.preview_ticks_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_ticks_band.hide()
        if self.preview_baseline_band:
            self.preview_baseline_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_baseline_band.hide()
        if self.preview_grid_band:
            self.preview_grid_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_grid_band.hide()
        self._clear_preview_labels()
    
    def activate(self):
        """
        Called when the tool is activated.
        Sets up the tool for use.
        """
        super(ProfilePointTool, self).activate()
        
        # Set cursor
        self.canvas.setCursor(self.cursor)
        
        # Clear any previous feedback
        self.clear_feedback()
        
        print("PLUGIN qAeroChart: ProfilePointTool activated")
    
    def deactivate(self):
        """
        Called when the tool is deactivated.
        Cleans up visual elements.
        """
        super(ProfilePointTool, self).deactivate()
        
        # Clear rubber band
        self.clear_feedback()
        
        # Emit deactivated signal
        self.deactivated.emit()
        
        print("PLUGIN qAeroChart: ProfilePointTool deactivated")
    
    def isZoomTool(self):
        """
        Indicates this is not a zoom tool.
        
        Returns:
            bool: False
        """
        return False
    
    def isTransient(self):
        """
        Indicates this tool is transient (temporary).
        
        Returns:
            bool: True - tool should be deactivated after use
        """
        return False  # Set to False so tool stays active until manually deactivated
    
    def isEditTool(self):
        """
        Indicates this is not an edit tool.
        
        Returns:
            bool: False
        """
        return False
    
    def flags(self):
        """
        Return flags for the map tool.
        
        Returns:
            QgsMapTool.Flags: Tool flags
        """
        return QgsMapTool.Flags()

    # ================= Preview API =================
    def set_preview_generator(self, generator_callable):
        """Provide a callable that produces preview geometry for a candidate origin.
        The callable should accept QgsPointXY and return a dict with keys:
          - 'profile_line': list[QgsPointXY]
          - 'tick_segments': list[list[QgsPointXY]]
          - 'tick_labels': list[{'pos': QgsPointXY, 'text': str}]
        """
        self._preview_generator = generator_callable

    def _clear_preview_labels(self):
        """Remove and clear all preview label items from canvas."""
        if not self.preview_label_items:
            return
        for item in self.preview_label_items:
            try:
                item.setVisible(False)
                item.deleteLater()
            except Exception:
                pass
        self.preview_label_items = []


class ProfilePointToolManager:
    """
    Manager class to handle ProfilePointTool lifecycle and integration.
    
    This class simplifies the management of the map tool, including activation,
    deactivation, and cleanup. It's designed to be used by the main plugin class.
    """
    
    def __init__(self, canvas, iface):
        """
        Initialize the tool manager.
        
        Args:
            canvas (QgsMapCanvas): The QGIS map canvas
            iface (QgisInterface): The QGIS interface object
        """
        self.canvas = canvas
        self.iface = iface
        self.tool = None
        self.previous_tool = None
        
        print("PLUGIN qAeroChart: ProfilePointToolManager initialized")
    
    def create_tool(self):
        """
        Create a new instance of ProfilePointTool.
        
        Returns:
            ProfilePointTool: The created tool instance
        """
        if self.tool is None:
            self.tool = ProfilePointTool(self.canvas)
            print("PLUGIN qAeroChart: ProfilePointTool instance created")
        
        return self.tool
    
    def activate_tool(self):
        """
        Activate the ProfilePointTool.
        Saves the current tool to restore later.
        """
        # Save current tool
        self.previous_tool = self.canvas.mapTool()
        
        # Create tool if it doesn't exist
        if self.tool is None:
            self.create_tool()
        
        # Set as active tool
        self.canvas.setMapTool(self.tool)
        
        print("PLUGIN qAeroChart: ProfilePointTool activated via manager")
    
    def deactivate_tool(self):
        """
        Deactivate the ProfilePointTool and restore previous tool.
        """
        if self.tool:
            # Clear feedback
            self.tool.clear_feedback()
        
        # Restore previous tool
        if self.previous_tool:
            self.canvas.setMapTool(self.previous_tool)
            print("PLUGIN qAeroChart: Previous tool restored")
        else:
            # If no previous tool, unset current tool
            self.canvas.unsetMapTool(self.tool)
            print("PLUGIN qAeroChart: Map tool unset")
        
        self.previous_tool = None
    
    def cleanup(self):
        """
        Clean up the tool and manager.
        Call this when the plugin is unloaded.
        """
        if self.tool:
            self.deactivate_tool()
            self.tool = None
        
        print("PLUGIN qAeroChart: ProfilePointToolManager cleaned up")
    
    def get_tool(self):
        """
        Get the current tool instance.
        
        Returns:
            ProfilePointTool: The tool instance or None
        """
        return self.tool

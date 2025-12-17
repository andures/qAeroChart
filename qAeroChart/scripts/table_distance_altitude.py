from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QFileDialog
import json
from qgis.core import (
    QgsProject,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsLayoutItemManualTable,
    QgsTableCell,
    QgsTextFormat,
    QgsLayoutFrame,
    QgsPrintLayout
)

# ---------------------------
# Ask user to select JSON file
# ---------------------------
json_file, _ = QFileDialog.getOpenFileName(None, "Select Table JSON", "", "JSON Files (*.json)")
if not json_file:
    raise Exception("No file selected")

with open(json_file, 'r') as f:
    data = json.load(f)

thr = data['thr']  # runway number
numeric_data = data['numeric_columns']  # dict: header -> value

# ---------------------------
# Layout setup
# ---------------------------
project = QgsProject.instance()
manager = project.layoutManager()
layouts = manager.layouts()

if layouts:
    layout = layouts[0]
    print(f"Using layout: {layout.name()}")
else:
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("AutoLayout")
    manager.addLayout(layout)
    print("Created new layout: AutoLayout")

# ---------------------------
# Table content
# ---------------------------
tbl_headers = [f'NM TO RWY{thr}'] + list(numeric_data.keys())
tbl_rw = ['ALTITUDE'] + list(numeric_data.values())

# Build the table rows
tbl_rows = [
    [QgsTableCell(h) for h in tbl_headers],
    [QgsTableCell(v) for v in tbl_rw]
]

# ---------------------------
# Remove existing table if present
# ---------------------------
for item in layout.items():
    if hasattr(item, "customProperty") and item.customProperty("name") == "distance_altitude_table":
        layout.removeLayoutItem(item)
        print("Removed existing distance_altitude_table")
        break

# ---------------------------
# Create manual table
# ---------------------------
t = QgsLayoutItemManualTable.create(layout)
t.setTableContents(tbl_rows)
t.setGridStrokeWidth(0.25)  # line width
t.setCustomProperty("name", "distance_altitude_table")

# Text formatting
text_format = QgsTextFormat()
text_format.setFont(QFont("Arial"))
text_format.setSize(8)
t.setContentTextFormat(text_format)
t.setGridColor(QColor(0, 0, 0, 255))

layout.addMultiFrame(t)

# ---------------------------
# Column widths accounting for cell margin and line width
# ---------------------------
original_total_width = 180.20  # total table width including frame
first_col_width = 36.20        # fixed first column width
num_dynamic_cols = len(tbl_headers) - 1
stroke_width = t.gridStrokeWidth()
cell_margin = 1.0  # mm

total_columns = len(tbl_headers)

# total extra width from vertical lines and cell margins
extra_width = (total_columns - 1) * stroke_width + 2 * cell_margin * total_columns

# remaining width for numeric columns
remaining_width = original_total_width - first_col_width - extra_width
dynamic_col_width = remaining_width / num_dynamic_cols

col_widths = [first_col_width] + [dynamic_col_width] * num_dynamic_cols
t.setColumnWidths(col_widths)

# ---------------------------
# Add frame with exact total width
# ---------------------------
frame_height = 9.8
frame = QgsLayoutFrame(layout, t)
frame.attemptResize(QgsLayoutSize(original_total_width, frame_height, QgsUnitTypes.LayoutMillimeters))
frame.attemptMove(QgsLayoutPoint(19.79, 190.439, QgsUnitTypes.LayoutMillimeters))
t.addFrame(frame)

print(f"✅ Table added dynamically with {len(numeric_data)} numeric columns from JSON")
print(f"Frame width: {original_total_width} mm, first column: {first_col_width} mm, each numeric column: {dynamic_col_width:.2f} mm")

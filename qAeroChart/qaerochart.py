# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAeroChart
                                 A QGIS plugin
 ICAO Aeronautical Chart Plugin
                              -------------------
        begin                : 2025-10-21
        git sha              : $Format:%H$
        copyright            : (C) 2025 by andures
        email                : your.email@example.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolBar

# Initialize Qt resources from file resources.py
# from .resources import *

# Import the code for the DockWidget
from .qaerochart_dockwidget import QAeroChartDockWidget
from .vertical_scale_dialog import VerticalScaleDockWidget
from .horizontal_scale_dialog import HorizontalScaleDockWidget
from .utils.logger import log
from .utils.qt_compat import Qt
import os.path


class QAeroChart:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = (QSettings().value('locale/userLocale') or '')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QAeroChart_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&qAeroChart')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'QAeroChart')
        # self.toolbar.setObjectName(u'QAeroChart')

        # print("** INITIALIZING qAeroChart")

        self.pluginIsActive = False
        self.dockwidget = None
        
        # Map tool manager (will be initialized in initGui)
        self.tool_manager = None

        # Layer manager (will be initialized in initGui)
        self.layer_manager = None
        # Layout toolbar action
        self.distance_table_action = None
        self._layout_toolbar_hooked = False

        # Profile controller (will be initialized in initGui)
        self._profile_manager = None
        self._controller = None

        # Dedicated toolbar for qAeroChart tools
        self.tools_toolbar = None
        self.generate_profile_action = None
        self.vertical_scale_action = None
        self.vertical_scale_dock = None
        # Top-level menu
        self.top_menu = None
        # Vertical scale dock (Issue #57 standalone)
        self.vertical_scale_dock = None
        self.vertical_scale_action = None
        # Horizontal scale dock (Issue #69)
        self.horizontal_scale_dock = None
        self.horizontal_scale_action = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QAeroChart', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, 'icons', 'icon.png')

        # Do not add to default Vector/Plugins menu; we'll create our own top menu
        self.add_action(
            icon_path,
            text=self.tr(u'qAeroChart - ICAO Aeronautical Charts'),
            callback=self.run,
            add_to_menu=False,
            add_to_toolbar=False,
            parent=self.iface.mainWindow())

        # Create dedicated toolbar and "Generate Profile" button (issue #4)
        self.tools_toolbar = self.iface.addToolBar('qAeroChart tools')
        self.tools_toolbar.setObjectName('qAeroChartTools')

        self.generate_profile_action = QAction(QIcon(icon_path), self.tr('Generate Profile'), self.iface.mainWindow())
        self.generate_profile_action.setObjectName('qAeroChartGenerateProfileAction')
        self.generate_profile_action.setStatusTip(self.tr('Open qAeroChart and generate a profile'))
        # For now, reuse existing entry point; opens the dock where user can generate/draw
        self.generate_profile_action.triggered.connect(self.run)
        self.tools_toolbar.addAction(self.generate_profile_action)

        # Vertical Scale action (Issue #57)
        vs_icon_path = os.path.join(self.plugin_dir, 'icons', 'icon_vertical_scale.svg')
        self.vertical_scale_action = QAction(QIcon(vs_icon_path), self.tr('Vertical Scale'), self.iface.mainWindow())
        self.vertical_scale_action.setObjectName('qAeroChartVerticalScaleAction')
        self.vertical_scale_action.setStatusTip(self.tr('Create vertical scale (meters/feet)'))
        self.vertical_scale_action.triggered.connect(self.open_vertical_scale_dock)
        self.tools_toolbar.addAction(self.vertical_scale_action)

        # Horizontal Scale action (Issue #69)
        hs_icon_path = os.path.join(self.plugin_dir, 'icons', 'icon_horizontal_scale.svg')
        if not os.path.exists(hs_icon_path):
            hs_icon_path = os.path.join(self.plugin_dir, 'icons', 'icon.png')
        self.horizontal_scale_action = QAction(QIcon(hs_icon_path), self.tr('Horizontal Scale'), self.iface.mainWindow())
        self.horizontal_scale_action.setObjectName('qAeroChartHorizontalScaleAction')
        self.horizontal_scale_action.setStatusTip(self.tr('Create horizontal scale (meters/feet)'))
        self.horizontal_scale_action.triggered.connect(self.open_horizontal_scale_dock)
        self.tools_toolbar.addAction(self.horizontal_scale_action)

        # Create top-level menu "qAeroChart" and insert it to the right of qPANSOPY if present (issue #3)
        try:
            menu_bar = self.iface.mainWindow().menuBar()
            self.top_menu = QMenu(self.tr('qAeroChart'), self.iface.mainWindow())
            self.top_menu.setObjectName('qAeroChartMenu')
            # Add our primary action
            self.top_menu.addAction(self.generate_profile_action)
            self.top_menu.addAction(self.vertical_scale_action)
            self.top_menu.addAction(self.horizontal_scale_action)

            # Try to position it right after qPANSOPY
            inserted = False
            actions = menu_bar.actions()
            for i, act in enumerate(actions):
                try:
                    title = act.text().replace('&', '').strip()
                except Exception:
                    title = ''
                if title.lower() == 'qpansopy':
                    if i + 1 < len(actions):
                        menu_bar.insertMenu(actions[i + 1], self.top_menu)
                    else:
                        menu_bar.addMenu(self.top_menu)
                    inserted = True
                    break
            if not inserted:
                # Fallback: append at end
                menu_bar.addMenu(self.top_menu)
        except Exception as e:
            print(f"PLUGIN qAeroChart WARNING: Could not create top-level menu: {e}")

        # Layout toolbar action: add distance/altitude table into print layout
        self.distance_table_action = QAction(QIcon(icon_path), self.tr('Add Distance/Altitude Table'), self.iface.mainWindow())
        self.distance_table_action.setObjectName('qAeroChartDistanceTableAction')
        self.distance_table_action.setStatusTip(self.tr('Insert a distance/altitude table into the active layout'))
        self.distance_table_action.triggered.connect(self._open_distance_table_builder)
        # Also hook into layout-designer openings to force-add the action to their toolbars
        try:
            self.iface.layoutDesignerOpened.connect(self._on_layout_designer_opened)
            self._layout_toolbar_hooked = True
        except Exception as e:
            print(f"PLUGIN qAeroChart WARNING: Could not hook layoutDesignerOpened: {e}")
        try:
            if self.top_menu:
                self.top_menu.addAction(self.distance_table_action)
        except Exception:
            pass
        
        # Initialize map tool manager — wrapped in try/except so a failure here
        # does NOT prevent layer_manager / controller from initialising (the
        # critical path for creating layers).
        try:
            from .tools import ProfilePointToolManager
            self.tool_manager = ProfilePointToolManager(
                self.iface.mapCanvas(),
                self.iface
            )
            log("Tool manager initialized")
        except Exception as e:
            print(f"[qAeroChart] WARNING: tool_manager init failed: {e}")
            log(f"Tool manager init failed: {e}", "WARNING")
            self.tool_manager = None

        # Initialize layer manager and profile controller
        from .core import LayerManager, ProfileManager, ProfileController
        self.layer_manager = LayerManager(self.iface)
        self._profile_manager = ProfileManager()
        self._controller = ProfileController(self._profile_manager, self.layer_manager)
        log("Layer manager and profile controller initialized")

    # --------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        log("Cleaning up...")

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        log("Unloading...")

        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&qAeroChart'),
                action)
            self.iface.removeToolBarIcon(action)
        # Remove custom toolbar and its action
        if self.tools_toolbar:
            if self.generate_profile_action:
                try:
                    self.tools_toolbar.removeAction(self.generate_profile_action)
                except Exception:
                    pass
            try:
                # QGIS will handle deletion of toolbar instance
                self.iface.mainWindow().removeToolBar(self.tools_toolbar)
            except Exception:
                pass
            self.tools_toolbar = None
            self.generate_profile_action = None
        # Remove top-level menu
        if self.top_menu:
            try:
                self.iface.mainWindow().menuBar().removeAction(self.top_menu.menuAction())
            except Exception:
                pass
            self.top_menu = None

        # Close vertical scale dock
        if self.vertical_scale_dock:
            try:
                self.iface.removeDockWidget(self.vertical_scale_dock)
                self.vertical_scale_dock.deleteLater()
            except Exception:
                pass
            self.vertical_scale_dock = None
            self.vertical_scale_action = None

        # Close horizontal scale dock
        if self.horizontal_scale_dock:
            try:
                self.iface.removeDockWidget(self.horizontal_scale_dock)
                self.horizontal_scale_dock.deleteLater()
            except Exception:
                pass
            self.horizontal_scale_dock = None
            self.horizontal_scale_action = None

        # Clean up tool manager
        if self.tool_manager:
            self.tool_manager.cleanup()
            self.tool_manager = None
        
        # Clean up controller and managers
        self._controller = None
        self._profile_manager = None

        # Clean up layer manager (optional - layers remain in project)
        if self.layer_manager:
            # Uncomment to remove layers on plugin unload:
            # self.layer_manager.remove_all_layers()
            self.layer_manager = None

        # Remove layout toolbar action
        if self.distance_table_action:
            try:
                self.iface.removeLayoutDesignerToolBarIcon(self.distance_table_action)
            except Exception:
                pass
            self.distance_table_action = None
        if self._layout_toolbar_hooked:
            try:
                self.iface.layoutDesignerOpened.disconnect(self._on_layout_designer_opened)
            except Exception:
                pass
            self._layout_toolbar_hooked = False

    # --------------------------------------------------------------------------

    def _active_layout_name(self):
        """Best-effort retrieval of the active layout name in the layout designer."""

        try:
            designer = self.iface.activeLayoutDesignerInterface()
            if designer is not None and hasattr(designer, "layout") and designer.layout() is not None:
                return designer.layout().name()
        except Exception:
            pass
        try:
            designer = self.iface.activeLayoutDesigner()
            if designer is not None and hasattr(designer, "layout") and designer.layout() is not None:
                return designer.layout().name()
        except Exception:
            pass
        return None

    def _open_distance_table_builder(self):
        """Launch the distance/altitude table builder dialog and insert the table."""

        try:
            from .scripts import table_distance_altitude
        except Exception as exc:
            print(f"PLUGIN qAeroChart ERROR: Cannot import table builder: {exc}")
            return

        default_layout = self._active_layout_name()
        parent_window = None
        try:
            designer = self.iface.activeLayoutDesignerInterface()
            if designer is not None:
                parent_window = designer.window()
                self._attach_action_to_designer(designer)
        except Exception:
            parent_window = None
        if parent_window is None:
            try:
                designer = self.iface.activeLayoutDesigner()
                if designer is not None:
                    parent_window = designer
                    self._attach_action_to_designer(designer)
            except Exception:
                parent_window = None

        try:
            table_distance_altitude.run(self.iface, default_layout_name=default_layout, parent_window=parent_window)
        except TypeError:
            # Fallback for environments that still have the older signature
            table_distance_altitude.run(self.iface, default_layout_name=default_layout)

    def _on_layout_designer_opened(self, designer_iface):
        """Ensure our action appears in the layout designer toolbar when a composition opens."""

        try:
            self._attach_action_to_designer(designer_iface)
        except Exception as exc:
            print(f"PLUGIN qAeroChart WARNING: Could not attach action to layout designer: {exc}")

    def _attach_action_to_designer(self, designer_iface):
        if self.distance_table_action is None or designer_iface is None:
            return

        # Preferred: use designer interface API (QGIS 3.x): add to tools toolbar
        try:
            add_method = getattr(designer_iface, 'addActionToToolbar', None)
            if callable(add_method):
                add_method(self.distance_table_action, 'mLayoutDesignerToolsToolbar')
                return
        except Exception:
            pass

        # Fallback: scan toolbars in the designer window
        target_names = {
            'mLayoutDesignerToolsToolbar',
            'mLayoutDesignerAddItemsToolbar',
            'mLayoutDesignerToolbar'
        }

        window = getattr(designer_iface, 'window', None)
        if callable(window):
            window = window()
        if not window:
            return

        toolbars = window.findChildren(QToolBar)
        chosen = None
        for bar in toolbars:
            if bar.objectName() in target_names:
                chosen = bar
                break
        if chosen is None and toolbars:
            chosen = toolbars[0]

        if chosen and self.distance_table_action not in chosen.actions():
            chosen.addAction(self.distance_table_action)

    # --------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            log("Starting...")

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget is None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = QAeroChartDockWidget(
                    iface=self.iface, controller=self._controller
                )

            # Pass tool manager (draw tool lives outside the controller)
            self.dockwidget.tool_manager = self.tool_manager

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

    def open_vertical_scale_dock(self) -> None:
        """Toggle the standalone Vertical Scale dock widget (Issue #67)."""
        try:
            if self.vertical_scale_dock is None:
                self.vertical_scale_dock = VerticalScaleDockWidget(self.iface.mainWindow())
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.vertical_scale_dock)
            elif self.vertical_scale_dock.isVisible():
                self.vertical_scale_dock.hide()
                return
            else:
                self.vertical_scale_dock.show_menu()
            self.vertical_scale_dock.show()
            self.vertical_scale_dock.raise_()
        except Exception as e:
            log(f"Could not open Vertical Scale dock: {e}", "ERROR")

    def open_horizontal_scale_dock(self) -> None:
        """Toggle the standalone Horizontal Scale dock widget (Issue #69)."""
        try:
            if self.horizontal_scale_dock is None:
                self.horizontal_scale_dock = HorizontalScaleDockWidget(self.iface.mainWindow())
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.horizontal_scale_dock)
            elif self.horizontal_scale_dock.isVisible():
                self.horizontal_scale_dock.hide()
                return
            else:
                self.horizontal_scale_dock.show_menu()
            self.horizontal_scale_dock.show()
            self.horizontal_scale_dock.raise_()
        except Exception as e:
            log(f"Could not open Horizontal Scale dock: {e}", "ERROR")

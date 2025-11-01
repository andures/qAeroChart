# -*- coding: utf-8 -*-
"""
Profile Creation Dialog Wrapper
"""

from qgis.PyQt.QtWidgets import QDialog
from .profile_creation_dialog_ui import Ui_ProfileCreationDialogBase


class ProfileCreationDialog(QDialog, Ui_ProfileCreationDialogBase):
    """Dialog for creating profile charts."""
    
    def __init__(self, parent=None):
        """Initialize the dialog."""
        super(ProfileCreationDialog, self).__init__(parent)
        self.setupUi(self)
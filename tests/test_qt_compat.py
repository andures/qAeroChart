"""Tests for the qt_compat compatibility shim (Task 3.1)."""
from qAeroChart.utils.qt_compat import Qt, QMessageBox, QAbstractItemView, QVariant, QColor, QFont


class TestQtCompat:
    def test_user_role_accessible(self):
        assert Qt.UserRole is not None

    def test_item_is_selectable_accessible(self):
        assert Qt.ItemIsSelectable is not None

    def test_custom_context_menu_accessible(self):
        assert Qt.CustomContextMenu is not None

    def test_key_f2_accessible(self):
        assert Qt.Key_F2 is not None

    def test_key_delete_accessible(self):
        assert Qt.Key_Delete is not None

    def test_left_button_accessible(self):
        assert Qt.LeftButton is not None

    def test_cross_cursor_accessible(self):
        assert Qt.CrossCursor is not None


class TestQMessageBoxCompat:
    def test_yes_accessible(self):
        assert QMessageBox.Yes is not None

    def test_no_accessible(self):
        assert QMessageBox.No is not None

    def test_question_callable(self):
        """question() must be callable (delegates to real Qt static method)."""
        assert callable(QMessageBox.question)


class TestQAbstractItemViewCompat:
    def test_extended_selection_accessible(self):
        assert QAbstractItemView.ExtendedSelection is not None


class TestQVariantCompat:
    def test_string_accessible(self):
        assert QVariant.String is not None

    def test_int_accessible(self):
        assert QVariant.Int is not None

    def test_double_accessible(self):
        assert QVariant.Double is not None

    def test_bool_accessible(self):
        assert QVariant.Bool is not None


class TestQColorCompat:
    def test_qcolor_importable(self):
        assert QColor is not None


class TestQFontCompat:
    def test_qfont_importable(self):
        assert QFont is not None

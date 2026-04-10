"""Tests for table item naming (#70) and table bug fixes (Bug A–E)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from qAeroChart.scripts.table_distance_altitude import (
    TABLE_ID_PREFIX as DAT_PREFIX,
    TABLE_NAME as DAT_TABLE_NAME,
    _next_table_id as dat_next_id,
    _remove_existing_table as dat_remove,
)
from qAeroChart.scripts.table_gs_rod import (
    TABLE_ID_PREFIX as GS_PREFIX,
    TABLE_NAME as GS_TABLE_NAME,
    _next_table_id as gs_next_id,
    _remove_existing_table as gs_remove,
)
from qAeroChart.scripts.table_oca_h import (
    TABLE_ID_PREFIX as OCA_PREFIX,
    TABLE_NAME as OCA_TABLE_NAME,
    _next_table_id as oca_next_id,
    _remove_existing_table as oca_remove,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _mock_item(item_id: str) -> MagicMock:
    """Create a mock layout item with the given id()."""
    m = MagicMock()
    m.id.return_value = item_id
    return m


def _mock_multiframe(name_prop: str | None = None) -> MagicMock:
    """Create a mock multiframe with an optional customProperty('name')."""
    mf = MagicMock()
    mf.customProperty.side_effect = lambda key: name_prop if key == "name" else None
    return mf


# ===================================================================
# _next_table_id — unit tests
# ===================================================================

class TestNextTableId:
    """Verify _next_table_id returns correct sequential IDs."""

    @pytest.mark.parametrize("next_fn,prefix", [
        (dat_next_id, DAT_PREFIX),
        (gs_next_id, GS_PREFIX),
        (oca_next_id, OCA_PREFIX),
    ])
    def test_no_existing_items(self, next_fn, prefix):
        layout = MagicMock()
        layout.items.return_value = []
        assert next_fn(layout, prefix) == f"{prefix}001"

    @pytest.mark.parametrize("next_fn,prefix", [
        (dat_next_id, DAT_PREFIX),
        (gs_next_id, GS_PREFIX),
        (oca_next_id, OCA_PREFIX),
    ])
    def test_one_existing(self, next_fn, prefix):
        layout = MagicMock()
        layout.items.return_value = [_mock_item(f"{prefix}001")]
        assert next_fn(layout, prefix) == f"{prefix}002"

    def test_gaps_in_sequence(self):
        layout = MagicMock()
        layout.items.return_value = [
            _mock_item(f"{DAT_PREFIX}001"),
            _mock_item(f"{DAT_PREFIX}003"),
        ]
        assert dat_next_id(layout, DAT_PREFIX) == f"{DAT_PREFIX}004"

    def test_ignores_other_prefixes(self):
        layout = MagicMock()
        layout.items.return_value = [_mock_item(f"{GS_PREFIX}001")]
        assert dat_next_id(layout, DAT_PREFIX) == f"{DAT_PREFIX}001"

    def test_handles_non_numeric_suffix(self):
        item = MagicMock()
        item.id.return_value = f"{DAT_PREFIX}abc"
        layout = MagicMock()
        layout.items.return_value = [item]
        assert dat_next_id(layout, DAT_PREFIX) == f"{DAT_PREFIX}001"

    def test_handles_item_without_id(self):
        item = MagicMock(spec=[])
        layout = MagicMock()
        layout.items.return_value = [item]
        assert dat_next_id(layout, DAT_PREFIX) == f"{DAT_PREFIX}001"

    def test_zero_padded_three_digits(self):
        layout = MagicMock()
        layout.items.return_value = []
        result = dat_next_id(layout, DAT_PREFIX)
        suffix = result[len(DAT_PREFIX):]
        assert len(suffix) == 3
        assert suffix == "001"


# ===================================================================
# _remove_existing_table — Bug A fix tests
# ===================================================================

class TestRemoveExistingTable:
    """Verify _remove_existing_table uses multiFrames(), not items()."""

    @pytest.mark.parametrize("remove_fn,table_name", [
        (dat_remove, DAT_TABLE_NAME),
        (gs_remove, GS_TABLE_NAME),
        (oca_remove, OCA_TABLE_NAME),
    ])
    def test_removes_matching_multiframe(self, remove_fn, table_name):
        mf = _mock_multiframe(table_name)
        layout = MagicMock()
        layout.multiFrames.return_value = [mf]

        remove_fn(layout)

        layout.removeMultiFrame.assert_called_once_with(mf)

    @pytest.mark.parametrize("remove_fn,table_name", [
        (dat_remove, DAT_TABLE_NAME),
        (gs_remove, GS_TABLE_NAME),
        (oca_remove, OCA_TABLE_NAME),
    ])
    def test_noop_when_no_match(self, remove_fn, table_name):
        mf = _mock_multiframe("some_other_table")
        layout = MagicMock()
        layout.multiFrames.return_value = [mf]

        remove_fn(layout)

        layout.removeMultiFrame.assert_not_called()

    @pytest.mark.parametrize("remove_fn", [dat_remove, gs_remove, oca_remove])
    def test_noop_when_empty(self, remove_fn):
        layout = MagicMock()
        layout.multiFrames.return_value = []

        remove_fn(layout)

        layout.removeMultiFrame.assert_not_called()

    def test_removes_all_matching_multiframes(self):
        mf1 = _mock_multiframe(DAT_TABLE_NAME)
        mf2 = _mock_multiframe(DAT_TABLE_NAME)
        layout = MagicMock()
        layout.multiFrames.return_value = [mf1, mf2]

        dat_remove(layout)

        assert layout.removeMultiFrame.call_count == 2


# ===================================================================
# TABLE_ID_PREFIX constants
# ===================================================================

class TestPrefixConstants:
    def test_distance_table_prefix(self):
        assert DAT_PREFIX == "distance_table_"

    def test_gs_table_prefix(self):
        assert GS_PREFIX == "gs_table_"

    def test_oca_table_prefix(self):
        assert OCA_PREFIX == "oca_table_"

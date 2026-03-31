"""
Global pytest configuration.
Imports QGIS mocks before any test module, ensuring qgis.* is available
without a running QGIS instance.
"""
import tests.mocks.qgis_mock  # noqa: F401

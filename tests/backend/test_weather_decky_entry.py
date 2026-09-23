"""Exercise the same async search entry point that Decky invokes."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, Mock


class WeatherDeckyEntryTests(unittest.TestCase):
    def test_weather_preview_and_stop_reach_backend_through_decky(self):
        root = Path(__file__).resolve().parents[2]
        with patch.dict(sys.modules, {"decky": types.ModuleType("decky")}):
            spec = importlib.util.spec_from_file_location("signalbar_weather_colour_main_test", root / "main.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = module.Plugin()
            plugin.engine = Mock()
            plugin.engine.preview_weather.return_value = True
            plugin.engine.stop_weather_preview.return_value = True
            self.assertTrue(asyncio.run(plugin.preview_weather("rain", 1)))
            plugin.engine.preview_weather.assert_called_once_with("rain", 1)
            self.assertTrue(asyncio.run(plugin.stop_weather_preview()))
            plugin.engine.stop_weather_preview.assert_called_once_with()

    def test_search_returns_results_or_diagnostic_without_raising(self):
        root = Path(__file__).resolve().parents[2]
        warnings = []
        decky = types.ModuleType("decky")
        decky.logger = types.SimpleNamespace(warning=warnings.append)
        with patch.dict(sys.modules, {"decky": decky}):
            spec = importlib.util.spec_from_file_location("signalbar_weather_main_test", root / "main.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin = module.Plugin()
            city = {"name": "Paris", "country": "France", "latitude": 48.85, "longitude": 2.35}
            with patch.object(module, "search_cities", return_value=[city]) as search:
                result = asyncio.run(plugin.search_weather_cities("Paris, France"))
                self.assertEqual(result, {"results": [city], "error": ""})
                search.assert_called_once_with("Paris, France")
            with patch.object(module, "search_cities", side_effect=OSError("network unavailable")):
                result = asyncio.run(plugin.search_weather_cities("Paris"))
                self.assertEqual(result["results"], [])
                self.assertIn("network unavailable", result["error"])
                self.assertIn("city search failed", warnings[-1])


if __name__ == "__main__":
    unittest.main()

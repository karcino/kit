# tests/test_setup_cmd.py
"""Tests for the interactive setup wizard."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from kit.cli import app
from kit.config import load_config, save_config, KitConfig

runner = CliRunner()


# ---------------------------------------------------------------------------
# kit setup — interactive wizard
# ---------------------------------------------------------------------------


class TestSetupWizard:
    """Test the interactive `kit setup` command."""

    def test_setup_saves_all_fields(self, tmp_path, monkeypatch):
        """Full happy-path: user provides address, API key, and transport mode."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        result = runner.invoke(
            app,
            ["setup"],
            input="Teststrasse 1, Berlin\nfake-api-key-123\nbicycling\n",
        )
        assert result.exit_code == 0
        assert "Welcome to kit" in result.output

        config = load_config(config_dir=tmp_path / "kit")
        assert config.home == "Teststrasse 1, Berlin"
        assert config.google_maps_api_key == "fake-api-key-123"
        assert config.default_mode == "bicycling"

    def test_setup_shows_api_key_instructions(self, tmp_path, monkeypatch):
        """Setup must print step-by-step instructions for getting a Maps API key."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        result = runner.invoke(
            app,
            ["setup"],
            input="Addr\nkey\ntransit\n",
        )
        assert result.exit_code == 0
        assert "console.cloud.google.com" in result.output
        assert "Directions API" in result.output
        assert "Geocoding API" in result.output
        assert "Create an API key" in result.output

    def test_setup_preserves_existing_config(self, tmp_path, monkeypatch):
        """Running setup on an existing config preserves fields not prompted."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "kit"

        # Pre-save a config with a calendar_id
        existing = KitConfig(calendar_id="work@group.calendar.google.com")
        save_config(existing, config_dir=config_dir)

        result = runner.invoke(
            app,
            ["setup"],
            input="Home\nmy-key\ndriving\n",
        )
        assert result.exit_code == 0

        config = load_config(config_dir=config_dir)
        assert config.calendar_id == "work@group.calendar.google.com"
        assert config.home == "Home"

    def test_setup_uses_defaults_on_empty_input(self, tmp_path, monkeypatch):
        """Pressing Enter on prompts uses sensible defaults."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        result = runner.invoke(
            app,
            ["setup"],
            input="\n\n\n",
        )
        assert result.exit_code == 0

        config = load_config(config_dir=tmp_path / "kit")
        # Default transport mode should be "transit"
        assert config.default_mode == "transit"

    def test_setup_rejects_invalid_transport_mode(self, tmp_path, monkeypatch):
        """Invalid transport mode should re-prompt or show error."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        result = runner.invoke(
            app,
            ["setup"],
            input="Addr\nkey\nhelicopter\ntransit\n",
        )
        assert result.exit_code == 0
        # Should eventually accept a valid mode
        config = load_config(config_dir=tmp_path / "kit")
        assert config.default_mode == "transit"


# ---------------------------------------------------------------------------
# kit setup --check — validate config
# ---------------------------------------------------------------------------


class TestSetupCheck:
    """Test the `kit setup --check` config validation."""

    def test_check_missing_config(self, tmp_path, monkeypatch):
        """--check with no config file reports missing fields."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        result = runner.invoke(app, ["setup", "--check"])
        assert result.exit_code != 0
        assert "home" in result.output.lower() or "address" in result.output.lower()
        assert "api" in result.output.lower()

    def test_check_valid_config_no_network(self, tmp_path, monkeypatch):
        """--check with all fields set passes basic validation (no network call)."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "kit"

        config = KitConfig(
            home="Teststrasse 1, Berlin",
            google_maps_api_key="fake-key",
            default_mode="transit",
        )
        save_config(config, config_dir=config_dir)

        result = runner.invoke(app, ["setup", "--check"])
        # Should pass basic (offline) validation
        assert "home" in result.output.lower() or "address" in result.output.lower()

    def test_check_partial_config(self, tmp_path, monkeypatch):
        """--check with missing API key reports it."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "kit"

        config = KitConfig(home="Berlin")
        save_config(config, config_dir=config_dir)

        result = runner.invoke(app, ["setup", "--check"])
        assert result.exit_code != 0
        assert "api" in result.output.lower()

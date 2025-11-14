"""Configuration loader for database seeding.

Loads seeding configuration from seeding.json to eliminate hardcoded
defaults, mappings, and special rules.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SeedingConfig:
    """Manages seeding configuration loaded from seeding.json."""

    _instance = None
    _config = None

    def __new__(cls):
        """Singleton pattern for configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls) -> "SeedingConfig":
        """Load configuration from seeding.json.

        Path is read from SEEDING_CONFIG_PATH environment variable.
        """
        if cls._config is None:
            # Read path from environment variable
            config_path_str = os.getenv("SEEDING_CONFIG_PATH", "src/config/seeding.json")
            config_path = Path(config_path_str)

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cls._config = json.load(f)
                logger.info("Loaded seeding configuration from %s", config_path)
            except FileNotFoundError:
                logger.error("Seeding configuration not found at %s", config_path)
                raise
            except json.JSONDecodeError as e:
                logger.error("Failed to parse seeding.json: %s", e)
                raise
        return cls()

    def get_user_defaults(self) -> Dict[str, Any]:
        """Get default attributes for seeded users."""
        return self._config["schemas"]["users"]["defaults"].copy()

    def get_user_special_rule(self, name: str) -> Dict[str, Any] | None:
        """Get special rules for a specific user name.

        Returns a copy of the rule dict to allow modifications without affecting config.
        """
        rule = self._config["schemas"]["users"]["transformations"]["name_based_rules"].get(name)
        return rule.copy() if rule else None

    def get_user_parsing_rules(self) -> Dict[str, str]:
        """Get column names for user parsing."""
        return self._config["schemas"]["users"]["fields"]["parsing"]

    def get_property_defaults(self) -> Dict[str, Any]:
        """Get default attributes for main properties."""
        return self._config["schemas"]["properties"]["main"]["defaults"].copy()

    def get_property_field_mappings(self, variant: str = "main") -> Dict[str, str]:
        """Get field→column mappings for properties.

        Args:
            variant: Property variant - "main" or "additional"

        Returns:
            Dictionary mapping field names to column names
        """
        return self._config["schemas"]["properties"][variant]["fields"]["parsing"]

    def get_property_type_mapping(self) -> Dict[str, str]:
        """Get code-to-type mapping for additional properties (Доп column)."""
        return self._config["schemas"]["properties"]["additional"]["transformations"][
            "code_to_type"
        ]

    def get_property_default_type(self) -> str:
        """Get default type for additional properties not in mapping."""
        return self._config["schemas"]["properties"]["additional"]["defaults"]["default_type"]

    def get_additional_property_config(self) -> Dict[str, Any]:
        """Get complete configuration for additional properties."""
        return self._config["schemas"]["properties"]["additional"]

    def get_dop_source_column(self) -> str:
        """Get the column name for additional properties source."""
        return self._config["schemas"]["properties"]["additional"]["fields"]["source_column"]

    def get_inherited_fields(self) -> list:
        """Get list of fields to inherit for additional properties."""
        return self._config["schemas"]["properties"]["additional"]["fields"]["inherited_fields"]

    def get_null_fields(self) -> list:
        """Get list of fields that should be null for additional properties."""
        return self._config["schemas"]["properties"]["additional"]["fields"]["null_fields"]

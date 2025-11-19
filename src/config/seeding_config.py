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

    def get_additional_users(self) -> Dict[str, Dict[str, Any]]:
        """Get users to be added during seeding (from 'add' section).

        Returns:
            Dict mapping user name to attributes dict
        """
        return self._config["schemas"]["users"].get("add", {}).copy()

    def get_user_parsing_rules(self) -> Dict[str, str]:
        """Get column names for user parsing."""
        return self._config["schemas"]["users"]["fields"]["parsing"]

    def get_property_defaults(self) -> Dict[str, Any]:
        """Get default attributes for main properties."""
        return self._config["schemas"]["properties"]["defaults"].copy()

    def get_property_field_mappings(self, variant: str = "main") -> Dict[str, str]:
        """Get field→column mappings for properties.

        Args:
            variant: Property variant - "main" or "additional"

        Returns:
            Dictionary mapping field names to column names
        """
        if variant == "main":
            return self._config["schemas"]["properties"]["fields"]["parsing"]
        else:
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

    def get_debit_parsing_rules(self) -> Dict[str, str]:
        """Get column names for debit parsing."""
        return self._config["schemas"]["debit_transactions"]["fields"]["parsing"]

    def get_debit_account_name(self) -> str:
        """Get the default account name for debits."""
        additional = self._config["schemas"]["debit_transactions"].get("additional", {})
        accounts = additional.get("accounts", {})
        defaults = accounts.get("defaults", {})
        return defaults.get("account_name", "Взносы")

    def get_debit_range_names(self) -> list:
        """Get the range names for debits (list of named ranges in Google Sheets).

        Returns:
            List of range name strings to process sequentially
        """
        range_names = self._config["schemas"]["debit_transactions"]["range_name"]
        # Handle both single string and array of strings
        if isinstance(range_names, list):
            return range_names
        elif isinstance(range_names, str):
            return [range_names]
        else:
            return []

    def get_debit_account_column(self) -> str:
        """Get the column name for account names in debit rows.

        Returns:
            Column name (e.g., 'Счет') or None if using default
        """
        additional = self._config["schemas"]["debit_transactions"].get("additional", {})
        accounts = additional.get("accounts", {})
        fields = accounts.get("fields", {})
        return fields.get("name_column")

    def get_credit_parsing_rules(self) -> Dict[str, str]:
        """Get column names for credit parsing.

        Returns:
            Dict with column mappings for credit data
        """
        return self._config["schemas"]["credit_transactions"]["fields"]["parsing"]

    def get_credit_range_names(self) -> list:
        """Get the range names for credits (list of named ranges in Google Sheets).

        Returns:
            List of range name strings to process sequentially
        """
        range_names = self._config["schemas"]["credit_transactions"]["range_name"]
        # Handle both single string and array of strings
        if isinstance(range_names, list):
            return range_names
        elif isinstance(range_names, str):
            return [range_names]
        else:
            return []

    def get_credit_defaults(self) -> Dict:
        """Get default values and transformations for credits.

        Returns:
            Dict with defaults and name-based transformation rules
        """
        additional = self._config["schemas"]["credit_transactions"].get("additional", {})
        if not additional:
            # Return empty transformations if not configured
            return {
                "transformations": {},
                "defaults": {},
            }
        return additional

    def get_user_range_name(self) -> str:
        """Get the named range name for users.

        Returns:
            Named range name (e.g., 'PropertiesOwners')
        """
        return self._config["schemas"]["users"].get("range_name")

    def get_property_range_name(self) -> str:
        """Get the named range name for properties.

        Returns:
            Named range name (e.g., 'PropertiesOwners')
        """
        return self._config["schemas"]["properties"].get("range_name")

    def get_service_periods(self) -> Dict[str, Dict]:
        """Get service period mappings for all transaction ranges.

        Resolves period references to full period definitions from service_periods block.
        Service periods are shared across both debit and credit transactions.

        Returns:
            Dict mapping range names to period info (name, start_date, end_date)
        """
        # Get the central service periods definitions
        service_periods_defs = self._config["schemas"]["service_periods"]

        result = {}

        # Process debit transaction service period mappings
        debit_range_to_period_ref = self._config["schemas"]["debit_transactions"].get(
            "service_periods", {}
        )
        for range_name, period_ref in debit_range_to_period_ref.items():
            if period_ref in service_periods_defs:
                result[range_name] = service_periods_defs[period_ref]

        # Process credit (expense) service period mappings
        credit_range_to_period_ref = self._config["schemas"]["credit_transactions"].get(
            "service_periods", {}
        )
        for range_name, period_ref in credit_range_to_period_ref.items():
            if period_ref in service_periods_defs:
                result[range_name] = service_periods_defs[period_ref]

        return result

    def get_debit_default_account(self) -> str:
        """Get the default account name for debit transactions.

        Returns:
            Account name (e.g., "Взносы")
        """
        additional = self._config["schemas"]["debit_transactions"].get("additional", {})
        accounts = additional.get("accounts", {})
        defaults = accounts.get("defaults", {})
        return defaults.get("account_name", "Взносы")

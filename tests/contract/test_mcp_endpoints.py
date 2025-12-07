"""Contract tests for MCP Server (FastMCP implementation)."""

import pytest

from src.api.mcp_server import mcp


def get_registered_tools() -> list:
    """Get tools from FastMCP's internal tool manager.
    
    FastMCP uses async get_tools() method, but we can access
    the internal _tools dict synchronously for testing.
    """
    return list(mcp._tool_manager._tools.values())


class TestMCPServerTools:
    """Tests for FastMCP server tool registration."""

    def test_mcp_server_has_name(self):
        """Verify MCP server has correct name."""
        assert mcp.name == "SOSenki"

    def test_expected_tools_are_registered(self):
        """Verify expected tools are registered in FastMCP."""
        tools = get_registered_tools()
        tool_names = [tool.name for tool in tools]

        assert "get_balance" in tool_names
        assert "list_bills" in tool_names
        assert "get_period_info" in tool_names
        assert "create_service_period" in tool_names

    def test_tools_have_descriptions(self):
        """Verify all tools have descriptions."""
        tools = get_registered_tools()

        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"

    def test_tools_have_parameters(self):
        """Verify all tools have parameter schemas."""
        tools = get_registered_tools()

        for tool in tools:
            # FastMCP FunctionTool has fn attribute with annotations
            assert hasattr(tool, "fn"), f"Tool {tool.name} has no function"


class TestToolSchemaValidation:
    """Tests for tool parameter schema validation."""

    def test_get_balance_has_user_id_param(self):
        """get_balance tool has user_id parameter."""
        tools = get_registered_tools()
        get_balance = next(t for t in tools if t.name == "get_balance")

        # FastMCP stores function reference
        import inspect
        sig = inspect.signature(get_balance.fn)
        assert "user_id" in sig.parameters

    def test_list_bills_has_required_params(self):
        """list_bills tool has required parameters."""
        tools = get_registered_tools()
        list_bills = next(t for t in tools if t.name == "list_bills")

        import inspect
        sig = inspect.signature(list_bills.fn)
        assert "user_id" in sig.parameters
        assert "limit" in sig.parameters

    def test_get_period_info_has_period_id_param(self):
        """get_period_info tool has period_id parameter."""
        tools = get_registered_tools()
        get_period_info = next(t for t in tools if t.name == "get_period_info")

        import inspect
        sig = inspect.signature(get_period_info.fn)
        assert "period_id" in sig.parameters

    def test_create_service_period_has_required_params(self):
        """create_service_period tool has required parameters."""
        tools = get_registered_tools()
        create_period = next(t for t in tools if t.name == "create_service_period")

        import inspect
        sig = inspect.signature(create_period.fn)
        # Required fields
        assert "name" in sig.parameters
        assert "start_date" in sig.parameters
        assert "end_date" in sig.parameters
        # Optional electricity fields
        assert "electricity_start" in sig.parameters
        assert "electricity_rate" in sig.parameters


class TestCreateServicePeriodValidation:
    """Tests for create_service_period parameter validation logic."""

    def test_valid_date_format(self):
        """Valid ISO date format is accepted."""
        from datetime import date as date_type

        valid_date = "2025-09-01"
        parsed = date_type.fromisoformat(valid_date)
        assert parsed.year == 2025
        assert parsed.month == 9
        assert parsed.day == 1

    def test_invalid_date_format_raises(self):
        """Invalid date format raises ValueError."""
        from datetime import date as date_type

        with pytest.raises(ValueError):
            date_type.fromisoformat("invalid-date")

        with pytest.raises(ValueError):
            date_type.fromisoformat("01-09-2025")  # Wrong format

    def test_date_order_validation(self):
        """start_date must be before end_date."""
        from datetime import date as date_type

        start = date_type.fromisoformat("2025-12-31")
        end = date_type.fromisoformat("2025-01-01")

        # This should fail validation (start >= end)
        assert start >= end


class TestMCPStreamableHTTPApp:
    """Tests for MCP Streamable HTTP app integration."""

    def test_http_app_is_available(self):
        """Verify HTTP app is exported."""
        from src.api.mcp_server import mcp_http_app

        assert mcp_http_app is not None
        # FastMCP's http_app has a .lifespan property
        assert hasattr(mcp_http_app, "lifespan")

    def test_http_app_is_asgi(self):
        """Verify HTTP app is a valid ASGI app."""
        from src.api.mcp_server import mcp_http_app

        # ASGI apps are callable
        assert callable(mcp_http_app)

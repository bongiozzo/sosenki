"""Contract tests for Makefile integration.

Tests for the `make seed` target and process integration.
"""

import subprocess
from pathlib import Path


class TestMakefileIntegration:
    """Contract tests for Makefile seed target (T036-T039)."""

    @staticmethod
    def get_project_root():
        """Get project root directory dynamically."""
        return Path(__file__).parent.parent.parent

    def test_make_help_displays_seed_target(self):
        """Test that `make help` documents the seed target (T039)."""
        project_root = self.get_project_root()
        result = subprocess.run(
            ["make", "help"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"make help failed: {result.stderr}"
        output = result.stdout

        # Verify seed target is documented
        assert "make seed" in output, "Seed target not found in help"
        assert "seed" in output.lower(), "Seed documentation missing"

    def test_make_help_mentions_offline_requirement(self):
        """Test that `make help` mentions offline requirement (T037)."""
        project_root = self.get_project_root()
        result = subprocess.run(
            ["make", "help"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout

        # Verify offline requirement is mentioned
        offline_mention = (
            "offline" in output.lower()
            or "offline only" in output.lower()
            or "must be offline" in output.lower()
        )
        assert offline_mention, (
            "Offline requirement not mentioned in help. "
            "User must understand app must be stopped before seeding."
        )

    def test_make_seed_target_exists_and_is_callable(self):
        """Test that `make seed` target exists and can be invoked (T036, T038)."""
        # Check that the target exists in the Makefile
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        assert makefile.exists(), "Makefile not found"

        makefile_content = makefile.read_text()
        assert "seed:" in makefile_content, "seed target not defined in Makefile"

        # Check that it references the CLI
        assert "src.cli.seed" in makefile_content, (
            "seed target does not reference Python CLI module"
        )

    def test_makefile_seed_documentation(self):
        """Test that Makefile seed target has clear documentation (T037)."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        # Find the seed target section (including comments above it)
        seed_start = makefile_content.find("# Database Seeding")
        if seed_start == -1:
            seed_start = makefile_content.find("seed:")
        seed_section = makefile_content[seed_start : seed_start + 600]

        # Verify documentation mentions offline requirement
        assert "offline" in seed_section.lower(), (
            "Seed documentation in Makefile does not mention offline requirement"
        )

        # Verify documentation mentions idempotency (either in comments or echo statements)
        has_idempotency_mention = (
            "idempotent" in seed_section.lower()
            or "running twice" in seed_section.lower()
            or "same result" in seed_section.lower()
        )
        assert has_idempotency_mention, (
            "Seed documentation does not mention idempotency characteristics"
        )

    def test_make_phony_targets_include_seed(self):
        """Test that .PHONY includes seed target (T036)."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        # Find .PHONY declaration
        assert ".PHONY:" in makefile_content, ".PHONY declaration not found"

        # Extract phony targets
        phony_line = [line for line in makefile_content.split("\n") if ".PHONY:" in line][0]
        assert "seed" in phony_line, (
            "seed target not declared in .PHONY. "
            "This ensures make seed works correctly."
        )

    def test_make_seed_uses_uv_and_python_cli(self):
        """Test that make seed properly invokes CLI via uv (T036)."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        # Find seed target
        seed_start = makefile_content.find("seed:")
        seed_section = makefile_content[seed_start : seed_start + 500]

        # Should use uv to run the CLI
        assert "uv run" in seed_section, (
            "seed target should use `uv run` for consistency"
        )
        assert "python -m src.cli.seed" in seed_section, (
            "seed target should invoke `python -m src.cli.seed`"
        )

    def test_makefile_seed_has_echo_statements_for_ux(self):
        """Test that seed target has helpful echo statements (T037)."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        # Find seed target
        seed_start = makefile_content.find("seed:")
        seed_section = makefile_content[seed_start : seed_start + 300]

        # Should have echo statements for user feedback
        assert "@echo" in seed_section, (
            "seed target should have @echo statements for user feedback"
        )

    def test_help_target_includes_seed_section(self):
        """Test that help target includes dedicated section for seeding (T039)."""
        result = subprocess.run(
            ["make", "help"],
            cwd="/Users/serpo/Work/SOSenki",
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout

        # Check for dedicated "Database Seeding" section
        has_seeding_section = (
            "Database Seeding" in output
            or "database seeding" in output.lower()
            or "Seeding" in output
        )
        assert has_seeding_section, (
            "help output should include a dedicated section for database seeding"
        )

    def test_makefile_lint_target_exists(self):
        """Test that lint target exists for code style validation (related to Phase 4)."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        assert "lint:" in makefile_content, "lint target not found in Makefile"
        assert "ruff check" in makefile_content, (
            "lint target should use ruff for code style checking"
        )

    def test_makefile_has_standard_targets(self):
        """Test that Makefile includes standard development targets."""
        makefile = Path("/Users/serpo/Work/SOSenki/Makefile")
        makefile_content = makefile.read_text()

        required_targets = ["help", "install", "test", "lint", "format", "seed"]
        for target in required_targets:
            assert f"{target}:" in makefile_content, (
                f"Makefile missing standard target: {target}"
            )

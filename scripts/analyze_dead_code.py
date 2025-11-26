"""Dead code analyzer using vulture and coverage tools."""

import subprocess
from pathlib import Path
from typing import Dict, List


class DeadCodeAnalyzer:
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)

    def analyze(self) -> Dict[str, List[str]]:
        """Run full dead code analysis."""
        # Find unused functions/classes via vulture
        unused_symbols = self._find_unused_symbols()

        return {
            "unused_symbols": unused_symbols,
        }

    def _find_unused_symbols(self) -> List[str]:
        """Use vulture to find unused code."""
        try:
            result = subprocess.run(
                ["vulture", str(self.src_dir), "--min-confidence", "80"],
                capture_output=True,
                text=True,
            )
            # Parse vulture output - each line is an unused symbol
            lines = result.stdout.strip().split("\n")
            return [line for line in lines if line.strip()]
        except Exception as e:
            print(f"Error running vulture: {e}")
            return []


if __name__ == "__main__":
    analyzer = DeadCodeAnalyzer()
    results = analyzer.analyze()
    print(f"\n{'=' * 60}")
    print("Dead Code Analysis Results")
    print(f"{'=' * 60}\n")

    if results["unused_symbols"]:
        print("Unused Symbols (confidence >= 80):")
        for symbol in results["unused_symbols"]:
            print(f"  - {symbol}")
    else:
        print("✓ No unused symbols found")

    print(f"\n{'=' * 60}\n")

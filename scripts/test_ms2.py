"""
Milestone 2 Validation Script
Tests LoL-MDC with real Riot API data to verify compression and quality.

Usage:
    python test_ms2.py --match-ids NA1_123 NA1_456
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import RIOT_API_KEY, RIOT_REGION
from lol_mdc.crawler import RiotAPIClient
from lol_mdc.compactor import LoLMatchCompactor


class Milestone2Validator:
    """Validates Milestone 2 deliverables"""

    def __init__(self):
        self.client = RiotAPIClient(RIOT_API_KEY, RIOT_REGION)
        self.compactor = LoLMatchCompactor()
        self.results = []

    def test_single_match(self, match_id: str) -> Dict[str, Any]:
        """Test compression on a single match"""
        details = self.client.get_match_details(match_id)
        if not details:
            return {
                "match_id": match_id,
                "status": "failed",
                "error": "Failed to fetch details",
            }

        timeline = self.client.get_match_timeline(match_id)
        if not timeline:
            return {
                "match_id": match_id,
                "status": "failed",
                "error": "Failed to fetch timeline",
            }

        try:
            compressed_text, metrics = self.compactor.compress_match(details, timeline)
        except Exception as e:
            return {"match_id": match_id, "status": "failed", "error": str(e)}

        return {
            "match_id": match_id,
            "status": "success",
            "metrics": {
                "raw_tokens": metrics.raw_tokens,
                "compressed_tokens": metrics.compressed_tokens,
                "compression_ratio": metrics.compression_ratio,
            },
            "compressed_text": compressed_text,
            "game_info": {
                "duration_minutes": details["info"]["gameDuration"] // 60,
                "game_mode": details["info"]["gameMode"],
                "patch": details["info"]["gameVersion"],
            },
        }

    def validate_strategic_preservation(
        self, result: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Check if strategic information is preserved in compressed output"""
        compressed = result["compressed_text"]

        return {
            "has_team_compositions": "Blue Team:" in compressed
            and "Red Team:" in compressed,
            "has_winner": "Winner:" in compressed,
            "has_phase_analysis": "PHASE ANALYSIS" in compressed,
            "has_gold_information": "Gold:" in compressed,
            "has_objectives": "Objectives:" in compressed
            or "DRAGON" in compressed
            or "BARON" in compressed,
            "has_structures": "Structures:" in compressed or "TOWER" in compressed,
            "has_timestamps": "m -" in compressed
            or ".0m" in compressed
            or "min" in compressed,
        }

    def run_validation_suite(self, match_ids: List[str]) -> Dict[str, Any]:
        """Run full validation on multiple matches"""
        print(f"Testing {len(match_ids)} matches (target: >=30x compression)")

        results = []
        for i, match_id in enumerate(match_ids, 1):
            print(f"[{i}/{len(match_ids)}] {match_id}...", end=" ")
            result = self.test_single_match(match_id)

            if result["status"] == "success":
                result["strategic_preservation"] = self.validate_strategic_preservation(
                    result
                )
                ratio = result["metrics"]["compression_ratio"]
                status = "OK" if ratio >= 30 else "LOW"
                print(f"{ratio:.1f}x [{status}]")
            else:
                print(f"FAILED: {result['error']}")

            results.append(result)

        return {
            "results": results,
            "summary": self._generate_summary(results),
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics"""
        successful = [r for r in results if r["status"] == "success"]

        if not successful:
            return {
                "total_matches": len(results),
                "successful": 0,
                "failed": len(results),
                "meets_target": False,
            }

        compression_ratios = [r["metrics"]["compression_ratio"] for r in successful]
        avg_ratio = sum(compression_ratios) / len(compression_ratios)

        preservation_summary = {}
        all_checks = [r.get("strategic_preservation", {}) for r in successful]
        if all_checks:
            for key in all_checks[0].keys():
                passed = sum(1 for check in all_checks if check.get(key, False))
                preservation_summary[key] = {
                    "passed": passed,
                    "total": len(all_checks),
                    "percentage": (passed / len(all_checks)) * 100,
                }

        return {
            "total_matches": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "compression": {
                "average_ratio": avg_ratio,
                "min_ratio": min(compression_ratios),
                "max_ratio": max(compression_ratios),
                "target": 30,
                "meets_target": avg_ratio >= 30,
            },
            "strategic_preservation": preservation_summary,
        }

    def print_final_report(self, validation_results: Dict[str, Any]):
        """Print final report"""
        summary = validation_results["summary"]

        print(f"\n{'='*50}")
        print("VALIDATION REPORT")
        print(f"{'='*50}")
        print(f"Matches: {summary['successful']}/{summary['total_matches']} successful")

        if summary["successful"] > 0:
            comp = summary["compression"]
            print(
                f"Compression: {comp['average_ratio']:.1f}x avg ({comp['min_ratio']:.1f}x - {comp['max_ratio']:.1f}x)"
            )
            print(f"Target (>=30x): {'PASS' if comp['meets_target'] else 'FAIL'}")

            print("\nStrategic Preservation:")
            for check, stats in summary["strategic_preservation"].items():
                status = "PASS" if stats["percentage"] >= 90 else "FAIL"
                print(f"  {check}: {stats['passed']}/{stats['total']} [{status}]")

        print(f"{'='*50}")

    def save_report(
        self,
        validation_results: Dict[str, Any],
        output_dir: Path,
    ):
        """Save detailed report to file"""
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / "report.json"
        with open(report_path, "w") as f:
            json.dump(validation_results, f, indent=2)
        print(f"Report saved to: {report_path}")

        examples_dir = output_dir / "examples"
        examples_dir.mkdir(exist_ok=True)

        for result in validation_results["results"]:
            if result["status"] == "success":
                output_file = examples_dir / f"{result['match_id']}_compressed.txt"
                with open(output_file, "w") as f:
                    f.write(result["compressed_text"])

        print(f"Examples saved to: {examples_dir}/")


def get_sample_match_ids(count: int = 10) -> List[str]:
    """Get sample match IDs for testing via manual entry."""
    print(f"Enter {count} match IDs:")
    match_ids = []
    for i in range(count):
        match_id = input(f"  {i+1}: ").strip()
        match_ids.append(match_id)
    return match_ids


def main():
    project_root = Path(__file__).parent.parent
    default_output = project_root / "output" / "milestone2"

    parser = argparse.ArgumentParser(description="Validate Milestone 2 deliverables")
    parser.add_argument(
        "--num-matches", type=int, default=10, help="Number of matches to test"
    )
    parser.add_argument(
        "--match-ids", type=str, nargs="+", help="Specific match IDs to test"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
        help="Output directory",
    )

    args = parser.parse_args()

    validator = Milestone2Validator()

    if args.match_ids:
        match_ids = args.match_ids
    else:
        match_ids = get_sample_match_ids(args.num_matches)

    if not match_ids:
        print("No match IDs provided.")
        return

    validation_results = validator.run_validation_suite(match_ids)
    validator.print_final_report(validation_results)
    validator.save_report(validation_results, args.output_dir)


if __name__ == "__main__":
    main()

"""
Task Generator Script for Milestone 3

Generates reasoning tasks from League of Legends matches.

Usage:
    python generate_tasks.py --match-ids NA1_XXX NA1_YYY ... --output dataset.json
"""

import sys
from pathlib import Path
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lol_mdc.crawler import RiotAPIClient
from lol_mdc.compactor import LoLMatchCompactor
from config import RIOT_API_KEY, RIOT_REGION

from task_generation import (
    ReasoningTask,
    TaskDataset,
    detect_all_patterns,
    get_template,
)


class TaskGenerator:
    """
    Main task generation pipeline.

    Workflow:
    1. Fetch match data from Riot API
    2. Compress using LoL-MDC
    3. Detect patterns
    4. Apply templates
    5. Generate tasks
    """

    def __init__(self):
        self.client = RiotAPIClient(RIOT_API_KEY, RIOT_REGION)
        self.compactor = LoLMatchCompactor()

    def generate_tasks_from_match(self, match_id: str) -> List[ReasoningTask]:
        """
        Generate all possible tasks from a single match.

        Args:
            match_id: Riot match ID (e.g., "NA1_5106582089")

        Returns:
            List of ReasoningTask objects
        """
        details = self.client.get_match_details(match_id)
        if not details:
            print("  Failed to fetch details")
            return []

        if not details.get("info", {}).get("teams"):
            print("  Skipping: incomplete match data")
            return []

        timeline = self.client.get_match_timeline(match_id)
        if not timeline:
            print("  Failed to fetch timeline")
            return []

        compressed_text, metrics = self.compactor.compress_match(details, timeline)
        print(f"  Compressed: {metrics}")

        strategic_events = self.compactor._extract_strategic_events(timeline)
        phase_summaries = self.compactor._extract_phase_summaries(timeline, details)

        compressed_match = {
            "match_id": match_id,
            "compressed_text": compressed_text,
            "strategic_events": strategic_events,
            "phase_summaries": phase_summaries,
        }

        all_patterns = detect_all_patterns(compressed_match)
        total_opportunities = sum(len(opps) for opps in all_patterns.values())
        print(f"  Patterns: {total_opportunities} opportunities")

        tasks = []
        for pattern_type, opportunities in all_patterns.items():
            template = get_template(pattern_type)
            if not template:
                continue

            for opportunity in opportunities:
                try:
                    task = template.create_task(
                        opportunity=opportunity,
                        compressed_match_state=compressed_text,
                        match_id=match_id,
                    )
                    tasks.append(task)
                except Exception as e:
                    print(f"  Warning: {pattern_type} - {e}")

        print(f"  Generated {len(tasks)} tasks")
        return tasks

    def generate_dataset(
        self,
        match_ids: List[str],
        dataset_id: str = "lol_reasoning_v1",
        output_file: str = None,
    ) -> TaskDataset:
        """
        Generate complete dataset from multiple matches.

        Args:
            match_ids: List of match IDs to process
            dataset_id: Identifier for the dataset
            output_file: Where to save the dataset (optional)

        Returns:
            TaskDataset object
        """
        print(f"Generating dataset from {len(match_ids)} matches")

        all_tasks = []
        for i, match_id in enumerate(match_ids, 1):
            print(f"\n[{i}/{len(match_ids)}] {match_id}")
            tasks = self.generate_tasks_from_match(match_id)
            all_tasks.extend(tasks)

        # Deduplicate by task_id
        seen_ids = {}
        unique_tasks = []
        for task in all_tasks:
            if task.task_id not in seen_ids:
                seen_ids[task.task_id] = True
                unique_tasks.append(task)

        if len(unique_tasks) < len(all_tasks):
            print(f"\nDeduplicated: {len(all_tasks)} -> {len(unique_tasks)} tasks")

        dataset = TaskDataset(
            dataset_id=dataset_id,
            version="1.0",
            tasks=unique_tasks,
            metadata={
                "num_matches": len(match_ids),
                "match_ids": match_ids,
                "generation_date": "2026-05-02",
                "compressor_version": "1.0",
                "reasoning_types": [
                    "strategic_planning",
                    "causal_inference",
                    "error_diagnosis",
                ],
            },
        )

        stats = dataset.get_stats()
        print(f"\nDataset: {stats['total_tasks']} tasks, {stats['unique_matches']} matches")

        if output_file:
            dataset.save_to_file(output_file)
            print(f"Saved to: {output_file}")

        return dataset


def main():
    """Command-line interface for task generation"""
    import argparse

    project_root = Path(__file__).parent.parent
    default_output = project_root / "output" / "milestone3" / "dataset.json"

    parser = argparse.ArgumentParser(
        description="Generate reasoning tasks from League of Legends matches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from one match
  python generate_tasks.py --match-ids NA1_5106582089

  # Generate from multiple matches
  python generate_tasks.py --match-ids NA1_XXX NA1_YYY NA1_ZZZ
        """,
    )

    parser.add_argument(
        "--match-ids",
        nargs="+",
        required=True,
        help="Match IDs to process (space-separated)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Output file path",
    )
    parser.add_argument(
        "--dataset-id",
        default="lol_reasoning_v1",
        help="Dataset identifier (default: lol_reasoning_v1)",
    )

    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    generator = TaskGenerator()
    dataset = generator.generate_dataset(
        match_ids=args.match_ids,
        dataset_id=args.dataset_id,
        output_file=str(args.output),
    )

    print(f"\nDone. Generated {len(dataset.tasks)} tasks.")


if __name__ == "__main__":
    main()

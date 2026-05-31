"""
Temporal Filtering for Prospective Tasks

Removes future events from match states to prevent data leakage.
Prospective tasks should only see events UP TO the question timestamp.
"""

import json
import re
from typing import Dict, List, Any


def extract_timestamp_from_line(line: str) -> float:
    """
    Extract timestamp in minutes from a line.

    Patterns matched:
    - "9.0m - Event"
    - "15.0m - Event"
    - "35 minutes"

    Returns:
        Float timestamp in minutes, or -1 if no timestamp found
    """
    # Pattern 1: X.Xm format (most common)
    match = re.search(r"(\d+\.?\d*)m\s*-", line)
    if match:
        return float(match.group(1))

    # Pattern 2: "Duration: X minutes"
    match = re.search(r"Duration:\s*(\d+)\s*minutes?", line, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return -1  # No timestamp found


def filter_match_state_until_timestamp(
    compressed_state: str, timestamp_min: float, keep_summary: bool = True
) -> str:
    """
    Filter compressed match state to only include events up to timestamp.

    Args:
        compressed_state: Full compressed match state
        timestamp_min: Question timestamp (events after this are removed)
        keep_summary: Keep match summary even if it mentions future

    Returns:
        Filtered match state with only past/present events
    """
    lines = compressed_state.split("\n")
    filtered_lines = []

    # A phase summary reflects end-of-phase state, so only show it once the
    # phase has fully elapsed. LATE GAME never completes in a prospective context.
    PHASE_COMPLETE_AT = {"EARLY GAME": 14.0, "MID GAME": 25.0, "LATE GAME": float("inf")}

    in_summary_section = False
    in_phase_section = False
    in_events_section = False
    current_phase_visible = False  # whether lines in the current phase block should be kept

    for line in lines:
        line_stripped = line.strip()

        # Track sections
        if "=== MATCH SUMMARY ===" in line:
            in_summary_section = True
            in_phase_section = False
            in_events_section = False
            filtered_lines.append(line)
            continue

        if "=== PHASE ANALYSIS ===" in line:
            in_summary_section = False
            in_phase_section = True
            in_events_section = False
            filtered_lines.append(line)
            continue

        if "=== KEY EVENTS ===" in line:
            in_summary_section = False
            in_phase_section = False
            in_events_section = True
            filtered_lines.append(line)
            continue

        # Handle summary section
        if in_summary_section:
            # Keep summary but filter "Duration" line to not reveal future
            if "Duration:" in line:
                # Replace with truncated duration
                filtered_lines.append(
                    f"Duration: Up to {timestamp_min} minutes (in progress)"
                )
            elif "Winner:" in line:
                # Remove winner info (it's from the future!)
                filtered_lines.append("Winner: Match in progress")
            else:
                filtered_lines.append(line)
            continue

        # Handle phase analysis section
        if in_phase_section:
            stripped_upper = line_stripped.upper()
            # Detect phase headers (e.g. "EARLY GAME:", "MID GAME:", "LATE GAME:")
            matched_phase = next(
                (p for p in PHASE_COMPLETE_AT if stripped_upper.startswith(p)), None
            )
            if matched_phase is not None:
                current_phase_visible = timestamp_min >= PHASE_COMPLETE_AT[matched_phase]
                if current_phase_visible:
                    filtered_lines.append(line)
            elif current_phase_visible:
                filtered_lines.append(line)
            # else: inside a hidden phase block — skip the line
            continue

        # Handle events section
        if in_events_section:
            # Empty line or section header
            if not line_stripped or line_stripped.endswith(":"):
                filtered_lines.append(line)
                continue

            # Extract timestamp from event line
            event_time = extract_timestamp_from_line(line)

            if event_time == -1:
                # No timestamp, keep it (might be header)
                filtered_lines.append(line)
            elif event_time <= timestamp_min:
                # Past or present event, keep it
                filtered_lines.append(line)
            # else: future event, drop it (don't add to filtered_lines)

            continue

        # Default: keep the line
        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def should_filter_task(task: Dict[str, Any]) -> bool:
    """
    Determine if a task should have its match state filtered.

    Retrospective tasks (Causal Inference, Error Diagnosis) need full context.
    Prospective tasks (Strategic Planning, etc.) should be filtered.

    Args:
        task: Task dictionary

    Returns:
        True if task should be filtered (prospective)
    """
    reasoning_type = task.get("reasoning_type", "")

    # Retrospective tasks need full match state
    retrospective_types = ["causal_inference", "error_diagnosis"]

    return reasoning_type not in retrospective_types


def process_dataset(input_path: str, output_path: str):
    """
    Process entire dataset and filter prospective tasks.

    Args:
        input_path: Path to original dataset JSON
        output_path: Path to save filtered dataset JSON
    """
    # Load dataset
    print(f"Loading dataset from {input_path}...")
    with open(input_path, "r") as f:
        data = json.load(f)

    tasks = data["tasks"]

    # Statistics
    filtered_count = 0
    kept_full_count = 0

    print(f"\nProcessing {len(tasks)} tasks...")

    for task in tasks:
        if should_filter_task(task):
            # Filter this task
            original_state = task["compressed_match_state"]
            timestamp = task.get("timestamp_min")

            if timestamp is not None:
                filtered_state = filter_match_state_until_timestamp(
                    original_state, timestamp
                )
                task["compressed_match_state"] = filtered_state
                filtered_count += 1
            else:
                print(
                    f"Warning: Task {task['task_id']} has no timestamp, skipping filter"
                )
        else:
            # Keep full match state (retrospective task)
            kept_full_count += 1

    # Save filtered dataset
    print(f"\nSaving filtered dataset to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    # Report
    print("\n" + "=" * 70)
    print("FILTERING COMPLETE")
    print("=" * 70)
    print(f"Total tasks: {len(tasks)}")
    print(f"Filtered (prospective): {filtered_count}")
    print(f"Kept full (retrospective): {kept_full_count}")
    print(f"\nOutput saved to: {output_path}")


def validate_filtering(dataset_path: str, sample_size: int = 5):
    """
    Validate that filtering worked correctly.

    Checks that prospective tasks have no future events.

    Args:
        dataset_path: Path to filtered dataset
        sample_size: Number of tasks to check in detail
    """
    with open(dataset_path, "r") as f:
        data = json.load(f)

    tasks = data["tasks"]

    print("\n" + "=" * 70)
    print("VALIDATION CHECK")
    print("=" * 70)

    prospective_tasks = [t for t in tasks if should_filter_task(t)]

    issues_found = []

    for task in prospective_tasks:
        timestamp = task.get("timestamp_min")
        if timestamp is None:
            continue

        match_state = task.get("compressed_match_state", "")
        lines = match_state.split("\n")

        future_events = []
        for line in lines:
            event_time = extract_timestamp_from_line(line)
            if event_time > timestamp:
                future_events.append((event_time, line.strip()))

        if future_events:
            issues_found.append(
                {
                    "task_id": task["task_id"],
                    "timestamp": timestamp,
                    "future_events": len(future_events),
                    "examples": future_events[:3],
                }
            )

    if issues_found:
        print(
            f"\n❌ PROBLEMS FOUND: {len(issues_found)} tasks still have future events"
        )
        for issue in issues_found[:5]:
            print(f"\nTask: {issue['task_id']}")
            print(f"  Timestamp: {issue['timestamp']} min")
            print(f"  Future events found: {issue['future_events']}")
            print(f"  Examples:")
            for time, event in issue["examples"]:
                print(f"    {time}m: {event[:60]}...")
    else:
        print(f"\n✅ VALIDATION PASSED!")
        print(f"Checked {len(prospective_tasks)} prospective tasks")
        print(f"No future events found in any task")

    # Show sample filtered tasks
    print("\n" + "=" * 70)
    print(f"SAMPLE FILTERED TASKS (first {sample_size})")
    print("=" * 70)

    for i, task in enumerate(prospective_tasks[:sample_size], 1):
        print(f"\n{i}. Task: {task['task_id']}")
        print(f"   Type: {task['reasoning_type']}")
        print(f"   Timestamp: {task['timestamp_min']} min")

        match_state = task["compressed_match_state"]

        # Count lines and events
        lines = match_state.split("\n")
        event_lines = [l for l in lines if extract_timestamp_from_line(l) > 0]

        print(
            f"   Match state: {len(lines)} lines, {len(event_lines)} timestamped events"
        )

        # Show last few event lines
        if event_lines:
            print(f"   Latest events:")
            for line in event_lines[-3:]:
                print(f"     {line.strip()[:70]}...")


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python filter_temporal_leakage.py <input_dataset.json> [output_dataset.json]"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = (
        sys.argv[2]
        if len(sys.argv) > 2
        else input_file.replace(".json", "_filtered.json")
    )

    # Process dataset
    process_dataset(input_file, output_file)

    # Validate
    validate_filtering(output_file)

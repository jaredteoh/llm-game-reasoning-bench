import json
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class GamePhase(Enum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"


class LoLMatchCompactor:
    def __init__(self):
        pass

    def count_tokens(self, text: str) -> int:
        words = len(text.split())
        return int(words * 0.75)  # ~1.3 words per token

    def compress_match(
        self, match_details: Dict[str, Any], timeline: Dict[str, Any]
    ) -> Tuple[str, CompactionMetrics]:
        """
        Main compression pipeline.

        Args:
            match_details: Output from /lol/match/v5/matches/{matchId}
            timeline: Output from /lol/match/v5/matches/{matchId}/timeline

        Returns:
            Tuple of (compressed_text, metrics)
        """
        # Calculate baseline token count
        raw_json = json.dumps({"details": match_details, "timeline": timeline})
        raw_tokens = self.count_tokens(raw_json)

        # Extract strategic information
        match_context = self._extract_match_context(match_details)
        phase_summaries = self._extract_phase_summaries(timeline, match_details)
        strategic_events = self._extract_strategic_events(timeline)

        # Generate compact text representation
        compressed_text = self._format_compact_summary(
            match_context, phase_summaries, strategic_events
        )

        compressed_tokens = self.count_tokens(compressed_text)
        compression_ratio = (
            raw_tokens / compressed_tokens if compressed_tokens > 0 else 0
        )

        metrics = CompactionMetrics(
            raw_tokens=raw_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategic_signals_preserved=[
                "match_context",
                "phase_summaries",
                "strategic_events",
            ],
        )

        return compressed_text, metrics

    def _extract_match_context(self, match_details: Dict[str, Any]) -> Dict[str, Any]:
        """Extract high-level match metadata and team compositions"""
        info = match_details.get("info", {})

        participants = info.get("participants", [])
        blue_team = [p for p in participants if p["teamId"] == 100]
        red_team = [p for p in participants if p["teamId"] == 200]

        context = {
            "game_duration_minutes": info.get("gameDuration", 0) // 60,
            "game_version": info.get("gameVersion", "unknown"),
            "blue_team": {
                "champions": [p["championName"] for p in blue_team],
                "win": info.get("teams", [{}])[0].get("win", False),
            },
            "red_team": {
                "champions": [p["championName"] for p in red_team],
                "win": (
                    info.get("teams", [{}])[1].get("win", False)
                    if len(info.get("teams", [])) > 1
                    else False
                ),
            },
        }

        return context

    def _extract_phase_summaries(
        self, timeline: Dict[str, Any], match_details: Dict[str, Any]
    ) -> Dict[GamePhase, Dict[str, Any]]:
        """
        Extract aggregated statistics for each game phase.
        Focuses on macro-level metrics: gold, objectives, and tempo.
        """
        frames = timeline.get("info", {}).get("frames", [])

        phase_data = {
            GamePhase.EARLY: {"frames": [], "duration": (0, self.EARLY_END)},
            GamePhase.MID: {"frames": [], "duration": (self.EARLY_END, self.MID_END)},
            GamePhase.LATE: {"frames": [], "duration": (self.MID_END, float("inf"))},
        }

        # Distribute frames into phases
        for frame in frames:
            timestamp_min = frame.get("timestamp", 0) / 60000  # Convert ms to minutes

            if timestamp_min < self.EARLY_END:
                phase_data[GamePhase.EARLY]["frames"].append(frame)
            elif timestamp_min < self.MID_END:
                phase_data[GamePhase.MID]["frames"].append(frame)
            else:
                phase_data[GamePhase.LATE]["frames"].append(frame)

        # Aggregate statistics for each phase
        summaries = {}
        for phase, data in phase_data.items():
            if not data["frames"]:
                continue

            summaries[phase] = self._aggregate_phase_stats(data["frames"], phase)

        return summaries

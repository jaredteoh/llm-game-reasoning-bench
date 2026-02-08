import json
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field


@dataclass
class CompactionMetrics:
    """Metrics for evaluating compression effectiveness"""
    raw_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategic_signals_preserved: List[str] = field(default_factory=list)
    
    def __str__(self):
        return (f"Raw: {self.raw_tokens:,} tokens | "
                f"Compressed: {self.compressed_tokens:,} tokens | "
                f"Ratio: {self.compression_ratio:.1f}x")


class LoLMatchCompactor:
    """
    Compresses League of Legends match data from raw Riot API format
    into compact summaries suitable for LLM reasoning tasks.
    """
    EARLY_END = 14
    MID_END = 25

    STRATEGIC_EVENTS = {
        'CHAMPION_KILL',
        'BUILDING_KILL',
        'ELITE_MONSTER_KILL',
        'CHAMPION_SPECIAL_KILL',  # Multi-kills, ace, etc.
    }


    def __init__(self):
        pass

    def count_tokens(self, text: str) -> int:
        """Count approximate tokens in a text string."""
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
        raw_json = json.dumps({"details": match_details, "timeline": timeline})
        raw_tokens = self.count_tokens(raw_json)

        match_context = self._extract_match_context(match_details)
        phase_summaries = self._extract_phase_summaries(timeline, match_details)
        strategic_events = self._extract_strategic_events(timeline)

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
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract aggregated statistics for each game phase.
        Focuses on macro-level metrics: gold, objectives, and tempo.
        """
        frames = timeline.get("info", {}).get("frames", [])

        phase_data = {
            "early": {"frames": [], "duration": (0, self.EARLY_END)},
            "mid": {"frames": [], "duration": (self.EARLY_END, self.MID_END)},
            "late": {"frames": [], "duration": (self.MID_END, float("inf"))},
        }

        for frame in frames:
            timestamp_min = frame.get("timestamp", 0) / 60000  # Convert ms to minutes

            if timestamp_min < self.EARLY_END:
                phase_data["early"]["frames"].append(frame)
            elif timestamp_min < self.MID_END:
                phase_data["mid"]["frames"].append(frame)
            else:
                phase_data["late"]["frames"].append(frame)

        summaries = {}
        for phase, data in phase_data.items():
            if not data["frames"]:
                continue

            summaries[phase] = self._aggregate_phase_stats(data["frames"], phase)

        return summaries
    
    def _aggregate_phase_stats(
        self,
        frames: List[Dict[str, Any]],
        phase: str
    ) -> Dict[str, Any]:
        """
        Aggregate frame data into phase-level macro statistics.
        
        Preserves:
        - Gold state and trends
        - Experience advantages
        - Objective control
        - Vision control (aggregated)
        """
        if not frames:
            return {}

        first_frame = frames[0]
        last_frame = frames[-1]
        
        def get_team_gold(frame, team_id):
            """Calculate total team gold from participant frames"""
            participant_frames = frame.get('participantFrames', {})
            return sum(
                pf.get('totalGold', 0) 
                for pid, pf in participant_frames.items()
                if pf.get('teamId') == team_id
            )

        blue_gold_start = get_team_gold(first_frame, 100)
        blue_gold_end = get_team_gold(last_frame, 100)
        red_gold_start = get_team_gold(first_frame, 200)
        red_gold_end = get_team_gold(last_frame, 200)
        
        gold_diff_start = blue_gold_start - red_gold_start
        gold_diff_end = blue_gold_end - red_gold_end
        gold_swing = gold_diff_end - gold_diff_start

        return {
            'phase': phase,
            'gold_state': {
                'blue_total': blue_gold_end,
                'red_total': red_gold_end,
                'difference': gold_diff_end,
                'swing': gold_swing,  # How much gold diff changed during phase
            },
            'frame_count': len(frames),
        }

    def _extract_strategic_events(self, timeline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract only strategically relevant events from timeline.
        
        Filters out:
        - Individual skill usage
        - Minor item purchases
        - Ward placements (aggregate to vision score instead)
        - Detailed positioning data
        """
        frames = timeline.get('info', {}).get('frames', [])
        strategic_events = []
        
        for frame in frames:
            timestamp_min = frame.get('timestamp', 0) / 60000

            for event in frame.get('events', []):
                event_type = event.get('type')

                if event_type not in self.STRATEGIC_EVENTS:
                    continue

                strategic_event = {
                    'timestamp_min': round(timestamp_min, 1),
                    'type': event_type,
                }

                if event_type == 'CHAMPION_KILL':
                    strategic_event.update({
                        'victim': event.get('victimId'),
                        'killer': event.get('killerId'),
                        'assistants': event.get('assistingParticipantIds', []),
                        'bounty': event.get('bounty', 0),
                    })
                    
                elif event_type == 'BUILDING_KILL':
                    strategic_event.update({
                        'building_type': event.get('buildingType'),
                        'lane': event.get('laneType'),
                        'tower_tier': event.get('towerType'),
                        'team_id': event.get('teamId'),
                    })
                    
                elif event_type == 'ELITE_MONSTER_KILL':
                    strategic_event.update({
                        'monster_type': event.get('monsterType'),
                        'monster_subtype': event.get('monsterSubType'),
                        'killer_team_id': event.get('killerTeamId'),
                    })
                
                strategic_events.append(strategic_event)
        
        return strategic_events
    
    def _format_compact_summary(
        self,
        match_context: Dict[str, Any],
        phase_summaries: Dict[str, Dict[str, Any]],
        strategic_events: List[Dict[str, Any]]
    ) -> str:
        """
        Format extracted data into a compact, LLM-friendly text representation.
        
        Uses structured natural language rather than raw JSON to:
        1. Reduce token count
        2. Improve LLM comprehension
        3. Make it easier for humans to validate
        """
        lines = []

        lines.append("=== MATCH SUMMARY ===")
        lines.append(f"Duration: {match_context['game_duration_minutes']} minutes")
        lines.append(f"Patch: {match_context['game_version']}")
        lines.append("")

        blue_champs = ", ".join(match_context['blue_team']['champions'])
        red_champs = ", ".join(match_context['red_team']['champions'])
        winner = "Blue" if match_context['blue_team']['win'] else "Red"
        
        lines.append(f"Blue Team: {blue_champs}")
        lines.append(f"Red Team: {red_champs}")
        lines.append(f"Winner: {winner} Team")
        lines.append("")

        lines.append("=== PHASE ANALYSIS ===")
        for phase in ["early", "mid", "late"]:
            if phase not in phase_summaries:
                continue

            summary = phase_summaries[phase]
            gold_state = summary['gold_state']

            lines.append(f"\n{phase.upper()} GAME:")
            lines.append(
                f"  Gold: Blue {gold_state['blue_total']:,} | "
                f"Red {gold_state['red_total']:,} | "
                f"Diff: {gold_state['difference']:+,} (Swing: {gold_state['swing']:+,})"
            )

        lines.append("\n=== KEY EVENTS ===")

        objective_kills = [e for e in strategic_events if e['type'] == 'ELITE_MONSTER_KILL']
        building_kills = [e for e in strategic_events if e['type'] == 'BUILDING_KILL']
        
        if objective_kills:
            lines.append("\nObjectives:")
            for event in objective_kills:
                timestamp = event['timestamp_min']
                monster = event.get('monster_type', 'Unknown')
                subtype = event.get('monster_subtype', '')
                team = "Blue" if event.get('killer_team_id') == 100 else "Red"
                
                obj_name = f"{monster} {subtype}".strip()
                lines.append(f"  {timestamp:>5.1f}m - {team} takes {obj_name}")
        
        if building_kills:
            lines.append("\nStructures:")
            for event in building_kills:
                timestamp = event['timestamp_min']
                building = event.get('building_type', 'Building')
                tier = event.get('tower_tier', '')
                lane = event.get('lane', '')
                team_destroyed = "Blue" if event.get('team_id') == 100 else "Red"
                team_attacker = "Red" if team_destroyed == "Blue" else "Blue"
                
                building_name = f"{tier} {building}".strip() if tier else building
                location = f" ({lane})" if lane and lane != 'NONE' else ""
                lines.append(f"  {timestamp:>5.1f}m - {team_attacker} destroys {team_destroyed}'s {building_name}{location}")
        
        return "\n".join(lines)
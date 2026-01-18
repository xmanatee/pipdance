"""
Choreography script parsing and data structures.

Supports:
- Pose definitions from JSON files
- Schedule definitions from simplified markdown (timestamp - pose_name)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

JOINT_ORDER = ["J1", "J2", "J3", "J4", "J5", "J6"]

JOINT_MAX_SPEED_DEG = {
    "J1": 180.0,
    "J2": 195.0,
    "J3": 180.0,
    "J4": 225.0,
    "J5": 225.0,
    "J6": 225.0,
}

# Pattern for simplified schedule: "MM:SS - pose_name"
CHECKPOINT_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\w+)")


@dataclass
class Pose:
    """A named arm pose with joint positions in degrees."""
    name: str
    joints_deg: List[float]  # J1-J6 in degrees


@dataclass
class Checkpoint:
    """A point in time when the arm should arrive at a pose."""
    time_s: float  # Arrival time in seconds
    pose_name: str


@dataclass
class Choreography:
    """Complete choreography: poses + timed checkpoints."""
    poses: Dict[str, Pose]
    checkpoints: List[Checkpoint]
    warnings: List[str] = field(default_factory=list)


def load_poses(path: Path) -> Dict[str, Pose]:
    """
    Load pose definitions from JSON.

    Expected format:
    {
      "scenes": [
        {"name": "stand", "joint_positions": {"J1": 0, "J2": 90, ...}},
        ...
      ]
    }
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    poses: Dict[str, Pose] = {}

    for scene in data.get("scenes", []):
        name = scene["name"]
        joints = scene["joint_positions"]
        joints_deg = [float(joints[j]) for j in JOINT_ORDER]
        poses[name] = Pose(name=name, joints_deg=joints_deg)

    return poses


def parse_schedule(path: Path) -> List[Checkpoint]:
    """
    Parse a simplified schedule markdown file.

    Format (one checkpoint per line):
        00:00 - stand
        00:06 - left_down
        00:10 - look_left

    Each line specifies when the arm should ARRIVE at that pose.
    """
    checkpoints: List[Checkpoint] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = CHECKPOINT_RE.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            pose_name = match.group(3)
            time_s = minutes * 60 + seconds
            checkpoints.append(Checkpoint(time_s=time_s, pose_name=pose_name))

    return checkpoints


def load_choreography(
    poses_path: Path | str,
    schedule_path: Path | str,
) -> Choreography:
    """
    Load a complete choreography from pose JSON and schedule markdown.

    Validates that all poses referenced in the schedule exist.
    Checks for speed limit violations between checkpoints.
    """
    poses_path = Path(poses_path)
    schedule_path = Path(schedule_path)

    poses = load_poses(poses_path)
    checkpoints = parse_schedule(schedule_path)
    warnings: List[str] = []

    # Validate all referenced poses exist
    for cp in checkpoints:
        if cp.pose_name not in poses:
            raise ValueError(
                f"Pose '{cp.pose_name}' at {cp.time_s}s not found in poses file. "
                f"Available: {', '.join(sorted(poses.keys()))}"
            )

    # Check speed limits between consecutive checkpoints
    for i in range(1, len(checkpoints)):
        prev = checkpoints[i - 1]
        curr = checkpoints[i]
        duration = curr.time_s - prev.time_s

        if duration <= 0:
            warnings.append(
                f"Invalid timing: {prev.pose_name}@{prev.time_s}s -> "
                f"{curr.pose_name}@{curr.time_s}s (duration={duration}s)"
            )
            continue

        prev_pose = poses[prev.pose_name]
        curr_pose = poses[curr.pose_name]

        for idx, joint in enumerate(JOINT_ORDER):
            delta = abs(curr_pose.joints_deg[idx] - prev_pose.joints_deg[idx])
            speed = delta / duration
            max_speed = JOINT_MAX_SPEED_DEG[joint]

            if speed > max_speed:
                warnings.append(
                    f"Speed limit: {prev.pose_name}->{curr.pose_name} "
                    f"{joint}: {speed:.1f} deg/s > {max_speed} deg/s"
                )

    return Choreography(poses=poses, checkpoints=checkpoints, warnings=warnings)

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

# Conservative speed limits matching URDF joint6 velocity=3 rad/s (~172°/s)
JOINT_MAX_SPEED_DEG = {
    "J1": 172.0,
    "J2": 172.0,
    "J3": 172.0,
    "J4": 172.0,
    "J5": 172.0,
    "J6": 172.0,
}

# Joint position limits from URDF (in degrees)
JOINT_LIMITS_DEG = {
    "J1": (-150.0, 150.0),  # URDF: -2.618 to 2.618 rad
    "J2": (0.0, 180.0),     # URDF: 0 to 3.14 rad
    "J3": (-170.0, 0.0),    # URDF: -2.967 to 0 rad
    "J4": (-100.0, 100.0),  # URDF: -1.745 to 1.745 rad
    "J5": (-70.0, 70.0),    # URDF: -1.22 to 1.22 rad
    "J6": (-120.0, 120.0),  # URDF: -2.0944 to 2.0944 rad
}

# Pattern for simplified schedule: "MM:SS.mmm - pose_name"
CHECKPOINT_RE = re.compile(r"(\d{1,2}):(\d{2})\.(\d{3})\s*[-–]\s*(\w+)")


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
        00:00.000 - stand
        00:06.500 - left_down
        00:10.250 - look_left

    Each line specifies when the arm should ARRIVE at that pose.
    Milliseconds are mandatory (exactly 3 digits).
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
            ms = int(match.group(3))
            pose_name = match.group(4)
            time_s = minutes * 60 + seconds + ms / 1000.0
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

    # Validate joint positions are within URDF limits
    validated_poses = set()
    for cp in checkpoints:
        if cp.pose_name in validated_poses:
            continue
        validated_poses.add(cp.pose_name)

        pose = poses[cp.pose_name]
        for idx, joint in enumerate(JOINT_ORDER):
            pos = pose.joints_deg[idx]
            lower, upper = JOINT_LIMITS_DEG[joint]
            if pos < lower or pos > upper:
                warnings.append(
                    f"Joint limit: pose '{pose.name}' {joint}={pos:.1f}° "
                    f"outside [{lower:.1f}°, {upper:.1f}°]"
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

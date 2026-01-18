"""
Interpolation functions for trajectory generation.

Provides linear, cubic spline, and easing-based interpolation
for smooth motion between choreography checkpoints.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Tuple


class EasingType(Enum):
    """Easing function types for motion profiles."""
    NONE = "none"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


def linear_interpolate(start: float, end: float, t: float) -> float:
    """
    Linear interpolation between two values.

    Args:
        start: Starting value
        end: Ending value
        t: Interpolation factor in [0, 1]

    Returns:
        Interpolated value
    """
    return start + (end - start) * t


def apply_easing(t: float, easing: EasingType) -> float:
    """
    Apply easing function to interpolation factor.

    Uses cubic ease functions for smooth acceleration/deceleration.

    Args:
        t: Linear interpolation factor in [0, 1]
        easing: Type of easing to apply

    Returns:
        Eased interpolation factor in [0, 1]
    """
    if easing == EasingType.NONE:
        return t
    elif easing == EasingType.EASE_IN:
        # Cubic ease-in: slow start, fast end
        return t * t * t
    elif easing == EasingType.EASE_OUT:
        # Cubic ease-out: fast start, slow end
        t1 = 1 - t
        return 1 - t1 * t1 * t1
    elif easing == EasingType.EASE_IN_OUT:
        # Cubic ease-in-out: slow start and end
        if t < 0.5:
            return 4 * t * t * t
        else:
            t1 = -2 * t + 2
            return 1 - t1 * t1 * t1 / 2
    else:
        return t


def interpolate_joints(
    start: List[float],
    end: List[float],
    t: float,
    easing: EasingType = EasingType.NONE,
) -> List[float]:
    """
    Interpolate between two joint position arrays.

    Args:
        start: Starting joint positions
        end: Ending joint positions
        t: Interpolation factor in [0, 1]
        easing: Easing function to apply

    Returns:
        Interpolated joint positions
    """
    t_eased = apply_easing(t, easing)
    return [linear_interpolate(s, e, t_eased) for s, e in zip(start, end)]


def cubic_spline_segment(
    p0: float, p1: float, p2: float, p3: float, t: float
) -> float:
    """
    Catmull-Rom cubic spline interpolation for one segment.

    Uses the 4 control points around the segment to compute
    a smooth curve that passes through p1 and p2.

    Args:
        p0: Point before start (for tangent calculation)
        p1: Segment start point
        p2: Segment end point
        p3: Point after end (for tangent calculation)
        t: Interpolation factor in [0, 1] within segment

    Returns:
        Interpolated value on the spline
    """
    t2 = t * t
    t3 = t2 * t

    # Catmull-Rom basis functions
    return 0.5 * (
        (2 * p1) +
        (-p0 + p2) * t +
        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
        (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    )


class CubicSplineInterpolator:
    """
    Catmull-Rom cubic spline interpolator for smooth joint trajectories.

    Produces continuous velocity through waypoints by considering
    neighboring points for tangent calculation.
    """

    def __init__(self, times: List[float], positions: List[List[float]]):
        """
        Initialize spline interpolator.

        Args:
            times: List of waypoint times in seconds
            positions: List of joint position arrays at each waypoint
        """
        if len(times) != len(positions):
            raise ValueError("Times and positions must have same length")
        if len(times) < 2:
            raise ValueError("Need at least 2 waypoints for interpolation")

        self.times = times
        self.positions = positions
        self.n_joints = len(positions[0])
        self.n_points = len(times)

    def _find_segment(self, t: float) -> Tuple[int, float]:
        """
        Find which segment contains time t and local interpolation factor.

        Returns:
            (segment_index, local_t) where segment_index is into self.times
            and local_t is in [0, 1]
        """
        if t <= self.times[0]:
            return 0, 0.0
        if t >= self.times[-1]:
            return self.n_points - 2, 1.0

        for i in range(self.n_points - 1):
            if self.times[i] <= t < self.times[i + 1]:
                duration = self.times[i + 1] - self.times[i]
                local_t = (t - self.times[i]) / duration if duration > 0 else 0.0
                return i, local_t

        return self.n_points - 2, 1.0

    def interpolate(self, t: float, easing: EasingType = EasingType.NONE) -> List[float]:
        """
        Interpolate joint positions at time t.

        Args:
            t: Time in seconds
            easing: Easing function to apply within each segment

        Returns:
            Joint positions at time t
        """
        seg_idx, local_t = self._find_segment(t)
        local_t = apply_easing(local_t, easing)

        result = []
        for j in range(self.n_joints):
            # Get 4 control points for Catmull-Rom
            # Clamp indices at boundaries
            i0 = max(0, seg_idx - 1)
            i1 = seg_idx
            i2 = min(self.n_points - 1, seg_idx + 1)
            i3 = min(self.n_points - 1, seg_idx + 2)

            p0 = self.positions[i0][j]
            p1 = self.positions[i1][j]
            p2 = self.positions[i2][j]
            p3 = self.positions[i3][j]

            value = cubic_spline_segment(p0, p1, p2, p3, local_t)
            result.append(value)

        return result


def create_interpolator(
    times: List[float],
    positions: List[List[float]],
    interpolation: str = "linear",
) -> "Interpolator":
    """
    Create an interpolator for the given waypoints.

    Args:
        times: List of waypoint times
        positions: List of joint position arrays
        interpolation: "linear" or "cubic"

    Returns:
        Interpolator instance
    """
    if interpolation == "cubic":
        return CubicSplineInterpolator(times, positions)
    else:
        return LinearInterpolator(times, positions)


class LinearInterpolator:
    """Linear interpolator between waypoints."""

    def __init__(self, times: List[float], positions: List[List[float]]):
        if len(times) != len(positions):
            raise ValueError("Times and positions must have same length")
        if len(times) < 2:
            raise ValueError("Need at least 2 waypoints for interpolation")

        self.times = times
        self.positions = positions
        self.n_points = len(times)

    def _find_segment(self, t: float) -> Tuple[int, float]:
        """Find segment and local t for time t."""
        if t <= self.times[0]:
            return 0, 0.0
        if t >= self.times[-1]:
            return self.n_points - 2, 1.0

        for i in range(self.n_points - 1):
            if self.times[i] <= t < self.times[i + 1]:
                duration = self.times[i + 1] - self.times[i]
                local_t = (t - self.times[i]) / duration if duration > 0 else 0.0
                return i, local_t

        return self.n_points - 2, 1.0

    def interpolate(self, t: float, easing: EasingType = EasingType.NONE) -> List[float]:
        """Interpolate joint positions at time t."""
        seg_idx, local_t = self._find_segment(t)
        local_t = apply_easing(local_t, easing)

        start = self.positions[seg_idx]
        end = self.positions[min(seg_idx + 1, self.n_points - 1)]

        return [linear_interpolate(s, e, local_t) for s, e in zip(start, end)]


# Type alias for interpolator protocol
Interpolator = LinearInterpolator | CubicSplineInterpolator

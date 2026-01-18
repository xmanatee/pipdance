"""Piper arm adapter implementations."""


def __getattr__(name: str):
    """Lazy import adapters to avoid importing dependencies until needed."""
    if name == "StandardPiperArm":
        from .standard import StandardPiperArm
        return StandardPiperArm
    if name == "WavesharePiperArm":
        from .waveshare import WavesharePiperArm
        return WavesharePiperArm
    if name == "SimulationPiperArm":
        from .simulation import SimulationPiperArm
        return SimulationPiperArm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["StandardPiperArm", "WavesharePiperArm", "SimulationPiperArm"]

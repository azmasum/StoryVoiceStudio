"""Hardware detection: CPU cores, RAM, GPU/VRAM via CUDA when available.

Never crashes because CUDA or a GPU is missing - CPU mode is always valid.
"""
from __future__ import annotations

import ctypes
import logging
import os
import platform
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Rough quality tiers by (vram_gb, ram_gb)
TIER_LOW = "LOW QUALITY (CPU)"
TIER_BALANCED = "BALANCED"
TIER_HIGH = "HIGH QUALITY"


@dataclass
class HardwareInfo:
    cpu_name: str = "Unknown CPU"
    cpu_cores: int = 1
    ram_gb: float = 0.0
    gpu_name: str = ""
    vram_gb: float = 0.0
    cuda_available: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def recommended_quality(self) -> str:
        if self.cuda_available and self.vram_gb >= 6 and self.ram_gb >= 16:
            return TIER_HIGH
        if self.ram_gb >= 8:
            return TIER_BALANCED
        return TIER_LOW


def _ram_gb() -> float:
    try:
        if os.name == "nt":

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024**3), 1)
        import resource  # pragma: no cover - POSIX only

        return round(resource.getrpagesize() * resource.getrlimit(3) / (1024**3), 1)
    except Exception:  # noqa: BLE001
        return 0.0


def _cpu_name() -> str:
    return platform.processor() or platform.machine() or "Unknown CPU"


def _detect_gpu(info: HardwareInfo) -> None:
    """Probe for NVIDIA GPUs through torch; degrade silently to CPU mode."""
    try:
        import torch  # type: ignore[import-untyped]

        if torch.cuda.is_available():
            info.cuda_available = True
            idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(idx)
            info.gpu_name = getattr(props, "name", "NVIDIA GPU")
            info.vram_gb = round(
                getattr(props, "total_memory", 0) / (1024**3), 1
            )
        else:
            info.notes.append("CUDA not available - running in CPU MODE.")
    except ImportError:
        info.notes.append(
            "PyTorch is not installed - CPU MODE (recommended for Piper TTS)."
        )
    except Exception as exc:  # noqa: BLE001 - any driver error must not crash
        log.debug("GPU probe failed: %s", exc)
        info.notes.append("GPU detection failed - using CPU MODE.")


def detect_hardware() -> HardwareInfo:
    info = HardwareInfo(cpu_name=_cpu_name(), cpu_cores=os.cpu_count() or 1)
    info.ram_gb = _ram_gb()
    _detect_gpu(info)
    log.info("Hardware: %s, %s cores, %.1f GB RAM, quality=%s",
             info.cpu_name, info.cpu_cores, info.ram_gb, info.recommended_quality)
    return info

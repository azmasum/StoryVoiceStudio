"""Audio quality checks run before export."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import soundfile as sf

from audio.dsp.loudness import integrated_lufs, peak_dbfs, true_peak_dbfs


@dataclass
class QualityIssue:
    severity: str      # info | warning | critical
    code: str
    message: str


@dataclass
class QualityReport:
    issues: list[QualityIssue] = field(default_factory=list)
    lufs: float = -70.0
    true_peak: float = -70.0
    duration_seconds: float = 0.0

    @property
    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    def summary_lines(self) -> list[str]:
        return [f"[{i.severity.upper()}] {i.message}" for i in self.issues]


def check_audio(path: str, target_lufs: float = -14.0,
                ceiling_dbtp: float = -1.0,
                missing_chunk_count: int = 0) -> QualityReport:
    """Analyze a rendered file; critical issues should block export."""
    report = QualityReport()
    try:
        data, rate = sf.read(path, dtype="float32")
    except Exception as exc:  # noqa: BLE001
        report.issues.append(QualityIssue(
            "critical", "unreadable", f"Cannot read audio file: {exc}"))
        return report

    mono = data.mean(axis=1) if data.ndim > 1 else data
    report.duration_seconds = len(mono) / rate if rate else 0.0

    peak = peak_dbfs(mono)
    report.true_peak = round(true_peak_dbfs(mono, rate), 2)
    report.lufs = round(integrated_lufs(mono, rate), 2)

    if peak >= -0.05:
        report.issues.append(QualityIssue(
            "critical", "clipping",
            "Audio is clipping (sample peak at or above 0 dBFS)."))

    if missing_chunk_count:
        report.issues.append(QualityIssue(
            "critical", "missing_chunks",
            f"{missing_chunk_count} chunk(s) failed to generate."))

    if report.duration_seconds > 5 and abs(report.lufs - target_lufs) > 3.0:
        report.issues.append(QualityIssue(
            "warning", "loudness",
            f"Integrated loudness {report.lufs} LUFS differs from target "
            f"{target_lufs} LUFS by more than 3 LU."))

    if report.true_peak > ceiling_dbtp + 0.3:
        report.issues.append(QualityIssue(
            "warning", "true_peak",
            f"True peak {report.true_peak} dBTP exceeds ceiling "
            f"{ceiling_dbtp} dBTP."))

    # Long silence detection (>= 6 s of near-digital silence).
    block = rate // 10
    quiet_blocks = 0
    longest_silence = 0.0
    for start in range(0, len(mono), block):
        segment = mono[start:start + block]
        if not len(segment):
            break
        if float(np.max(np.abs(segment))) < 1e-4:
            quiet_blocks += 1
            longest_silence = max(longest_silence, quiet_blocks * block / rate)
        else:
            quiet_blocks = 0
    if longest_silence >= 6.0:
        report.issues.append(QualityIssue(
            "warning", "long_silence",
            f"Found {longest_silence:.1f}s of complete silence."))

    _ = integrated_lufs  # referenced above
    return report


__all__ = ["QualityIssue", "QualityReport", "check_audio"]

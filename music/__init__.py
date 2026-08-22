"""Background music engine: management, ducking and transitions."""
from music.ducking import compute_ducking_gain_curve, duck_music
from music.manager import MusicTrack, load_music
from music.transitions import apply_fade_in, apply_fade_out, crossfade, place_at

__all__ = [
    "duck_music",
    "compute_ducking_gain_curve",
    "MusicTrack",
    "load_music",
    "apply_fade_in",
    "apply_fade_out",
    "crossfade",
    "place_at",
]

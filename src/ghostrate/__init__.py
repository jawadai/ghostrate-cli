"""GhostRate — Audio Steganography & Forensic Tool.

Embed and reveal hidden spoken messages inside music using phase cancellation
and cryptographic key scrambling.
"""

from .cli import (
    read_wav,
    write_stereo_wav,
    write_mono_wav,
    generate_key_sequence,
    apply_key_scrambler,
    linear_resample,
    normalize,
    hide,
    reveal,
    info,
    main,
)

__version__ = "1.0.4"
__all__ = [
    "read_wav",
    "write_stereo_wav",
    "write_mono_wav",
    "generate_key_sequence",
    "apply_key_scrambler",
    "linear_resample",
    "normalize",
    "hide",
    "reveal",
    "info",
    "main",
]


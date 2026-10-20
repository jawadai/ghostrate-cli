#!/usr/bin/env python3
"""GhostRate CLI & Library Core Implementation.

Zero third-party dependencies (uses only standard library wave, struct, argparse).
"""

import argparse
import struct
import sys
import wave


def generate_key_sequence(password: str, length: int):
    """Generates a deterministic bipolar pseudo-random sequence {-1.0, 1.0}
    using a 32-bit FNV-1a hash seed and a 32-bit Xorshift PRNG.
    """
    if not password or not password.strip():
        return [1.0] * length

    seed = 2166136261
    for char in password:
        seed = ((seed ^ ord(char)) * 16777619) & 0xFFFFFFFF
    if seed == 0:
        seed = 1

    state = seed
    seq = [1.0] * length
    chip_size = 4
    current_sign = 1.0

    for i in range(length):
        if i % chip_size == 0:
            state = (state ^ ((state << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
            state = (state ^ (state >> 17)) & 0xFFFFFFFF
            state = (state ^ ((state << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
            current_sign = 1.0 if (state >> 31) == 0 else -1.0
        seq[i] = current_sign

    return seq


def apply_key_scrambler(samples, key_seq):
    """Scrambles or descrambles samples with a bipolar key sequence."""
    n = min(len(samples), len(key_seq))
    return [samples[i] * key_seq[i] for i in range(n)]


def read_wav(file_path):
    """Reads a WAV file and returns (samples_left, samples_right, sample_rate, num_channels)."""
    with wave.open(file_path, "rb") as wf:
        num_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        raw_bytes = wf.readframes(nframes)

    if sampwidth != 2:
        raise ValueError(
            f"Unsupported sample bit-depth: {sampwidth * 8}-bit. Please provide 16-bit PCM WAV."
        )

    num_samples = nframes * num_channels
    fmt = f"<{num_samples}h"
    ints = struct.unpack(fmt, raw_bytes)

    if num_channels == 1:
        mono = [s / 32768.0 for s in ints]
        return mono, mono, framerate, 1
    elif num_channels == 2:
        left = [ints[i * 2] / 32768.0 for i in range(nframes)]
        right = [ints[i * 2 + 1] / 32768.0 for i in range(nframes)]
        return left, right, framerate, 2
    else:
        raise ValueError(f"Unsupported channel count: {num_channels}")


def write_stereo_wav(file_path, left, right, sample_rate):
    """Writes interleaved 16-bit stereo PCM WAV file."""
    nframes = len(left)
    out_ints = []
    for i in range(nframes):
        s_l = max(-1.0, min(1.0, left[i]))
        s_r = max(-1.0, min(1.0, right[i]))
        out_ints.append(int(round(s_l * 32767)))
        out_ints.append(int(round(s_r * 32767)))

    fmt = f"<{len(out_ints)}h"
    raw_bytes = struct.pack(fmt, *out_ints)

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)


def write_mono_wav(file_path, samples, sample_rate):
    """Writes 16-bit mono PCM WAV file."""
    out_ints = [
        int(round(max(-1.0, min(1.0, s)) * 32767)) for s in samples
    ]
    fmt = f"<{len(out_ints)}h"
    raw_bytes = struct.pack(fmt, *out_ints)

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)


def linear_resample(samples, src_rate, dst_rate):
    """Fast linear interpolation resampler."""
    if src_rate == dst_rate:
        return list(samples)
    ratio = dst_rate / src_rate
    dst_len = int(round(len(samples) * ratio))
    out = [0.0] * dst_len
    for i in range(dst_len):
        src_pos = i / ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx + 1 < len(samples):
            out[i] = samples[idx] * (1.0 - frac) + samples[idx + 1] * frac
        elif idx < len(samples):
            out[i] = samples[idx]
    return out


def normalize(samples, target_peak=0.95):
    """Normalizes peak amplitude."""
    peak = max(abs(s) for s in samples) if samples else 0
    if peak == 0:
        return samples
    scale = target_peak / peak
    return [s * scale for s in samples]


def hide(music_path, voice_path, output_path="stego_output.wav", stealth=0.06, password="", key=""):
    """Programmatic API to embed voice into music."""
    password = key or password
    music_l, music_r, music_rate, _ = read_wav(music_path)
    voice_l, _, voice_rate, _ = read_wav(voice_path)

    if voice_rate != music_rate:
        voice_aligned = linear_resample(voice_l, voice_rate, music_rate)
    else:
        voice_aligned = voice_l

    voice_aligned = normalize(voice_aligned, 0.95)
    music_len = len(music_l)

    if password:
        key_seq = generate_key_sequence(password, music_len)
        voice_payload = apply_key_scrambler(voice_aligned, key_seq)
    else:
        voice_payload = voice_aligned

    stego_left = [0.0] * music_len
    stego_right = [0.0] * music_len

    for i in range(music_len):
        m = (music_l[i] + music_r[i]) * 0.5
        v = (voice_payload[i] if i < len(voice_payload) else 0.0) * stealth
        stego_left[i] = max(-1.0, min(1.0, m + v))
        stego_right[i] = max(-1.0, min(1.0, m - v))

    write_stereo_wav(output_path, stego_left, stego_right, music_rate)
    return output_path


def reveal(stego_path, output_path="revealed_voice.wav", password="", key=""):
    """Programmatic API to extract hidden voice from stego WAV."""
    password = key or password
    stego_l, stego_r, sample_rate, num_channels = read_wav(stego_path)

    if num_channels < 2:
        raise ValueError("Input file is Mono. Phase steganography requires a stereo file.")

    nframes = len(stego_l)
    diff = [stego_l[i] - stego_r[i] for i in range(nframes)]

    if password:
        key_seq = generate_key_sequence(password, nframes)
        revealed_raw = apply_key_scrambler(diff, key_seq)
    else:
        revealed_raw = diff

    revealed_voice = normalize(revealed_raw, 0.95)
    write_mono_wav(output_path, revealed_voice, sample_rate)
    return output_path


def info(file_path):
    """Analyzes audio file phase difference."""
    l, r, rate, channels = read_wav(file_path)
    dur = len(l) / rate
    diff_energy = sum((l[i] - r[i]) ** 2 for i in range(len(l))) if channels == 2 else 0
    total_energy = sum((l[i] ** 2 + r[i] ** 2) for i in range(len(l))) + 1e-9 if channels == 2 else 1
    ratio = (diff_energy / total_energy) * 100 if channels == 2 else 0
    return {
        "file": file_path,
        "channels": channels,
        "sample_rate": rate,
        "duration": dur,
        "phase_difference_energy_pct": ratio,
        "has_payload": ratio > 0.05,
    }


def main():
    parser = argparse.ArgumentParser(
        prog="ghostrate",
        description="GhostRate CLI — Audio Steganography & Forensic Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # hide
    p_hide = subparsers.add_parser("hide", help="Embed secret voice into music")
    p_hide.add_argument("music", help="Path to host music WAV file")
    p_hide.add_argument("voice", help="Path to secret voice WAV file")
    p_hide.add_argument("-o", "--output", default="stego_output.wav", help="Output stego WAV path")
    p_hide.add_argument("-s", "--stealth", type=float, default=0.06, help="Stealth gain (default: 0.06)")
    p_hide.add_argument("-k", "--key", "--password", dest="key", default="", help="Cryptographic password")

    # reveal
    p_reveal = subparsers.add_parser("reveal", help="Extract hidden voice from stego WAV")
    p_reveal.add_argument("input", help="Path to stego WAV file")
    p_reveal.add_argument("-o", "--output", default="revealed_voice.wav", help="Output revealed WAV path")
    p_reveal.add_argument("-k", "--key", "--password", dest="key", default="", help="Decryption password")

    # info
    p_info = subparsers.add_parser("info", help="Inspect audio file metadata")
    p_info.add_argument("input", help="Path to WAV file")

    args = parser.parse_args()

    if args.command == "hide":
        print(f"[*] Embedding secret voice from '{args.voice}' into '{args.music}'...")
        out = hide(args.music, args.voice, args.output, args.stealth, args.key)
        print(f"[SUCCESS] Stego audio saved to: {out}")
    elif args.command == "reveal":
        print(f"[*] Extracting secret voice from '{args.input}'...")
        out = reveal(args.input, args.output, args.key)
        print(f"[SUCCESS] Revealed voice saved to: {out}")
    elif args.command == "info":
        res = info(args.input)
        print("--- Audio File Analysis ---")
        print(f"File:        {res['file']}")
        print(f"Channels:    {res['channels']}")
        print(f"Sample Rate: {res['sample_rate']} Hz")
        print(f"Duration:    {res['duration']:.2f} seconds")
        print(f"Phase Difference Energy: {res['phase_difference_energy_pct']:.3f}%")
        if res['has_payload']:
            print("[NOTE] Significant stereo phase difference detected (likely contains a payload)!")
        else:
            print("[NOTE] Audio channels are mono/centered.")


if __name__ == "__main__":
    main()


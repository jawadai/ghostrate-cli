GhostRate is an Audio steganography and forensic command-line tool. Embed and reveal hidden spoken voice messages inside any music track using phase mid-side inversion and phantom center balancing.

* **Filter-Immune:** Survives external audio converters, streaming compression, resamplers, and anti-aliasing downsampling.
* **Forensic Extraction:** Mid-side phase cancellation $(L - R)$ cancels the host music into silence, revealing the secret spoken voice with $+18\text{ dB}$ make-up gain.
* **Zero Dependencies:** Uses only Python's built-in standard library (`wave`, `struct`, `argparse`).

## Installation

```bash
pip install ghostrate
```

Compatible with Python 3.8+ on Linux, macOS, and Windows.

## Quick Start & CLI Usage

### 1. Hide Voice Inside Music

```bash
# Standard stego track:
ghostrate hide music.wav voice.wav -o stego_song.wav --stealth 0.06

# Passcode-protected (scrambles speech with cryptographic sequence):
ghostrate hide music.wav voice.wav -o stego_song.wav --stealth 0.06 --key "MySecret123"
```

* `--stealth 0.06`: Adjusts voice stealth level (`0.03` for nearly invisible, `0.06` for balanced, `0.15` for louder).
* `--key "password"`: Scrambles the voice using a deterministic pseudo-random key sequence. Without this key, decoding yields only white noise.

### 2. Reveal Secret Message from Any Stego File

```bash
# Standard decoding:
ghostrate reveal stego_song.wav -o revealed_secret.wav

# Passcode-protected decoding:
ghostrate reveal stego_song.wav -o revealed_secret.wav --key "MySecret123"
```

Cancels out the host music and recovers the isolated speech.

### 3. Inspect Audio File Phase Correlation

```bash
ghostrate info stego_song.wav
```

Analyzes stereo difference energy to detect whether an audio track contains a hidden payload.

## Programmatic Python Usage

You can also import and use `ghostrate` directly in your Python code:

```python
import ghostrate

# Embed voice in music
ghostrate.hide("music.wav", "voice.wav", output_path="stego_track.wav", stealth=0.06, key="MyPassword")

# Reveal hidden voice
ghostrate.reveal("stego_track.wav", output_path="extracted_voice.wav", key="MyPassword")

# Inspect phase correlation
metadata = ghostrate.info("stego_track.wav")
print(metadata["has_payload"])  # True
print(metadata["sample_rate"])  # 44100
```

## How the Math Works

1. **Phantom Center Normalization:**
   Most commercial songs have wide stereo guitars or synths ($L \ne R$). GhostRate first sums both channels into a phantom center mono base:
   $$M[n] = \frac{\text{Music}_L[n] + \text{Music}_R[n]}{2}$$

2. **Phase Inversion Embedding:**
   $$\text{Left Ear} = M[n] + g \cdot \text{Voice}[n]$$
   $$\text{Right Ear} = M[n] - g \cdot \text{Voice}[n]$$

3. **Phase Cancellation Decoding:**
   $$\text{Decoded} = \text{Left} - \text{Right} = (M - M) + 2g \cdot \text{Voice} = \mathbf{2g \cdot \text{Voice}}$$
   The music cancels to $0$, and the voice doubles in volume.

## Web Studio

An in-browser GUI version is also available at: [https://ghostrate-xi.vercel.app](https://ghostrate-xi.vercel.app)

## License

MIT License. See [LICENSE](LICENSE) for details.

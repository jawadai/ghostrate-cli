import math
import struct
import wave
import unittest
import tempfile
import os
from ghostrate.cli import hide, reveal, info, generate_key_sequence, apply_key_scrambler

class TestGhostRateCLI(unittest.TestCase):
    def setUp(self):
        self.rate = 44100
        self.dur = 1.0
        self.n = int(self.rate * self.dur)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.music_path = os.path.join(self.temp_dir.name, "music.wav")
        self.voice_path = os.path.join(self.temp_dir.name, "voice.wav")
        self.stego_path = os.path.join(self.temp_dir.name, "stego.wav")
        self.revealed_path = os.path.join(self.temp_dir.name, "revealed.wav")

        # Synthesize stereo music
        m_bytes = bytearray()
        for i in range(self.n):
            t = i / self.rate
            val = int(math.sin(2 * math.pi * 440 * t) * 14000)
            m_bytes.extend(struct.pack('<hh', val, val))

        with wave.open(self.music_path, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
            wf.writeframes(m_bytes)

        # Synthesize mono voice
        v_bytes = bytearray()
        for i in range(self.n):
            t = i / self.rate
            val = int(math.sin(2 * math.pi * 880 * t) * 12000)
            v_bytes.extend(struct.pack('<h', val))

        with wave.open(self.voice_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
            wf.writeframes(v_bytes)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_hide_and_reveal_public(self):
        hide(self.music_path, self.voice_path, self.stego_path, stealth=0.06)
        self.assertTrue(os.path.exists(self.stego_path))
        meta = info(self.stego_path)
        self.assertTrue(meta["has_payload"])

        reveal(self.stego_path, self.revealed_path)
        self.assertTrue(os.path.exists(self.revealed_path))

    def test_hide_and_reveal_password(self):
        hide(self.music_path, self.voice_path, self.stego_path, stealth=0.06, key="TestSecret")
        # Decoding with correct key
        reveal(self.stego_path, self.revealed_path, key="TestSecret")
        self.assertTrue(os.path.exists(self.revealed_path))

if __name__ == "__main__":
    unittest.main()

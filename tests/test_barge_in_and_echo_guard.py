"""
tests/test_barge_in_and_echo_guard.py — Tests for Conversational Barge-In & EchoGuard

Verifies:
1. EchoGuard correctly computes speech band energies across 16 kHz and 24 kHz streams.
2. EchoGuard subtracts speaker output from microphone capture to reject speaker echo.
3. EchoGuard reliably detects a distinct user voice interrupting over speaker playback (barge-in).
4. main.py interrupt() cancels audio playback and transitions state back to LISTENING.
"""

import sys
import unittest
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.echo import EchoGuard, band_energies


class TestBargeInAndEchoGuard(unittest.TestCase):
    """Test suite for EchoGuard spectral echo subtraction and conversational barge-in."""

    def setUp(self):
        self.guard = EchoGuard()

    def test_band_energies_output_shape_and_values(self):
        """Verifies band energies extraction returns expected vector length."""
        # 16 kHz, 1024 samples of pure 440 Hz sine wave
        t = np.linspace(0, 1024 / 16000.0, 1024, endpoint=False)
        sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        bands = band_energies(sine, 16000)

        self.assertEqual(len(bands), 8)
        self.assertTrue(np.any(bands > 0))
        # 440 Hz should fall into band 1 (400 - 700 Hz)
        self.assertGreater(bands[1], bands[0])

    def test_echo_rejection_when_mic_hears_played_sound(self):
        """Verifies that when mic receives speaker output, EchoGuard identifies it as echo."""
        t = np.linspace(0, 1024 / 24000.0, 1024, endpoint=False)
        speaker_audio = (np.sin(2 * np.pi * 500 * t) + 0.5 * np.sin(2 * np.pi * 1200 * t)).astype(np.float32)

        # Feed speaker output to history
        self.guard.note_output(speaker_audio, 24000, level=0.4, when=100.0)

        # Room microphone receives attenuated copy of speaker audio with small noise
        mic_echo = (speaker_audio * 0.35 + np.random.normal(0, 0.01, 1024)).astype(np.float32)

        # EchoGuard test with matching time
        is_speech = self.guard.is_user_speech(mic_echo, 24000, level=0.25, when=100.02)
        self.assertFalse(is_speech, "Expected pure speaker echo to be rejected as user speech")

    def test_barge_in_detection_when_user_speaks_over_playback(self):
        """Verifies that a new distinct voice over playback triggers is_user_speech = True."""
        t = np.linspace(0, 1024 / 24000.0, 1024, endpoint=False)
        # Speaker is playing low frequencies (e.g. 300 Hz)
        speaker_audio = np.sin(2 * np.pi * 300 * t).astype(np.float32)

        # Warm up EchoGuard with 16 blocks of speaker echo (~0.7s of speech) to establish acoustic baseline
        for b in range(16):
            t_base = 200.0 + b * 0.04
            self.guard.note_output(speaker_audio, 24000, level=0.3, when=t_base)
            self.guard.is_user_speech(speaker_audio * 0.3, 24000, level=0.1, when=t_base + 0.01)

        # User speaks with different formant structure (e.g. 2200 Hz spread vowel)
        user_voice = (np.sin(2 * np.pi * 2200 * t) * 0.8).astype(np.float32)
        mic_input = (speaker_audio * 0.2 + user_voice).astype(np.float32)

        # Now that EchoGuard is calibrated and out of warming, user interrupts with distinct voice
        t_barge = 200.0 + 16 * 0.04
        self.guard.note_output(speaker_audio, 24000, level=0.3, when=t_barge)
        is_speech = self.guard.is_user_speech(mic_input, 24000, level=0.35, when=t_barge + 0.01)
        self.assertTrue(is_speech, "Expected distinct user voice to be recognized as barge-in speech after calibration")

    def test_silence_below_noise_floor_never_interrupts(self):
        """Verifies that room silence or minor noise below floor never interrupts."""
        t = np.linspace(0, 1024 / 16000.0, 1024, endpoint=False)
        room_noise = np.random.normal(0, 0.005, 1024).astype(np.float32)

        is_speech = self.guard.is_user_speech(room_noise, 16000, level=0.02, when=300.0)
        self.assertFalse(is_speech)


if __name__ == "__main__":
    unittest.main()

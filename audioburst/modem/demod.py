import numpy as np
from typing import List, Optional, Tuple
from audioburst.config import AudioConfig
from audioburst.utils.logger import log


class MultiToneDemodulator:
    def __init__(self, config: AudioConfig):
        self.config=config
        self.sample_rate=config.sample_rate
        self.base_freq=config.base_freq
        self.tone_spacing=config.tone_spacing
        self.num_tones=config.tones
        self.bits_per_tone=config.bits_per_tone
        self.symbol_duration=config.symbol_duration
        self.samples_per_symbol=int(self.sample_rate * self.symbol_duration)
        self._frequencies=self._compute_frequencies()
        self._fft_n=self.samples_per_symbol * 8
        self._window=np.hanning(self.samples_per_symbol)

    def _compute_frequencies(self) -> np.ndarray:
        return np.array([
            self.base_freq + i * self.tone_spacing
            for i in range(self.num_tones)
        ])

    def _detect_tone_powers(self, samples: np.ndarray) -> np.ndarray:
        windowed=samples * self._window
        fft=np.fft.rfft(windowed, n=self._fft_n)
        freqs=np.fft.rfftfreq(self._fft_n, 1.0 / self.sample_rate)
        magnitudes=np.abs(fft)
        tone_powers=np.zeros(self.num_tones, dtype=np.float64)
        for i, freq in enumerate(self._frequencies):
            idx=np.argmin(np.abs(freqs - freq))
            start=max(0, idx - 4)
            end=min(len(magnitudes), idx + 5)
            tone_powers[i]=np.max(magnitudes[start:end])
        return tone_powers

    def decode_symbol(self, samples: np.ndarray) -> Optional[bytes]:
        if len(samples) < self.samples_per_symbol:
            return None
        chunk=samples[:self.samples_per_symbol].astype(np.float64)
        tone_powers=self._detect_tone_powers(chunk)
        max_power=np.max(tone_powers)
        if max_power < 1e-10:
            return b'\x00' * ((self.num_tones + 7) // 8)
        threshold=max_power * 0.15
        bits=0
        for i in range(self.num_tones):
            if tone_powers[i] > threshold:
                bits |= (1 << (self.num_tones - 1 - i))
        num_bytes=(self.num_tones + 7) // 8
        return bits.to_bytes(num_bytes, 'big')

    def decode_stream(self, audio: np.ndarray) -> List[bytes]:
        symbols=[]
        num_symbols=len(audio) // self.samples_per_symbol
        for i in range(num_symbols):
            start=i * self.samples_per_symbol
            end=start + self.samples_per_symbol
            symbol=self.decode_symbol(audio[start:end])
            if symbol is not None:
                symbols.append(symbol)
        return symbols

    def detect_signal_presence(self, samples: np.ndarray) -> bool:
        if len(samples) < self.samples_per_symbol:
            return False
        chunk=samples[:self.samples_per_symbol].astype(np.float64)
        tone_powers=self._detect_tone_powers(chunk)
        noise_floor=np.percentile(tone_powers, 25) + 1e-10
        signal_peak=np.max(tone_powers)
        return signal_peak > noise_floor * 2.0

    @property
    def frequencies(self) -> np.ndarray:
        return self._frequencies

"""desktop/voice/devices.py — audio device resolver (PC-1).

Enumeration + izbor ulaznog/izlaznog audio uređaja preko sounddevice/PortAudio,
sa stabilnim indeksom, human-readable nazivom i validacijom. Rješava "agent me
ne čuje" — bez eksplicitnog `device=` sounddevice tiho koristi sistemski default
koji se može promijeniti. Ovdje se uređaj bira eksplicitno.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float

    @property
    def is_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def is_output(self) -> bool:
        return self.max_output_channels > 0


class AudioDeviceService:
    """Enumeriše i bira audio uređaje (thin wrapper oko sounddevice)."""

    def __init__(self, sd_module: Any = None) -> None:
        import sounddevice as sd

        self._sd = sd_module or sd

    def _list(self) -> list[AudioDevice]:
        devices = self._sd.query_devices()
        result = []
        for index, d in enumerate(devices):
            name = str(d.get("name", f"device-{index}"))
            # Izbaci virtualne "mapper" uređaje (ne sviraju sami po sebi).
            if "Sound Mapper" in name or name.startswith("Primary Sound"):
                continue
            result.append(
                AudioDevice(
                    index=index,
                    name=name,
                    max_input_channels=int(d.get("max_input_channels", 0) or 0),
                    max_output_channels=int(d.get("max_output_channels", 0) or 0),
                    default_samplerate=float(d.get("default_samplerate", 0) or 0),
                )
            )
        return result

    def list_inputs(self) -> list[AudioDevice]:
        return [d for d in self._list() if d.is_input]

    def list_outputs(self) -> list[AudioDevice]:
        return [d for d in self._list() if d.is_output]

    def default_input(self) -> AudioDevice | None:
        try:
            info = self._sd.query_devices(kind="input")
            return AudioDevice(
                index=int(info["index"]) if "index" in info else 0,
                name=str(info.get("name", "default")),
                max_input_channels=int(info.get("max_input_channels", 0) or 0),
                max_output_channels=int(info.get("max_output_channels", 0) or 0),
                default_samplerate=float(info.get("default_samplerate", 0) or 0),
            )
        except Exception:
            inputs = self.list_inputs()
            return inputs[0] if inputs else None

    def default_output(self) -> AudioDevice | None:
        try:
            info = self._sd.query_devices(kind="output")
            return AudioDevice(
                index=int(info["index"]) if "index" in info else 0,
                name=str(info.get("name", "default")),
                max_input_channels=int(info.get("max_input_channels", 0) or 0),
                max_output_channels=int(info.get("max_output_channels", 0) or 0),
                default_samplerate=float(info.get("default_samplerate", 0) or 0),
            )
        except Exception:
            outputs = self.list_outputs()
            return outputs[0] if outputs else None

    def resolve_input(self, index: int | None) -> AudioDevice | None:
        """Vrati uređaj po indeksu; None/nevalidan → system default. Nikad ne diže."""
        if index is None:
            return self.default_input()
        for d in self.list_inputs():
            if d.index == index:
                return d
        return self.default_input()

    def resolve_output(self, index: int | None) -> AudioDevice | None:
        if index is None:
            return self.default_output()
        for d in self.list_outputs():
            if d.index == index:
                return d
        return self.default_output()

    def is_valid_input(self, index: int) -> bool:
        return any(d.index == index for d in self.list_inputs())

    def is_valid_output(self, index: int) -> bool:
        return any(d.index == index for d in self.list_outputs())

"""Testovi za audio device resolver (PC-1)."""

from desktop.voice.devices import AudioDevice, AudioDeviceService


class _FakeSD:
    def __init__(self, devices, kind_map):
        self._devices = devices
        self._kind_map = kind_map

    def query_devices(self, kind=None):
        if kind is None:
            return self._devices
        return self._kind_map.get(kind)


def _make_devices():
    return [
        {"name": "Mic A", "max_input_channels": 1, "max_output_channels": 0, "default_samplerate": 48000},
        {"name": "Speakers", "max_input_channels": 0, "max_output_channels": 2, "default_samplerate": 48000},
        {"name": "Headset", "max_input_channels": 1, "max_output_channels": 2, "default_samplerate": 44100},
    ]


def _service():
    devices = _make_devices()
    sd = _FakeSD(devices, {"input": devices[0], "output": devices[1]})
    return AudioDeviceService(sd_module=sd)


def test_list_inputs_only_input_devices():
    svc = _service()
    inputs = svc.list_inputs()
    assert [d.name for d in inputs] == ["Mic A", "Headset"]


def test_list_outputs_only_output_devices():
    svc = _service()
    outputs = svc.list_outputs()
    assert [d.name for d in outputs] == ["Speakers", "Headset"]


def test_default_input_and_output():
    svc = _service()
    assert svc.default_input().name == "Mic A"
    assert svc.default_output().name == "Speakers"


def test_resolve_input_none_returns_default():
    svc = _service()
    assert svc.resolve_input(None).name == "Mic A"


def test_resolve_input_valid_index():
    svc = _service()
    # Headset je index 2 (input)
    assert svc.resolve_input(2).name == "Headset"


def test_resolve_input_invalid_index_falls_back_to_default():
    svc = _service()
    assert svc.resolve_input(999).name == "Mic A"
    assert svc.resolve_input(1).name == "Mic A"  # 1 je output-only


def test_is_valid_input_and_output():
    svc = _service()
    assert svc.is_valid_input(0) is True
    assert svc.is_valid_input(1) is False  # output-only
    assert svc.is_valid_output(1) is True


def test_virtual_mapper_devices_filtered():
    devices = [
        {"name": "Microsoft Sound Mapper - Output", "max_input_channels": 0, "max_output_channels": 2, "default_samplerate": 48000},
        {"name": "Primary Sound Driver", "max_input_channels": 0, "max_output_channels": 2, "default_samplerate": 48000},
        {"name": "Speakers (Realtek)", "max_input_channels": 0, "max_output_channels": 2, "default_samplerate": 48000},
    ]
    sd = _FakeSD(devices, {"output": devices[2]})
    svc = AudioDeviceService(sd_module=sd)
    outputs = svc.list_outputs()
    assert [d.name for d in outputs] == ["Speakers (Realtek)"]

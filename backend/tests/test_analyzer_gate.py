import pytest
from app.analyzers.humacount30ts import HumaCount30TSAdapter
from app.analyzers.base import UnsupportedDeviceFormat

def test_humacount_adapter_fails_closed():
    with pytest.raises(UnsupportedDeviceFormat):
        HumaCount30TSAdapter().parse(b"synthetic-not-a-real-device-message")

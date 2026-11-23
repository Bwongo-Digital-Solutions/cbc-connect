from .base import AnalyzerAdapter, UnsupportedDeviceFormat

class HumaCount30TSAdapter(AnalyzerAdapter):
    """Intentionally disabled until model/firmware/interface and sample exports are confirmed."""
    def parse(self, payload: bytes):
        raise UnsupportedDeviceFormat(
            "HumaCount 30TS parser is not validated. Supply de-identified real exports and "
            "confirm firmware, interface, baud/framing or TCP settings, and vendor protocol."
        )

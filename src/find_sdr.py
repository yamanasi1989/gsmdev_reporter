#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
import SoapySDR

class SdrFinder:
    # SoapySDR driver -> (людська назва, префікс osmosdr)
    DRIVERS = {
        "rtlsdr":  ("RTL-SDR", "rtl"),
        "hackrf":  ("HackRF", "hackrf"),
        "lime":    ("LimeSDR", "soapy"), 
        "bladerf": ("bladeRF", "bladerf"),
    }

    def __init__(self, drivers=None):
        self.drivers = drivers if drivers is not None else self.DRIVERS

    def soapy_devices(self):
        counters = defaultdict(int)
        result = []
        for d in SoapySDR.Device.enumerate():
            dev = {str(k): str(v) for k, v in dict(d).items()}
            driver = dev.get("driver", "unknown")
            instance = counters[driver]
            counters[driver] += 1

            args = f"driver={driver}"
            if dev.get("serial"):
                args += f",serial={dev['serial']}"

            name, osmo = self.drivers.get(driver, (driver, driver))

            dev["instance"] = instance
            dev["id"] = f"{driver}:{instance}"
            dev["type"] = name
            dev["soapy_args"] = args
            dev["device_args"] = f"{osmo}={instance}"

            result.append(dev)
        return result

    def find(self):
        out = {
            "devices": [],
            "errors": [],
        }
        try:
            out["devices"] = self.soapy_devices()
        except Exception as e:
            out["errors"].append(f"soapysdr_devices: {e}")
        return out

    def to_json(self, indent=2):
        return json.dumps(self.find(), indent=indent)


def main():
    finder = SdrFinder()
    sys.stdout.write(finder.to_json())
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
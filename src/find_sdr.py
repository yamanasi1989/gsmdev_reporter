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

    # (vid, pid) -> (driver, назва)
    KNOWN_USB = {
        ("0bda", "2838"): ("rtlsdr", "RTL-SDR"),
        ("0bda", "2832"): ("rtlsdr", "RTL-SDR"),
        ("1d50", "6089"): ("hackrf", "HackRF One"),
        ("1d50", "6108"): ("lime", "LimeSDR"),
        ("1d50", "6109"): ("lime", "LimeSDR Mini"),
        ("2cf0", "5250"): ("bladerf", "bladeRF x40/x115"),
        ("2cf0", "5246"): ("bladerf", "bladeRF 2.0"),
    }

    def __init__(self, drivers=None, known_usb=None):
        self.drivers = drivers if drivers is not None else self.DRIVERS
        self.known_usb = known_usb if known_usb is not None else self.KNOWN_USB

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

    def usb_devices(self):
        try:
            import usb.core
            import usb.util
        except ImportError:
            return []

        counters = defaultdict(int)
        found = []
        for d in usb.core.find(find_all=True) or []:
            key = (f"{d.idVendor:04x}", f"{d.idProduct:04x}")
            if key not in self.known_usb:
                continue

            driver, name = self.known_usb[key]
            instance = counters[driver]
            counters[driver] += 1
            _, osmo = self.drivers.get(driver, (driver, driver))

            port_path = ".".join(map(str, d.port_numbers)) if d.port_numbers else ""

            dev = {
                "driver": driver,
                "instance": instance,          # порядок в USB-переліку
                "id": f"{driver}:{instance}",
                "type": name,
                "vendor_id": key[0],
                "product_id": key[1],
                "bus": str(d.bus),
                "address": str(d.address),
                "port_path": port_path,
                # збігається з іменем у /sys/bus/usb/devices/, напр. "1-2.3"
                "usb_id": f"{d.bus}-{port_path}" if port_path else str(d.bus),
                "device_args": f"{osmo}={instance}",
                "soapy_instance": None,        # заповнюється в merge()
            }

            # серійник читається без claim інтерфейсу, тож працює і для зайнятого пристрою
            try:
                if d.iSerialNumber:
                    dev["serial"] = usb.util.get_string(d, d.iSerialNumber)
            except Exception:
                pass

            found.append(dev)
        return found

    @staticmethod
    def _norm(serial):
        return serial.strip().lower() if serial else None

    def merge(self, soapy, usb_list):
        """Для кожного USB-пристрою знаходить відповідний запис SoapySDR
        за (driver, serial) і проставляє soapy_instance та soapy_args.
        Якщо збігу немає (пристрій зайнятий або немає модуля) — None."""
        pool = defaultdict(list)
        for s in soapy:
            sn = self._norm(s.get("serial"))
            if sn:
                pool[(s["driver"], sn)].append(s)

        for u in usb_list:
            sn = self._norm(u.get("serial"))
            candidates = pool.get((u["driver"], sn)) if sn else None
            if candidates:
                # pop(0): однакові серійники (типово для RTL-SDR) роздаються по черзі
                s = candidates.pop(0)
                u["soapy_instance"] = s["instance"]
                u["soapy_args"] = s["soapy_args"]
                u["device_args"] = s["device_args"]
        return usb_list

    def find(self):
        out = {
            "devices": [],
            "usb_devices": [],
            "errors": [],
        }
        for key, fn in (("devices", self.soapy_devices),
                        ("usb_devices", self.usb_devices)):
            try:
                out[key] = fn()
            except Exception as e:
                out["errors"].append(f"{key}: {e}")

        try:
            self.merge(out["devices"], out["usb_devices"])
        except Exception as e:
            out["errors"].append(f"merge: {e}")
        return out

    def to_json(self, indent=2):
        return json.dumps(self.find(), indent=indent)


def main():
    finder = SdrFinder()
    sys.stdout.write(finder.to_json())
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-soapysdr \
        python3-usb \
        libusb-1.0-0 \
        soapysdr-module-rtlsdr \
        soapysdr-module-hackrf \
        soapysdr-module-lms7 \
        soapysdr-module-bladerf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY src/find_sdr.py .

ENTRYPOINT ["python3", "find_sdr.py"]
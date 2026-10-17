#!/usr/bin/env python3
"""Set the XRP eye servos to fixed angles while Kefali is stopped."""

import argparse
import subprocess
import sys
import time

import serial

import config


LIMITS = {3: (30.0, 90.0), 4: (30.0, 900.0)}


def ping(port):
    port.write(b'PING\n')
    port.flush()
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if port.readline().strip() == b'PONG':
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--horizontal', type=float, help='Servo 3 angle, 30-90 degrees; 60 is center')
    parser.add_argument('--vertical', type=float, help='Servo 4 angle, 30-60 degrees')
    args = parser.parse_args()
    commands = [(3, args.horizontal), (4, args.vertical)]
    commands = [(port, angle) for port, angle in commands if angle is not None]
    if not commands:
        parser.error('provide --horizontal and/or --vertical')
    for port, angle in commands:
        low, high = LIMITS[port]
        if not low <= angle <= high:
            parser.error(f'Servo {port} must be between {low:g} and {high:g} degrees')

    result = subprocess.run(
        ['systemctl', 'show', 'kefali.service', '-p', 'ActiveState', '--value'],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != 'inactive':
        parser.error('stop kefali.service before using this command')

    device = serial.Serial(port=None, baudrate=config.XRP_SERIAL_BAUD,
                           timeout=0.5, exclusive=True)
    device.dtr = False
    device.port = config.XRP_SERIAL_PORT
    device.open()
    try:
        time.sleep(2.3)
        device.reset_input_buffer()
        if not ping(device):
            raise RuntimeError('XRP did not answer PING; no servo command sent')
        for port, angle in commands:
            device.write(f'S:{port}:{angle:g}\n'.encode('ascii'))
            device.flush()
            if not ping(device):
                raise RuntimeError(f'XRP stopped responding after Servo {port} command')
            print(f'Servo {port}: commanded {angle:g} degrees; XRP responded')
    finally:
        device.close()


if __name__ == '__main__':
    try:
        main()
    except (OSError, serial.SerialException, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)

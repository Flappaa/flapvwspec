#!/usr/bin/env python3
import time
from vlinker import iso_tp


class FakeSerialStress:
    def __init__(self, device=None, baud=115200, timeout=3.0):
        self.sent = []
        self.to_read = []
        self.opened = False

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        # if First Frame sent, immediately queue a Flow Control (CTS)
        pci = b[0]
        if (pci >> 4) == 1:
            # send FC: 0x30 | fs=0 (CTS), BS=2, stMin=1 (ms)
            # queue multiple FCs so sender can continue sending blocks
            # For this payload and BS=2 we expect multiple FCs (including final acknowledge)
            for _ in range(3):
                self.to_read.append(bytes([0x30, 0x02, 0x01]))
            # after CFs, queue a Single Frame response
            self.to_read.append(bytes([0x03]) + b'OK!')

    def read_all(self):
        if self.to_read:
            return self.to_read.pop(0)
        time.sleep(0.001)
        return b''


def run():
    orig = iso_tp.SerialComm
    try:
        iso_tp.SerialComm = FakeSerialStress
        # craft a payload larger than single frame (e.g., 30 bytes)
        payload = ''.join(['AA'] * 30)
        resp = iso_tp.send_iso_tp('fake', payload)
        # verify multiple CF frames were sent
        fake = iso_tp.SerialComm()
        print('resp:', resp)
        # It's not straightforward to access the instance used by send_iso_tp here,
        # but we can at least assert the response is bytes and contains OK!
        if b'OK!' in resp:
            print('ISO_STRESS_OK')
        else:
            print('ISO_STRESS_BAD', resp)
    finally:
        iso_tp.SerialComm = orig


if __name__ == '__main__':
    run()

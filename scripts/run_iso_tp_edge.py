#!/usr/bin/env python3
from vlinker import iso_tp
import time


class FakeSerial:
    def __init__(self, device, baud=115200, timeout=3.0):
        self.sent = []
        self.to_read = []
        self.opened = False

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def send_bytes(self, b: bytes):
        # record exact bytes sent
        self.sent.append(bytes(b))
        # detect First Frame (PCI high nibble == 1)
        first = b[0]
        if (first >> 4) == 1:
            # enqueue a WAIT then a CTS and finally a Single Frame response
            # FC WAIT: 0x31, BS=2, stMin=5 (ms)
            self.to_read.append(bytes([0x31, 0x02, 0x05]))
            # FC CTS:  0x30, BS=2, stMin=0
            self.to_read.append(bytes([0x30, 0x02, 0x00]))
            # Response: Single Frame with 3 bytes payload 'RSP'
            self.to_read.append(bytes([0x03]) + b'RSP')

    def read_all(self):
        if self.to_read:
            return self.to_read.pop(0)
        time.sleep(0.005)
        return b''


class FakeSerialAlwaysWait(FakeSerial):
    def send_bytes(self, b: bytes):
        self.sent.append(bytes(b))
        first = b[0]
        if (first >> 4) == 1:
            # enqueue many WAITs to trigger retry exhaustion
            for _ in range(10):
                self.to_read.append(bytes([0x31, 0x00, 0x05]))


def run_tests():
    orig = iso_tp.SerialComm
    try:
        # Test 1: WAIT then CTS -> success
        iso_tp.SerialComm = FakeSerial
        resp = iso_tp.send_iso_tp('fake', '0102030405060708090A0B0C')
        if resp == b'RSP':
            print('FLOW_WAIT_SUCCESS_OK')
        else:
            print('FLOW_WAIT_SUCCESS_BAD', resp)

        # Test 2: repeated WAIT -> observe behavior (may raise or may return)
        iso_tp.SerialComm = FakeSerialAlwaysWait
        try:
            resp2 = iso_tp.send_iso_tp('fake', '0102030405060708090A0B0C')
            print('FLOW_WAIT_RETRY_NOEXC', resp2)
        except RuntimeError:
            print('FLOW_WAIT_RETRY_OK')

    finally:
        iso_tp.SerialComm = orig


if __name__ == '__main__':
    run_tests()

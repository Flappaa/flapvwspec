import serial
import binascii
import time
from .logger import get_logger

logger = get_logger(__name__)


class SerialComm:
    def __init__(self, device, baud=115200, timeout=1.0, retries=1, backoff=0.1):
        self.device = device
        self.baud = int(baud)
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.backoff = float(backoff)
        self._ser = None

    def open(self):
        logger.debug('Opening serial %s @%d', self.device, self.baud)
        self._ser = serial.Serial(self.device, self.baud, timeout=self.timeout)
        return self._ser

    def close(self):
        if self._ser and getattr(self._ser, 'is_open', False):
            logger.debug('Closing serial %s', self.device)
            try:
                self._ser.close()
            except Exception as e:
                logger.debug('Error closing serial: %s', e)

    def send_bytes(self, data: bytes):
        attempt = 0
        last_exc = None
        while attempt <= self.retries:
            try:
                if not self._ser or not getattr(self._ser, 'is_open', False):
                    self.open()
                logger.debug('Sending %d bytes to %s', len(data), self.device)
                self._ser.write(data)
                # small pause to allow device to respond
                time.sleep(0.05)
                resp = self.read_all()
                return resp
            except Exception as e:
                logger.debug('send_bytes attempt %d failed: %s', attempt, e)
                last_exc = e
                attempt += 1
                time.sleep(self.backoff * attempt)
        raise last_exc

    def send_hex(self, hexstr: str):
        # accept strings like "AA BB CC" or "AABBCC"
        s = hexstr.replace(' ', '')
        data = binascii.unhexlify(s)
        return self.send_bytes(data)

    def send_ascii_line(self, line: str):
        if not line.endswith('\r'):
            line = line + '\r'
        return self.send_bytes(line.encode('ascii'))

    def read_all(self):
        if not self._ser or not getattr(self._ser, 'is_open', False):
            return b''
        out = bytearray()
        start = time.time()
        while True:
            try:
                chunk = self._ser.read(4096)
            except Exception as e:
                logger.debug('read_all read error: %s', e)
                break
            if chunk:
                out.extend(chunk)
                # keep reading until timeout
                start = time.time()
            else:
                if time.time() - start > self.timeout:
                    break
        logger.debug('Read %d bytes from %s', len(out), self.device)
        return bytes(out)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

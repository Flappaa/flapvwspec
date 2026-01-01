import time
import binascii
from typing import Optional

from .serial_comm import SerialComm
from .logger import get_logger

logger = get_logger(__name__)


def _hexdump(b: bytes) -> str:
    return binascii.hexlify(b).decode('ascii')


def _hexstr_to_bytes(s: str) -> bytes:
    s2 = s.replace(' ', '')
    return binascii.unhexlify(s2)


def _stmin_to_seconds(s: int) -> float:
    """Convert ISO-TP stMin value to seconds.

    0x00-0x7F -> milliseconds
    0xF1-0xF9 -> (n-0xF0)*100 microseconds
    """
    if not s:
        return 0.0
    if 0xF1 <= s <= 0xF9:
        usec = (s - 0xF0) * 100
        return usec / 1_000_000.0
    return s / 1000.0


def _parse_flow_control(buf: bytes):
    """Locate and parse a Flow Control (FC) frame from a buffer.

    Scans the buffer for a byte with PCI nibble 0x3 and returns
    (flow_status, block_size, st_min, consumed_bytes_from_start) or None.
    """
    if not buf:
        return None
    # scan buffer for any FC start
    for i in range(len(buf)):
        first = buf[i]
        if (first >> 4) != 3:
            continue
        flow_status = first & 0x0F
        block_size = buf[i+1] if i+1 < len(buf) else 0
        st_min = buf[i+2] if i+2 < len(buf) else 0
        consumed = (i + 1 + (1 if i+1 < len(buf) else 0) + (1 if i+2 < len(buf) else 0))
        return (flow_status, block_size, st_min, consumed)
    return None


def send_iso_tp(device: str, payload_hex: str, baud: int = 115200, timeout: float = 3.0) -> bytes:
    """Send a UDS payload over ISO-TP-like framing and return the assembled response bytes.

    This implements a minimal ISO-TP sender/receiver suitable for CAN-over-serial adapters
    that accept raw bytes. It uses the classic ISO-TP PCI layout:
      - Single Frame (SF): 0x0 | len (1 byte header)
      - First Frame (FF): 0x10 | (len >> 8), second byte = len & 0xFF
      - Consecutive Frame (CF): 0x20 | seq (1..15)
      - Flow Control (FC): 0x30 | flowStatus, blockSize, stMin

    Note: This is a pragmatic implementation; some adapters require different encapsulation.
    """
    data = _hexstr_to_bytes(payload_hex)
    total_len = len(data)
    sc = SerialComm(device, baud=baud, timeout=timeout)
    sc.open()
    def _read_response(sc: SerialComm, timeout: float) -> bytes:
        start = time.time()
        buf = bytearray()
        # read initial data, but skip any leading Flow Control (FC) frames
        first = sc.read_all()
        if not first:
            return b''
        buf.extend(first)
        # scan buffer for the first non-FC frame start.
        # Flow Control frames are 3-byte units: PCI(0x3_), blockSize, stMin.
        def _locate_first_non_fc(barr: bytearray):
            i = 0
            L = len(barr)
            while i < L:
                b = barr[i]
                if ((b >> 4) & 0x0F) == 3:
                    # if we have a full FC (3 bytes) skip it, otherwise indicate we need more
                    if i + 2 < L:
                        i += 3
                        continue
                    else:
                        return None  # incomplete FC at end -> need more data
                # found non-FC start
                return i
            return None

        first_non_fc_index = _locate_first_non_fc(buf)
        while first_non_fc_index is None and time.time() - start < timeout:
            more = sc.read_all()
            if more:
                buf.extend(more)
                first_non_fc_index = _locate_first_non_fc(buf)
            else:
                time.sleep(0.005)
        if first_non_fc_index is None:
            return b''
        if first_non_fc_index:
            buf = bytearray(buf[first_non_fc_index:])
        pci = buf[0]
        frame_type = (pci >> 4) & 0x0F
        # Single Frame
        if frame_type == 0:
            length = pci & 0x0F
            # payload follows first byte
            payload = bytes(buf[1:1+length])
            while len(payload) < length and time.time() - start < timeout:
                more = sc.read_all()
                if more:
                    payload += more
            return payload[:length]

        # First Frame
        if frame_type == 1:
            # ensure we have second byte for length
            while len(buf) < 2 and time.time() - start < timeout:
                more = sc.read_all()
                if more:
                    buf.extend(more)
            if len(buf) < 2:
                raise RuntimeError('incomplete First Frame')
            length = ((buf[0] & 0x0F) << 8) | buf[1]
            assembled = bytearray(buf[2:])
            seq_expected = 1
            # continue reading consecutive frames until assembled length reached
            while len(assembled) < length and time.time() - start < timeout:
                chunk = sc.read_all()
                if not chunk:
                    time.sleep(0.01)
                    continue
                idx = 0
                while idx < len(chunk):
                    b0 = chunk[idx]
                    typ = (b0 >> 4) & 0x0F
                    if typ == 2:
                        # consecutive frame
                        seq = b0 & 0x0F
                        # data follows
                        data_part = chunk[idx+1: idx+1+7]
                        assembled.extend(data_part)
                        idx += 1 + len(data_part)
                    elif typ == 3:
                        # flow control from responder; skip
                        # FC format: 3 | fs, blockSize, stMin
                        idx += len(chunk) - idx
                    else:
                        # unknown, append rest
                        assembled.extend(chunk[idx:])
                        idx = len(chunk)
            return bytes(assembled[:length])

        # other frame types: return raw
        return bytes(buf)

    try:
        if total_len <= 7:
            # single frame: header + data
            header = bytes([total_len & 0x0F])
            tosend = header + data
            sc.send_bytes(tosend)
            return _read_response(sc, timeout)

        # First Frame send
        ff_high = 0x10 | ((total_len >> 8) & 0x0F)
        ff_low = total_len & 0xFF
        ff_payload = bytes([ff_high, ff_low]) + data[:6]
        sc.send_bytes(ff_payload)


        # wait for Flow Control (FC). ECUs may send FC in multiple read chunks.
        start = time.time()
        fc_buf = bytearray()
        fc_parsed = None
        while time.time() - start < timeout and fc_parsed is None:
            chunk = sc.read_all()
            if chunk:
                fc_buf.extend(chunk)
            # try to parse an FC from accumulated buffer
            fc_parsed = _parse_flow_control(bytes(fc_buf))
            if fc_parsed:
                break
            time.sleep(0.01)
        if not fc_parsed:
            raise RuntimeError('no flow control response')
        flow_status, block_size, st_min, _consumed = fc_parsed
        # consume parsed FC bytes so subsequent parses find newer FCs
        if _consumed:
            try:
                del fc_buf[:_consumed]
            except Exception:
                fc_buf = bytearray()

        # handle immediate FC meanings before sending CFs
        if flow_status == 2:
            raise RuntimeError('responder overflow / abort')
        if flow_status == 1:
            # initial WAIT: honor st_min and wait for CTS up to retry limit
            wait_attempts = 0
            max_wait_attempts = 5
            while flow_status == 1 and wait_attempts < max_wait_attempts:
                wait_attempts += 1
                wait_secs = _stmin_to_seconds(st_min) or 0.05
                time.sleep(wait_secs)
                # read further FCs (accumulate into fc_buf)
                more = sc.read_all()
                if more:
                    fc_buf.extend(more)
                    fc_parsed = _parse_flow_control(bytes(fc_buf))
                    if fc_parsed:
                        flow_status, block_size, st_min, _consumed = fc_parsed
                        if _consumed:
                            try:
                                del fc_buf[:_consumed]
                            except Exception:
                                fc_buf = bytearray()
                        break
            if flow_status == 1:
                raise RuntimeError('responder WAIT exceeded retries')

        # use module-level `_stmin_to_seconds` helper

        # send consecutive frames honoring block_size (BS) and st_min
        offset = 6
        seq = 1
        # helper to send one CF
        def _send_cf(seq, chunk):
            cf_header = bytes([0x20 | (seq & 0x0F)])
            cf_payload = cf_header + chunk
            sc.send_bytes(cf_payload)

        cf_payload_space = 7
        st_seconds = _stmin_to_seconds(st_min)

        # when block_size == 0 -> sender may send all CFs without waiting for more FC
        while offset < total_len:
            to_send = block_size if block_size > 0 else 999999
            sent_in_block = 0
            while offset < total_len and sent_in_block < to_send:
                take = min(cf_payload_space, total_len - offset)
                chunk = data[offset:offset+take]
                _send_cf(seq, chunk)
                offset += take
                seq = (seq + 1) & 0x0F
                # ISO-TP sequence numbers roll 0..15; ensure modulo behaviour
                sent_in_block += 1
                # respect minimum separation time
                if st_seconds:
                    time.sleep(st_seconds)
            # if we've finished sending all data, exit without waiting for another FC
            if offset >= total_len:
                break
            # if sender used BS==0, loop will keep sending until all done
            if block_size == 0:
                continue
            # otherwise, wait for next FC before continuing
            fc_buf = bytearray()
            fc_parsed = None
            start_fc = time.time()
            wait_attempts = 0
            max_wait_attempts = 5
            while time.time() - start_fc < timeout and fc_parsed is None:
                chunk = sc.read_all()
                if chunk:
                    fc_buf.extend(chunk)
                fc_parsed = _parse_flow_control(bytes(fc_buf))
                if fc_parsed:
                    break
                time.sleep(0.01)
            if not fc_parsed:
                raise RuntimeError('no subsequent flow control after block')
            flow_status, block_size, st_min, _ = fc_parsed
            # handle flow status meanings: 0=CTS,1=Waiting,2=Overflow
            if flow_status == 1:
                # WAIT: pause according to st_min and retry a limited number of times
                wait_attempts += 1
                if wait_attempts > max_wait_attempts:
                    raise RuntimeError('responder WAIT exceeded retries')
                wait_secs = _stmin_to_seconds(st_min) or 0.05
                time.sleep(wait_secs)
                continue
            if flow_status == 2:
                raise RuntimeError('responder overflow / abort')

        # now read assembled response from remote
        resp = _read_response(sc, timeout)
        return resp
    finally:
        if hasattr(sc, 'close'):
            try:
                sc.close()
            except Exception:
                pass

import time
import signal
from .serial_comm import SerialComm


def _hexify(b: bytes) -> str:
    return b.hex().upper()


def start_capture(device: str, out_file: str, baud: int = 115200, timeout: float = 1.0, duration: float = None):
    """Start capturing serial traffic from `device` and write timestamped hex lines to `out_file`.

    Format: ISO8601<TAB>DIRECTION<TAB>HEX
    DIRECTION is 'R' (read). Currently no write tracing is done.
    Stops after `duration` seconds if provided, otherwise until Ctrl-C.
    """
    stop = False

    def _sigint(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _sigint)

    start_t = time.time()
    with SerialComm(device, baud=baud, timeout=timeout) as s, open(out_file, 'wb') as f:
        # header
        f.write(b'# vlinker capture\n')
        f.flush()
        while not stop:
            now = time.time()
            if duration and (now - start_t) > duration:
                break
            data = s.read_all()
            if data:
                ts = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(now))
                line = f"{ts}\tR\t{_hexify(data)}\n"
                f.write(line.encode('ascii'))
                f.flush()
            else:
                # small sleep to avoid busy loop
                time.sleep(0.05)


def capture_once(device: str, duration: float = 1.0, **kwargs):
    """Convenience function that captures for `duration` seconds into a temporary file and returns its path.

    Not robust for production; intended for interactive use.
    """
    import tempfile
    td = tempfile.NamedTemporaryFile(prefix='vlinker-capture-', suffix='.log', delete=False)
    td.close()
    start_capture(device, td.name, duration=duration, **kwargs)
    return td.name

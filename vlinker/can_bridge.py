import subprocess
import shutil
import sys
import time

def start_slcand(device, can_iface='can0', bitrate=500000):
    """Try to start `slcand` (userspace slcan daemon) to attach a serial device as a SocketCAN interface.

    Returns True if the attach command was started successfully.
    """
    slcand = shutil.which('slcand') or shutil.which('slcan_attach')
    if not slcand:
        print('No slcand/slcan_attach found in PATH. Install `slcan` utilities (can-utils).')
        return False
    cmd = ['sudo', slcand, '-S', str(bitrate), device, can_iface]
    print('Running:', ' '.join(cmd))
    try:
        p = subprocess.Popen(cmd)
        time.sleep(0.2)
        return p.poll() is None
    except Exception as e:
        print('Failed to start slcand:', e)
        return False


def stop_slcand(can_iface='can0'):
    # Try to bring interface down via ip link
    try:
        subprocess.run(['sudo', 'ip', 'link', 'set', can_iface, 'down'], check=False)
        return True
    except Exception:
        return False


def attach_slcan_with_pythoncan(device, can_iface='can0', bitrate=500000):
    """Attempt to open an slcan bus via python-can (if present) and return the Bus object.

    Note: this requires `python-can` and system slcan support.
    """
    try:
        import can
    except Exception as e:
        print('python-can not available:', e)
        return None
    try:
        bus = can.interface.Bus(bustype='slcan', channel=device, bitrate=bitrate)
        print('Opened python-can slcan on', device)
        return bus
    except Exception as e:
        print('Failed to open slcan via python-can:', e)
        return None

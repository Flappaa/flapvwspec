#!/usr/bin/env python3
import argparse
import glob
import os
import sys
from vlinker.serial_comm import SerialComm


def list_ports():
    byid = glob.glob('/dev/serial/by-id/*')
    if byid:
        for p in byid:
            print(f"{p} -> {os.path.realpath(p)}")
    else:
        print('No entries in /dev/serial/by-id')
    tty = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    if tty:
        print('\nRaw tty devices:')
        for t in tty:
            print(' -', t)


def info(path):
    if os.path.exists(path):
        print(path, '->', os.path.realpath(path))
    else:
        print('Path not found:', path)
        sys.exit(2)


def detect():
    byid = glob.glob('/dev/serial/by-id/*')
    for p in byid:
        name = os.path.basename(p).lower()
        if 'vgate' in name or 'vlinker' in name or 'vgatemall' in name:
            print(os.path.realpath(p))
            return 0
    for t in glob.glob('/dev/ttyUSB*'):
        print(t)
        return 0
    return 1


def serial_open(args):
    with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
        print(f'Opened {args.device} at {args.baud}')
        data = s.read_all()
        if data:
            print('Initial data:', data.hex())


def serial_send_hex(args):
    try:
        with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
            resp = s.send_hex(args.hex)
            if resp:
                print('Response (hex):', resp.hex())
            else:
                print('No response')
    except Exception as e:
        print('Error:', e)
        sys.exit(2)


def serial_send_at(args):
    try:
        with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
            resp = s.send_ascii_line(args.cmd)
            if resp:
                try:
                    print('Response (ascii):', resp.decode('utf-8', errors='replace'))
                except Exception:
                    print('Response (hex):', resp.hex())
            else:
                print('No response')
    except Exception as e:
        print('Error:', e)
        sys.exit(2)


def main():
    p = argparse.ArgumentParser(prog='vlinker')
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('list')
    info_p = sub.add_parser('info')
    info_p.add_argument('path')
    sub.add_parser('detect')
    sub.add_parser('diag')
    sub.add_parser('can')
    sub.add_parser('adv')
    sub.add_parser('capture')
    sub.add_parser('profile')

    sp = sub.add_parser('serial')
    ssub = sp.add_subparsers(dest='sact')
    open_p = ssub.add_parser('open')
    open_p.add_argument('device')
    open_p.add_argument('--baud', default=115200, type=int)
    open_p.add_argument('--timeout', default=1.0, type=float)

    sendhex = ssub.add_parser('send-hex')
    sendhex.add_argument('device')
    sendhex.add_argument('hex')
    sendhex.add_argument('--baud', default=115200, type=int)
    sendhex.add_argument('--timeout', default=1.0, type=float)

    sendat = ssub.add_parser('at')
    sendat.add_argument('device')
    sendat.add_argument('cmd')
    sendat.add_argument('--baud', default=115200, type=int)
    sendat.add_argument('--timeout', default=1.0, type=float)

    # Simple dispatch: inspect sys.argv to allow subparsers to parse their own args
    if len(sys.argv) < 2:
        p.print_help()
        return
    cmd = sys.argv[1]
    if cmd == 'list':
        list_ports()
    elif cmd == 'info':
        info_args = info_p.parse_args(sys.argv[2:])
        info(info_args.path)
    elif cmd == 'detect':
        sys.exit(detect())
    elif cmd == 'serial':
        sargs = sp.parse_args(sys.argv[2:])
        if sargs.sact == 'open':
            serial_open(sargs)
        elif sargs.sact == 'send-hex':
            serial_send_hex(sargs)
        elif sargs.sact == 'at':
            serial_send_at(sargs)
        else:
            sp.print_help()
    elif cmd == 'diag':
        import argparse as _arg
        dp = _arg.ArgumentParser(prog='vlinker diag')
        dp.add_argument('diag_cmd', choices=['scan', 'read-dtc', 'send-hex', 'clear-dtc', 'measure'])
        dp.add_argument('device')
        dp.add_argument('--mode', choices=['elm', 'raw'], default='elm')
        dp.add_argument('--baud', type=int, default=115200)
        dp.add_argument('--timeout', type=float, default=1.0)
        dp.add_argument('--hex', dest='hex', default=None)
        dargs = dp.parse_args(sys.argv[2:])
        from vlinker.diag import scan_ecus, read_dtc, send_raw_hex
        if dargs.diag_cmd == 'scan':
            r = scan_ecus(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('Scan response:', r.hex())
            else:
                print('No response')
        elif dargs.diag_cmd == 'read-dtc':
            r = read_dtc(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('DTCs:')
                for dtc in r:
                    print(' -', dtc)
            else:
                print('No DTCs or no response')
        elif dargs.diag_cmd == 'send-hex':
            if not dargs.hex:
                dp.error('send-hex requires --hex HEX')
            r = send_raw_hex(dargs.device, dargs.hex, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('Response:', r.hex())
            else:
                print('No response')
        elif dargs.diag_cmd == 'clear-dtc':
            from vlinker.diag import clear_dtc
            ok = clear_dtc(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            print('Clear DTCs:', 'success' if ok else 'failed')
        elif dargs.diag_cmd == 'measure':
            if not dargs.hex:
                dp.error('measure requires --hex PID_HEX (e.g. --hex 010C)')
            from vlinker.diag import read_measure
            raw = read_measure(dargs.device, dargs.hex, baud=dargs.baud, timeout=dargs.timeout)
            if raw:
                print('Measure raw:', raw.hex())
            else:
                print('No response')
    elif cmd == 'can':
        import argparse as _arg
        cp = _arg.ArgumentParser(prog='vlinker can')
        cp.add_argument('can_cmd', choices=['attach-slcan', 'attach-pycan'])
        cp.add_argument('device')
        cp.add_argument('--iface', default='can0')
        cp.add_argument('--bitrate', type=int, default=500000)
        cargs = cp.parse_args(sys.argv[2:])
        from vlinker.can_bridge import start_slcand, attach_slcan_with_pythoncan
        if cargs.can_cmd == 'attach-slcan':
            ok = start_slcand(cargs.device, can_iface=cargs.iface, bitrate=cargs.bitrate)
            print('Started slcand:', ok)
        elif cargs.can_cmd == 'attach-pycan':
            bus = attach_slcan_with_pythoncan(cargs.device, can_iface=cargs.iface, bitrate=cargs.bitrate)
            print('Bus:', bus)
    elif cmd == 'adv':
        import argparse as _arg
        ap = _arg.ArgumentParser(prog='vlinker adv')
        ap.add_argument('adv_cmd', choices=['req-seed', 'send-key', 'uds', 'coding', 'sec-access'])
        ap.add_argument('device')
        ap.add_argument('--hex', default=None, help='Hex payload or identifier')
        ap.add_argument('--key', default=None, help='Key as hex string for send-key')
        ap.add_argument('--profile', default='manual', help='ECU profile name for sec-access')
        ap.add_argument('--baud', type=int, default=115200)
        ap.add_argument('--timeout', type=float, default=1.0)
        ap.add_argument('--dry-run', action='store_true', help='Prepare payload but do not send')
        ap.add_argument('--force', action='store_true', help='Force send even without dry-run')
        aargs = ap.parse_args(sys.argv[2:])
        from vlinker.advanced import request_seed, send_key, send_uds_raw, perform_coding_write
        from vlinker.ecu_profiles import list_profiles, get_profile
        if aargs.adv_cmd == 'req-seed':
            r = request_seed(aargs.device, baud=aargs.baud, timeout=aargs.timeout)
            print('Seed:', r.hex() if r else None)
        elif aargs.adv_cmd == 'send-key':
            if not aargs.key:
                ap.error('--key is required for send-key')
            key_bytes = bytes.fromhex(aargs.key.replace(' ', ''))
            r = send_key(aargs.device, key_bytes, baud=aargs.baud, timeout=aargs.timeout)
            print('Response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'uds':
            if not aargs.hex:
                ap.error('--hex required for uds')
            r = send_uds_raw(aargs.device, aargs.hex, baud=aargs.baud, timeout=aargs.timeout)
            print('UDS response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'coding':
            if not aargs.hex:
                ap.error('--hex required for coding (identifier)')
            import sys as _sys
            data = _sys.stdin.buffer.read() if not _sys.stdin.isatty() else b''
            if not data and not aargs.dry_run:
                ap.error('Provide coding bytes on stdin (binary) or pipe hex, or use --dry-run to preview payload.')
            if not aargs.dry_run and not aargs.force:
                ap.error('To perform coding write you must pass --force (or use --dry-run to preview).')
            if aargs.dry_run:
                payload = perform_coding_write(aargs.device, aargs.hex, data, baud=aargs.baud, timeout=aargs.timeout, dry_run=True)
                print('Prepared payload (dry-run):', payload)
            else:
                r = perform_coding_write(aargs.device, aargs.hex, data, baud=aargs.baud, timeout=aargs.timeout, dry_run=False)
                print('Coding response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'sec-access':
            from vlinker.advanced import security_access_with_profile
            prof = get_profile(aargs.profile)
            if not prof:
                print('Unknown profile:', aargs.profile)
                print('Available:', ','.join(list_profiles()))
                sys.exit(2)
            res = security_access_with_profile(aargs.device, aargs.profile, baud=aargs.baud, timeout=aargs.timeout)
            print('Mode:', res.get('mode'))
            print('Seed:', res.get('seed').hex() if res.get('seed') else None)
            if res.get('key'):
                print('Key (sent):', res.get('key').hex())
            if res.get('response'):
                print('Response:', res.get('response').hex())
    elif cmd == 'capture':
        import argparse as _arg
        cp = _arg.ArgumentParser(prog='vlinker capture')
        cp.add_argument('cap_cmd', choices=['start', 'parse'])
        cp.add_argument('device_or_file')
        cp.add_argument('--out', '-o', default='capture.log')
        cp.add_argument('--duration', type=float, default=None)
        cargs = cp.parse_args(sys.argv[2:])
        if cargs.cap_cmd == 'start':
            from vlinker.capture import start_capture
            print('Starting capture; press Ctrl-C to stop')
            start_capture(cargs.device_or_file, cargs.out, duration=cargs.duration)
            print('Capture saved to', cargs.out)
        elif cargs.cap_cmd == 'parse':
            from vlinker.capture_parser import parse_capture_file, find_seed_requests
            parsed = parse_capture_file(cargs.device_or_file)
            seeds = find_seed_requests(parsed)
            if not seeds:
                print('No seed requests found in', cargs.device_or_file)
            else:
                for ts, req, resp in seeds:
                    print(f'Request at {ts}: {req.hex()} -> Response: {resp.hex()}')
    elif cmd == 'profile':
        import argparse as _arg
        pp = _arg.ArgumentParser(prog='vlinker profile')
        pp.add_argument('prof_cmd', choices=['analyze', 'build', 'interactive'])
        pp.add_argument('path', nargs='?')
        pp.add_argument('--name', help='Name for generated profile (when building)')
        pp.add_argument('--algo', help='Algorithm name to use when building (e.g., reverse, xor_5A)')
        pargs = pp.parse_args(sys.argv[2:])
        if pargs.prof_cmd == 'analyze':
            from vlinker.profile_builder import analyze_capture
            res = analyze_capture(pargs.path)
            if not res:
                print('No seed suggestions found')
            else:
                for r in res:
                    print('At', r['ts'], 'seed:', r['seed_hex'])
                    for c in r['candidates']:
                        print(' -', c['name'], c['key_hex'])
        elif pargs.prof_cmd == 'build':
            if not pargs.name or not pargs.algo:
                pp.error('build requires --name and --algo')
            from vlinker.profile_builder import analyze_capture, save_profile_from_suggestion
            res = analyze_capture(pargs.path)
            if not res:
                print('No suggestions found; nothing to build')
            else:
                suggestion = res[0]
                path = save_profile_from_suggestion(pargs.name, suggestion, pargs.algo)
                if path:
                    print('Profile written to', path)
                else:
                    print('Failed to write profile; check algo name')
        elif pargs.prof_cmd == 'interactive':
            from vlinker.profile_builder import interactive_build
            cap = pargs.path or input('Path to capture file (or Enter to cancel): ').strip()
            if not cap:
                print('No capture provided; aborting')
            else:
                interactive_build(cap)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
import argparse
import glob
import os
import sys
from vlinker.serial_comm import SerialComm


def list_ports():
    byid = glob.glob('/dev/serial/by-id/*')
    if byid:
        for p in byid:
            print(f"{p} -> {os.path.realpath(p)}")
    else:
        print('No entries in /dev/serial/by-id')
    tty = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    if tty:
        print('\nRaw tty devices:')
        for t in tty:
            print(' -', t)


def info(path):
    if os.path.exists(path):
        print(path, '->', os.path.realpath(path))
    else:
        print('Path not found:', path)
        sys.exit(2)


def detect():
    byid = glob.glob('/dev/serial/by-id/*')
    for p in byid:
        name = os.path.basename(p).lower()
        if 'vgate' in name or 'vlinker' in name or 'vgatemall' in name:
            print(os.path.realpath(p))
            return 0
    for t in glob.glob('/dev/ttyUSB*'):
        print(t)
        return 0
    return 1


def serial_open(args):
    with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
        print(f'Opened {args.device} at {args.baud}')
        data = s.read_all()
        if data:
            print('Initial data:', data.hex())


def serial_send_hex(args):
    try:
        with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
            resp = s.send_hex(args.hex)
            if resp:
                print('Response (hex):', resp.hex())
            else:
                print('No response')
    except Exception as e:
        print('Error:', e)
        sys.exit(2)


def serial_send_at(args):
    try:
        with SerialComm(args.device, baud=args.baud, timeout=args.timeout) as s:
            resp = s.send_ascii_line(args.cmd)
            if resp:
                try:
                    print('Response (ascii):', resp.decode('utf-8', errors='replace'))
                except Exception:
                    print('Response (hex):', resp.hex())
            else:
                print('No response')
    except Exception as e:
        print('Error:', e)
        sys.exit(2)


def main():
    p = argparse.ArgumentParser(prog='vlinker')
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('list')
    info_p = sub.add_parser('info')
    info_p.add_argument('path')
    sub.add_parser('detect')
    sub.add_parser('diag')
    sub.add_parser('can')
    sub.add_parser('adv')
    sub.add_parser('capture')
    sub.add_parser('profile')

    sp = sub.add_parser('serial')
    ssub = sp.add_subparsers(dest='sact')
    open_p = ssub.add_parser('open')
    open_p.add_argument('device')
    open_p.add_argument('--baud', default=115200, type=int)
    open_p.add_argument('--timeout', default=1.0, type=float)

    sendhex = ssub.add_parser('send-hex')
    sendhex.add_argument('device')
    sendhex.add_argument('hex')
    sendhex.add_argument('--baud', default=115200, type=int)
    sendhex.add_argument('--timeout', default=1.0, type=float)

    sendat = ssub.add_parser('at')
    sendat.add_argument('device')
    sendat.add_argument('cmd')
    sendat.add_argument('--baud', default=115200, type=int)
    sendat.add_argument('--timeout', default=1.0, type=float)

    # Simple dispatch: inspect sys.argv to allow subparsers to parse their own args
    if len(sys.argv) < 2:
        p.print_help()
        return
    cmd = sys.argv[1]
    if cmd == 'list':
        list_ports()
    elif cmd == 'info':
        info_args = info_p.parse_args(sys.argv[2:])
        info(info_args.path)
    elif cmd == 'detect':
        sys.exit(detect())
    elif cmd == 'serial':
        sargs = sp.parse_args(sys.argv[2:])
        if sargs.sact == 'open':
            serial_open(sargs)
        elif sargs.sact == 'send-hex':
            serial_send_hex(sargs)
        elif sargs.sact == 'at':
            serial_send_at(sargs)
        else:
            sp.print_help()
    elif cmd == 'diag':
        import argparse as _arg
        dp = _arg.ArgumentParser(prog='vlinker diag')
        dp.add_argument('diag_cmd', choices=['scan', 'read-dtc', 'send-hex', 'clear-dtc', 'measure'])
        dp.add_argument('device')
        dp.add_argument('--mode', choices=['elm', 'raw'], default='elm')
        dp.add_argument('--baud', type=int, default=115200)
        dp.add_argument('--timeout', type=float, default=1.0)
        dp.add_argument('--hex', dest='hex', default=None)
        dargs = dp.parse_args(sys.argv[2:])
        from vlinker.diag import scan_ecus, read_dtc, send_raw_hex
        if dargs.diag_cmd == 'scan':
            r = scan_ecus(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('Scan response:', r.hex())
            else:
                print('No response')
        elif dargs.diag_cmd == 'read-dtc':
            r = read_dtc(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('DTCs:')
                for dtc in r:
                    print(' -', dtc)
            else:
                print('No DTCs or no response')
        elif dargs.diag_cmd == 'send-hex':
            if not dargs.hex:
                dp.error('send-hex requires --hex HEX')
            r = send_raw_hex(dargs.device, dargs.hex, baud=dargs.baud, timeout=dargs.timeout)
            if r:
                print('Response:', r.hex())
            else:
                print('No response')
        elif dargs.diag_cmd == 'clear-dtc':
            from vlinker.diag import clear_dtc
            ok = clear_dtc(dargs.device, mode=dargs.mode, baud=dargs.baud, timeout=dargs.timeout)
            print('Clear DTCs:', 'success' if ok else 'failed')
        elif dargs.diag_cmd == 'measure':
            if not dargs.hex:
                dp.error('measure requires --hex PID_HEX (e.g. --hex 010C)')
            from vlinker.diag import read_measure
            raw = read_measure(dargs.device, dargs.hex, baud=dargs.baud, timeout=dargs.timeout)
            if raw:
                print('Measure raw:', raw.hex())
            else:
                print('No response')
    elif cmd == 'can':
        import argparse as _arg
        cp = _arg.ArgumentParser(prog='vlinker can')
        cp.add_argument('can_cmd', choices=['attach-slcan', 'attach-pycan'])
        cp.add_argument('device')
        cp.add_argument('--iface', default='can0')
        cp.add_argument('--bitrate', type=int, default=500000)
        cargs = cp.parse_args(sys.argv[2:])
        from vlinker.can_bridge import start_slcand, attach_slcan_with_pythoncan
        if cargs.can_cmd == 'attach-slcan':
            ok = start_slcand(cargs.device, can_iface=cargs.iface, bitrate=cargs.bitrate)
            print('Started slcand:', ok)
        elif cargs.can_cmd == 'attach-pycan':
            bus = attach_slcan_with_pythoncan(cargs.device, can_iface=cargs.iface, bitrate=cargs.bitrate)
            print('Bus:', bus)
    elif cmd == 'adv':
        import argparse as _arg
        ap = _arg.ArgumentParser(prog='vlinker adv')
        ap.add_argument('adv_cmd', choices=['req-seed', 'send-key', 'uds', 'coding', 'sec-access'])
        ap.add_argument('device')
        ap.add_argument('--hex', default=None, help='Hex payload or identifier')
        ap.add_argument('--key', default=None, help='Key as hex string for send-key')
        ap.add_argument('--profile', default='manual', help='ECU profile name for sec-access')
        ap.add_argument('--baud', type=int, default=115200)
        ap.add_argument('--timeout', type=float, default=1.0)
        ap.add_argument('--dry-run', action='store_true', help='Prepare payload but do not send')
        ap.add_argument('--force', action='store_true', help='Force send even without dry-run')
        aargs = ap.parse_args(sys.argv[2:])
        from vlinker.advanced import request_seed, send_key, send_uds_raw, perform_coding_write
        from vlinker.ecu_profiles import list_profiles, get_profile
        if aargs.adv_cmd == 'req-seed':
            r = request_seed(aargs.device, baud=aargs.baud, timeout=aargs.timeout)
            print('Seed:', r.hex() if r else None)
        elif aargs.adv_cmd == 'send-key':
            if not aargs.key:
                ap.error('--key is required for send-key')
            key_bytes = bytes.fromhex(aargs.key.replace(' ', ''))
            r = send_key(aargs.device, key_bytes, baud=aargs.baud, timeout=aargs.timeout)
            print('Response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'uds':
            if not aargs.hex:
                ap.error('--hex required for uds')
            r = send_uds_raw(aargs.device, aargs.hex, baud=aargs.baud, timeout=aargs.timeout)
            print('UDS response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'coding':
            if not aargs.hex:
                ap.error('--hex required for coding (identifier)')
            import sys as _sys
            data = _sys.stdin.buffer.read() if not _sys.stdin.isatty() else b''
            if not data and not aargs.dry_run:
                ap.error('Provide coding bytes on stdin (binary) or pipe hex, or use --dry-run to preview payload.')
            if not aargs.dry_run and not aargs.force:
                ap.error('To perform coding write you must pass --force (or use --dry-run to preview).')
            if aargs.dry_run:
                payload = perform_coding_write(aargs.device, aargs.hex, data, baud=aargs.baud, timeout=aargs.timeout, dry_run=True)
                print('Prepared payload (dry-run):', payload)
            else:
                r = perform_coding_write(aargs.device, aargs.hex, data, baud=aargs.baud, timeout=aargs.timeout, dry_run=False)
                print('Coding response:', r.hex() if r else None)
        elif aargs.adv_cmd == 'sec-access':
            from vlinker.advanced import security_access_with_profile
            prof = get_profile(aargs.profile)
            if not prof:
                print('Unknown profile:', aargs.profile)
                print('Available:', ','.join(list_profiles()))
                sys.exit(2)
            res = security_access_with_profile(aargs.device, aargs.profile, baud=aargs.baud, timeout=aargs.timeout)
            print('Mode:', res.get('mode'))
            print('Seed:', res.get('seed').hex() if res.get('seed') else None)
            if res.get('key'):
                print('Key (sent):', res.get('key').hex())
            if res.get('response'):
                print('Response:', res.get('response').hex())
    elif cmd == 'capture':
        import argparse as _arg
        cp = _arg.ArgumentParser(prog='vlinker capture')
        cp.add_argument('cap_cmd', choices=['start', 'parse'])
        cp.add_argument('device_or_file')
        cp.add_argument('--out', '-o', default='capture.log')
        cp.add_argument('--duration', type=float, default=None)
        cargs = cp.parse_args(sys.argv[2:])
        if cargs.cap_cmd == 'start':
            from vlinker.capture import start_capture
            print('Starting capture; press Ctrl-C to stop')
            start_capture(cargs.device_or_file, cargs.out, duration=cargs.duration)
            print('Capture saved to', cargs.out)
        elif cargs.cap_cmd == 'parse':
            from vlinker.capture_parser import parse_capture_file, find_seed_requests
            parsed = parse_capture_file(cargs.device_or_file)
            seeds = find_seed_requests(parsed)
            if not seeds:
                print('No seed requests found in', cargs.device_or_file)
            else:
                for ts, req, resp in seeds:
                    print(f'Request at {ts}: {req.hex()} -> Response: {resp.hex()}')
    elif cmd == 'profile':
        import argparse as _arg
        pp = _arg.ArgumentParser(prog='vlinker profile')
        pp.add_argument('prof_cmd', choices=['analyze', 'build', 'interactive'])
        pp.add_argument('path', nargs='?')
        pp.add_argument('--name', help='Name for generated profile (when building)')
        pp.add_argument('--algo', help='Algorithm name to use when building (e.g., reverse, xor_5A)')
        pargs = pp.parse_args(sys.argv[2:])
        if pargs.prof_cmd == 'analyze':
            from vlinker.profile_builder import analyze_capture
            res = analyze_capture(pargs.path)
            if not res:
                print('No seed suggestions found')
            else:
                for r in res:
                    print('At', r['ts'], 'seed:', r['seed_hex'])
                    for c in r['candidates']:
                        print(' -', c['name'], c['key_hex'])
        elif pargs.prof_cmd == 'build':
            if not pargs.name or not pargs.algo:
                pp.error('build requires --name and --algo')
            from vlinker.profile_builder import analyze_capture, save_profile_from_suggestion
            res = analyze_capture(pargs.path)
            if not res:
                print('No suggestions found; nothing to build')
            else:
                suggestion = res[0]
                path = save_profile_from_suggestion(pargs.name, suggestion, pargs.algo)
                if path:
                    print('Profile written to', path)
                else:
                    print('Failed to write profile; check algo name')
        elif pargs.prof_cmd == 'interactive':
            from vlinker.profile_builder import interactive_build
            cap = pargs.path or input('Path to capture file (or Enter to cancel): ').strip()
            if not cap:
                print('No capture provided; aborting')
            else:
                interactive_build(cap)
    else:
        p.print_help()


if __name__ == '__main__':
    main()

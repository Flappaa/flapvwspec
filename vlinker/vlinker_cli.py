#!/usr/bin/env python3
"""Package-local CLI shim for installed environment."""
from vlinker import serial_comm  # ensure package imports work
import importlib

try:
    # If root module exists (development), import it
    vroot = importlib.import_module('vlinker_cli')
    main = vroot.main
except Exception:
    # Otherwise, import the root CLI logic from this package by reading the file
    # fallback: execute the top-level script contents
    from . import serial_comm as _sc  # noqa: F401
    # import the module by executing the root file if present
    try:
        import pkgutil
        data = pkgutil.get_data('vlinker', 'vlinker_cli.py')
        if data:
            # execute in module namespace
            ns = {}
            exec(data.decode('utf-8'), ns)
            main = ns.get('main')
        else:
            raise ImportError('cannot load vlinker_cli')
    except Exception as e:
        raise ImportError('Failed to provide vlinker CLI shim') from e

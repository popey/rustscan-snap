#!/usr/bin/env python3
"""Check the installed snap against two ports owned by this test on loopback."""
from pathlib import Path
import re
import socket
import subprocess

artifacts = Path('artifacts')
artifacts.mkdir(exist_ok=True)
recipe = Path('snap/snapcraft.yaml').read_text()
expected = re.search(r"(?m)^version: '([^']+)'$", recipe).group(1)
version = subprocess.run(['snap', 'run', 'rustscan', '--version'],
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         timeout=30, check=True).stdout
(artifacts / 'version.log').write_text(version)
assert re.search(r'(?<![0-9.])' + re.escape(expected) + r'(?![0-9.])', version), version
# Keep both sockets bound so no other process can claim the closed test port.
with socket.socket() as opened, socket.socket() as closed:
    opened.bind(('127.0.0.1', 0))
    opened.listen(1)
    closed.bind(('127.0.0.1', 0))
    open_port, closed_port = opened.getsockname()[1], closed.getsockname()[1]
    command = ['snap', 'run', 'rustscan', '--no-config', '--greppable',
               '--scripts', 'none', '--batch-size', '2', '--timeout', '1000',
               '--addresses', '127.0.0.1', '--ports', f'{open_port},{closed_port}']
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30, check=True)
    (artifacts / 'loopback-scan.log').write_text(result.stdout)
    matches = re.findall(r'127\.0\.0\.1\s*->\s*\[([0-9,\s]*)\]', result.stdout)
    assert len(matches) == 1, result.stdout
    detected = {int(port.strip()) for port in matches[0].split(',') if port.strip()}
    assert detected == {open_port}, (detected, open_port, closed_port, result.stdout)
print('Installed version and open/closed loopback port checks passed')

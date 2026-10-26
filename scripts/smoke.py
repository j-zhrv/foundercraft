#!/usr/bin/env python3
"""Read the installed plugin through the selected Desktop app-server runtime.

Does not start a model conversation, learning session, or microphone.
"""

import argparse
import json
from pathlib import Path
import queue
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', default='codex', help='Desktop app-server executable')
    parser.add_argument('--marketplace-path', type=Path,
                        default=Path(__file__).resolve().parents[1] / '.agents/plugins/marketplace.json')
    args = parser.parse_args()
    process = subprocess.Popen([args.codex, 'app-server'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    messages = queue.Queue()

    def read():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                pass
        messages.put(None)

    threading.Thread(target=read, daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + '\n')
        process.stdin.flush()

    def request(ident, method, params):
        send({'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic() + 30
        while True:
            result = messages.get(timeout=max(0, deadline - time.monotonic()))
            if result is None:
                raise RuntimeError('app-server exited before response')
            if result.get('id') == ident:
                if 'error' in result:
                    raise RuntimeError(result['error'])
                return result['result']

    try:
        request(1, 'initialize', {
            'clientInfo': {'name': 'foundercraft-package-smoke', 'version': '0.2.0'},
            'capabilities': {'experimentalApi': True},
        })
        send({'method': 'initialized'})
        result = request(2, 'plugin/read', {
            'pluginName': 'foundercraft',
            'marketplacePath': str(args.marketplace_path.resolve()),
        })['plugin']
        skills = [{'name': skill['name'], 'enabled': skill['enabled']} for skill in result['skills']]
        summary = result['summary']
        if not (summary['installed'] and summary['enabled']
                and skills == [{'name': 'foundercraft:foundercraft-coach', 'enabled': True}]
                and result['mcpServers'] == [] and result['apps'] == [] and result['hooks'] == []):
            raise RuntimeError('Expected installed/enabled skills-only FounderCraft')
        print(json.dumps({'installed': True, 'enabled': True, 'version': summary.get('localVersion'),
                          'skills': skills, 'mcpServers': [], 'apps': [], 'hooks': []}, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()

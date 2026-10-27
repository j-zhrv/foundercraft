#!/usr/bin/env python3
"""Check the public source and optionally validate links/schema or build a ZIP."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/foundercraft'
SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
OPENAI_CATEGORIES = {
    'Business & Operations', 'Communication', 'Creativity', 'Data & Analytics',
    'Developer Tools', 'Education & Research', 'Entertainment', 'Finance',
    'Healthcare', 'Other', 'Productivity', 'Scientific Research', 'Security', 'Travel',
}
EXPECTED = {
    'plugin.json', '.codex-plugin/plugin.json', 'assets/icon.svg',
    'skills/foundercraft-coach/SKILL.md',
    *('skills/foundercraft-coach/references/' + name + '.md' for name in (
        'browser', 'guided-dialogue', 'learning-feedback', 'practice',
        'session-onboarding', 'voice-entry', 'site-handoff')),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contained(base, relative):
    target = (base / relative).resolve()
    require(target.is_relative_to(base.resolve()), f'Path escapes root: {relative}')
    require(target.is_file(), f'Missing file: {relative}')
    return target


def fetch(url):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and not parsed.username and not parsed.password,
            f'Unsafe URL: {url}')
    request = Request(url, headers={'User-Agent': 'FounderCraft-package-check/0.2'})
    with urlopen(request, timeout=30) as response:
        require(response.status == 200, f'HTTP {response.status}: {url}')
        require(urlsplit(response.url).scheme == 'https', f'Insecure redirect: {url}')
        response.read(1)
    return url


def check(args):
    candidates = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT, text=True).split('\0')
    files = sorted({ROOT / name for name in candidates if name})
    require(files, 'No source files found')
    external = set()
    for path in files:
        require(not path.is_symlink(), f'Symlink: {path.relative_to(ROOT)}')
        require(path.is_file() and path.stat().st_size <= 1024 * 1024,
                f'Unexpected or oversized file: {path.relative_to(ROOT)}')
        text = path.read_text(encoding='utf-8')
        for pattern in (
            r'(?i)(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',
            r'(?i)sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}',
            r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            r'(?i)pluginrel_[a-f0-9]{24,}|plugins?_[a-f0-9]{24,}',
        ):
            require(not re.search(pattern, text), f'Secret/private ID pattern: {path.relative_to(ROOT)}')
        if path.suffix in ('.md', '.json', '.svg'):
            for pattern in (
                r'(?i)Евгени[йюяе]|eugene|я-учусь-FounderCraft',
                r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
                r'/home/[^/\s]+|/mnt/prefect|[A-Z]:\\Users\\',
            ):
                require(not re.search(pattern, text), f'Personal data pattern: {path.relative_to(ROOT)}')
        if path.suffix == '.json':
            json.loads(text)
        if path.suffix == '.md':
            for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)', text):
                url = urlsplit(target)
                if url.scheme:
                    require(url.scheme == 'https', f'Non-HTTPS link: {target}')
                    external.add(target.split('#')[0])
                elif url.path:
                    resolved = (path.parent / unquote(url.path)).resolve()
                    require(resolved.is_relative_to(ROOT), f'Link escapes repo: {target}')
                    require(resolved.is_file(), f'Broken link in {path.relative_to(ROOT)}: {target}')

    actual = {str(path.relative_to(PACKAGE)) for path in PACKAGE.rglob('*') if path.is_file()}
    require(actual == EXPECTED, f'Unexpected package inventory: {actual ^ EXPECTED}')
    manifest = json.loads((PACKAGE / 'plugin.json').read_text())
    legacy = json.loads((PACKAGE / '.codex-plugin/plugin.json').read_text())
    require(manifest.get('$schema') == SCHEMA, 'Wrong portable schema')
    require(manifest.get('name') == 'foundercraft', 'Wrong package name')
    require(re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', manifest['version']), 'Not SemVer')
    require(not ({'skills', 'mcpServers', 'apps', 'interface'} & manifest.keys()), 'Legacy fields at portable root')
    openai = manifest['extensions']['com.openai']
    require(set(openai) == {'interface'}, 'Unexpected services/hooks/app bindings')
    interface = openai['interface']
    require(0 < len(interface['shortDescription']) <= 30, 'Subtitle exceeds 30 characters')
    require(interface['category'] in OPENAI_CATEGORIES,
            'Unsupported OpenAI interface.category: use an exact supported listing title')
    require(isinstance(interface['capabilities'], list), 'Capabilities must be an array')
    prompts = interface['defaultPrompt']
    require(isinstance(prompts, list) and 1 <= len(prompts) <= 3, 'Wrong starter prompts')
    require(all(isinstance(p, str) and 0 < len(p) <= 128 for p in prompts), 'Starter prompt too long')
    for field in ('logo', 'composerIcon'):
        contained(PACKAGE, interface[field])
    for field in ('name', 'version', 'description', 'author', 'keywords'):
        require(legacy[field] == manifest[field], f'Manifest mismatch: {field}')
    require(legacy['interface'] == interface and legacy['skills'] == './skills', 'Overlay mismatch')
    if args.schema:
        schema = json.loads(Path(args.schema).read_text())
        validator = jsonschema.validators.validator_for(schema)
        validator.check_schema(schema)
        validator(schema).validate(manifest)
        print('PASS official portable JSON Schema')
    for path in PACKAGE.glob('skills/*/SKILL.md'):
        text = path.read_text()
        require(text.startswith('---\n'), 'Missing skill frontmatter')
        frontmatter = yaml.safe_load(text.split('---\n', 2)[1])
        require(frontmatter['name'] == path.parent.name, 'Wrong skill name')
        require(isinstance(frontmatter['description'], str) and frontmatter['description'].strip(),
                'Missing skill description')
    icon = ET.parse(PACKAGE / 'assets/icon.svg').getroot()
    require(icon.tag.endswith('svg') and int(icon.attrib['width']) >= 48
            and icon.attrib['width'] == icon.attrib['height'], 'Icon must be square, at least 48px')
    marketplace = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
    require(marketplace['name'] == 'foundercraft' and len(marketplace['plugins']) == 1, 'Wrong marketplace')
    entry = marketplace['plugins'][0]
    require(entry['name'] == manifest['name'], 'Catalog identity mismatch')
    require(isinstance(entry.get('category'), str) and entry['category'].strip(),
            'Marketplace category must be a nonblank string')
    require(entry['category'] == interface['category'], 'FounderCraft category labels differ')
    require(entry['source'] == {'source': 'local', 'path': './plugins/foundercraft'}, 'Wrong source')
    require(entry['policy'] == {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'Wrong policy/product restriction')
    require(contained(ROOT, entry['source']['path'] + '/plugin.json') == PACKAGE / 'plugin.json', 'Wrong package root')
    external.update((SCHEMA, manifest['homepage'], manifest['repository']))
    print(f'PASS manifests, YAML, icon, package inventory ({len(actual)} files), local links')
    print(f'PASS typical secret/private-ID/personal-data scan ({len(files)} public source files)')
    if args.links:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for url in pool.map(fetch, sorted(external)):
                print(f'PASS HTTPS {url}')
    if args.archive:
        archive = Path(args.archive).resolve()
        require(not archive.is_relative_to(ROOT), 'Write archive outside source repository')
        with ZipFile(archive, 'w', ZIP_DEFLATED) as output:
            for name in sorted(EXPECTED):
                output.write(PACKAGE / name, name)
        with ZipFile(archive) as output:
            require(set(output.namelist()) == EXPECTED and output.testzip() is None, 'Invalid ZIP')
        print(f'PASS ZIP ({len(EXPECTED)} files): {archive}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', help='Path to downloaded official plugin JSON Schema')
    parser.add_argument('--links', action='store_true', help='Check public HTTPS links (network required)')
    parser.add_argument('--archive', help='Build and inspect plugin-only ZIP outside repository')
    try:
        check(parser.parse_args())
    except (OSError, ValueError, KeyError, jsonschema.ValidationError, yaml.YAMLError) as error:
        print(f'FAIL {error}', file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Validate repository Markdown destinations and Markdown heading anchors offline."""
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]

def prose(text):
    # Ignore fenced examples; preserve inline link destinations in prose/tables.
    return re.sub(r'^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text,
                  flags=re.M | re.S)

def anchors(path):
    found, counts = set(), {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(path.read_text()), re.M):
        heading = re.sub(r'!?\[([^]]+)\]\([^)]*\)', r'\1', heading)
        heading = re.sub(r'<[^>]*>', '', heading).lower()
        slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug + (f'-{count}' if count else ''))
    found.update(re.findall(r'(?:id|name)=["\']([^"\']+)', path.read_text()))
    return found

def main():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others',
                                     '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    files = sorted({ROOT / n for n in names if n.endswith('.md') and (ROOT/n).is_file()})
    errors, checked, external = [], 0, 0
    cache = {}
    for path in files:
        body = prose(path.read_text())
        destinations = re.findall(r'!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+["\'][^\n]*?["\'])?\s*\)', body)
        refs = dict((a.strip().lower(), b) for a,b in re.findall(r'^\s*\[([^]]+)\]:\s*(<[^>]+>|\S+)', body, re.M))
        for label, ref in re.findall(r'!?\[([^]\n]+)\]\[([^]\n]*)\]', body):
            key = (ref or label).strip().lower()
            if key not in refs:
                errors.append(f'{path.relative_to(ROOT)}: undefined reference [{key}]')
        destinations += list(refs.values())
        for raw in destinations:
            raw = raw.strip('<>')
            parts = urlsplit(raw)
            if parts.scheme or parts.netloc:
                external += 1
                continue
            target = (ROOT / unquote(parts.path).lstrip('/') if parts.path.startswith('/')
                      else path.parent / unquote(parts.path)) if parts.path else path
            target = target.resolve()
            checked += 1
            if not target.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing {raw}')
            elif parts.fragment and target.suffix == '.md':
                if target not in cache:
                    cache[target] = anchors(target)
                if unquote(parts.fragment) not in cache[target]:
                    errors.append(f'{path.relative_to(ROOT)}: missing anchor {raw}')
    print(json.dumps(dict(markdown_files=len(files), internal_links_checked=checked,
                          external_links_skipped=external, errors=errors), indent=2))
    return bool(errors)

if __name__ == '__main__':
    sys.exit(main())

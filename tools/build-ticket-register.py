"""Generate the archived, read-only ADS-themed local ticket snapshot."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / '.scratch/procurement-mvp/issues'
OUTPUT = ROOT / 'mockups/procurement-ui-prototype/public/tickets.html'
THEMES = ROOT / 'mockups/procurement-ui-prototype/node_modules/@atlaskit/tokens/dist/esm/artifacts/themes'


def theme_css(name):
    source = (THEMES / f'atlassian-{name}.js').read_text(encoding='utf-8')
    match = re.search(r'export default\s+("(?:[^"\\]|\\.)*")\s*;', source, re.S)
    if not match:
        raise ValueError(f'Unsupported theme asset format: {name}')
    return json.loads(match.group(1))


def main():
    tickets = []
    references = {}
    for path in sorted(ISSUES.glob('*.md')):
        raw = path.read_text(encoding='utf-8')
        heading = raw.splitlines()[0].removeprefix('# ')
        key, title = heading.split(': ', 1)
        before_sections = raw.split('\n## ', 1)[0]
        metadata = dict(re.findall(r'^([A-Za-z ]+): (.*)$', before_sections, re.M))
        sections = {}
        for part in raw.split('\n## ')[1:]:
            name, _, body = part.partition('\n')
            sections[name.strip()] = body.strip()
        ref_paths = [line[2:].strip() for line in sections.get('References', '').splitlines() if line.startswith('- ')]
        for relative in ref_paths:
            candidate = (ROOT / relative).resolve()
            if candidate.is_relative_to(ROOT) and candidate.is_file():
                references[relative] = candidate.read_text(encoding='utf-8')
        tickets.append({
            'key': key, 'number': path.name[:2], 'title': title,
            'status': metadata['Status'], 'progress': metadata['Progress'],
            'type': metadata['Type'], 'priority': metadata['Priority'],
            'milestone': metadata['Milestone'], 'owner': metadata['Owner'],
            'dependencies': [] if metadata['Blocked by'] == 'None' else metadata['Blocked by'].split(', '),
            'sections': sections, 'references': ref_paths,
            'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'markdown': raw,
        })
    if not tickets or len({t['key'] for t in tickets}) != len(tickets):
        raise ValueError('Ticket list is empty or contains duplicate IDs')
    numbers = {t['number'] for t in tickets}
    for ticket in tickets:
        if set(ticket['dependencies']) - numbers:
            raise ValueError(f"Unknown dependency on {ticket['key']}")
    setup_paths = ['AGENTS.md', 'docs/agents/issue-tracker.md', 'docs/agents/triage-labels.md', 'docs/agents/domain.md']
    setup_applied = all((ROOT / path).is_file() for path in setup_paths)
    setup_text = '\n\n'.join('## ' + path + '\n\n```markdown\n' + (ROOT / path).read_text(encoding='utf-8').strip() + '\n```' for path in setup_paths) if setup_applied else (ROOT / 'docs/agents/setup-preview.md').read_text(encoding='utf-8')
    payload = {
        'tickets': tickets, 'references': references,
        'setup': setup_text, 'setupApplied': setup_applied,
        'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    template = (ROOT / 'tools/ticket-register.template.html').read_text(encoding='utf-8')
    output = template.replace('/*__ADS_THEME_CSS__*/', theme_css('light') + '\n' + theme_css('dark'))
    output = output.replace('/*__TICKET_DATA__*/', json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c'))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding='utf-8')
    print(f'Generated {OUTPUT.relative_to(ROOT)} from {len(tickets)} Markdown tickets.')


if __name__ == '__main__':
    main()

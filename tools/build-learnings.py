"""Publish the canonical learnings folder to the existing Vite prototype server.

The generated mirror is disposable. Engineering documents referenced by lessons are
copied under _project; generated HTML links are adjusted to those snapshots.
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'learnings'
OUTPUT = ROOT / 'mockups/procurement-ui-prototype/public/learnings'


def main():
    # Only replace the exact generated mirror, never canonical learning material.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(SOURCE, OUTPUT)
    for path in OUTPUT.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        for attribute, relative in re.findall(r'(href|src)="(\.\./\.\./[^"#?]+)"', text):
            target = (SOURCE / path.relative_to(OUTPUT).parent / relative).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError(f'Invalid project reference: {relative}')
            if target.is_relative_to(SOURCE):
                # Canonical learning files are already mirrored with their assets.
                # Keep cross-links inside that tree instead of copying orphan HTML.
                destination = OUTPUT / target.relative_to(SOURCE)
                local_link = Path(os.path.relpath(destination, path.parent)).as_posix()
                text = text.replace(f'{attribute}="{relative}"', f'{attribute}="{local_link}"')
                continue
            project_relative = target.relative_to(ROOT)
            destination = OUTPUT / '_project' / project_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
            text = text.replace(f'{attribute}="{relative}"', f'{attribute}="../_project/{project_relative.as_posix()}"')
        path.write_text(text, encoding='utf-8')
    print(f'Published learning workspace: {OUTPUT}')


if __name__ == '__main__':
    main()

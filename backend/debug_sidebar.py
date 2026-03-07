from pathlib import Path
import re

_here = Path(__file__).resolve().parent
text = (_here / "ui" / "components" / "sidebar.py").read_text()
m = re.search(r'custom_html = f"""(.*)"""', text, flags=re.S)
if m:
    html = m.group(1)
    processed = html.replace('{{', '{').replace('}}', '}')
    # print entire html around script
    idx = processed.find('<script>')
    print(processed[idx:idx+500])
else:
    print('not found')

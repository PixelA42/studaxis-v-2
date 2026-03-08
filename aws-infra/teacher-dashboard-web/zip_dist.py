"""Create deploy.zip with forward slashes (Amplify/Linux compatible)."""
import zipfile
from pathlib import Path

dist = Path("dist")
out = Path("deploy.zip")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in dist.rglob("*"):
        if f.is_file():
            arcname = f.relative_to(dist).as_posix()
            zf.write(f, arcname)

print(f"Created {out}")

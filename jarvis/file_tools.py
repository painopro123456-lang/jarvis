"""Read-only file discovery helpers."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import hashlib

def find_duplicates(limit: int=30) -> str:
    roots=[Path.home()/"Desktop",Path.home()/"Documents",Path.home()/"Downloads"]
    by_size=defaultdict(list)
    scanned=0
    for root in roots:
        if not root.exists(): continue
        try:
            for p in root.rglob("*"):
                try:
                    if p.is_file() and not p.is_symlink():
                        size=p.stat().st_size
                        if size>0: by_size[size].append(p)
                        scanned+=1
                except (OSError,PermissionError): pass
                if scanned>=15000: break
        except (OSError,PermissionError): pass
    duplicates=[]
    for size,paths in by_size.items():
        if len(paths)<2: continue
        hashes=defaultdict(list)
        for p in paths:
            try:
                h=hashlib.sha256()
                with p.open("rb") as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
                hashes[h.hexdigest()].append(p)
            except (OSError,PermissionError): pass
        for group in hashes.values():
            if len(group)>1:
                duplicates.append((size,group))
                if sum(len(g) for _,g in duplicates)>=limit: break
    if not duplicates: return f"No duplicate files found in Desktop, Documents or Downloads (checked up to {scanned} files)."
    lines=[f"Found {len(duplicates)} duplicate groups (read-only; nothing was deleted):"]
    for size,group in duplicates:
        lines.append(f"\n{size/1024/1024:.1f} MB each:")
        lines.extend("  "+str(p) for p in group)
    return "\n".join(lines)

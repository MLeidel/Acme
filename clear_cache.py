#!/usr/bin/env python3
# delcache.py

# WARNING: If a browser/process is running and using the cache,
# you may lose data or see weird behavior until it restarts.

import os
import shutil
from pathlib import Path

def clear_by_deleting():
    ''' Removes all cached items for the neo browser (neo.pyc) '''
    cache_root = Path.home() / ".cache" / "acme.pyc" / "WebKitCache" / "Version 17"
    if not cache_root.exists():
        print("Cache path not found:", cache_root)
    else:
        shutil.rmtree(cache_root)
        print("Deleted:", cache_root)

    cache_root = Path.home() / ".cache" / "acme.py" / "WebKitCache" / "Version 17"
    if not cache_root.exists():
        print("Cache path not found:", cache_root)
    else:
        shutil.rmtree(cache_root)
        print("Deleted:", cache_root)

if __name__ == "__main__":
    clear_by_deleting()


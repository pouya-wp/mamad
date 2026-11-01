"""Install an OpenAI key from stdin inside the Frappe backend container.

Usage: docker exec -i cafe-backend-1 env/bin/python /tmp/install-openai-key.py
The key is never passed as a command-line argument or printed.
"""

import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path


config_path = Path("/home/frappe/frappe-bench/sites/frontend/site_config.json")
key = sys.stdin.readline().strip().replace("\\_", "_")
if not re.fullmatch(r"sk-proj-[A-Za-z0-9_-]{50,}", key):
    raise SystemExit("Invalid project key format; nothing changed")

config = json.loads(config_path.read_text(encoding="utf-8"))
config["ai_api_key"] = key
original_stat = config_path.stat()
fd, temporary_path = tempfile.mkstemp(prefix=".site_config.", dir=config_path.parent)
try:
    os.fchmod(fd, stat.S_IMODE(original_stat.st_mode))
    os.fchown(fd, original_stat.st_uid, original_stat.st_gid)
    with os.fdopen(fd, "w", encoding="utf-8") as target:
        json.dump(config, target, ensure_ascii=False, indent=2)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary_path, config_path)
except BaseException:
    try:
        os.unlink(temporary_path)
    except FileNotFoundError:
        pass
    raise

print("OpenAI key installed in site configuration")

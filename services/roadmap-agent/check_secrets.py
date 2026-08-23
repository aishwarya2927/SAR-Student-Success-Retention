"""
check_secrets.py

Run this from inside services/roadmap-agent (same folder as chat_app.py):

    python check_secrets.py

It reads .streamlit/secrets.toml directly (bypassing Streamlit entirely) and
tells you exactly what's wrong: a TOML parse error with line number, or a
missing/malformed key, or if parsing succeeds, prints the resolved
structure with password hashes masked (never printed in full).
"""

import sys
from pathlib import Path

secrets_path = Path(".streamlit") / "secrets.toml"

if not secrets_path.exists():
    print(f"FAIL: {secrets_path.resolve()} does not exist.")
    print("Check you're running this from services/roadmap-agent, and that")
    print("the file is actually named secrets.toml (not secrets.toml.txt).")
    sys.exit(1)

raw_text = secrets_path.read_text(encoding="utf-8")
print(f"File found: {secrets_path.resolve()}  ({len(raw_text.splitlines())} lines)\n")

try:
    import tomllib  # Python 3.11+
    parsed = tomllib.loads(raw_text)
except ModuleNotFoundError:
    try:
        import tomli
        parsed = tomli.loads(raw_text)
    except ModuleNotFoundError:
        print("Neither tomllib (3.11+) nor tomli is available.")
        print("Run: pip install tomli --break-system-packages")
        sys.exit(1)
except Exception as e:
    print("FAIL: secrets.toml is not valid TOML.")
    print(f"Parse error: {e}")
    print("\nMost common cause: two or more `key = value` pairs (or a")
    print("[table] header and a key) ended up on the same line. Every")
    print("key = value pair and every [table.header] must be on its own line.")
    sys.exit(1)

print("PASS: secrets.toml parsed successfully as TOML.\n")

auth = parsed.get("auth")
if auth is None:
    print("FAIL: no top-level [auth...] section found at all.")
    print("Expected [auth.cookie] and [auth.credentials.usernames.<id>] tables.")
    sys.exit(1)

cookie = auth.get("cookie")
if cookie is None:
    print("FAIL: [auth.cookie] table is missing.")
else:
    print("[auth.cookie] contents:")
    print(f"  name         = {cookie.get('name')!r}")
    key_val = cookie.get("key")
    print(f"  key          = {'<set, ' + str(len(key_val)) + ' chars>' if key_val else '<MISSING>'}")
    print(f"  expiry_days  = {cookie.get('expiry_days')!r}")

credentials = auth.get("credentials")
if credentials is None:
    print("\nFAIL: [auth.credentials...] table is missing.")
    sys.exit(1)

usernames = credentials.get("usernames")
if not usernames:
    print("\nFAIL: no usernames found under [auth.credentials.usernames.*]")
    sys.exit(1)

print(f"\n[auth.credentials.usernames] — {len(usernames)} user(s) found:")
for username, details in usernames.items():
    password = details.get("password", "")
    masked = (password[:7] + "..." + str(len(password)) + " chars") if password else "<MISSING>"
    print(f"  username key = {username!r}")
    print(f"    name     = {details.get('name')!r}")
    print(f"    email    = {details.get('email')!r}")
    print(f"    password = {masked}")

print("\nIf everything above looks correct, the config itself is fine and")
print("the problem is elsewhere (e.g. Streamlit caching an old secrets")
print("read — try fully stopping and restarting `streamlit run`).")
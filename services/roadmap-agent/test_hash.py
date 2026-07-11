"""
test_hash.py — one-time diagnostic script.
Run with:  python test_hash.py
Confirms whether a plain-text password actually matches a bcrypt hash,
without any shell quoting issues (PowerShell mangles $ signs on the
command line, so this check must live in a real .py file).
 
Delete this file once you're done testing.
"""
 
import bcrypt
 
# Edit these two values to whatever you're testing:
PLAIN_PASSWORD = "CHANGE-ME-1"
STORED_HASH = "$2b$12$UiwgGGDTJ7rU06.V3o.skel3LGR4QGhkwD4GxzojteorBs5AaK6Zy"
 
result = bcrypt.checkpw(PLAIN_PASSWORD.encode("utf-8"), STORED_HASH.encode("utf-8"))
print("Password matches hash:", result)
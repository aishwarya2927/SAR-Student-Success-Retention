"""
generate_password_hashes.py

One-time, OFFLINE utility to generate bcrypt password hashes compatible with
streamlit-authenticator==0.3.2 (see requirements.txt).

⚠️ SECURITY WARNING
--------------------
- Run this locally. Do NOT run it on Streamlit Cloud or any shared server.
- Do NOT commit this file to Git after filling in real plain-text passwords.
- Do NOT paste real passwords into chat_app.py — hashing must never happen
  inside the running app or on every rerun.
- After copying the printed hashes into .streamlit/secrets.toml, clear the
  STUDENT_PASSWORDS dict below (or delete this file / your shell history).
- Never print or log plain-text passwords after hashing.

USAGE
-----
1. Edit STUDENT_PASSWORDS below: map each real Student ID (must exist in the
   student CSV dataset) to a TEMPORARY plain-text password.
2. Run:
       python generate_password_hashes.py
3. Copy each printed block into .streamlit/secrets.toml
   (NEVER into secrets.example.toml, and NEVER into Git).
4. Immediately clear the plain-text passwords from this file.
"""

import streamlit_authenticator as stauth

# ----------------------------------------------------------------------
# EDIT THIS LOCALLY ONLY. Never commit real values.
# ----------------------------------------------------------------------
STUDENT_PASSWORDS = {
    # "STUDENT_ID": "TemporaryPlainTextPassword",
    "STU202600058": "CHANGE-ME-1",
    "STU202600091": "CHANGE-ME-2",
    "STU202600114": "CHANGE-ME-3",
}
# ----------------------------------------------------------------------


def _hash_one(plain_password: str) -> str:
    """
    Hashes a single plain-text password to bcrypt, trying every known
    streamlit-authenticator Hasher API shape (this has changed across
    package versions/builds), so this script keeps working regardless of
    exactly which variant is installed.
    """
    # Variant A: top-level stauth.Hasher(list).generate() -> list[str]
    if hasattr(stauth, "Hasher"):
        try:
            return stauth.Hasher([plain_password]).generate()[0]
        except Exception:
            pass
        try:
            return stauth.Hasher.hash(plain_password)
        except Exception:
            pass
        try:
            return stauth.Hasher().hash(plain_password)
        except Exception:
            pass

    # Variant B: Hasher moved to streamlit_authenticator.utilities.hasher
    try:
        from streamlit_authenticator.utilities.hasher import Hasher as _Hasher
        try:
            return _Hasher([plain_password]).generate()[0]
        except Exception:
            pass
        try:
            return _Hasher.hash(plain_password)
        except Exception:
            pass
        try:
            return _Hasher().hash(plain_password)
        except Exception:
            pass
    except ImportError:
        pass

    # Variant C: plain bcrypt fallback (works no matter what, since
    # streamlit-authenticator's own dependency list includes bcrypt).
    try:
        import bcrypt
        return bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
    except Exception:
        pass

    raise RuntimeError(
        "Could not hash the password with any known API.\n"
        "Run this diagnostic command and share the output:\n"
        '  python -c "import streamlit_authenticator as stauth; print(dir(stauth))"'
    )


def main() -> None:
    if not STUDENT_PASSWORDS:
        print("STUDENT_PASSWORDS is empty. Nothing to hash.")
        return

    student_ids = list(STUDENT_PASSWORDS.keys())
    plain_passwords = list(STUDENT_PASSWORDS.values())

    hashed_passwords = [_hash_one(pw) for pw in plain_passwords]

    print("\nCopy the following into .streamlit/secrets.toml "
          "(create the [auth.credentials.usernames.<ID>] table if it "
          "doesn't already exist, and only add the `password` line under it):\n")

    for sid, hashed in zip(student_ids, hashed_passwords):
        print(f"[auth.credentials.usernames.{sid}]")
        print(f'password = "{hashed}"')
        print()

    print(
        "⚠️  Reminder: clear STUDENT_PASSWORDS above now, and never commit "
        "plain-text passwords, hashes, or this output to a public repository."
    )


if __name__ == "__main__":
    main()

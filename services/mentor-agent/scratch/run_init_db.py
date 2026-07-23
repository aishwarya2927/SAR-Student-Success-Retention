import os
import sys

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def run():
    print(f"DATABASE_URL is: {database.DATABASE_URL}")
    print(f"IS_POSTGRES is: {database.IS_POSTGRES}")
    print("Running init_db()...")
    try:
        database.init_db()
        print("init_db() finished successfully!")
    except Exception as e:
        print(f"Error during init_db(): {e}")

if __name__ == "__main__":
    run()

"""Create the MongoDB users of both instances, each limited to the ex09 database.

  ex09_app     readWrite on ex09   (instance A)
  ex09_reader  read on ex09        (instance B)

Runs as root (MONGO_ADMIN_URL in .env.setup). Safe to run again.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(".env.setup", override=True)

DB = os.environ["MONGO_DB"]
USERS = {
    "ex09_app": ("readWrite", os.environ["MONGO_APP_PASSWORD"]),
    "ex09_reader": ("read", os.environ["MONGO_READER_PASSWORD"]),
}


def main() -> None:
    # The users live in ex09 (authSource=ex09), so they cannot clash with users of other projects.
    admin_db = MongoClient(os.environ["MONGO_ADMIN_URL"])[DB]
    for user, (role, password) in USERS.items():
        roles = [{"role": role, "db": DB}]
        if admin_db.command("usersInfo", user)["users"]:
            admin_db.command("updateUser", user, pwd=password, roles=roles)
            print(f"updated user {user} on {DB}: {role} on {DB}")
        else:
            admin_db.command("createUser", user, pwd=password, roles=roles)
            print(f"created user {user} on {DB}: {role} on {DB}")


if __name__ == "__main__":
    main()

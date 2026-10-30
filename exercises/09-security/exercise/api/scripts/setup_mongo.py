"""Create the MongoDB user ex09_app with readWrite on the ex09 database only.

Runs as root (MONGO_ADMIN_URL), then connects as the new user (MONGO_URL) to show that a
write to another database is refused. Safe to run again.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure

load_dotenv(override=True)

DB = os.environ["MONGO_DB"]
USER = os.environ["MONGO_APP_USER"]


def main() -> None:
    # The user lives in ex09 (authSource=ex09), so it cannot clash with users of other projects.
    admin_db = MongoClient(os.environ["MONGO_ADMIN_URL"])[DB]
    roles = [{"role": "readWrite", "db": DB}]
    password = os.environ["MONGO_APP_PASSWORD"]
    if admin_db.command("usersInfo", USER)["users"]:
        admin_db.command("updateUser", USER, pwd=password, roles=roles)
        print(f"updated user {USER} on {DB}")
    else:
        admin_db.command("createUser", USER, pwd=password, roles=roles)
        print(f"created user {USER} on {DB} with readWrite on {DB} only")

    client = MongoClient(os.environ["MONGO_URL"])
    print(f"connected as {client[DB].command('connectionStatus')['authInfo']['authenticatedUsers']}")
    try:
        client[f"{DB}_other"].probe.insert_one({"x": 1})
        print(f"insert into {DB}_other: allowed (unexpected)")
    except OperationFailure as exc:
        print(f"insert into {DB}_other: refused ({exc.details['codeName']})")


if __name__ == "__main__":
    main()

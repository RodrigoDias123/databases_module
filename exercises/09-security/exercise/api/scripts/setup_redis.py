"""Create the Redis ACL user ex09_app, which may only run INCR on keys counter:*.

Runs ACL SETUSER as the default user (REDIS_ADMIN_URL), then connects as the new user.
Every refused command is first checked with ACL DRYRUN, so nothing dangerous is ever sent.
"""

import os

import redis
from dotenv import load_dotenv

load_dotenv(override=True)

USER = os.environ["REDIS_APP_USER"]
PASSWORD = os.environ["REDIS_APP_PASSWORD"]
RULES = ("reset", "on", f">{PASSWORD}", "~counter:*", "-@all", "+incr", "+select")


def main() -> None:
    admin = redis.Redis.from_url(os.environ["REDIS_ADMIN_URL"], decode_responses=True)
    # reset: start from no permissions, so running this again gives the same result.
    # ~counter:*: only these keys. -@all +incr: only INCR. +select: the URL picks database 9.
    admin.execute_command("ACL", "SETUSER", USER, *RULES)
    print(f"ACL SETUSER {USER} {' '.join(RULES).replace(PASSWORD, '***')}")

    app = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    print(f"{'INCR counter:probe':<20} -> {app.execute_command('INCR', 'counter:probe')}")
    for command in (("INCR", "other:probe"), ("GET", "counter:probe"), ("KEYS", "*"), ("FLUSHALL",)):
        label = " ".join(command)
        # Send it as ex09_app only once Redis has confirmed that the ACL refuses it.
        if admin.execute_command("ACL", "DRYRUN", USER, *command) == "OK":
            print(f"{label:<20} -> allowed by the ACL (not sent)")
            continue
        try:
            app.execute_command(*command)
        except redis.exceptions.NoPermissionError as exc:
            print(f"{label:<20} -> {exc}")
    admin.delete("counter:probe")


if __name__ == "__main__":
    main()

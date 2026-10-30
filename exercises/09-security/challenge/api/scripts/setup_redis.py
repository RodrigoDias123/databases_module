"""Create the Redis ACL users of both instances, each limited to keys counter:*.

  ex09_app     INCR and GET   (instance A)
  ex09_reader  GET only       (instance B)

Runs ACL SETUSER as the default user (REDIS_ADMIN_URL in .env.setup), then asks Redis with
ACL DRYRUN what each user may run. Nothing is sent as the restricted users here.
"""

import os

import redis
from dotenv import load_dotenv

load_dotenv(".env.setup", override=True)

# reset: start from no permissions, so running this again gives the same result.
# ~counter:*: only these keys. -@all: no command unless listed. +select: the URLs pick database 9.
USERS = {
    "ex09_app": (os.environ["REDIS_APP_PASSWORD"], ("+incr", "+get")),
    "ex09_reader": (os.environ["REDIS_READER_PASSWORD"], ("+get",)),
}
PROBES = (("GET", "counter:x"), ("INCR", "counter:x"), ("GET", "other:x"), ("SET", "counter:x", "1"))


def main() -> None:
    admin = redis.Redis.from_url(os.environ["REDIS_ADMIN_URL"], decode_responses=True)
    for user, (password, commands) in USERS.items():
        rules = ("reset", "on", f">{password}", "~counter:*", "-@all", *commands, "+select")
        admin.execute_command("ACL", "SETUSER", user, *rules)
        print(f"ACL SETUSER {user} {' '.join(rules).replace(password, '***')}")
    for user in USERS:
        for command in PROBES:
            answer = admin.execute_command("ACL", "DRYRUN", user, *command)
            print(f"  {user:<12} {' '.join(command):<18} -> {answer}")


if __name__ == "__main__":
    main()

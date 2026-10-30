import os

import psycopg
import redis
from dotenv import load_dotenv
from pymongo import MongoClient

# override=True: the .env of this project wins over URLs already in the shell (the dev container
# sets REDIS_URL and MONGO_URL for the root users), so the app never runs as an admin by accident.
load_dotenv(override=True)

# Every connection uses the limited users of the exercise. The admin URLs are only read
# by the setup scripts.
DATABASE_URL = os.environ["DATABASE_URL"]

# ex09_app with readWrite on the ex09 database only.
mongo = MongoClient(os.environ["MONGO_URL"])
mongo_db = mongo[os.environ["MONGO_DB"]]

# ex09_app may only run INCR on keys that start with counter:.
r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def pg_connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)

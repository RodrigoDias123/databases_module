import os

import psycopg
import redis
from dotenv import load_dotenv
from pymongo import MongoClient

# The same code runs as instance A or B: only the environment differs. ENV_FILE picks the file
# (.env.a or .env.b). override=True: the file wins over URLs already in the shell (the dev container
# sets REDIS_URL and MONGO_URL for the root users), so an instance never runs as an admin by accident.
load_dotenv(os.environ.get("ENV_FILE", ".env"), override=True)

DATABASE_URL = os.environ["DATABASE_URL"]

mongo = MongoClient(os.environ["MONGO_URL"])
mongo_db = mongo[os.environ["MONGO_DB"]]

r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def pg_connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)

from typing import Annotated

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr
from pymongo.errors import OperationFailure

from app.clients import mongo_db, pg_connect, r

app = FastAPI(title="Challenge 09: security")


# --- Privilege errors -----------------------------------------------------------------------
# The code never asks which instance it is. A write is refused by the engine, and these handlers
# turn exactly that refusal into a 403. Every other error is raised again and stays a 500.

def forbidden(engine: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": f"{engine} refused: {message}"})


@app.exception_handler(psycopg.Error)
def postgres_error(request: Request, exc: psycopg.Error):
    # 42501 insufficient_privilege: "permission denied for table actor".
    if exc.sqlstate == "42501":
        return forbidden("postgres", exc.diag.message_primary)
    raise exc


@app.exception_handler(OperationFailure)
def mongo_error(request: Request, exc: OperationFailure):
    # 13 Unauthorized: "not authorized on ex09 to execute command { insert: ... }".
    if exc.code == 13:
        # Only the code name: the full message repeats the whole internal command.
        return forbidden("mongo", exc.details["codeName"])
    raise exc


@app.exception_handler(redis.exceptions.NoPermissionError)
def redis_error(request: Request, exc: redis.exceptions.NoPermissionError):
    # Redis answers -NOPERM when the ACL does not allow the command or the key.
    return forbidden("redis", str(exc))


# --- PostgreSQL -----------------------------------------------------------------------------

class ActorIn(BaseModel):
    first_name: StrictStr
    last_name: StrictStr


@app.post("/actors", status_code=201)
def create_actor(body: ActorIn):
    """The SQL text and the values travel separately: the values are never parsed as SQL."""
    with pg_connect() as conn:
        actor_id = conn.execute(
            "INSERT INTO actor (first_name, last_name) VALUES (%s, %s) RETURNING actor_id",
            (body.first_name, body.last_name),
        ).fetchone()[0]
    return {"actor_id": actor_id}


@app.get("/actors/{actor_id}")
def get_actor(actor_id: int):
    with pg_connect() as conn:
        row = conn.execute(
            "SELECT actor_id, first_name, last_name FROM actor WHERE actor_id = %s", (actor_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "actor not found")
    return {"actor_id": row[0], "first_name": row[1], "last_name": row[2]}


# --- MongoDB --------------------------------------------------------------------------------

class NoteIn(BaseModel):
    # Strict types: "1" is not coerced to 1, and {"$ne": null} is not a string, so both are a 422.
    # extra="forbid": no other field reaches the document.
    model_config = ConfigDict(extra="forbid")

    customer_id: StrictInt
    text: StrictStr


@app.post("/notes", status_code=201)
def create_note(body: NoteIn):
    """The document is built from typed fields, never from the raw JSON body."""
    result = mongo_db.notes.insert_one({"customer_id": body.customer_id, "text": body.text})
    return {"id": str(result.inserted_id)}


@app.get("/notes")
def list_notes(customer_id: int):
    """customer_id is parsed as an int, so the filter can never become an operator."""
    notes = mongo_db.notes.find({"customer_id": customer_id}).sort("_id", 1)
    return [{"id": str(n["_id"]), "customer_id": n["customer_id"], "text": n["text"]} for n in notes]


# --- Redis ----------------------------------------------------------------------------------

# Letters, digits, _ and - only: no glob characters (*, ?, [) and no : to escape the counter: prefix.
CounterName = Annotated[str, Path(pattern=r"^[a-z0-9_-]{1,32}$")]


@app.post("/counters/{name}")
def increment_counter(name: CounterName):
    """INCR on one fixed key. The key name is validated before it reaches Redis."""
    # r.incr() sends INCRBY, which the ACL does not allow: send exactly INCR.
    return {"name": name, "value": r.execute_command("INCR", f"counter:{name}")}


@app.get("/counters/{name}")
def get_counter(name: CounterName):
    """A counter that was never incremented does not exist yet: it reads as 0, as INCR would start."""
    value = r.execute_command("GET", f"counter:{name}")
    return {"name": name, "value": int(value or 0)}

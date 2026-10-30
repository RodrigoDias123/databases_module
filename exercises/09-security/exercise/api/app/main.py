from typing import Annotated

from fastapi import FastAPI, Path
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from app.clients import mongo_db, pg_connect, r

app = FastAPI(title="Exercise 09: security")


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


# --- Redis ----------------------------------------------------------------------------------

# Letters, digits, _ and - only: no glob characters (*, ?, [) and no : to escape the counter: prefix.
CounterName = Annotated[str, Path(pattern=r"^[a-z0-9_-]{1,32}$")]


@app.post("/counters/{name}")
def increment_counter(name: CounterName):
    """INCR on one fixed key. The key name is validated before it reaches Redis."""
    # r.incr() sends INCRBY, which the ACL does not allow: send exactly INCR.
    return {"name": name, "value": r.execute_command("INCR", f"counter:{name}")}

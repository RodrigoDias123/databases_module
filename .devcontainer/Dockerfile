# Pinned to bookworm: the PGDG and MongoDB apt repos below are bookworm ones
FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends gnupg curl ca-certificates \
 # PostgreSQL 18 client: pg_dump/pg_restore must be >= the server version
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
 # mongosh + mongodump/mongorestore
 && curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
      | gpg --dearmor -o /usr/share/keyrings/mongodb-8.0.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/mongodb-8.0.gpg] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" \
      > /etc/apt/sources.list.d/mongodb-org-8.0.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      postgresql-client-18 redis-tools mongodb-mongosh \
 # mongodb-database-tools has no arm64 build in the Debian repo (Apple Silicon),
 # so install the .deb from MongoDB's download site for the right architecture
 && case "$(dpkg --print-architecture)" in \
      arm64) MDBT_PLATFORM=ubuntu2204-arm64 ;; \
      *)     MDBT_PLATFORM=debian12-x86_64 ;; \
    esac \
 && curl -fsSL -o /tmp/mdbt.deb \
      "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-${MDBT_PLATFORM}-100.13.0.deb" \
 && apt-get install -y --no-install-recommends /tmp/mdbt.deb \
 && rm -f /tmp/mdbt.deb \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

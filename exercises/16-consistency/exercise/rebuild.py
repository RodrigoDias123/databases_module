"""Rebuild customer:{customer_id}:categories in Redis from PostgreSQL.

One query reads every (customer, category) pair; one pipeline writes every set. Each set
is built in a temporary key and renamed over the real one, so readers see the old set or
the new one, never half of it. Keys of customers who should not have a set are deleted.
"""

from categories import existing_keys, expected_sets, r


def main() -> None:
    expected = expected_sets()  # the one query
    stale = existing_keys() - expected.keys()  # e.g. a set for a customer with no rentals

    pipe = r.pipeline(transaction=False)  # one round trip; each RENAME is atomic on its own
    for key, names in expected.items():
        tmp = f"{key}:tmp"  # does not match customer:*:categories, so verify never sees it
        pipe.delete(tmp)
        pipe.sadd(tmp, *names)
        pipe.rename(tmp, key)  # replaces the old set in one step
    for key in stale:
        pipe.delete(key)
    pipe.execute()

    print(f"rebuilt {len(expected)} sets, deleted {len(stale)} stale keys")


if __name__ == "__main__":
    main()

"""Compare every customer:{customer_id}:categories set with PostgreSQL.

Prints every difference (missing key, wrong size, missing or extra members, key for a
customer who should not have one) and exits with 1 if there is any, 0 otherwise.
"""

import sys

from categories import existing_keys, expected_sets, r


def main() -> int:
    expected = expected_sets()
    present = existing_keys()

    # read every expected set in one pipeline (one round trip instead of 997)
    keys = sorted(expected, key=lambda k: int(k.split(":")[1]))
    pipe = r.pipeline(transaction=False)
    for key in keys:
        pipe.smembers(key)
    actual = dict(zip(keys, pipe.execute()))

    problems: list[str] = []
    for key in keys:
        want, got = expected[key], actual[key]
        if key not in present:
            problems.append(f"{key}: missing (expected {len(want)} members)")
            continue
        if len(got) != len(want):
            problems.append(f"{key}: size {len(got)}, expected {len(want)}")
        if missing := want - got:
            problems.append(f"{key}: missing members {sorted(missing)}")
        if extra := got - want:
            problems.append(f"{key}: extra members {sorted(extra)}")
    for key in sorted(present - expected.keys()):
        problems.append(f"{key}: should not exist ({r.scard(key)} members)")

    for line in problems:
        print(line)
    print(
        f"checked {len(keys)} sets, {len(present)} keys in Redis: "
        + (f"{len(problems)} differences" if problems else "OK")
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

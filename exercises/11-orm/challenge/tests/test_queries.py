from sqlalchemy import text

from queries import films_with_actors_and_categories

# Handwritten SQL for the same result, counted outside assert_max_queries.
EXPECTED = text("""
    SELECT
        (SELECT count(*) FROM film_actor WHERE film_id <= 100) AS actors,
        (SELECT count(*) FROM film_category WHERE film_id <= 100) AS categories
""")


def test_first_100_films_with_actors_and_categories(session, assert_max_queries):
    with assert_max_queries(3):
        films = films_with_actors_and_categories(session)

    expected = session.execute(EXPECTED).one()
    assert len(films) == 100
    assert films[0]["title"] == "ACADEMY DINOSAUR"
    assert "PENELOPE GUINESS" in films[0]["actors"]
    assert sum(len(f["actors"]) for f in films) == expected.actors
    assert sum(len(f["categories"]) for f in films) == expected.categories

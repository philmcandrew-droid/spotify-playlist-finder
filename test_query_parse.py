from query_parse import parse_quoted, playlist_name_score, playlist_search_queries


def test_parse_quoted_variants():
    assert parse_quoted("Phil McAndrew") == ("Phil McAndrew", False)
    assert parse_quoted('"Phil McAndrew"') == ("Phil McAndrew", True)
    assert parse_quoted("“Phil McAndrew”") == ("Phil McAndrew", True)
    assert parse_quoted('"Phil McAndrew”') == ("Phil McAndrew", True)
    assert parse_quoted("  Phil   McAndrew  ") == ("Phil McAndrew", False)
    assert parse_quoted("'Phil McAndrew'") == ("'Phil McAndrew'", False)


def test_playlist_scores():
    assert playlist_name_score("Phil McAndrew Live", "Phil McAndrew") == 300
    assert playlist_name_score("Best of Phil McAndrew", "Phil McAndrew") == 200
    assert playlist_name_score("Phil Coulter", "Phil McAndrew") == 0
    assert playlist_name_score("Phil McAndrew", "Phil McAndrew") == 400


def test_search_queries():
    assert playlist_search_queries(["Phil McAndrew"], exact=True) == ['"Phil McAndrew"', "Phil McAndrew"]
    assert playlist_search_queries(["Phil McAndrew"], exact=False) == ["Phil McAndrew"]


if __name__ == "__main__":
    test_parse_quoted_variants()
    test_playlist_scores()
    test_search_queries()
    print("ok")

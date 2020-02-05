from IncidentsPerFeed import get_feeds, main, generate_query_params
from CommonServerPython import demisto

MODULES = {"test feed": {"brand": "test feed", "state": "active"},
           "non active feed": {"brand": "non active feed", "state": "disabled"},
           "some module": {"brand": "some module", "state": "active"}}


def test_results_structure(mocker):
    incidents = [{"Contents": {"total": 10}}]
    mocker.patch.object(demisto, 'getModules', return_value=MODULES)
    mocker.patch.object(demisto, 'executeCommand', return_value=incidents)
    mocker.patch.object(demisto, 'results')
    expected_result = [{'groups': [{'data': [10], 'name': 'Incidents'}], 'name': 'test feed'}]
    main()
    results = demisto.results.call_args[0][0]["Contents"]
    assert results == expected_result, f'Did not got the expected results:\n{results} != {expected_result}'


def test_get_active_feeds(mocker):
    mocker.patch.object(demisto, 'getModules', return_value=MODULES)
    feeds = get_feeds()
    assert feeds == {"test feed"}


def test_query_parameters():
    tests = {
        ("test_feed", "3 days ago", "closeReason:False Positive"):
            {"query": f'indicator.sourceBrands:test_feed and closeReason:False Positive',
             "fromdate": "3 days ago"},
        ("test_feed", "3 days ago", None): {"query": f'indicator.sourceBrands:test_feed', "fromdate": "3 days ago"},
        ("test_feed", None, None): {"query": f'indicator.sourceBrands:test_feed'}
    }
    for params, expected_response in tests.items():
        _assert_query_params(params, expected_response)


def _assert_query_params(params, expected_query):
    query = generate_query_params(*params)
    assert query == expected_query, f"Did not got the expected query:\n{query} != {expected_query}"

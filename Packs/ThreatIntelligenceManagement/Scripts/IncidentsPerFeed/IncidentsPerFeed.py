from CommonServerPython import *


def get_incidents_count_by_feed(feed, from_date, query=None) -> int:
    """Counts the incidents amount that fits the query and has indicators that came from the given feed.
        Args:
                feed: Feed from which the incidents' indicator should be from
                from_date: The date from the incidents should be queried
                query: Additional filters for the 'getIncidents' command
        Returns:
            total amount of incidents returned.
    """
    params = generate_query_params(feed, from_date, query)
    res = demisto.executeCommand("getIncidents", params)
    queried_incidents_count = res[0]["Contents"]["total"]
    return queried_incidents_count


def generate_query_params(feed, from_date, query):
    """Generating parameters for 'getIncidents' command according to relevant feed, date, and additional query
        Args:
                feed: Feed from which the incidents indicator should be from
                from_date: The date from the incidents should be queried
                query: Additional filters for the 'getIncidents' command

        Returns:
            A set with feed names
        """
    query_string = f'indicator.sourceBrands:{feed}'
    if query:
        query_string += f' and {query}'
    params = {"query": query_string}
    if from_date:
        params.update({"fromdate": from_date})
    return params


def get_feeds() -> set:
    """Return all enabled modules
            Returns:
                A set with feed names
    """
    modules = demisto.getModules()  # type: ignore  # pylint: disable=E1101
    return {module_details["brand"] for module_details in modules.values() if  # pylint: disable=E1101
            active_feed(module_details)}


def active_feed(module) -> bool:
    """Checks if module is active and if it's a feed and return a boolean accordingly
        Args:
                module: Module to check if is active feed
        Returns:
            True if the module's brand has 'feed' in it and if module 'state is 'active' else False
    """
    return 'feed' in module["brand"].lower() and module["state"] == 'active'


def generate_groups(feed_types,
                    from_date,
                    distinct_incidents_query=None,
                    distinction_name=None,
                    ):
    """If distinct_incidents_query is given- return the amount of incidents that match the query and the amount of
    the remaining incidents that has indicators from those feeds.
    If distinct_incidents_query is not given- will only return the amount
        Args:
               feed_types :A set Containing feed names
               distinct_incidents_query: A string with additional incidents query. Example: 'closeReason:"False Positive"'
               distinction_name: A string with the distinction name to display in the widget. Example: 'False Positive Incidents'
        Returns:
            Chart widget require list of 'group' as response
       where group has "name": string, "data" [int], "groups": [group]
        """
    data = {}
    for feed in feed_types:
        incidents_count_by_feed = get_incidents_count_by_feed(feed, from_date)
        distinct_incidents_count = get_incidents_count_by_feed(feed,
                                                               from_date,
                                                               distinct_incidents_query) if distinct_incidents_query else 0
        data[feed] = [{"name": "Incidents", "data": [incidents_count_by_feed - distinct_incidents_count]}]
        if distinction_name:
            data[feed].append({"name": distinction_name, "data": [distinct_incidents_count]})

    return [{"name": key, "groups": value} for key, value in data.items()]


def main():
    feed_types = get_feeds()
    distinct_incidents_query = demisto.args().get("query")
    distinct_incidents = demisto.args().get("incidents_distinction_name")
    from_date = demisto.args().get('from')
    groups = generate_groups(feed_types, from_date, distinct_incidents_query, distinct_incidents)
    human_readable = tableToMarkdown('Incidents count by feed', groups)
    demisto.results({
        'Type': entryTypes['note'],
        'Contents': groups,
        'ContentsFormat': formats['text'],
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': human_readable
    })


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()

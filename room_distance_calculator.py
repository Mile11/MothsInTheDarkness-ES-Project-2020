"""
EXPERT SYSTEM PROJECT 2020/2021
Faculty of Electrical Engineering and Computing
FILIP MILIC

Utility module used for constructing graphs and calculating minimum distances between rooms.
"""

import math


def bellman_ford(graph, first):
    """
    The Bellman-Ford algorithm determines the shortesr distance from the start
    node, to all of the other nodes in the graph.

    :param graph: The graph.
    :param first: The node from which we want to figure out the shortest path from.
    :return:
    """

    d = {}
    predecessor = {}
    new_graph = {}

    for node in graph.keys():
        if node == first:
            d[node] = 0
            predecessor[node] = ''
        else:
            d[node] = math.inf
            predecessor[node] = ''

    to_be_ch = set()
    to_be_ch.add(first)

    while len(to_be_ch) != 0:
        v = to_be_ch.pop()
        for u in graph[v]:
            dnew = d[v] + u[1]
            if dnew < d[u[0]]:
                d[u[0]] = dnew
                predecessor[u[0]] = v
                to_be_ch.add(u[0])

    for node in graph.keys():
        temp = []
        for vs in graph[node]:
            if predecessor[vs[0]] == node:
                temp.append(vs)

        new_graph[node] = temp

    return new_graph


def get_distance(graph, r_from, r_to):
    """
    Calculate the distance between two points in the minimized graph.

    :param graph: Minimized graph.
    :param r_from: Starting room.
    :param r_to: Destination room.
    :return:
    """

    dist = 0
    node = (r_to, 1)
    while node != (r_from, 1):
        for g in graph:
            if node in graph[g]:
                dist += 1
                node = (g, 1)
                break

    return dist


def generate_graph(rooms, with_secret=False):
    """
    Generate the graph from the room structure.

    :param rooms: A list of rooms.
    :param with_secret: Determines whether or not to add secret passages to the graph.
    :return:
    """

    graph = {}
    for r in rooms:
        if r not in graph:
            graph[r] = []
        for e in rooms[r].room_info["exits"].values():
            graph[r].append((e, 1))

        if with_secret and "secret_exits" in rooms[r].room_info:
            for e in rooms[r].room_info["secret_exits"].values():
                graph[r].append((e, 1))

    return graph


def submit_distances(prolog, assets, alibis):
    """
    Adds the distances between the rooms in the alibis and the place of crime
    to the Prolog database, by creating a Bellman-Ford graph and using it to
    calculating the distance between the two nodes.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param assets: All of the game assets.
    :param alibis: The last-known alibis of all the characters.
    :return:
    """

    rooms = assets.rooms

    # Generate a graph, not taking into account the hidden passages.
    graph = generate_graph(rooms)

    # Generate a graph, taking into account the hidden passages between rooms.
    graph_with_secrets = generate_graph(rooms, True)

    # Get the place of crime.
    place_of_crime = list(prolog.query("place_of_crime(X)"))[0]["X"]

    for a in alibis:
        for k in alibis[a]:
            alibi = alibis[a][k]
            if alibi:

                # Create the minimum graphs.
                min_graph = bellman_ford(graph, alibi[0])
                min_graph_with_secret = bellman_ford(graph_with_secrets, alibi[0])

                # Get the distances that depend on the two versions of the graphs.
                dist = get_distance(min_graph, alibi[0], place_of_crime)
                dist_secret = get_distance(min_graph_with_secret, alibi[0], place_of_crime)

                prolog.assertz(f"manhattan({alibi[0]}, {place_of_crime}, {dist})")
                prolog.assertz(f"manhattan_secret({alibi[0]}, {place_of_crime}, {dist_secret})")

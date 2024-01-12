import os
from networkx import DiGraph, topological_generations

from todoist_api_python.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print
from rich.tree import Tree
from dataclasses import asdict

app = typer.Typer(chain=True)
state = {"api": None}

__all__ = ["ThrottledApi", "throttle_requests",
           "tdobj_to_node", "tditer_to_graph"]

REQUEST_LIMIT = 450 / (15 * 60)  # 450 requests per 15 minutes.


class ThrottledApi(TodoistAPI):
    @classmethod
    def wrap_api_calls(cls):
        for method in [getattr(super(), m) for m in dir(super())
                       if not m.startswith("__") and
                       callable(getattr(super(), m))]:
            setattr(cls, throttle_requests(method))

    @property
    def rql(self):
        return self.request_limit

    @rql.setter
    def rql(self, value):
        self.request_limit = value

    def __init__(self, *args, **kwargs):
        self.request_limit = REQUEST_LIMIT
        self.last_r_time = 0
        self.r_rate = None
        super().__init__(*args, **kwargs)

    def update_rate(self):
        print("Update Rate Here.")


PROJECT_KEYS = ["color",
                "comment_count",
                "id",
                "is_favorite",
                "is_inbox_project",
                "is_shared",
                "is_team_inbox",
                "name",
                "order",
                "parent_id",
                "url",
                "view_style"]

TASK_KEYS = [
    "id",
    "content",
    "description",
    "comment_count",
    "is_completed",
    "order",
    "priority",
    "project_id",
    "labels",
    "due",
    "section_id",
    "parent_id",
    "creator_id",
    "created_at",
    "assignee_id",
    "assigner_id",
    "url"]


@ app.command()
def show(itemkind: str):
    api = state["api"]
    print(f"Showing: {itemkind.lower()}")
    match itemkind.lower():
        case "projects":
            result = api.get_projects()

        case "tasks":
            result = api.get_tasks()

        case "labels":
            result = api.get_labels()

    graph, failed = add_to_graph(result)
    link_to_parents(graph)
    return graph


@ app.command()
def add(itemkind: str):
    api = state["api"]
    print(f"Adding: {itemkind}")


@ app.callback()
def startup():
    # I should be able to set up this to take it from the environment
    # or an argument, but it's taking the argument with the env variable
    # as the command.
    api_key = os.environ.get("TODOIST_API_KEY")
    print(api_key)
    api = TodoistAPI(api_key)
    state["api"] = api
    return api


def tdobj_to_node(tdobj, parent_attr_list=["parent_id", "project_id"]):
    """ Return a node and edges suitable for adding to a graph.

    tdobj: an todoist object, or an object with an `id` attribute
        suitable as a nx.DiGraph node, and at least one of `parent_attr_list`
        holding a node id to point to.
            Example: {"id": 123, "parent_id": 321}
    parent_attr_list: list of object attributes that may hold a parent node.

    Returns:
        A tuple of the id and id data suitable for adding to a graph, and a
        dict mapping `parent_attr_list` to the edge data. Edge endpoints of
        None are not returned.
    """
    try:
        nd = asdict(tdobj)
    except TypeError as e:
        raise TypeError(f"asdict failed on {type(tdobj)}") from e

    nd["obj"] = tdobj
    edges = {}
    for attr in parent_attr_list:
        try:
            # Parent ID can be None, not a valid edge.
            if getattr(tdobj, attr) is not None:
                edges[attr] = (tdobj.id, getattr(tdobj, attr))

        except AttributeError:
            pass
    return (nd["id"], nd), edges


def test_tdobj_to_node():
    obj = {"name": "tester",
           "id": 123,
           "parent_id": 321}
    assert tdobj_to_node(obj) == ((obj.id, obj),
                                  {"parent_id": (obj.id, obj.parent_id)})
    del obj["parent_id"]
    obj["project_id"] = 321
    assert tdobj_to_node(obj) == ((obj.id, obj),
                                  {"project_id": (obj.id, obj.project_id)})
    del obj["parent_id"]
    assert tdobj_to_node(obj) == ((obj.id, obj),
                                  {})

    obj = {"name": "tester",
           "id": 123,
           "parent_id": 321,
           "project_id": 213}
    assert tdobj_to_node(obj) == ((obj.id, obj),
                                  {"project_id": (obj.id, obj.project_id),
                                   "parent_id": (obj.id, obj.parent_id),
                                   }
                                  )


def tditer_to_graph(tditer,
                    parent_attr_list=["parent_id", "project_id"],
                    g=None):
    """ Return a graph from an iterable.

    Accepts an iterable of objects with at least an id attribute to be used as a node
    and one attribute named in `parent_attr_list`, as a node to point to.

    tditer: iterable of todoist objects.
    parent_attr_list: list of object attributes that may hold parent node.
        If multiple attributes have values, only the first is used.
        (This is to keep subtasks from pointing to their project
        and parent task.)
    g: an nx.DiGraph to which the `tditer` objects are added.

    Returns: A DiGraph of objects in `tditer`.
    """
    if g is None:
        g = nx.DiGraph()
    ndicts = {}
    for obj in tditer:
        nd, edges = tdobj_to_node(obj, parent_attr_list=parent_attr_list)
        node, node_dict = nd
        g.add_node(node, **node_dict)

        for attr in parent_attr_list:
            try:
                g.add_edge(node, edges[attr][1])
            except KeyError:
                pass

    # g.add_nodes_from(ndicts.items())
    # g.add_edges_from(edges)
    return g


if __name__ == "__main__":
    app()

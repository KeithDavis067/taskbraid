import os
from networkx import DiGraph, topological_generations
import networkx as nx

from todoist_api_python.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print
from rich.tree import Tree
from modify import manage_supertask_link, manage_supertask_links
import nxutils as nxu


app = typer.Typer(chain=True)
state = {"api": None}

__all__ = ["ThrottledApi",
           "tdobj_to_node_and_edges", "tditer_to_graph",
           "manage_supertask_link", "manage_supertask_links"]


REQUEST_LIMIT = 450 / (15 * 60)  # 450 requests per 15 minutes.


def throttle_requests():
    raise NotImplementedError()


class ThrottledApi(TodoistAPI):
    @ classmethod
    def wrap_api_calls(cls):
        for method in [getattr(super(), m) for m in dir(super())
                       if not m.startswith("__") and
                       callable(getattr(super(), m))]:
            setattr(cls, throttle_requests(method))

    @ property
    def rql(self):
        return self.request_limit

    @ rql.setter
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


def tdobj_to_node_and_edges(tdobj,
                            parent_attr_list=["parent_id",
                                              "project_id",
                                              "section_id"],
                            edge_attr_func=lambda obj: type(obj).__name__,
                            **kwargs):
    """ A wrapper around nxutils.obj_to_node_and_edges to set todist defaults."""

    return nxu.obj_to_node_and_edges(tdobj, "id",
                                     parent_attr_list,
                                     edge_attr_func, **kwargs)


def tditer_to_graph(tditer, g=None, ):
    if g is None:
        g = nx.DiGraph()
    nodebunch = []
    edgebunch = []
    for ele in tditer:
        node, edges = tdobj_to_node_and_edges(ele)
        print(edges)
        nodebunch.append(node)
        edgebunch.append(edges)

    g.add_nodes_from(nodebunch)
    g.add_edges_from(edgebunch)


if __name__ == "__main__":
    app()

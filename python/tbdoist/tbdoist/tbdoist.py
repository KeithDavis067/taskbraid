import os
from networkx import DiGraph, topological_generations
import networkx as nx

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task, Project, Section
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
           "td_obj_to_node_and_edges", "td_iter_to_graph",
           "manage_supertask_link", "manage_supertask_links",
           "td_g_to_tree_view"]


REQUEST_LIMIT = 450 / (15 * 60)  # 450 requests per 15 minutes.

TYPE_MAP = {Project: {"id": "project_id",
                      "getter": "get_project",
                      "getser": "get_projects"},
            Task: {"id": "task_id",
                   "getter": "get_task",
                   "getser": "get_tasks"},
            Section: {"id": "section_id",
                      "getter": "get_section",
                      "getser": "get_sections"},
            }

# TODO: Write a tool to build smaller parts of the graph from tdapi.


def build_local_graph(tdapi, obj):
    try:
        tmap = TYPE_MAP[type(obj)]
    except KeyError:
        raise f"Cannot build todoist_api map from type {type(obj)}."

    obj_id = obj.id

    succ = []
    id_attr = TYPE_MAP[type(obj)]["id"]
    for td_type in TYPE_MAP:
        try:
            hold = get


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


def td_obj_to_node_and_edges(tdobj,
                             parent_attr_list=["parent_id",
                                               "project_id",
                                               "section_id"],
                             edge_attr_func=lambda obj: {
                                 "type": type(obj).__name__},
                             **kwargs):
    """ A wrapper around nxutils.obj_to_node_and_edges to set todist defaults."""

    return nxu.obj_to_node_and_edges(tdobj, "id",
                                     parent_attr_list,
                                     edge_attr_func=edge_attr_func, **kwargs)


def td_iter_to_graph(td_iter, g=None, **kwargs):
    if g is None:
        g = nx.DiGraph()
    nodebunch = []
    edgebunch = []
    for ele in td_iter:
        node, edges = td_obj_to_node_and_edges(ele, **kwargs)
        nodebunch.append(node)
        edgebunch += edges

    g.add_nodes_from(nodebunch)
    g.add_edges_from(edgebunch)


def td_obj_to_nb_graph(tdapi, obj):
    for ele in TYPESD:
        TYPESD["ele"]


def is_subtask(obj):
    if not isinstance(obj, Task):
        return False
    try:
        if obj.parent_id is not None:
            return True
    except AttributeError:
        pass
    return False


def is_in_section(obj):
    try:
        if obj.section_id is not None:
            return True
    except AttributeError:
        pass
    return False


def td_g_filter_factory(g):
    def filter(u, v):
        obj = g.nodes[u]["obj"]
        parent_obj = g.nodes[v]["obj"]

        if isinstance(obj, Task):
            if is_subtask(obj):
                if isinstance(parent_obj, Task):
                    print(
                        f"keeping subtask {obj.content} of supertask {parent_obj.content}")
                    return True
                else:
                    return False
            else:
                if is_in_section(obj):
                    if isinstance(parent_obj, Section):
                        return True
                    else:
                        return False
                else:
                    if isinstance(parent_obj, Project):
                        return True
                    else:
                        return False

        return True

    return filter


def td_g_label_func(g, n):
    for attr in ["content", "name"]:
        try:
            try:
                return getattr(g.nodes[n], attr)
            except AttributeError:
                return getattr(g.nodes[n]["obj"], attr)
        except AttributeError:
            continue

    return str(g.nodes[n])


def td_g_to_tree_view(g):
    sg = nx.subgraph_view(g, filter_edge=td_g_filter_factory(g))
    rev = nx.reverse_view(sg)
    return rev


def td_diGraph_to_richTree(g, **kwargs):
    # The filter needs the non-reversed view,
    # but diGraph_to_richTree needs the reversed view.
    rev = td_g_to_tree_view(g)
    return nxu.diGraph_to_richTree(rev, label_func=td_g_label_func)


if __name__ == "__main__":
    app()

import os
from networkx import DiGraph, topological_generations

from todoist_api_python.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print
from rich.tree import Tree

app = typer.Typer(chain=True)
state = {"api": None}

REQUEST_LIMIT = 450 / (15 * 60)  # 450 requests per 15 minutes.


def throttle_requests(method):
    if self.rate_if_call_now > self.rql:


class ThrottledApi(TodoistAPI):
    @classmethod
    def wrap_api_calls(cls):
        for method in [getattr(super(), m) for m in dir(super()) if not m.startswith("__") and callable(getattr(super(), m))]:
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
        print("Update Rate Here.")`


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

# Project(
#     color='charcoal',
#     comment_count=0,
#     id='2307271342',
#     is_favorite=False,
#     is_inbox_project=False,
#     is_shared=False,
#     is_team_inbox=False,
#     name='General Project',
#     order=2,
#     parent_id='2307271348',
#     url='https://todoist.com/showProject?id=2307271342',
#     view_style='list'
# )
#
#
# def item_as_branch(item):
#     match type(item):
#
#     Example commands for planning:
#     IF overall cli is called "tdcli"
#     tdcli show projects
#     tdcli show all projects
#     tdcli
#


# def build_graph(api):
#     # The foolowing is sijmple, eventually we will add:
#     # dates, collaborators and comments.
#     item_types = {"projects": api.get_projects,
#              "sections": api.get_sections,
#              "tasks": api.get_tasks}
#
#     for itype in itemtypes:
#         graph.add_nodes_from(item_types[itype]())
#


def add_to_graph(obj, graph=None):
    if graph is None:
        graph = DiGraph()

    failed_items = []
    try:
        graph.add_node(obj.id, todoist_item=obj)
    except AttributeError:
        try:
            for item in obj:
                graph, failed = add_to_graph(item, graph)
                if failed:
                    failed_items.extend(failed)
            return (graph, failed_items)
        except TypeError:
            return (graph, [obj])

    return (graph, failed_items)


def link_to_parents(graph):
    for node, data in graph.nodes.data():
        try:
            pid = data["item"].parent_id
        except AttributeError:
            pid = None
        if pid is not None:
            graph.add_edge(pid, node)


# def graph_to_tree(graph):
#     t = Tree("Projects")
#     gens = topological_generations(graph)
#     for gen in gens:
#         for node in gen:
#


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


if __name__ == "__main__":
    app()

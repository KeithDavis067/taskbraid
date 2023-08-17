from todoist_api_python.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print
from rich.tree import Tree
import os

app = typer.Typer(chain=True)
state = {"api": None}

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


def project_to_tree(projects):
    pt = Tree("Projects")
    topprojects = list(filter(lambda proj: proj.parent_id is None, projects))
    subprojects = list(
        filter(lambda proj: proj.parent_id is not None, projects))
    for project in topprojects:
        branch = pt.add(project.name)
        for p in filter(lambda proj: proj.parent_id == project.id,
                        subprojects):
            branch.add(p.name)

    return pt


@app.command()
def show(itemkind: str):
    api = state["api"]
    print(f"Showing: {itemkind.lower()}")
    match itemkind.lower():
        case "projects":
            result = api.get_projects()

        case "tasks":
            result = api.get_tasks()

    print(project_to_tree(result))


@app.command()
def add(itemkind: str):
    api = state["api"]
    print(f"Adding: {itemkind}")


@app.callback()
def main():
    # I should be able to set up this to take it from the environment
    # or an argument, but it's taking the argument with the env variable
    # as the command.
    api_key = os.environ.get("TODOIST_API_KEY")
    state["api"] = TodoistAPI(api_key)


if __name__ == "__main__":
    app()

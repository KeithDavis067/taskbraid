from todoist_api.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print, inspect

app = typer.Typer()
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


# def show_item(item, style="minimal"):
#     """Select better printing for items."""
#     collected = {}
#
#     if style.lower() in ["min", "minimal"]:
#         keys = ["name", "parent_id", "color", ]
#
#     for key in keys:
#
@app.command()
def show(itemkind: str):
    api = state["api"]
    print(f"Showing: {itemkind.lower()}")
    match itemkind.lower():
        case "projects":
            result = api.get_projects()

        case "tasks":
            result = api.get_tasks()

    print(result)


@app.command()
def create(itemkind: str):
    api = state["api"]
    print(f"Adding: {itemkind}")


@app.callback()
def main(api_key:
         Annotated[str, typer.Argument(envvar="POETRY_TODOIST_API_KEY")]):

    state["api"] = TodoistAPI(api_key)


if __name__ == "__main__":
    app()

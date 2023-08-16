from todoist_api.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print

PROJECT_KEYS = ["color",
                "comment_count",
                "color",
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


def show_project(project, keys=None):
    """Print an easier to read version of a project."""
    if keys is None:
        print(project["name",



def main(api_key: Annotated[str,
         typer.Argument(envvar="POETRY_TODOIST_API_KEY")]):
    api=TodoistAPI(api_key)
    projects=api.get_projects()
    for project in projects:
        print(project)


if __name__ == "__main__":
    typer.run(main)

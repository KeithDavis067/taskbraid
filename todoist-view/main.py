from todoist_api.api import TodoistAPI
# from todoist_api.api_async import TodoistAPIAsync
import typer
from typing_extensions import Annotated
from rich import print


def main(api_key: Annotated[str,
         typer.Argument(envvar="POETRY_TODOIST_API_KEY")]):
    api = TodoistAPI(api_key)
    projects = api.get_projects()
    print(projects)


if __name__ == "__main__":
    typer.run(main)

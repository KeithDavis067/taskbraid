import os
from todoist_api.api import TodoistAPI

if __name__ == "__main__":

    TODOIST_API_KEY = os.environ.get('TODOIST_API_KEY')

    api = TodoistAPI(TODOIST_API_KEY)

    try:
        projects = api.get_projects()
        print(projects)
    except Exception as error:
        print(error)

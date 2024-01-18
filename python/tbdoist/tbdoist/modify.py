from requests.exceptions import HTTPError
import pytest


__all__ = ["manage_supertask_links", "manage_supertask_link"]


def manage_supertask_link(tdapi, task, update=True):
    """ Add, remove, or update supertask link on task.

    Parameters:
        tdapi: A TodoistAPI instance.
        task: A todoist task object or task id.
        update: Flag to set if update happens in this function.
            Default is `True`. If `False` return a dict with
            "content" key and value suitable for use in
            Todoist API.

    Returns:
        Task object if successful update or `None` if not update neede.
        If update=False a dict of:
        `{id: task.id, "content": newcontent}`

    """
    divider = " :: "

    # Allow task or task.id as parameter, get original content.
    try:
        oc = task.content
    except AttributeError:
        task = tdapi.get_task(task)
        oc = task.content

    # Set head if task has a parent.
    try:
        parent = tdapi.get_task(task.parent_id)
        head = f"[`{parent.content}`]({parent.url})"
    except (AttributeError, HTTPError):
        head = None

    # Determine new content if task has parent.
    if head is not None:
        if oc.startswith(head):
            newc = None
        else:
            newc = divider.join([head, oc])

    # Check if header needs to be removed from oc if task
    # no longer has a parent.
    if head is None:
        if divider not in oc:
            newc = None
        else:
            newc = oc.split(divider)[1]

    # Update or create result dict.
    if newc is not None:
        if update:
            result = tdapi.update_task(task.id, content=newc)
        else:
            result = {id: task.id, "content": newc}
    else:
        result = None
    return result


def manage_supertask_links(tdapi, *args, **kwargs):
    # If first arg is set it may be ids or tasks.
    if len(args) > 0:
        tasksarg = args[0]
        args = args[1:]

    # If tasks kwarg is set it may be tasks or ids.
    if "tasks" in kwargs:
        tasksarg = kwargs["tasks"]
        del tasksarg["tasks"]

    # Try to extract ids.
    try:
        try:
            ids = [task.id for task in tasksarg]
        except AttributeError:
            ids = tasksarg
    except NameError:
        pass

    # Extract update for passing to manage_supertask_link.
    if "update" in kwargs:
        update = kwargs["update"]
        del kwargs["update"]
    else:
        try:
            if args[1] not in [False, True]:
                update = True
            else:
                update = args[1]
                del args[1]
        except IndexError:
            update = True

    results = []
    try:
        tasks = tdapi.get_tasks(*args, ids=ids, **kwargs)
    except NameError:
        tasks = tdapi.get_tasks(*args, **kwargs)
    for task in tasks:
        result = manage_supertask_link(tdapi, task, update=update)
        results.append(result)
    return results


if __name__ == "__main__":
    pass

from requests.exceptions import HTTPError


__all__ = ["manage_supertask_links", "manage_supertask_link"]


def manage_supertask_link(tdapi, task, update=True):
    divider = " :: "
    try:
        oc = task.content
    except AttributeError:
        task = tdapi.get_task(task)
        oc = task.content

    try:
        parent = tdapi.get_task(task.parent_id)
        head = f"[`{parent.content}`]({parent.url})"
    except (AttributeError, HTTPError):
        head = None

    if head is not None:
        if oc.startswith(head):
            newc = None
        else:
            newc = divider.join([head, oc])

    if head is None:
        if divider not in oc:
            newc = None
        else:
            newc = oc.split(divider)[1]

    if newc is not None:
        if update:
            result = tdapi.update_task(task.id, content=newc)
        else:
            result = {"content": newc}
    else:
        result = None
    return result


def manage_supertask_links(tdapi, *args, **kwargs):
    # If first arg is set if may be ids or tasks.
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

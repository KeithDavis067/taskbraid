from requests.exceptions import HTTPError


__all__ = ["manage_supertask_links", "manage_supertask_link"]


def manage_supertask_link(tdapi, task):
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
        result = tdapi.update_task(task.id, content=newc)
    else:
        result = None
    return result


def manage_supertask_links(tdapi, *args, **kwargs):
    tasks = tdapi.get_tasks(*args, **kwargs)
    for task in tasks:
        manage_supertask_link(tdapi, task)


if __name__ == "__main__":
    pass

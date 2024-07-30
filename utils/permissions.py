from flask import redirect, request, render_template

from database.models import People


def _requires_password():
    return (
        render_template(
            "permissions/login.html",
            error="This page requires a password to access:",
        ),
        403,
    )


def _incorrect_password():
    return (
        render_template(
            "permissions/login.html",
            error="The password you entered is not correct",
        ),
        403,
    )


def _no_permissions():
    return (
        render_template(
            "permissions/no_access.html",
            error="Your user does not have permissions to access this page",
        ),
        403,
    )


def logout():
    resp = redirect("/")
    resp.delete_cookie("userKey")
    resp.delete_cookie("userName")
    return resp


def login():
    key = request.args.get("key", None)
    if key is None:  # this is done so if you want to change your password you can do it easily live
        stored_key = request.cookies.get("userKey", None)
        if stored_key and stored_key in [i.password for i in People.query.all()]:
            return False  # if the key already exists then we don't need to get the password
        return _requires_password()
    if key in [i.password for i in People.query.all()]:
        resp = redirect(request.base_url)  # TODO: find a nice way to do this that doesnt look so cancer
        resp.set_cookie("userKey", key)
        resp.set_cookie("userName", People.query.filter(People.password == key).first().name)
        return resp
    else:
        return _incorrect_password()


def fetch_user():
    return request.cookies.get("userKey", None)


def fetch_user_name():
    return request.cookies.get("userName", None)


def admin_only(func):
    def inner(*args, **kwargs):

        resp = login()
        if resp:  # this is a little hacky, but it gets the job done.
            return resp

        key = request.cookies.get("userKey", None)
        if key in [i.password  for i in People.query.filter(People.is_admin).all()]:
            return func(*args, **kwargs)

        return _no_permissions()

    inner.__name__ = func.__name__  # changing name of inner function so flask acts nicely <3
    return inner


def officials_only(func):
    def inner(*args, **kwargs):
        resp = login()
        if resp:
            return resp
        return func(*args, **kwargs)

    inner.__name__ = func.__name__  # changing name of inner function so flask acts nicely <3
    return inner


def user_on_mobile() -> bool:
    user_agent = request.headers.get("User-Agent")
    user_agent = user_agent.lower()
    phones = ["android", "iphone"]

    if any(x in user_agent for x in phones):
        return True
    return False

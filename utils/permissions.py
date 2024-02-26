from flask import request, render_template
from structure.AllTournament import get_all_officials

def _requires_password():
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )

def _incorrect_password():
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )

def _no_permissions():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Your user does not have permissions to access this page",
                ),
                403,
            )

def admin_only(func):
    print("admin only1")
    def inner(*args, **kwargs):
        print("admin only2")
        key = request.args.get("key", None)
        print("admin only3")
        if key is None:
            print("admin only4")
            return _requires_password()
            print("admin only5")
        if key in [i.key for i in get_all_officials()]:
            print("admin only6")
            if key in [i.key for i in get_all_officials() if i.admin]:
                print("admin only7")
                return func(*args, **kwargs)
                print("admin only8")
            return _no_permissions()  
            print("admin only9")
        return _incorrect_password()
        print("admin only10")
    inner.__name__ = func.__name__ # changing name of inner function so flask acts nicely <3
    return inner

def officials_only(func):
    def inner(*args, **kwargs):
        key = request.args.get("key", None)
        if key is None:
            _requires_password()
        if key not in [i.key for i in get_all_officials()]:
            _incorrect_password()
        func(*args, **kwargs)
    
    inner.__name__ = func.__name__ # changing name of inner function so flask acts nicely <3
    return inner

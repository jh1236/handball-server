from typing import Callable

from flask import request, render_template

from structure.UniversalTournament import UniversalTournament
from utils.permissions import fetch_user_name


def render_template_sidebar(template: str, **kwargs):
    from start import comps

    c = UniversalTournament()
    for i in comps.values():
        if i.link in request.path:
            c = i
    a = {
        **kwargs,
        "tournaments": [i for i in comps.values()],
        "current_tournament": c,
        "username": fetch_user_name(),
    }
    return render_template(template, **a)

from flask import request, render_template

from database.models import People
from utils.databaseManager import DatabaseManager
from utils.permissions import fetch_user_name


def link(tournament):
    return f"{tournament}/" if tournament else ""


def render_template_sidebar(template: str, **kwargs):
    with DatabaseManager() as c:
        tournaments = c.execute("""SELECT searchable_name, name FROM tournaments""").fetchall()
    current = None
    for i in tournaments:
        if i[0] in request.path:
            current = i
    current = current or (None, None)
    username = fetch_user_name()
    person = People.query.filter(People.name == username).first()
    a = {
        **kwargs,
        "tournaments": tournaments,
        "username": username,
        "user_image": person.image() if person else None,
    }
    if "tournament" not in a:
        a["tournament"] = current[1] or "Squarer's United Sporting Syndicate Handball"
    if "tournamentLink" not in a:
        a["tournamentLink"] = link(current[0])

    return render_template(template, **a)

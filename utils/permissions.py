import random
import time
from flask import redirect, request, render_template
import bcrypt
from database.models import People, Officials
from database import db
import secrets


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

def encrypt(password):
    salt = bcrypt.gensalt()
    pw = bytes(password, 'utf-8')
    # print(salt, pw)
    hashed_password = bcrypt.hashpw(pw, salt)
    return hashed_password

def set_password(person_id, password):
    """ args: person_id:int, password
    Sets the password for the person with the given id"""
    password = encrypt(password)
    People.query.filter(People.id == person_id).first().password = password
    db.session.commit()
    
def check_password(person_id, password):
    """ args: person_id:int, password
    Returns True if the password is correct, otherwise returns False"""
    hashed_password = People.query.filter(People.id == person_id).first().password
    return bcrypt.checkpw(bytes(password, "utf-8"), hashed_password)

# def login_page():
#     return render_template("permissions/login.html")
def get_time():
    return int(time.time())

def reset_token(person_id):
    person = People.query.filter(People.id == person_id).first()
    person.session_token = None
    db.session.commit()

def get_token(person_id, password):
    """ args: person_id:int, password
    Returns the token if the password is correct, otherwise returns False
    If the token already exists and is not expired, it will return that token"""
    if check_password(person_id, password):
        person = People.query.filter(People.id == person_id).first()
        # if they have no token, or their token has expired, give them a new one
        session_token = person.session_token
        if not session_token or person.token_timeout < get_time():
            # session_token = f"WhereDidYouComeFrom.{get_time()}.WhyAreYouLookingAtMe.{secrets.token_urlsafe(16)}.PleaseImNotWearingAnyClothes"
            session_token = f"{get_time()}{secrets.token_urlsafe(16)}"
            person.session_token = session_token
        person.token_timeout = get_time()+60*60*24*7  # 1 week
        db.session.commit()
        return session_token
    return False

def check_token(person_id, token):
    person = People.query.filter(People.id == person_id).first()
    if not token or person.token_timeout < get_time():
        return False
    return person.session_token == token

def check_valid_token(person_id, token):
    person = People.query.filter(People.id == person_id).first()
    return person.session_token == token and person.token_timeout < int(time.time())





def logout():
    resp = redirect("/")
    resp.delete_cookie("token")
    resp.delete_cookie("userID")
    resp.delete_cookie("userKey")
    resp.delete_cookie("userName")
    return resp


# def login():
#     key = request.args.get("key", None)
#     if key is None:  # this is done so if you want to change your password you can do it easily live
#         stored_key = request.cookies.get("userKey", None)
#         if stored_key in [i.password for i in People.query.all()]:
#             return False  # if the key already exists then we don't need to get the password
#         return _requires_password()
#     if key in [i.key for i in People.query.all()]:
#         resp = redirect(request.base_url)  # TODO: find a nice way to do this that doesnt look so cancer
#         resp.set_cookie("userKey", key)
#         resp.set_cookie("userName", People.query.filter(People.password == key).first().name)
#         return resp
#     else:
#         return _incorrect_password()


def fetch_user():
    return request.cookies.get("userKey", None)


def fetch_user_name():
    return request.cookies.get("userName", None)


def admin_only(func):
    def inner(*args, **kwargs):

        token = request.cookies.get("token", None)
        user_id = request.cookies.get("userID", None)
        if not check_valid_token(user_id, token):
            return _no_permissions()
        if user_id in [i.id for i in People.query.filter(People.is_admin).all()]:
            return func(*args, **kwargs)

        return _no_permissions()

    inner.__name__ = func.__name__  # changing name of inner function so flask acts nicely <3
    return inner


def officials_only(func):
    def inner(*args, **kwargs):
        

        token = request.cookies.get("token", None)
        user_id = request.cookies.get("userID", None)
        if not check_valid_token(user_id, token):
            return _no_permissions()
        
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

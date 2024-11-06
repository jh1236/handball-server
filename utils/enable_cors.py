from flask import Response, jsonify


def enable_cors(func):
    def inner(*args, **kwargs):
        response = jsonify(func(*args, **kwargs))
        print(response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        print(response.headers)
        return response

    inner.__name__ = func.__name__
    return inner

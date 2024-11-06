def enable_cors(func):
    def inner(*args, **kwargs):
        response = func(*args, **kwargs)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    inner.__name__ = func.__name__
    return inner

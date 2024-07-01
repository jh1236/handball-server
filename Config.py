class Config(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(
                cls, *args, **kwargs)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self.use_warnings = False
        self.badminton_style_serves = False

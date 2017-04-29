
class SettingsHolder(object):
    def __init__(self, default_settings):
        self.default_settings = default_settings

    def __getattr__(self, name):
        return getattr(self.__dict__['default_settings'], name, None)

class Settings(object):
    def __init__(self, default_settings, user_settings = None):
        self._d = SettingsHolder(default_settings)
        if user_settings is not None:
            for attr in dir(user_settings):
                if attr[0] != '_':
                    setattr(self._d, attr, getattr(user_settings, attr, None))

    def __getattr__(self, name):
        return getattr(self.__dict__['_d'], name, None)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)

import default_config
try:
    import config as user_config
except ImportError:
    user_config = None

settings = Settings(default_config, user_config)


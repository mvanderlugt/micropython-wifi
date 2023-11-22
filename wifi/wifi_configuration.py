from json import dumps, dump, load

from micropython import const

NAME = const("wifi")
SSID = const("ssid")
PASSWORD = const("password")


class WifiConfiguration:
    properties = (SSID, PASSWORD)

    def __init__(self, ssid: str = None, password: str = None):
        self.ssid = ssid
        self.password = password
        self.filename = f"configuration/{NAME}.json"

    def __str__(self) -> str:
        return f"WifiConfiguration(ssid='{self.ssid}', password='{self.password}')"

    def to_dict(self) -> dict:
        config = dict()
        for property_name in self.properties:
            if property_name in config:
                config[property_name] = getattr(self, property_name)
        return config

    def to_json(self) -> str:
        config = self.to_dict()
        return dumps(config)

    def load(self) -> None:
        try:
            with open(self.filename) as stream:
                config = load(stream)
                self.update(config)
        except OSError as error:
            if error.errno == 2:
                pass  # todo should missing config file raise exception?
            else:
                raise error

    def update(self, config: dict) -> None:
        for property_name in self.properties:
            if property_name in config:
                setattr(self, property_name, config[property_name])

    def save(self) -> None:
        config = self.to_dict()
        with open(self.filename, 'w') as stream:
            dump(config, stream)

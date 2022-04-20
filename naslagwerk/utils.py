from time import perf_counter
from configparser import ConfigParser


class Stopwatch:
    def __init__(self):
        self.storage = []
        self()

    def __call__(self):
        now = perf_counter()
        self.storage.append(now)

    def split(self):
        self()
        return self.storage[-1] - self.storage[-2]

    def total(self):
        self()
        return self.storage[-1] - self.storage[0]

    @property
    def start(self):
        return self.storage[0]

    @property
    def times(self):
        return [t - self.start for t in self.storage]

    @property
    def splits(self):
        return [t2 - t1 for t1, t2 in zip(self.storage, self.storage[1:])]


def load_ini(path):
    config = ConfigParser()
    config.read(path, encoding='utf8')
    return {k:v for s in config.sections() for k,v in config.items(s)}


def write_ini(path, dct):
    config = ConfigParser()
    config.read_dict({'PROPERTIES': dct})
    with open(path, 'w') as configfile:
        config.write(configfile)

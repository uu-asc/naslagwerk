from time import perf_counter
from string import Template
from configparser import ConfigParser


class Stopwatch:
    SPLIT = "[finished in ${time}]"
    TOTAL = """
+------------------------------------------------------------------+
    :: TOTAL RUN TIME :: ${time}
+==================================================================+
"""

    def __init__(self, will_print=True):
        self.will_print = will_print
        self.times = []
        self.click()

    def click(self):
        now = perf_counter()
        self.times.append(now)

    def split(self):
        self.click()
        time = self.times[-1] - self.times[-2]
        if self.will_print:
            print(Template(self.SPLIT).substitute(time=self.format_time(time)))
        return time

    def total(self):
        self.click()
        time = self.times[-1] - self.times[0]
        if self.will_print:
            print(Template(self.TOTAL).substitute(time=self.format_time(time)))
        return time

    def display(self, ):
        print(f'[finished in {self.split():.2f}s]')

    @staticmethod
    def format_time(time):
        return f"{time:.2f}s"

    @property
    def start(self):
        return self.times[0]

    @property
    def durations(self):
        return [t - self.start for t in self.times]

    @property
    def splits(self):
        return [t2 - t1 for t1, t2 in zip(self.times, self.times[1:])]


def load_ini(path):
    config = ConfigParser()
    config.read(path, encoding='utf8')
    return {k:v for s in config.sections() for k,v in config.items(s)}


def write_ini(path, dct):
    config = ConfigParser()
    config.read_dict({'PROPERTIES': dct})
    with open(path, 'w') as configfile:
        config.write(configfile)

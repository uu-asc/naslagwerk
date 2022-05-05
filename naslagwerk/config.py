from configparser import ConfigParser
from pathlib import Path
from types import SimpleNamespace
from functools import cached_property


class Config:
    MODULEDIR = Path(__file__).parent.parent.absolute().resolve()
    DEFAULT = MODULEDIR / 'config.defaults.ini'

    def __init__(self, path):
        self.path = Path(path)
        self.parser = ConfigParser(converters={
            'path': self.getpath,
            'abspath': self.getabspath,
            'string': self.getstring,
        })
        self.parser.read([self.DEFAULT, path], encoding='utf8')

    @property
    def WORKDIR(self):
        return self.path.parent.absolute().resolve()

    @cached_property
    def AVAILABLE_STYLES(self):
        path = self.PATHS.defaults / 'styles'
        return [f.stem for f in path.glob('*.css')]

    @cached_property
    def PATHS(self):
        topofile = self.parser['FILENAMES'].getstring('topography')
        chlogfile = self.parser['FILENAMES'].getstring('changelog')
        paths = self.parser['PATHS']
        PATHS = {k:paths.getabspath(k) for k in paths}
        PATHS['defaults'] = self.MODULEDIR / 'templates'
        PATHS['topography'] = self.WORKDIR / topofile
        PATHS['changelog'] = self.WORKDIR / chlogfile
        return SimpleNamespace(**PATHS)

    @property
    def PROPERTIES(self):
        return SimpleNamespace(**self.parser['PROPERTIES'])

    def getstring(self, i):
        return i.strip('"\n').replace('\n', ' ')

    def getpath(self, i):
        return Path(self.getstring(i))

    def getabspath(self, path):
        if isinstance(path, str):
            path = self.getpath(path)
        if not path.is_absolute():
            path = (self.WORKDIR / path).absolute()
        return path.resolve()

    def write_ini(self):
        with open(self.path, 'w', encoding='utf8') as configfile:
            self.parser.write(configfile)

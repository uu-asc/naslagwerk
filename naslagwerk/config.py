import configparser
from pathlib import Path
from types import SimpleNamespace


WORKDIR = Path(__file__).parent.parent.absolute()

getstring = lambda i: i.strip('"\n').replace('\n', ' ')
getpath = lambda i: Path(getstring(i))


def getabspath(path):
    if isinstance(path, str):
        path = getpath(path)
    if not path.is_absolute():
        path = (WORKDIR / path).absolute()
    return path.resolve()


def get_configparser():
    converters = {
        'path': getpath,
        'abspath': getabspath,
        'string': getstring,
    }
    return configparser.ConfigParser(converters=converters)


configfile = WORKDIR / 'config.ini'
config = get_configparser()
if not configfile.exists():
    config.read_dict({
        'PATHS': {
            'content': WORKDIR / 'content',
            'templates': WORKDIR / 'templates',
            'output': WORKDIR / 'output',
        },
        'FILENAMES': {
            'topography': 'topography.xlsx',
            'properties': 'properties.ini',
            'changelog':  'changelog.json',
        }
    })
    with open(configfile, 'w') as f:
        config.write(f)
config.read(configfile, encoding='utf8')


PATHS = {k:config['PATHS'].getabspath(k) for k in config['PATHS']}
topofile = config['FILENAMES'].getstring('topography')
propfile = config['FILENAMES'].getstring('properties')
chlogfile = config['FILENAMES'].getstring('changelog')
PATHS['defaults'] = WORKDIR / 'templates'
PATHS['topography'] = PATHS['content'] / topofile
PATHS['properties'] = PATHS['content'] / propfile
PATHS['changelog'] = PATHS['content'] / chlogfile
PATHS = SimpleNamespace(**PATHS)

AVAILABLE_STYLES = [f.stem for f in (PATHS.templates / 'styles').glob('*.css')]

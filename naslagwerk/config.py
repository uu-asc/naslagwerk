import configparser
from pathlib import Path
from types import SimpleNamespace


getstring = lambda i: i.strip('"\n').replace('\n', ' ')
getpath = lambda i: Path(getstring(i))


def get_configparser():
    converters = {'path': getpath, 'string': getstring}
    return configparser.ConfigParser(converters=converters)


WORKDIR = Path(__file__).resolve().parent.parent
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


PATHS = {k:config['PATHS'].getpath(k) for k in config['PATHS']}
topofile = config['FILENAMES'].getstring('topography')
propfile = config['FILENAMES'].getstring('properties')
chlogfile = config['FILENAMES'].getstring('changelog')
PATHS['topography'] = PATHS['content'] / topofile
PATHS['properties'] = PATHS['content'] / propfile
PATHS['changelog'] = PATHS['content'] / chlogfile
PATHS = SimpleNamespace(**PATHS)

AVAILABLE_STYLES = [f.stem for f in (PATHS.templates / 'styles').glob('*.css')]

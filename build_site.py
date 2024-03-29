from naslagwerk.utils import Stopwatch, load_ini, write_ini

stopwatch = Stopwatch()

import argparse

parser = argparse.ArgumentParser(description='Build static site')
parser.add_argument(
    'naslagwerk',
    help=("""
locatie van naslagwerk directory;
mag volledig pad zijn;
indien alleen naam van naslagwerk is opgegeven,
dan zoekt script in parent directory.
"""))
parser.add_argument(
    '-c', '--clean',
    help='set flag to empty output folder first',
    action='store_true',
    default=False)
parser.add_argument(
    '-v', '--version',
    help='set flag to create new version',
    action='store_true')
parser.add_argument(
    '-s', '--skip',
    nargs='*',
    choices=['pages', 'folders'],
    default=[],
    help='skip pages and/or folders')
args = parser.parse_args()

title = f"BUILD SITE :: {args.naslagwerk}"
header = f"""
+==================================================================+
|{title:^66}|
+==================================================================+

   clean output folder?  {args.clean}
   create new version?   {args.version}
   skip sections?        {args.skip}
"""
print(header)
print('imports', flush=True, end=' ')

import json
import shutil
from pathlib import Path
from filecmp import dircmp
from datetime import date
from multiprocessing.dummy import Pool

from naslagwerk.config import Config
from naslagwerk.site import Topography, make_environment
from naslagwerk.page import Page

stopwatch.split()

# init
print('init', flush=True)

pool = Pool(6)

print("- laad config")
path = Path(args.naslagwerk)
if len(path.parts) == 1:
    path = '..' / path
configfile = path / 'config.ini'
config = Config(configfile)
if not configfile.exists():
    config.write_ini()
PATHS = config.PATHS

print("- laad topografie")
if not PATHS.topography.exists():
    raise FileNotFoundError("""
  Topografie niet gevonden.
  1. Heeft de site al een topografie?
     ---> controleer path in config.ini
  2. Ben je de site aan het initialiseren?
     ---> run eerst build_topography.py om topografie aan te maken
""")
topo = Topography.read_excel(PATHS.topography)

print("- laad changelog")
if not PATHS.changelog.exists():
    PATHS.changelog.touch()
    init = {
        "v0.1": {
            "date": date.today().strftime('%Y-%m-%d'),
            "comment": "Eerste oplevering."
        }
    }
    PATHS.changelog.write_text(json.dumps(init), encoding='utf8')
chlog = json.loads(PATHS.changelog.read_text(encoding='utf8'))

stopwatch.split()
info = f"""
   +------------------------------------------------------------+
   | title:   {config.PROPERTIES.title:<50}|
   | version: {config.PROPERTIES.version:<50}|
   | pages:   {len(topo.data):<50}|
   +------------------------------------------------------------+
"""
print(info)

if args.clean:
    print('clean output directory')

    shutil.rmtree(PATHS.output)
    stopwatch.split()
    stopwatch.split()

if args.version:
    new_version = input("New version: ")
    comment = input("Comment for changelog: ")
    print()

    chlog[new_version] = {'date': str(date.today()), 'comment': comment}
    PATHS.changelog.write_text(json.dumps(chlog), encoding='utf8')
    config.parser['PROPERTIES']['version'] = new_version
    config.write_ini()
    stopwatch.split()

environment = make_environment(config, topo, chlog)

# pages
if not 'pages' in args.skip:
    print('pages')

    def write_page(md):
        print(f' «{md.name}»')
        page = Page.read_md(md, config, topo, environment)
        if page is not None:
            page.write(PATHS.output)

    pool.map(write_page, PATHS.content.glob('**/*.md'))
    stopwatch.split()

# copy
if not 'folders' in args.skip:
    print('folders')

    def copy_files(task):
        key, src, dst = task
        src.mkdir(exist_ok=True, parents=True)
        dst.mkdir(exist_ok=True, parents=True)
        cmp = dircmp(src, dst)
        files = [f for f in cmp.left_list if f not in cmp.same_files]
        print(f" «{key}»{'::': >{16-len(key)}} {len(files)} files")
        for file in files:
            try:
                shutil.copyfile(src / file, dst / file)
            except PermissionError:
                print(f'geen toestemming om "{file}" te kopiëren')

    folders_to_copy = [
        ('iframes',
            PATHS.content / 'iframes',
            PATHS.output / 'iframes'),
        ('images',
            PATHS.content / 'images',
            PATHS.output / 'images'),
        ('css-defaults',
            PATHS.defaults / 'styles',
            PATHS.output / 'css'),
    ]
    custom_folders_to_copy = [
        ('css-custom',
            PATHS.templates / 'styles',
            PATHS.output / 'css'),
    ]
    pool.map(copy_files, folders_to_copy)
    pool.map(copy_files, custom_folders_to_copy)
    stopwatch.split()

stopwatch.total()

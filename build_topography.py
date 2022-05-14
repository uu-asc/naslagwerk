"""
build_topography script
=======================
This script builds or rebuilds the site topography within the naslagwerk folder according to the table in "topography.xlsx". It will do the following things:

1. Try to read site topography from "topography.xlsx" in naslagwerk folder.
    * If this fails, create empty topography (with only a homepage).
    * If this succeeds, sort table and forward fill sections, chapters and groups.
2. Check if topography is valid:
    * No missing values in the order columns.
    * No duplicates.
    If topography is invalid break script.
3. For rows lacking `page_id`, create and add unique `page_id`.
4. Loop over .md files in content folder and for every file:
    * Check `page_id`:
        - if `page_id` is unknown, prompt user to delete file.
        (These files will be ignored when building site; however for maintainability it may be advisable to clean this files up.)
    * Check if each filepath follows this naming convention:

        [ content folder / section_order + section / chapter_order + group_order + page_order + page_name ]

    If not: rename the path and/or filename.
5. Check if all `page_ids` have associated .md file. If not:
    - Create .md file following naming convention above.
6. Save topography in "topography.xlsx".

Make sure that section_oder, chapter_order and group_order are filled for each page in the topography. If there are no groups within a chapter or no chapters within a section the order value should be 1.

Another thing to note is that this script will organize the .md files into folders for convenience only. Where the .md files are stored has no bearing on how the site is actually built. You could move the files around and it would make no difference - as long as the site builder is able to find the relevant files.
"""
from naslagwerk.utils import Stopwatch

stopwatch = Stopwatch()

import argparse

parser = argparse.ArgumentParser(description='Build static site')
parser.add_argument(
    'naslagwerk',
    help=(
        'locatie van naslagwerk directory; '
        'mag volledig pad zijn; '
        'indien alleen naam van naslagwerk is opgegeven, '
        'dan zoekt script in parent directory')
)
args = parser.parse_args()

header = """
====================================================================
|                         BUILD TOPOGRAPHY                         |
====================================================================
"""
print(header)
print('imports', flush=True, end=' ')

from multiprocessing.dummy import Pool
from pathlib import Path
from uuid import uuid4

import pandas as pd

from naslagwerk.config import Config

stopwatch.split()


def load_topography(path):
    if not path.exists():
        print('\nGeen topografie gevonden ---> nieuwe aanmaken')
        return pd.DataFrame({
            'page_id':       [None],
            'section_order': [1],
            'section':       ['Home'],
            'chapter_order': [1],
            'chapter':       [None],
            'group_order':   [1],
            'group':         [None],
            'page_order':    [1],
            'page':          ['Home'],
            'code':          [None],
        })
    else:
        df = pd.read_excel(path).rename(columns=str.lower)
        todo = {i[:-6]:i for i in df.filter(like='_order').columns}
        df = df.sort_values(list(todo.values()))
        grouper = []
        for col, ordercol in todo.items():
            grouper.append(ordercol)
            s = df.groupby(grouper)[col].transform(pd.Series.ffill)
            df = df.assign(**{col: s})
        return df


def check_df(df):
    cols = [i for i in df.columns if i.endswith('_order')]
    test = df[['section', 'page', *cols]]
    hasnans = test.isna().any(axis=None)
    assert not hasnans, (f"""
Fout in topografie: missende waarden
-- zie rijen: {test[test.isna().any(axis=1)].index.values + 2}
""")
    test = df[cols]
    hasdupes = test.duplicated().any()
    assert not hasdupes, (f"""
Fout in topografie: dubbeling in volgorde
-- zie rijen: {test[test.duplicated(keep=False)].index.values + 2}
""")


def make_id_generator(page_ids):
    def generate_id():
        "Generate a unique id."
        while True:
            page_id = str(uuid4()).split('-')[0]
            if not page_id in page_ids:
                break
        page_ids.append(page_id)
        return page_id
    return generate_id


def path_from_record(s):
    section_order = f"{s.section_order:02}"
    chapter_order = f"{s.chapter_order:02}"
    group_order = f"{s.group_order:02}"
    page_order = f"{s.page_order:02}"

    section = s.section.lower()
    chapter = s.chapter.lower()
    page_name = s.page.lower()

    order = chapter_order + group_order + page_order
    fn_elements = filter(None, [order, chapter, page_name])
    filename = ' - '.join(fn_elements) + '.md'
    return f"{section_order}_{section}/{filename}"


def find_id(path):
    text = path.read_text(encoding='utf-8')
    if not '\n' in text:
        return
    page_id, _ = text.split('\n', 1)
    return path, page_id, page_id in df.index


def prompt_delete(path, page_id):
    while True:
        should_delete = input(f"""
>>> File "{path.name}" heeft onbekende id <{page_id}>.
>>> Verwijderen (j/n)?
""")
        should_delete = should_delete.lower()[0]
        if should_delete in ['y', 'j', 'n']:
            break
    if not should_delete == 'n':
        print(f'    File "{path.name}" wordt verwijderd...')
        path.unlink()


def rename_file(path, page_id):
    expected_path = PATHS.content / path_from_record(df.loc[page_id])
    if not path == expected_path:
        print(f' «{expected_path.name}»')
        if not expected_path.parent.exists():
            expected_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(expected_path)


def make_file(page_id):
    file_path = PATHS.content / path_from_record(df.loc[page_id])
    print(f' «{file_path.name}»')
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    text = page_id + '\n'
    file_path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    # loading config
    print('load config', flush=True)
    configfile = Path(args.naslagwerk)
    if len(configfile.parts) == 1:
        configfile = '..' / configfile
    config = Config(configfile / 'config.ini')
    PATHS = config.PATHS

    for key, path in vars(PATHS).items():
        print(f" > {key:.<12}{path}")

    stopwatch.split()

    # loading topography
    print('load topofile', flush=True, end=' ')
    df = load_topography(PATHS.topography)
    check_df(df)
    stopwatch.split()

    # creating page ids
    print('creating page_ids', flush=True, end=' ')
    generate_id = make_id_generator(df.page_id.to_list())
    fill_empty_ids = lambda i: generate_id() if pd.isna(i) else i
    df['page_id'] = df.page_id.apply(fill_empty_ids)
    df = df.set_index('page_id').fillna(value='')
    stopwatch.split()

    # finding page ids
    print('finding page_ids', flush=True, end=' ')
    files = PATHS.content.glob('**/*.md')
    pool = Pool(6)
    results = pool.map(find_id, files)
    found = [(path, pid) for path, pid, found in results if found]
    not_found = [(path, pid) for path, pid, found in results if not found]
    stopwatch.split()

    # renaming updated files
    if found:
        print('renaming updated files', flush=True)
        pool.starmap(rename_file, found)
        stopwatch.split()

    # deleting unknown files
    if not_found:
        print('deleting unknown files', flush=True)
        for path, page_id in not_found:
            prompt_delete(path, page_id)
        stopwatch.split()

    # create files for new page ids
    print('creating files', flush=True)
    new_ids = set(df.index.values) - set(pid for _, pid in found)
    pool.map(make_file, new_ids)
    stopwatch.split()

    # save topography file
    print('save topography', flush=True, end=' ')
    writer = pd.ExcelWriter(PATHS.topography)
    df.to_excel(writer, 'site_topography')
    writer.save()
    stopwatch.split()
    stopwatch.total()

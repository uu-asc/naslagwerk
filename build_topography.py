"""
build_topography script
=======================
This script builds or rebuilds the site topography within the content folder according to the table in `topography.xlsx`. It will do the following things:

1. Try to read the site topography from `topography.xlsx` in the content folder. If this fails it will create an empty topography table (with only a homepage) and store it in the content folder.
2. Check if any rows lack a `page_id` and if so create and add unique `page_ids` to these rows.
3. Loop over the .md files in the content folder and for every file:
    - Check the `page_id`; if a `page_id` is found that is unknown to the site topography definition, then prompt the user to delete the file. (Files with `page_ids` that are not defined in the site topography are ignored when building the site. Thus they can be safely left within the content folder. However this may later lead to confusion when maintaining the site.)
    - Check if each path and filename follows this naming convention:

        [ content folder / section_order + section / chapter_order + group_order + page_order + page_name ]

    if not: rename the path and/or filename.
4. Check if all `page_ids` have an associated .md file. If this is not the case:
    - Create the .md file following the naming convention above.
5. Save the updated table in `topography.xlsx`.

This script can add `page_ids` where they are missing but other than that the site topography must be well formatted. At this point in time there is no other validation performed on the topography table. This means that the order for each page needs to be fully specified. Make sure that section_oder, chapter_order and group_order are filled for each page. If there are no groups within a chapter or no chapters within a section the order value should be 1.

Another thing to note is that this script will organize the .md files into folders for convenience only. Where the .md files are stored has no bearing on how the site is actually built. You could move the files around and it would make no difference - as long as the site builder is able to find the relevant files.
"""
from naslagwerk.utils import Stopwatch

stopwatch = Stopwatch()

header = """
====================================================================
|                         BUILD TOPOGRAPHY                         |
====================================================================
"""
print(header)
print('imports', flush=True, end=' ')

from multiprocessing.dummy import Pool
from uuid import uuid4

import pandas as pd

from naslagwerk.config import PATHS

print(f'[finished in {stopwatch.split():.2f}s]')

def make_id_generator(page_ids):
    def generate_id():
        """
        Generate a unique id.
        """
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
        delete = input(
            f"File '{path.name}' "
            f"has unknown page id <{page_id}>. Delete file (y/n)? ")
        delete = delete.lower()[0]
        if delete in ['y', 'j', 'n']:
            break
    if not delete == 'n':
        print(f'Deleting {path.name}.')
        path.unlink()

def rename_file(path, page_id):
    expected_path = path_content / path_from_record(df.loc[page_id])
    if not path == expected_path:
        print(f' «{expected_path.name}»')
        if not expected_path.parent.exists():
            expected_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(expected_path)

def make_file(page_id):
    file_path = path_content / path_from_record(df.loc[page_id])
    print(f' «{file_path.name}»')
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    text = page_id + '\n'
    file_path.write_text(text, encoding='utf-8')


# loading topography
print('load topofile', flush=True, end=' ')
path_content = PATHS.content
topofile = PATHS.topography
if not topofile.exists():
    df = pd.DataFrame({
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
    order_cols = [
        'section_order',
        'chapter_order',
        'group_order',
        'page_order',
    ]
    df = pd.read_excel(topofile
    ).rename(columns=str.lower
    ).sort_values(order_cols)
    test = df[['section', 'page', *order_cols]]
    hasnans = test.isna().any(axis=None)
    assert not hasnans, (
        "Topography error: following row(s): "
        f"{test[test.isna().any(axis=1)].index.values + 2} "
        "has missing values."
    )
print(f'[finished in {stopwatch.split():.2f}s]')

# creating page ids
print('creating page_ids', flush=True, end=' ')
generate_id = make_id_generator(df.page_id.to_list())
fill_empty_ids = lambda i: generate_id() if pd.isna(i) else i
df['page_id'] = df.page_id.apply(fill_empty_ids)
df = df.set_index('page_id').fillna(value='')
print(f'[finished in {stopwatch.split():.2f}s]')

# finding page ids
print('finding page_ids', flush=True, end=' ')
files = path_content.glob('**/*.md')
pool = Pool(6)
results = pool.map(find_id, files)
found = [(path, pid) for path, pid, found in results if found]
not_found = [(path, pid) for path, pid, found in results if not found]
print(f'[finished in {stopwatch.split():.2f}s]')

# renaming updated files
if found:
    print('renaming updated files', flush=True)
    pool.starmap(rename_file, found)
    print(f'[finished in {stopwatch.split():.2f}s]')

# deleting unknown files
if not_found:
    print('deleting unknown files', flush=True)
    for path, page_id in not_found:
        prompt_delete(path, page_id)
    print(f'[finished in {stopwatch.split():.2f}s]')

# create files for new page ids
print('creating files', flush=True)
new_ids = set(df.index.values) - set(pid for _, pid in found)
pool.map(make_file, new_ids)
print(f'[finished in {stopwatch.split():.2f}s]')

# save topography file
print('save topography', flush=True, end=' ')
writer = pd.ExcelWriter(topofile)
df.to_excel(writer, 'site_topography')
writer.save()
print(f'[finished in {stopwatch.split():.2f}s]')

print('-------------------------------------------------')
print(    f'::TOTAL RUN TIME:: {stopwatch.total():.2f}s.')
print('=================================================')

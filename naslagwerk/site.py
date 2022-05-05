import json
from configparser import ConfigParser
from functools import cached_property
from warnings import warn

import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader
from markdown import Markdown
from markdown.extensions.toc import TocExtension


def make_environment(config, topography, changelog=None):
    searchpath=[config.PATHS.templates, config.PATHS.defaults]
    loader = FileSystemLoader(searchpath=searchpath)
    environment = Environment(
        loader=loader,
        trim_blocks=True,
        lstrip_blocks=True,
        auto_reload=False,
    )
    environment.globals = {
        'props': config.PROPERTIES,
        'topo': topography.data,
        'hrefs_sections': topography.hrefs_sections,
        'sitemap': topography.sitemap,
        'changelog': changelog if changelog is not None else {},
        'watermark': """
    <!-- This site was built with the site builder at https://github.com/uu-asc/naslagwerk licensed under the GNU General Public License v3.0. -->
    """
    }
    return environment


class Topography:
    def __init__(self, data):
        self.data = data
        self.page_ids = self.data.index.values
        self.sections = self.data.section.unique().tolist()

    @cached_property
    def hrefs_sections(self):
        """
        Series associating sections with hrefs of first page of that section.
        """
        return self.data.groupby('section', sort=False).href.first()

    @cached_property
    def crossrefs(self):
        """
        Series of crossreferences.
        """
        return pd.concat([
            self.hrefs_sections,
            self.data.dropna(subset=['code']).set_index('code').href,
        ])

    @cached_property
    def sitemap(self):
        data = self.data.fillna({
            'chapter': self.data.chapter_order,
            'group': self.data.group_order,
        }).set_index(['section', 'chapter', 'group'])[['page', 'href']]
        return nested_dict_from_data(data)

    @classmethod
    def read_excel(cls, path):
        data = pd.read_excel(path, index_col=0).rename(columns=str.lower)
        cols = [col for col in data.columns if '_order' in col]
        data = data.sort_values(by=cols)
        first_row = data.index[0]

        # hrefs and nestedness
        cols = ['section', 'chapter', 'group', 'page']
        data['href'] = data[cols].apply(convert_to_href, axis=1)
        data['nestedness'] = data.href.str.count('/').apply(lambda i: i * '../')
        data.loc[first_row, 'href'] = 'index.html'
        data.loc[first_row, 'nestedness'] = ''

        # next and previous page ids
        data['next_page_id'] = np.roll(data.index.values, -1)
        data['prev_page_id'] = np.roll(data.index.values, 1)

        # breadcrumbs
        cols = ['section', 'chapter', 'group', 'page']
        drop_crumbs = lambda s: s.dropna().str.cat(sep=' | ')
        data['breadcrumbs'] = data[cols].agg(drop_crumbs, axis=1)
        return cls(data)


def nested_dict_from_data(data):
    """
    Create nested dict from dataframe with multiindex.
    """
    dct = dict()
    level = data.index.get_level_values(0).unique()
    for key in level:
        subdata = data.loc[key]
        if data.index.nlevels > 1:
            dct[key] = nested_dict_from_data(subdata)
        else:
            dct[key] = list(data.loc[[key]].values)
    return dct


def convert_to_href(args):
    """
    Create href from cleaned up arguments (joined left to right).
    - Removes leading and trailing whitespace.
    - Converts spaces to underscores.
    - Ignores non-string arguments.
    """
    clean = lambda i: i.lower().strip().replace(' ', '_')
    items = [clean(i) for i in args if isinstance(i, str)]
    return '/'.join(items) + '.html'

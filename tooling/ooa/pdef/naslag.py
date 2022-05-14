import pandas as pd
from pandas.io.formats.style import Styler
from jinja2 import Environment, FileSystemLoader

import pdef.tabel as tbl


loader = FileSystemLoader(searchpath='templates')
ENV = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)


def processtappen(pdef):
    cols = ['hoofdstuk', 'rubriek_omschrijving']
    rubrieken = pdef.rubrieken[cols].drop_duplicates()
    to_replace = {'S': 'Studentvragen', 'I': 'Checklist'}
    cats = pd.CategoricalDtype(to_replace.values(), ordered=True)
    vragen = (
        tbl.maak_ps(pdef)
        .merge(rubrieken, how='left')
        .assign(
            onderdeel = lambda df: df.actor.replace(to_replace),
            is_afh = lambda df: df.is_afh.replace({True: 'ja', False: 'nee'}))
    )

    def listify(s):
        code = s.antwoord_code
        tekst = s.antwoord_nl
        if code.hasnans:
            return False
        return list(zip(code, tekst))

    grouper = ['onderdeel', 'hoofdstuk', 'processtap']
    antw = (
        vragen
        .merge(tbl.maak_antw(pdef), how='left')
        .query("actueel == 'J'")
        .groupby(grouper)
        .apply(listify)
        .rename('antw')
    )
    data = (
        pd.merge(
            antw,
            vragen
            .set_index(grouper)
            .fillna({'tekst_nl': '-'}),
            left_index=True,
            right_index=True)
        .reset_index()
        .astype({'onderdeel': cats})
        .sort_values(['onderdeel', 'hs_nr', 'ps_nr'])
    )
    template = ENV.get_template('pdef.processtappen.jinja')
    return template.render(data=data)


def autov(table):
    styles = [
        {'selector': '',
        'props': 'font-size: .9em;'},
        {'selector': 'tbody th:not(.level0)',
        'props': 'background-color: transparent; color: black;'},
        {'selector': 'tbody :not(.level0):hover',
        'props': 'background-color: transparent;'},
        {'selector': 'tbody th.level0',
        'props': 'background-color: var(--color-theme-light);'},
    ]

    template = ENV.get_template('pdef.autov.jinja')
    data = Styler(table, cell_ids=False).set_table_styles(styles).to_html()
    return template.render(data=data)

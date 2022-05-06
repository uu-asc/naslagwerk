from types import SimpleNamespace
import pandas as pd
from query import QueryResult


def load_pdef_datasets(proces):
    proces = proces.lower()
    load_qr = lambda t: QueryResult.read_pickle(f"ref_ooa/{t}_{proces}").frame

    afh   = load_qr('processtap_afh')
    antw  = load_qr('processtap_antwoorden')
    opl   = load_qr('processtap_opleiding')
    rub   = load_qr('rubriek')
    label = load_qr('labelteksten')

    actor_cats = pd.CategoricalDtype(['S', 'A', 'I', 'D'], ordered=True)
    ps = (
        load_qr('processtappen')
        .rename(columns={'hs_volgnummer':'hs_nr', 'ps_volgnummer': 'ps_nr'})
        .astype({'actor': actor_cats})
    )
    ropl = (
        QueryResult
        .read_pickle("referentie/ref_OST_OPLEIDING")
        .frame
        .rename(columns=str.lower)
        [['opleiding', 'faculteit', 'aggregaat_1', 'aggregaat_2']]
        .replace({'faculteit': {'IVLOS': 'GST', 'RA': 'UCR', 'SW': 'FSW'}})
        .assign(aanwezig='O')
    )
    stdlabels = (
        QueryResult
        .read_pickle("referentie/ref_STT_UIX_LABEL")
        .frame
        .rename(columns=str.lower)
        .rename(columns={'ulab_id': 'label_id'})
    )

    return SimpleNamespace(**{
        'processtappen': ps,
        'afhankelijkheden': afh,
        'antwoorden': antw,
        'opleidingen': opl,
        'rubrieken': rub,
        'labels': label,
        'stdlabels': stdlabels,
        'refopleiding': ropl,
    })


def load_autov_datasets(proces):
    def load_qr(table):
        return (
            QueryResult
            .read_pickle(f"referentie/ref_{table}")
            .frame
            .rename(columns=str.lower)
        )
    tabellen = {
        'overgang':        'OST_IO_PROCES_AUT_OVERGANG',
        'regel':           'OST_IO_PROCES_AUT_OV_RG',
        'aanvraag':        'OST_IO_PROCES_AUT_OV_RG_AANV',
        'rubriek':         'OST_IO_PROCES_AUT_OV_RG_HOOFD',
        'processtap':      'OST_IO_PROCES_AUT_OV_RG_PS',
        'antwoord':        'OST_IO_PROCES_AUT_OV_RG_AW_PS',
        'omhangen':        'OST_IO_PROCES_AUT_OV_RG_OMHANG',
        'termijnbewaking': 'OST_IO_PROCES_AUT_OV_RG_STERM',
    }

    datasets = {k:load_qr(v) for k,v in tabellen.items()}
    heeft_io_proces = pd.Series(
        index = datasets.keys(),
        data = ['io_proces' in i.columns for i in datasets.values()],
        name = 'heeft_io_proces'
    )

    heeft_iaor_id = pd.Series(
        index = datasets.keys(),
        data = ['iaor_id' in i.columns for i in datasets.values()],
        name = 'heeft_iaor_id'
    )

    def prep(key, df):
        to_drop = [
            'io_proces',
            'creatie_gebruiker',
            'creatie_applicatie',
            'creatie_datum',
            'mutatie_gebruiker',
            'mutatie_applicatie',
            'mutatie_datum',
        ]
        if heeft_io_proces.loc[key]:
            df = df.query(f"io_proces == '{proces}'")
        if heeft_iaor_id.loc[key]:
            df = df.set_index('iaor_id')
        return df.drop(to_drop, axis=1, errors='ignore')

    proces_autov = {k:prep(k,v) for k,v in datasets.items()}
    return SimpleNamespace(**proces_autov)

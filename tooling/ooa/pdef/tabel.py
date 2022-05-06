from types import SimpleNamespace
import pandas as pd


def test_afhankelijkheden(df1, df2, is_heeft):
    s1 = df1.hoofdstuk.astype(object) + df1.processtap
    if is_heeft == 'is':
        s2 = df2.afh_hoofdstuk.astype(object) + df2.afh_processtap
    else:
        s2 = df2.hoofdstuk.astype(object) + df2.processtap
    return s1.isin(s2)


def maak_ps(datasets):
    ps = datasets.processtappen.copy()
    afh = datasets.afhankelijkheden.copy()

    groupby = [
        'actor',
        'hoofdstuk',
        'hs_nr',
        'processtap',
        'ps_nr',
        'tekst_nl',
        'actueel',
    ]
    ps = ps.assign(
        is_afh = lambda df: test_afhankelijkheden(df, afh, 'is'),
        heeft_afh = lambda df: test_afhankelijkheden(df, afh, 'heeft'),
    ).set_index(groupby).reset_index().sort_values(['actor', 'hs_nr', 'ps_nr'])

    # map systeemlijst_io to children
    query = "systeemlijst_io.notna()"
    mapper = ps.query(query, engine='python'
    ).set_index('ipro_id').systeemlijst_io
    ps.parent_ipro_id = ps.parent_ipro_id.fillna(ps.ipro_id)
    ps.systeemlijst_io = ps.parent_ipro_id.map(mapper)
    return ps


def maak_antw(datasets):
    ps = datasets.processtappen.copy()
    antw = datasets.antwoorden.copy()

    groupby = [
        'actor',
        'hoofdstuk',
        'hs_nr',
        'processtap',
        'ps_nr',
        'tekst_nl',
        'actueel',
    ]
    return (
        antw
        .rename(columns={'actueel': 'actueel_antwoord'})
        .merge(ps[groupby])
        .set_index(groupby)
        .reset_index()
        .sort_values(['actor', 'hs_nr', 'ps_nr', 'volgnummer'])
    )


def maak_opl(datasets, pdef_ps):
    """
    Maak een overzicht van koppeling processtap-opleiding waarbij:
    - O: opleidingspecifieke vraag
    - U: universele vraag
    """
    opl = datasets.opleidingen.copy()
    ref = datasets.refopleiding.copy()

    groupby = [
        'actor',
        'hoofdstuk',
        'hs_nr',
        'processtap',
        'ps_nr',
        'tekst_nl',
        'tekst_en',
        'systeemlijst_io',
        'actueel',
    ]
    to_all = lambda row: pd.Series(
        ['U'] * len(row),
        index=row.index,
        dtype=object,
    )
    to_dtype = {'systeemlijst_io': object}
    pdef_ps = pdef_ps[groupby].astype(to_dtype)

    return (
        opl
        .merge(pdef_ps)
        .merge(ref)
        .drop_duplicates(subset=groupby + ['opleiding'])
        .pivot(
            index=groupby,
            columns=['faculteit', 'aggregaat_1', 'aggregaat_2', 'opleiding'],
            values='aanwezig')
        .sort_index(level=[0,1,2,3], axis=1)
        .reindex(pdef_ps.set_index(groupby).index)
        .apply(lambda row: to_all(row) if not row.any() else row, axis=1)
        .assign(aantal=lambda df: df.count(axis=1))
    )


def maak_autov(dataset):
    """
    Overzicht automatische overgangen.
    """
    def ontdubbel(data, to_merge, categories=[]):
        merge_rows = lambda s: ';'.join(sorted(s))
        return data.groupby(level=0).agg({
            **{col:'first' for col in categories},
            **{col:merge_rows for col in to_merge},
        })

    def maak_aw(data):
        g = data.gesloten_antwoord_code
        o = data.open_antwoord_code
        s = data.systeem_antwoord_code
        data['antwoord'] = g.fillna(o).fillna(s)
        return data

    processed = SimpleNamespace(**{
        'aanvraag': dataset.aanvraag.pipe(
            ontdubbel,
            to_merge = ['besluit_status']
        ),
        'rubriek': dataset.rubriek.pipe(
            ontdubbel,
            to_merge = ['status'],
            categories = ['hoofdstuk']
        ),
        'processtap': dataset.processtap.pipe(
            ontdubbel,
            to_merge = ['status'],
            categories = ['hoofdstuk', 'processtap']
        ),
        'antwoord': dataset.antwoord.pipe(maak_aw).pipe(
            ontdubbel,
            to_merge = ['antwoord'],
            categories = ['hoofdstuk', 'processtap']
        ),
    })

    volgnummers = dataset.overgang.set_index('code').volgnummer
    get_volgnummers = lambda df: df.code.replace(volgnummers)
    dataset.regel = dataset.regel.assign(volgnummer = get_volgnummers)

    to_join = {
        k:dataset.regel.reset_index().merge(df.reset_index())
        for k,df in vars(processed).items()
    }

    mapping_niveau = {'A': 'proces', 'R': 'rubriek', 'P': ''}
    mapping_soort = {'S': 'status', 'A': 'antwoord'}
    return (
        pd.concat(to_join.values())
        .rename(columns={
            'volgnummer': '#',
            'operator_1': 'op.',
            'besluit_status': 'proces',
            'hoofdstuk': 'rubriek'})
        .set_index(['#', 'code', 'type'])
        .sort_index(ascending=[True, True, False, True])
        .drop(columns=['iaor_id', 'operator_2'])
        [[
            'niveau',
            'soort',
            'op.',
            'proces',
            'rubriek',
            'processtap',
            'status',
            'antwoord',
        ]]
        .assign(
            niveau = lambda df: df.niveau.replace(mapping_niveau),
            soort = lambda df: df.niveau + df.soort.replace(mapping_soort))
        .drop(columns = ['niveau'])
        .set_index('soort', append=True)
        .astype('string')
    )

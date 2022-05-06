import pandas as pd


def maak_stats_aantallen(pdef_ps):
    plat = pdef_ps.reset_index()
    n_rubriek = plat.groupby('actor').hoofdstuk.nunique().rename('n_rubriek')
    n_processtap = plat.groupby('actor').size().rename('n_processtap')
    n_per_type = plat.pivot_table(
        index='actor',
        columns='type_vraag',
        aggfunc='size',
    )

    return (
        pd.concat([
            n_rubriek,
            n_processtap,
            n_per_type], axis=1)
        .reindex(['S', 'A', 'I', 'D'])
        .T.assign(totaal=lambda df: df.sum(axis=1))
        .T.assign(totaal=lambda df: df.sum(axis=1))
    )


def maak_stats_aantallen_per_fac(pdef_opl):
    return (
        pdef_opl
        .iloc[:,:-1]
        .groupby(level=0)
        .count()
        .groupby(level=0, axis=1)
        .max()
        .reindex(['S', 'A', 'I', 'D'])
        .T.assign(totaal=lambda df: df.sum(axis=1))
        .T.assign(totaal=lambda df: df.sum(axis=1))
    )

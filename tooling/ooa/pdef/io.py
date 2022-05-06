def to_excel(proces, path):
    filename = '.'.join(proces.lower().split('_'))
    writer = pd.ExcelWriter(path / f"ooa.{filename}.pdef.xlsx")
    workbook = writer.book
    workbook.set_properties({
        'title':    f'procesdefinitie {proces.lower()}',
        'subject':  'osiris online application | procesdefinitie',
        'author':   'Centrale Studentenadministratie',
        'company':  'Universiteit Utrecht',
        'created':  datetime.date.today(),
    })

    pdef, pdef_antw, pdef_opl, pdef_n, pdef_fac = maak_pdef(proces)
    pdef_autov = maak_pdef_autov(proces)
    pdef.to_excel(writer, 'ps')
    pdef_antw.to_excel(writer, 'antw')
    pdef_opl.reset_index().to_excel(writer, 'opl')
    pdef_autov.to_excel(writer, 'aut_ov')
    pdef_n.to_excel(writer, 'stats')
    pdef_fac.to_excel(writer, 'stats', startrow=len(pdef_n)+2)

    for sheet, df in zip(['ps', 'antw', 'opl'], [pdef, pdef_antw, pdef_opl]):
        df = df.reset_index()
        worksheet = writer.sheets[sheet]
        worksheet.set_column(0, 0, None, None, {'hidden': 1})
        add_autofilter(worksheet, df)
        worksheet.freeze_panes(1, 0)
        format_index(writer, sheet)
    format_pdef_opl(writer, pdef_opl)

    workbook.add_worksheet(proces.lower())
    workbook.get_worksheet_by_name(proces.lower()).set_tab_color('#FF9900')
    writer.save()


def add_autofilter(worksheet, df):
    has_multi_col = len(df.columns.names) > 1
    correction = 1 if has_multi_col else 0
    offset_col = df.index.nlevels - 1
    offset_row = df.columns.nlevels - 1 + correction
    rows, cols = df.shape
    worksheet.autofilter(
        offset_row,
        offset_col,
        offset_row + rows - 1,
        offset_col + cols - 1)


def format_index(writer, sheet):
    workbook = writer.book
    index_format = workbook.add_format({'bold': True, 'border': 1})
    worksheet = writer.sheets[sheet]

    for col in range(1,6):
        worksheet.set_column(col, col, None, index_format)


def format_pdef_opl(writer, df):
    workbook = writer.book
    # true_format = workbook.add_format({'bg_color': '#D7E4BC'})
    index_format = workbook.add_format({'bold': True, 'border': 1})
    empty_format = workbook.add_format({'bold': False, 'border': 0})
    worksheet = writer.sheets['opl']

    for col, val in zip(range(1,10), df.index.names):
        worksheet.write(4, col, val, index_format)

    for row, val in zip(range(0,4), df.columns.names):
        worksheet.write(row, 9, val, index_format)

    for row in range(0,4):
        for col in range(0,9):
            worksheet.write(row, col, ' ', empty_format)

    worksheet.freeze_panes(df.columns.nlevels + 1, 10)

    # length, width = df.shape
    # offset = df.index.nlevels
    # worksheet.conditional_format(
    #     offset, offset, length+offset-1, width+offset-2, {
    #         'type':     'cell',
    #         'criteria': '==',
    #         'value':    True,
    #         'format':   true_format
    #     })

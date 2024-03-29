import re
from io import StringIO

import pandas as pd
from markdown import markdown


EXTENSIONS = [
    'abbr',
    'attr_list',
    'def_list',
    'fenced_code',
    'footnotes',
    'nl2br',
    'sane_lists',
    'smarty',
    'tables',
]


class Converter:
    def __init__(self, environment, context, config):
        self.environment = environment
        self.context = context
        self.config = config

    def template(self, template):
        """
        Render template from custom folder with environment context.
        """
        template = template.strip('\n')
        template = self.environment.get_template(f'custom/{template}')
        return template.render(**self.context)

    def container(self, text, process=True, **kwargs):
        """
        Wrap text in div container. Add ``kwargs`` to div.
        """
        kwargs = {k.strip('_'):v for k,v in kwargs.items()}
        template = self.environment.get_template('snippets/container.jinja')
        if '\n' in text and process:
            text = markdown(text, extensions=EXTENSIONS)
        return template.render(
            content=text,
            kwargs=kwargs
        )

    def collapsible(self, text):
        """
        Split section into subsections and render these as collapsibles.
        """
        template = self.environment.get_template('snippets/collapsible.jinja')
        collapsibles = []
        regex = re.compile('^### ', flags=re.M)
        items = [i.split('\n', 1) for i in regex.split(text)[1:]]
        for label, content in items:
            hide = None
            if ':' in label:
                label, hide = label.split(':')
            hide = False if hide not in ['hide'] else True
            collapsible = template.render(
                content=markdown(content, extensions=EXTENSIONS),
                label=label,
                hide=hide,
            )
            collapsibles.append(collapsible)
        return '\n'.join(collapsibles)

    def iframe(self, iframe):
        """
        Render page ``iframe`` in the iframes folder as iframe.
        """
        iframe = iframe.strip('\n')
        template = self.environment.get_template('snippets/iframe.jinja')
        return template.render(iframe=iframe, **self.context)

    def raw_html(self, filename):
        filename = filename.strip('\n')
        path = self.config.PATHS.content / 'raw' / filename
        return path.read_text(encoding='utf8')

    def image(self, image, **kwargs):
        """
        Render image that zooms when clicked.
        """
        if 'width' not in kwargs:
            kwargs['width'] = "100%"
        image = image.strip('\n')
        template = self.environment.get_template('snippets/image.jinja')
        return template.render(
            image=image,
            kwargs=kwargs,
            **self.context
        )

    def clickzoom(self, image, **kwargs):
        """
        Render image that zooms when clicked.
        """
        if 'width' not in kwargs:
            kwargs['width'] = "100%"
        image = image.strip('\n')
        template = self.environment.get_template('snippets/clickzoom.jinja')
        return template.render(
            image=image,
            kwargs=kwargs,
            **self.context
        )

    def card(self, text):
        """
        Render html for card from csv.
        """
        template = self.environment.get_template('snippets/card.jinja')
        buffer = StringIO(text)
        content = pd.read_csv(
            buffer,
            # engine='python',
            skipinitialspace=True,
            quotechar="'",
            header=None,
            names=['key', 'value']
        ).set_index('key')['value'].apply(to_markdown)
        return template.render(content=content)

    def table(self, text, **kwargs):
        """
        Render basic table from csv.
        """
        buffer = StringIO(text)
        df = pd.read_csv(
            buffer,
            skipinitialspace=True,
            quotechar="'",
            header=0,
        )
        with pd.option_context('display.max_colwidth', -1):
            html = df.to_html(
                index=False,
                na_rep='',
                escape=False
            )
        return self.container(
            html,
            process=False,
            class_='table__container',
            **kwargs
        )

    def flextable(self, text):
        """
        Render flextable from csv.
        """
        from functools import partial

        def div(i, class_=None, style=None):
            class_ = f' class="{class_}"' if class_ else ''
            style = f' style="{style}"' if style else ''
            return f"<div{class_}{style}>{i}</div>"

        def on_index(df, class_, axis=0):
            df = df.copy() if axis == 0 else df.T
            apply_div = partial(div, class_=class_)
            df.index = df.index.map(apply_div)
            return df if axis == 0 else df.T

        def add_span(s):
            return s.apply(lambda i: f"<span>{s.name}</span>{i}")

        df = (
            csv_to_df(text)
            .apply(add_span)
            .pipe(on_index, class_='flextable__index')
            .pipe(on_index, class_='flextable__header', axis=1)
            .applymap(div)
        )

        make_body = lambda s: ''.join([i+v for i,v in s.iteritems()])
        body = df.agg(''.join, axis=1).agg(make_body)
        header_name = div(df.columns.name or '', class_='flextable__header')
        header = header_name + ''.join(df.columns)

        style = f"grid-template-columns: repeat({df.shape[1]+1}, auto)"
        return div(header + body, class_='flextable', style=style)


def csv_to_df(text, header_row=0, header_names=None):
    """
    Converts csv to dataframe and applies markdown to cells if applicable.
    """
    return pd.read_csv(
        StringIO(text),
        skipinitialspace=True,
        quotechar="'",
        header=header_row,
        names=header_names,
    ).applymap(to_markdown)


def to_markdown(text):
    """
    Returns html from text if it contains any of the following symbols:
        [*, #, `, \\n]
    """
    symbols = ['*', '#', '`', '\n']
    if not text == text:
        text = ''
    text = str(text)
    if not any(symbol in char for char in text for symbol in symbols):
        return text
    return markdown(text, extensions=EXTENSIONS).replace('\n', '')

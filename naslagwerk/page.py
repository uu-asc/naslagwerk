import re
import warnings
from datetime import datetime
from functools import cached_property, reduce

from markdown import Markdown
from markdown.extensions.toc import TocExtension

from naslagwerk.convert import Converter, EXTENSIONS


class Page:
    def __init__(
        self,
        config,
        topography,
        environment,
        template='main',
        page_id=None,
        text=None,
        ctime=None,
        mtime=None,
    ):
        self.config = config
        self.topography = topography
        self.environment = environment
        self.template = template
        self.page_id = page_id
        self.text = text
        self.ctime = ctime
        self.mtime = mtime
        self.styles = []

    @property
    def content(self):
        toc = TocExtension(
            title=self.config.PROPERTIES.toc_title,
            anchorlink=True,
        )
        extensions = EXTENSIONS + [toc]
        markdown = Markdown(extensions=extensions)
        converter = Converter(self.environment, self.context, self.config)

        def render(item):
            if isinstance(item, tuple):
                func, text, (args, kwargs) = item
                method = getattr(converter, func)
                try:
                    item = method(text, *args, **kwargs)
                except Exception as e:
                    from textwrap import indent
                    raise Exception(
                        f"Fout gevonden in pagina met page_id: {self.page_id}\n"
                        f"Zie volgende passage:\n{indent(text, prefix='> ')}"
                    ) from e
            return item

        sections = [render(item) for item in self.sections]
        if not sections:
            return self.config.PROPERTIES.tbd

        html = markdown.convert('\n'.join(sections))
        return self.postprocess(html)

    @cached_property
    def context(self):
        page_data = {}
        if self.page_id is not None:
            to_rename = {
                'section': 'this_section',
                'chapter': 'this_chapter',
                'group': 'this_group',
                'page': 'this_page',
            }
            page_data = self.topography.data.loc[self.page_id].rename(to_rename)
        return {
            **page_data,
            'ctime': self.ctime,
            'mtime': self.mtime,
            'styles': list(dict.fromkeys(self.styles)),
        }

    def render(self):
        template = self.environment.get_template(f'page/{self.template}.jinja')
        return template.render(content=self.content, **self.context)

    def write(self, path):
        html = self.render()
        path = path / self.context['href']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')

    @cached_property
    def sections(self):
        sections = list()
        items = re.split(r"_{5,}\n", self.text or '')
        for item in items:
            if len(item) == 0:
                continue
            elif item[0] == '|':
                func_name, body = item[1:].split('\n', 1)
                if ':' in func_name:
                    func_name, args = func_name.split(':', maxsplit=1)
                else:
                    func_name, args = func_name, ''
                func_name = func_name.strip().lower()
                if func_name in self.config.AVAILABLE_STYLES:
                    self.styles.append(func_name)
                item = (func_name, body, self.get_args(args))
            sections.append(item)
        return sections

    def get_args(self, items):
        args, kwargs = [], {}
        for item in items.split(','):
            if '=' in item:
                key, val = item.split('=', maxsplit=1)
                kwargs[key.strip()] = val.strip(' \'"')
            else:
                args.append(item) if item else None
        return args, kwargs

    def postprocess(self, item):
        compose = lambda methods: reduce(lambda f,g: lambda x: g(f(x)), methods)
        methods = (getattr(self, i) for i in dir(self) if i.startswith('pp_'))
        pipeline = compose(methods)
        return pipeline(item)

    def pp_arrows(self, item):
        arrows = {
            '-&gt;': '&rarr;',
            '&lt;-': '&larr;',
            '=&gt;': '&rArr;',
            '&lt;=': '&lArr;',
        }
        for arrow, sub in arrows.items():
            item = item.replace(arrow, sub)
        return item

    def pp_crossrefs(self, item):
        regex = re.compile("\[([^#\[\]]+?)(#.+?)?\]")
        def make_crossref(match):
            code, anchor = match.group(1,2)
            if code in self.topography.crossrefs:
                href = self.topography.crossrefs[code]
                url = f"{self.context['nestedness']}{href}{anchor or ''}"
                return f'<a class="crossref" href="{url}">{code}</a>'
            warnings.warn(
                f"page_id '{self.page_id}' crossref {match.group(0)} "
                "komt niet voor in topo", stacklevel=5)
            return match.group(0)
        return regex.sub(make_crossref, item)

    def pp_shortcuts(self, item):
        regex = re.compile("(ctrl|alt|shift|&#8862; Win)\s?(?:-|\+)\s?(\S)")
        def format_kbd(match):
            kbd = lambda i: f"<kbd>{i}</kbd>"
            return ' + '.join(kbd(i) for i in match.groups())
        return regex.sub(format_kbd, item)

    @classmethod
    def read_md(
        cls,
        path,
        config,
        topography,
        environment,
        encoding='utf-8'
    ):
        """
        Instantiate Page from markdown file.
        """
        ctimestamp = path.stat().st_ctime
        mtimestamp = path.stat().st_mtime
        ctime = datetime.fromtimestamp(ctimestamp).strftime('%d-%m-%Y')
        mtime = datetime.fromtimestamp(mtimestamp).strftime('%d-%m-%Y')
        md = path.read_text(encoding=encoding)
        page_id, text = md.split('\n', 1)
        if page_id not in topography.data.index:
            print(
f"""
+-----------------------------------------------------------------------------+
                            !! WAARSCHUWING !!
+-----------------------------------------------------------------------------+
   - file: "{path.relative_to(config.WORKDIR)}"
   - id:   <{page_id}>

   Id komt niet voor in topografie
   -> bestand kan niet worden verwerkt
+-----------------------------------------------------------------------------+
""")
            return None
        return cls(
            config,
            topography,
            environment,
            page_id=page_id,
            text=text,
            ctime=ctime,
            mtime=mtime,
        )

import re
from datetime import datetime
from functools import cached_property, reduce

from markdown import Markdown
from markdown.extensions.toc import TocExtension

from naslagwerk.config import AVAILABLE_STYLES
from naslagwerk.convert import Converter


class Page:
    def __init__(
        self,
        site,
        topography,
        environment,
        template='main',
        page_id=None,
        text=None,
        ctime=None,
        mtime=None,
    ):
        self.page_id = page_id
        self.text = text
        self.site = site
        self.topography = topography
        self.environment = environment
        self.template = template
        self.ctime = ctime
        self.mtime = mtime
        self.styles = set()

    @property
    def content(self):
        toc = TocExtension(
            title=self.site['toc_title'],
            anchorlink=True,
        )
        EXTENSIONS = ['nl2br', toc]
        markdown = Markdown(extensions=EXTENSIONS)
        converter = Converter(self.environment, self.context)

        def render(item):
            if isinstance(item, tuple):
                func, text, (args, kwargs) = item
                method = getattr(converter, func)
                item = method(text, *args, **kwargs)
            return item

        sections = [render(item) for item in self.sections]
        if not sections:
            return self.site['tbd']

        html = markdown.convert('\n'.join(sections))
        return self.postprocess(html)

    @cached_property
    def context(self):
        page_data = {}
        if self.page_id is not None:
            to_rename = {
                'section': 'this_section',
                'chapter': 'this_chapter',
                'page': 'this_page',
            }
            page_data = self.topography.data.loc[self.page_id].rename(to_rename)
        return {
            **page_data,
            'ctime': self.ctime,
            'mtime': self.mtime,
            'styles': self.styles,
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
                func, body = item[1:].split('\n', 1)
                if ':' in func:
                    func, args = func.split(':', maxsplit=1)
                else:
                    func, args = func, ''
                func = func.strip().lower()
                self.styles.add(func) if func in AVAILABLE_STYLES else None
                item = (func, body, self.get_args(args))
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

    def pp_crossrefs(self, item):
        regex = re.compile("\[([^#\[\]]+?)(#.+?)?\]")
        def make_crossref(match):
            code, anchor = match.group(1,2)
            if code in self.topography.crossrefs:
                href = self.topography.crossrefs[code]
                url = f"{self.context['nestedness']}{href}{anchor or ''}"
                return f'<a class="crossref" href="{url}">{code}</a>'
            return match.group(0)
        return regex.sub(make_crossref, item)

    # def pp_crossrefs(self, item):
    #     for code, href in self.topography.crossrefs.items():
    #         url = self.context['nestedness'] + href
    #         crossref =f'<a class="crossref" href="{url}">{code}</a>'
    #         item = item.replace(f'[{code}]', crossref)
    #     return item

    def pp_shortcuts(self, item):
        regex = re.compile("(ctrl|alt|shift)\s?(?:-|\+)\s?(\S)")
        def format_kbd(match):
            kbd = lambda i: f"<kbd>{i}</kbd>"
            return ' + '.join(kbd(i) for i in match.groups())
        return regex.sub(format_kbd, item)

    @classmethod
    def read_md(
        cls,
        path,
        site,
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
        return cls(
            site,
            topography,
            environment,
            page_id=page_id,
            text=text,
            ctime=ctime,
            mtime=mtime,
        )

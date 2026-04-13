from re import Match
from typing import Any

from mistune import BlockParser, BlockState, HTMLRenderer, Markdown
from mistune.directives import BaseDirective, DirectivePlugin
from slugify import slugify


class Join(DirectivePlugin):
    NAME = "join_accordion"

    def parse(self, block: BlockParser, m: Match[str], state: BlockState):
        options = dict(self.parse_options(m))

        if options.get("close"):
            return {"type": "join_accordion_end"}
        return {
            "type": "join_accordion_start",
        }

    def __call__(self, directive: BaseDirective, md: Markdown) -> None:
        directive.register(self.NAME, self.parse)

        assert md.renderer is not None  # noqa: S101
        if md.renderer.NAME == "html":
            md.renderer.register(
                "join_accordion_start",
                lambda x: '<div class="join join-vertical w-full">',
            )
            md.renderer.register("join_accordion_end", lambda x: "</div>")


def render_join_start(
    self: HTMLRenderer,
):
    return


class Accordion(DirectivePlugin):
    NAME = "accordion"

    def parse(self, block: BlockParser, m: Match[str], state: BlockState):
        options = dict(self.parse_options(m))
        print(options)

        title = self.parse_title(m)

        content = self.parse_content(m)
        children = [
            {
                "type": "accordion_title",
                "text": title,
            },
            {
                "type": "accordion_content",
                "children": self.parse_tokens(block, content, state),
            },
        ]
        return {
            "type": "accordion",
            "children": children,
            "attrs": {
                "title": title,
            },
        }

    def __call__(self, directive: BaseDirective, md: Markdown) -> None:
        directive.register(self.NAME, self.parse)

        assert md.renderer is not None  # noqa: S101
        if md.renderer.NAME == "html":
            md.renderer.register("accordion", render_block_accordion)
            md.renderer.register("accordion_title", render_accordion_title)
            md.renderer.register("accordion_content", render_accordion_content)


def render_block_accordion(
    self: HTMLRenderer,
    text: str,
    title: str,
    **attrs: Any,
):
    print(attrs)
    slug = slugify(title)
    return f"""
        <details class="collapse bg-secondary join-item border border-primary collapse-arrow" name="{slug}">
        {text}
        </details>
    """  # noqa: E501


def render_accordion_title(
    self: HTMLRenderer,
    title: str,
    **attrs: Any,
):
    return f'<summary class="collapse-title font-semibold">{title}</summary>'


def render_accordion_content(self: Any, text: str) -> str:
    return f'<div class="collapse-content text-md">{text}</div>'

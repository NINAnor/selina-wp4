#!/usr/bin/env python3
import io
import json
import logging
import pathlib
from collections import defaultdict
from typing import Any

import environ
import mistune
import pandoc
import structlog
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mistune.directives import Admonition, RSTDirective, TableOfContents
from slugify import slugify

from .directives import Accordion, Join

app = FastAPI()

env = environ.Env()

BASE_DIR = pathlib.Path(__file__).parent.parent.parent
environ.Env.read_env(str(BASE_DIR / ".env"))

MODE = env("MODE", default="dev")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.DEBUG if env.bool("DEBUG", default=False) else logging.INFO
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)
log = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
templates.env.globals["MODE"] = MODE

app.mount("/static", StaticFiles(directory="static"), name="static")

with (BASE_DIR / "config.yml").open(mode="r") as f:
    templates.env.globals["CONFIG"] = yaml.load(f, yaml.SafeLoader)


WEBSITE_PATH = BASE_DIR / "website"
ALLOWED_PAGES = [e.stem for e in WEBSITE_PATH.iterdir() if e.is_file()]

log.debug("found these pages", pages=ALLOWED_PAGES)

SURVEY_CONFIG = json.load((BASE_DIR / "static" / "survey-config.json").open("r"))
log.debug("using survey config", config=SURVEY_CONFIG)


SURVEY_DEBUG_PATH = BASE_DIR / "survey.json" if MODE == "dev" else None

STOP_WORDS = [
    "What",
    "is",
    "are",
    "which",
    "should",
    "the",
    "a",
    "an",
    "of",
    "in",
    "for",
    "as",
    "s",
    "if",
    "or",
    "it",
    "she",
    "he",
    "all",
    "to",
    "this",
    "that",
    "these",
    "those",
    "at",
    "and",
    "how",
    "e",
    "g",
    "i",
    "be",
]


class Slugifier:
    def __init__(self):
        self.__ids = defaultdict(lambda: 0)

    def run(self, *args, **kwargs):
        result = slugify(*args, **kwargs)

        self.__ids[result] += 1
        return (
            result
            if self.__ids.get(result) < 2
            else f"{result}-{self.__ids.get(result)}"
        )


class CustomRenderer(mistune.HTMLRenderer):
    def __init__(
        self,
        slugifier: Slugifier,
        escape: bool = True,
        debug=False,
        page_name: str = "",
    ):
        super().__init__(escape=False)
        self.slugifier = slugifier
        self.debug = debug
        self.page_name = page_name

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        header_id = attrs.get("id") or self.slugifier.run(
            text,
            stopwords=STOP_WORDS,
            lowercase=True,
            word_boundary=True,
            max_length=50,
        )
        if self.debug:
            return f'<div class="flex flex-col gap-4"><h{level} id="{header_id}">{text}</h{level}><small>/{self.page_name}#{header_id}</small></div>\n'  # noqa: E501
        return f'<h{level} id="{header_id}">{text}</h{level}>\n'


def get_markdown(content: str, debug: bool = False, page_name: str = "") -> str:
    slugifier = Slugifier()
    return mistune.create_markdown(
        renderer=CustomRenderer(slugifier=slugifier, debug=debug, page_name=page_name),
        plugins=[
            "footnotes",
            "url",
            "superscript",
            "subscript",
            "def_list",
            "table",
            RSTDirective([Admonition(), TableOfContents(), Accordion(), Join()]),
        ],
    )(content)


if SURVEY_DEBUG_PATH:

    @app.get("/survey-debug")
    def preview(request: Request):
        if not SURVEY_DEBUG_PATH.exists():
            return "create a file survey.json in the root of the project with the data you want to debug"  # noqa: E501

        with SURVEY_DEBUG_PATH.open("r") as f:
            survey = templates.get_template("survey-render.md.jinja").render(
                json.load(f)
            )

        return templates.TemplateResponse(
            request=request,
            name="pages.html.jinja",
            context={"content": get_markdown(survey)},
        )


@app.post("/submit")
def submit(request_body: dict[Any, Any]):
    log.debug("submitted", data=request_body)

    if SURVEY_DEBUG_PATH:
        with SURVEY_DEBUG_PATH.open("w") as f:
            json.dump(request_body, f)

    survey = templates.get_template("survey-render.md.jinja").render(**request_body)

    doc = pandoc.read(survey, format="markdown")
    content = pandoc.write(doc, format="odt")
    if isinstance(content, bytes):
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.oasis.opendocument.text",
        )


@app.get("/survey")
async def survey(request: Request):
    return templates.TemplateResponse(
        request=request, name="survey.html.jinja", context={"config": SURVEY_CONFIG}
    )


@app.get("/{page_name:path}", response_class=HTMLResponse)
async def index(request: Request, page_name: str, debug: bool = False):
    if page_name == "":
        return templates.TemplateResponse(request=request, name="index.html.jinja")
    elif page_name in ALLOWED_PAGES:
        content = get_markdown(
            (WEBSITE_PATH / (pathlib.Path(page_name).with_suffix(".md")))
            .open("r")
            .read(),
            # Use attrs from processed tokens if available
            debug=debug,
            page_name=page_name,
        )
        return templates.TemplateResponse(
            request=request, name="pages.html.jinja", context={"content": content}
        )
    else:
        raise HTTPException(status_code=404, detail="Page not found")

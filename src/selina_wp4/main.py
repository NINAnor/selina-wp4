#!/usr/bin/env python3

import io
import json
import logging
import pathlib
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
from slugify import slugify

app = FastAPI()

env = environ.Env()

BASE_DIR = pathlib.Path(__file__).parent.parent.parent
environ.Env.read_env(str(BASE_DIR / ".env"))

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
app.mount("/static", StaticFiles(directory="static"), name="static")

with (BASE_DIR / "config.yml").open(mode="r") as f:
    templates.env.globals["CONFIG"] = yaml.load(f, yaml.SafeLoader)


WEBSITE_PATH = BASE_DIR / "website"
ALLOWED_PAGES = [e.stem for e in WEBSITE_PATH.iterdir() if e.is_file()]

log.debug("found these pages", pages=ALLOWED_PAGES)

SURVEY_CONFIG = json.load((BASE_DIR / "static" / "survey-config.json").open("r"))
log.debug("using survey config", config=SURVEY_CONFIG)


SURVEY_DEBUG_PATH = BASE_DIR / "survey.json"


class CustomRenderer(mistune.HTMLRenderer):
    def heading(self, text: str, level: int, **attrs: Any) -> str:
        # Use attrs from processed tokens if available
        return f'<h{level} id="{slugify(text)}">{text}</h{level}>\n'


markdown_html = mistune.create_markdown(renderer=CustomRenderer())


@app.get("/survey-debug")
def preview(request: Request):
    if not SURVEY_DEBUG_PATH.exists():
        return "create a file survey.json in the root of the project with the data you want to debug"  # noqa: E501

    with SURVEY_DEBUG_PATH.open("r") as f:
        survey = templates.get_template("survey-render.md.jinja").render(json.load(f))

    return templates.TemplateResponse(
        request=request,
        name="pages.html.jinja",
        context={"content": markdown_html(survey)},
    )


@app.post("/submit")
def submit(request_body: dict[Any, Any]):
    log.debug("submitted", data=request_body)

    with SURVEY_DEBUG_PATH.open("w") as f:
        json.dump(request_body, f)

    survey = templates.get_template("survey-render.md.jinja").render(**request_body)

    doc = pandoc.read(survey, format="markdown")
    content = pandoc.write(doc, format="docx")
    if isinstance(content, bytes):
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


@app.get("/survey")
async def survey(request: Request):
    return templates.TemplateResponse(
        request=request, name="survey.html.jinja", context={"config": SURVEY_CONFIG}
    )


@app.get("/{page_name:path}", response_class=HTMLResponse)
async def index(request: Request, page_name: str):
    if page_name == "":
        return templates.TemplateResponse(request=request, name="index.html.jinja")
    elif page_name in ALLOWED_PAGES:
        content = markdown_html(
            (WEBSITE_PATH / (pathlib.Path(page_name).with_suffix(".md")))
            .open("r")
            .read()
        )
        return templates.TemplateResponse(
            request=request, name="pages.html.jinja", context={"content": content}
        )
    else:
        raise HTTPException(status_code=404, detail="Page not found")

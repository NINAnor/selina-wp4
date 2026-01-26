# Selina WP4

## Setup
Install `pixi`: https://pixi.sh/latest/

```bash
pixi install
pixi run dev
```

Open your browser at http://localhost:8000


## Customization
### Development with docker
A basic docker image is already provided, run:
```bash
docker compose up --build watch
```

### Website content
Add markdown pages in `website`, the name of the file will be the url of the page

### Survey
Modify `static/survey-config.json` with a valid configuration from [SurveyJS Form Creator]().

Modify `templates/survey-render.md.jinja` to render a valid markdown content

"""Ponto de entrada do aplicativo Radar Imobiliario."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import pesquisa

app = FastAPI(title="Radar Imobiliario")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(pesquisa.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def pagina_pesquisa(request: Request):
    return templates.TemplateResponse("pesquisa.html", {"request": request})

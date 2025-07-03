import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user

templates = Jinja2Templates(directory="templates")
router = APIRouter()

YA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

REGIONS = {
    "213": "Москва",
    "2": "Санкт-Петербург",
    "54": "Екатеринбург",
}


def fetch_yandex_results(keyword: str, region: str) -> List[str]:
    url = "https://yandex.ru/search/"
    params = {"text": keyword, "lr": region}
    r = requests.get(url, params=params, headers=YA_HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select("a.link.organic__url-link"):
        href = a.get("href")
        if href and not href.startswith("/clk"):
            links.append(href)
        if len(links) >= 20:
            break
    return links

def parse_page(url: str) -> Dict[str, str]:
    r = requests.get(url, headers=YA_HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    data = {
        "url": url,
        "title": soup.title.text if soup.title else "",
        "description": "",
        "keywords": "",
        "h1": "",
        "h2": "",
        "h3": "",
    }
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        data["description"] = desc["content"]
    kw = soup.find("meta", attrs={"name": "keywords"})
    if kw and kw.get("content"):
        data["keywords"] = kw["content"]
    h1 = soup.find("h1")
    if h1:
        data["h1"] = h1.get_text(strip=True)
    h2 = soup.find("h2")
    if h2:
        data["h2"] = h2.get_text(strip=True)
    h3 = soup.find("h3")
    if h3:
        data["h3"] = h3.get_text(strip=True)
    return data

@router.get("/search", response_class=HTMLResponse)
def search_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("search.html", {"request": request, "regions": REGIONS})

@router.post("/search", response_class=HTMLResponse)
def search(request: Request, keyword: str = Form(...), region: str = Form(...), user=Depends(get_current_user)):
    links = fetch_yandex_results(keyword, region)
    results = [parse_page(link) for link in links]
    return templates.TemplateResponse("search.html", {"request": request, "regions": REGIONS, "results": results})

@router.post("/generate", response_class=HTMLResponse)
def generate(request: Request, urls: List[str] = Form(...), user=Depends(get_current_user)):
    import openai

    openai.api_key = os.getenv("OPENAI_API_KEY")
    texts = "\n".join(urls)
    prompt = (
        "На основе следующего контента сайтов сгенерируй 3 варианта title (до 60 символов) и 3 варианта description (до 160 символов). "
        "Сайты:\n" + texts
    )
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    meta_text = response.choices[0].message.content
    return templates.TemplateResponse("meta.html", {"request": request, "meta": meta_text})

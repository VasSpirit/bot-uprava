from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from telegram_sender import send_telegram_message
from auth import *

create_user_db()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("send.html", {"request": request, "user": user})

@app.post("/send")
async def send(
    request: Request,
    chat_id: str = Form(...),
    message: str = Form(...),
    custom_template: str = Form(""),
    template: str = Form(default=None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    final_message = ""
    if template:
        final_message += template + "\n\n"
    final_message += message
    if custom_template:
        final_message += f"\n\n{custom_template}"
    final_message += "\n\nПожалуйста, не отвечайте на это сообщение."

    success = send_telegram_message(chat_id, final_message)
    return templates.TemplateResponse("send.html", {"request": request, "user": user, "sent": success})

@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_user(username, password):
        response = RedirectResponse("/", status_code=302)
        login_user(response, username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if user_exists(username):
        return templates.TemplateResponse("register.html", {"request": request, "error": "User already exists"})
    register_user(username, password)
    response = RedirectResponse("/", status_code=302)
    login_user(response, username)
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login")
    logout_user(response)
    return response

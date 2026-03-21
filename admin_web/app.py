import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from main_bot.database import (
    add_server_node,
    get_all_bots_admin,
    get_all_main_users,
    get_all_payments,
    get_server_nodes,
    get_setting,
    get_stats_summary,
    get_web_admin_credentials,
    init_db,
    set_server_enabled,
    set_setting,
    set_web_admin_credentials,
)
from main_bot.launcher import block_child_bot, start_child_bot, stop_child_bot, unblock_child_bot

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
app = FastAPI(title='BotCraft Admin')
app.add_middleware(SessionMiddleware, secret_key=os.getenv('WEB_ADMIN_SECRET_KEY', 'change_this_secret_key'))
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


def is_auth(request: Request) -> bool:
    return bool(request.session.get('admin_ok'))


def guard(request: Request):
    return None if is_auth(request) else RedirectResponse('/login', status_code=302)


@app.on_event('startup')
async def startup():
    await init_db()


@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse('/dashboard' if is_auth(request) else '/login', status_code=302)


@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request, error: str = ''):
    return templates.TemplateResponse('login.html', {'request': request, 'error': error})


@app.post('/login')
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    saved_user, saved_pass = await get_web_admin_credentials()
    if username == saved_user and password == saved_pass:
        request.session['admin_ok'] = True
        return RedirectResponse('/dashboard', status_code=302)
    return templates.TemplateResponse('login.html', {'request': request, 'error': 'Login yoki parol xato'}, status_code=400)


@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=302)


@app.get('/dashboard', response_class=HTMLResponse)
async def dashboard(request: Request):
    g = guard(request)
    if g:
        return g
    return templates.TemplateResponse('dashboard.html', {'request': request, 'stats': await get_stats_summary(), 'nodes': await get_server_nodes()})


@app.get('/users', response_class=HTMLResponse)
async def users_page(request: Request):
    g = guard(request)
    if g:
        return g
    return templates.TemplateResponse('users.html', {'request': request, 'users': await get_all_main_users()})


@app.get('/bots', response_class=HTMLResponse)
async def bots_page(request: Request, msg: str = ''):
    g = guard(request)
    if g:
        return g
    return templates.TemplateResponse('bots.html', {'request': request, 'bots': await get_all_bots_admin(), 'msg': msg})


@app.post('/bots/{bot_id}/stop')
async def bot_stop(request: Request, bot_id: int):
    g = guard(request)
    if g:
        return g
    ok, msg = await stop_child_bot(bot_id)
    return RedirectResponse(f"/bots?msg={msg}", status_code=302)


@app.post('/bots/{bot_id}/start')
async def bot_start(request: Request, bot_id: int):
    g = guard(request)
    if g:
        return g
    ok, msg = await start_child_bot(str(PROJECT_ROOT), bot_id)
    return RedirectResponse(f"/bots?msg={msg}", status_code=302)


@app.post('/bots/{bot_id}/block')
async def bot_block(request: Request, bot_id: int):
    g = guard(request)
    if g:
        return g
    ok, msg = await block_child_bot(bot_id)
    return RedirectResponse(f"/bots?msg={msg}", status_code=302)


@app.post('/bots/{bot_id}/unblock')
async def bot_unblock(request: Request, bot_id: int):
    g = guard(request)
    if g:
        return g
    ok, msg = await unblock_child_bot(bot_id)
    return RedirectResponse(f"/bots?msg={msg}", status_code=302)


@app.get('/payments', response_class=HTMLResponse)
async def payments_page(request: Request):
    g = guard(request)
    if g:
        return g
    return templates.TemplateResponse('payments.html', {'request': request, 'payments': await get_all_payments()})


@app.get('/nodes', response_class=HTMLResponse)
async def nodes_page(request: Request):
    g = guard(request)
    if g:
        return g
    return templates.TemplateResponse('nodes.html', {'request': request, 'nodes': await get_server_nodes()})


@app.post('/nodes/add')
async def add_node(request: Request, code: str = Form(...), label: str = Form(...), host: str = Form(...), max_bots: int = Form(...)):
    g = guard(request)
    if g:
        return g
    await add_server_node(code.strip(), label.strip(), host.strip(), int(max_bots))
    return RedirectResponse('/nodes', status_code=302)


@app.post('/nodes/toggle/{code}')
async def toggle_node(request: Request, code: str):
    g = guard(request)
    if g:
        return g
    current = next((n for n in await get_server_nodes() if n[0] == code), None)
    if current:
        await set_server_enabled(code, not bool(current[4]))
    return RedirectResponse('/nodes', status_code=302)


@app.get('/settings', response_class=HTMLResponse)
async def settings_page(request: Request, saved: str = ''):
    g = guard(request)
    if g:
        return g
    settings = {
        'trial_days': await get_setting('trial_days', '10'),
        'kino_paid_30': await get_setting('kino_paid_30', '49000'),
        'media_paid_30': await get_setting('media_paid_30', '39000'),
        'shop_paid_30': await get_setting('shop_paid_30', '59000'),
        'referral_bonus': await get_setting('referral_bonus', '1000'),
        'payment_card': await get_setting('payment_card', ''),
        'payment_card_owner': await get_setting('payment_card_owner', ''),
    }
    web_user, _ = await get_web_admin_credentials()
    return templates.TemplateResponse('settings.html', {'request': request, 'settings': settings, 'saved': saved, 'web_user': web_user})


@app.post('/settings/save')
async def settings_save(
    request: Request,
    trial_days: str = Form(...),
    kino_paid_30: str = Form(...),
    media_paid_30: str = Form(...),
    shop_paid_30: str = Form(...),
    referral_bonus: str = Form(...),
    payment_card: str = Form(...),
    payment_card_owner: str = Form(...),
):
    g = guard(request)
    if g:
        return g
    await set_setting('trial_days', trial_days)
    await set_setting('kino_paid_30', kino_paid_30)
    await set_setting('media_paid_30', media_paid_30)
    await set_setting('shop_paid_30', shop_paid_30)
    await set_setting('referral_bonus', referral_bonus)
    await set_setting('payment_card', payment_card)
    await set_setting('payment_card_owner', payment_card_owner)
    return RedirectResponse('/settings?saved=saqlandi', status_code=302)


@app.post('/profile/save')
async def profile_save(request: Request, username: str = Form(...), password: str = Form(...), password2: str = Form(...)):
    g = guard(request)
    if g:
        return g
    if password != password2:
        return RedirectResponse('/settings?saved=parollar_mos_emas', status_code=302)
    await set_web_admin_credentials(username.strip(), password)
    return RedirectResponse('/settings?saved=profil_saqlandi', status_code=302)

import logging
import os
import signal
import subprocess
import sys
from typing import Any

from .database import (
    get_all_active_bots,
    update_bot_process_pid,
    get_bot_by_id,
    set_bot_active_state,
    set_bot_blocked_state,
)

logger = logging.getLogger(__name__)


def _safe_username(value: str) -> str:
    value = value or 'childbot'
    cleaned = ''.join(ch for ch in value if ch.isalnum() or ch in ('_', '-'))
    return cleaned or 'childbot'


def build_child_process(project_root: str, *, bot_type: str, token: str, owner_id: int, admin_id: int, channel_id: str = '', channel_type: str = 'public', bot_username: str = ''):
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    child_log_path = os.path.join(logs_dir, f"child_{owner_id}_{_safe_username(bot_username)}.log")

    env = os.environ.copy()
    env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUNBUFFERED'] = '1'
    env['BOTCRAFT_OWNER_ID'] = str(owner_id)
    env['BOTCRAFT_ADMIN_ID'] = str(admin_id)

    if bot_type == 'kino':
        script_path = os.path.join(project_root, 'kino_bot', 'run_kino_bot.py')
        env.update({
            'KINO_BOT_TOKEN': token,
            'KINO_CHANNEL_ID': channel_id or '',
            'KINO_CHANNEL_TYPE': channel_type or 'public',
            'KINO_ADMIN_ID': str(admin_id),
            'KINO_OWNER_ID': str(owner_id),
            'KINO_ADMIN_USERNAME': os.getenv('KINO_ADMIN_USERNAME', '@admin'),
            'KINO_ARCHIVE_CHANNEL_ID': channel_id or '',
            'PAYMENT_CARD': os.getenv('PAYMENT_CARD', '8600 0000 0000 0000'),
            'PAYMENT_CARD_OWNER': os.getenv('PAYMENT_CARD_OWNER', 'Ism Familiya'),
        })
        cwd = project_root
    elif bot_type == 'shop':
        instance_key = _safe_username(bot_username or token.split(':')[0])
        base_dir = os.path.join(project_root, 'shop_bot', 'instances', instance_key)
        env.update({'BOT_TOKEN': token, 'ADMIN_IDS': str(admin_id), 'SHOP_BOT_BASE_DIR': base_dir})
        script_path = os.path.join(project_root, 'shop_bot', 'run_shop_bot.py')
        cwd = os.path.join(project_root, 'shop_bot')
    else:
        instance_key = _safe_username(bot_username or token.split(':')[0])
        base_dir = os.path.join(project_root, 'media_bot', 'instances', instance_key)
        env.update({'BOT_TOKEN': token, 'ADMIN_IDS': str(admin_id), 'MEDIA_BOT_BASE_DIR': base_dir})
        script_path = os.path.join(project_root, 'media_bot', 'run_media_bot.py')
        cwd = os.path.join(project_root, 'media_bot')

    return script_path, cwd, env, child_log_path


def _spawn_child(project_root: str, row: tuple[Any, ...]) -> int:
    # created_bots columns: id, owner_id, owner_username, bot_token, bot_username, bot_type, channel_id, channel_type, admin_id, created_at,
    # expires_at, is_active, process_pid, plan_code, price_paid, meta_json, server_code, is_blocked, stopped_at, blocked_at
    token = row[3]
    bot_username = row[4] or token.split(':')[0]
    bot_type = row[5] or 'kino'
    channel_id = row[6] or ''
    channel_type = row[7] or 'public'
    admin_id = int(row[8] or 0)
    owner_id = int(row[1] or 0)

    script_path, cwd, env, child_log_path = build_child_process(
        project_root,
        bot_type=bot_type,
        token=token,
        owner_id=owner_id,
        admin_id=admin_id,
        channel_id=channel_id,
        channel_type=channel_type,
        bot_username=bot_username,
    )
    with open(child_log_path, 'ab') as child_log:
        proc = subprocess.Popen([sys.executable, script_path], env=env, cwd=cwd, stdout=child_log, stderr=child_log)
    return proc.pid


async def restart_active_bots(project_root: str):
    bots = await get_all_active_bots()
    restarted = 0
    for token, bot_type, channel_id, channel_type, admin_id, owner_id in bots:
        try:
            username_hint = token.split(':')[0]
            script_path, cwd, env, child_log_path = build_child_process(
                project_root,
                bot_type=bot_type,
                token=token,
                owner_id=int(owner_id or 0),
                admin_id=int(admin_id or 0),
                channel_id=channel_id or '',
                channel_type=channel_type or 'public',
                bot_username=username_hint,
            )
            with open(child_log_path, 'ab') as child_log:
                proc = subprocess.Popen([sys.executable, script_path], env=env, cwd=cwd, stdout=child_log, stderr=child_log)
            await update_bot_process_pid(token, proc.pid)
            restarted += 1
        except Exception:
            logger.exception('Child botni qayta ishga tushirishda xato')
    return restarted


async def stop_child_bot(bot_id: int) -> tuple[bool, str]:
    row = await get_bot_by_id(bot_id)
    if not row:
        return False, 'Bot topilmadi'
    pid = row[12]
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            logger.warning('Stop paytida process topilmadi: %s', pid)
        except Exception:
            logger.exception('Child botni to\'xtatishda xato')
            return False, 'Processni to\'xtatib bo\'lmadi'
    await set_bot_active_state(bot_id, False)
    return True, 'Bot to\'xtatildi'


async def start_child_bot(project_root: str, bot_id: int) -> tuple[bool, str]:
    row = await get_bot_by_id(bot_id)
    if not row:
        return False, 'Bot topilmadi'
    if int(row[17] or 0) == 1:
        return False, 'Bot bloklangan'
    if int(row[11] or 0) == 1 and row[12]:
        return True, 'Bot allaqachon ishlayapti'
    try:
        pid = _spawn_child(project_root, row)
        await set_bot_active_state(bot_id, True, pid=pid)
        return True, f'Bot ishga tushdi (PID {pid})'
    except Exception:
        logger.exception('Child botni ishga tushirishda xato')
        return False, 'Child bot ishga tushmadi'


async def block_child_bot(bot_id: int) -> tuple[bool, str]:
    row = await get_bot_by_id(bot_id)
    if not row:
        return False, 'Bot topilmadi'
    ok, msg = await stop_child_bot(bot_id)
    if not ok and 'topilmadi' in msg.lower():
        return ok, msg
    await set_bot_blocked_state(bot_id, True)
    return True, 'Bot bloklandi'


async def unblock_child_bot(bot_id: int) -> tuple[bool, str]:
    row = await get_bot_by_id(bot_id)
    if not row:
        return False, 'Bot topilmadi'
    await set_bot_blocked_state(bot_id, False)
    return True, 'Bot blokdan chiqarildi'

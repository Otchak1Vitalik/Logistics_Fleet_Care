"""
Надсилання листів (Gmail SMTP).
Якщо пошту не налаштовано (MAIL_USERNAME / MAIL_PASSWORD у файлі .env),
лист не надсилається, а код виводиться в консоль сервера - демо-режим.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from flask import current_app

log = logging.getLogger(__name__)

TEXTS = {
    'uk': {
        'subject': 'Код входу KRUTII TRANS: {code}',
        'hello': 'Вітаємо, {name}!',
        'intro': 'Ваш код для входу в систему управління автопарком:',
        'expires': 'Код дійсний {minutes} хв. Не повідомляйте його нікому.',
        'ignore': 'Якщо ви не намагалися увійти, просто проігноруйте цей лист.',
    },
    'en': {
        'subject': 'KRUTII TRANS sign-in code: {code}',
        'hello': 'Hello, {name}!',
        'intro': 'Your code to sign in to the fleet management system:',
        'expires': 'The code is valid for {minutes} min. Do not share it with anyone.',
        'ignore': 'If you did not try to sign in, just ignore this email.',
    },
}


def mail_configured():
    cfg = current_app.config
    return bool(cfg.get('MAIL_USERNAME') and cfg.get('MAIL_PASSWORD'))


def _html(t, name, code, minutes):
    digits = ''.join(
        f'<td style="width:52px;height:60px;border-radius:12px;background:#eef2ff;border:2px solid #c7d2fe;'
        f'font:700 30px Arial,sans-serif;color:#312e81;text-align:center">{d}</td><td style="width:10px"></td>'
        for d in code)
    return f"""<!doctype html><html><body style="margin:0;background:#f3f4f6;padding:24px 0">
<table align="center" width="460" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;font-family:Arial,sans-serif">
<tr><td style="background:#4f46e5;padding:20px 28px;color:#fff;font:700 20px Arial,sans-serif">KRUTII TRANS</td></tr>
<tr><td style="padding:28px">
<p style="margin:0 0 8px;font-size:16px;color:#111827">{t['hello'].format(name=name)}</p>
<p style="margin:0 0 20px;font-size:14px;color:#4b5563">{t['intro']}</p>
<table align="center" cellpadding="0" cellspacing="0"><tr>{digits}</tr></table>
<p style="margin:22px 0 6px;font-size:13px;color:#4b5563">{t['expires'].format(minutes=minutes)}</p>
<p style="margin:0;font-size:12px;color:#9ca3af">{t['ignore']}</p>
</td></tr></table></body></html>"""


def send_login_code(email, name, code, lang='uk'):
    """Надсилає код входу. Повертає 'sent' або 'demo'."""
    cfg = current_app.config
    minutes = cfg.get('LOGIN_CODE_TTL_MINUTES', 5)
    t = TEXTS.get(lang, TEXTS['uk'])

    if not mail_configured():
        msg = f'[ДЕМО-РЕЖИМ] Код входу для {email}: {code} (пошту не налаштовано в .env)'
        log.warning(msg)
        print(msg, flush=True)
        return 'demo'

    message = EmailMessage()
    message['Subject'] = t['subject'].format(code=code)
    message['From'] = formataddr((cfg['MAIL_FROM_NAME'], cfg['MAIL_USERNAME']))
    message['To'] = email
    message.set_content('\n'.join([
        t['hello'].format(name=name), '', t['intro'], '', f'    {code}', '',
        t['expires'].format(minutes=minutes), t['ignore'],
    ]))
    message.add_alternative(_html(t, name, code, minutes), subtype='html')

    if cfg.get('MAIL_USE_SSL', True):
        with smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], context=ssl.create_default_context(), timeout=15) as smtp:
            smtp.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
            smtp.send_message(message)
    else:
        # порт 587 зі STARTTLS (або локальний тестовий сервер без шифрування)
        with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=15) as smtp:
            smtp.ehlo()
            if smtp.has_extn('starttls'):
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if smtp.has_extn('auth'):
                smtp.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
            smtp.send_message(message)
    return 'sent'

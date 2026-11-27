"""Вхід за кодом з пошти: надсилання, перевірка, обмеження спроб і термін дії."""
from datetime import datetime, timedelta

import pytest
from bson import ObjectId

import routes.auth as auth_routes


@pytest.fixture()
def sent(monkeypatch):
    """Перехоплює надсилання листа і зберігає останній код."""
    box = {}

    def fake_send(email, name, code, lang='uk'):
        box.update(email=email, name=name, code=code, lang=lang)
        return 'demo'
    monkeypatch.setattr(auth_routes, 'send_login_code', fake_send)
    return box


def set_email(db, ids, username, email='driver.ivanov@gmail.com'):
    db.users.update_one({'_id': ObjectId(ids[username])}, {'$set': {'email': email}})


def test_no_email_gives_generic_error(app, db, ids, sent):
    client = app.test_client()
    r1 = client.post('/api/auth/email-code/request', json={'username': 'driver'})
    r2 = client.post('/api/auth/email-code/request', json={'username': 'nobody'})
    assert r1.status_code == r2.status_code == 400
    assert r1.get_json()['error'] == r2.get_json()['error']  # не видає, чи існує логін
    assert sent == {}


def test_full_login_with_code(app, db, ids, sent):
    set_email(db, ids, 'driver')
    client = app.test_client()
    r = client.post('/api/auth/email-code/request', json={'username': 'driver', 'lang': 'en'})
    body = r.get_json()
    assert r.status_code == 200 and body['email'] == 'dr' + '•' * 11 + '@gmail.com' and body['length'] == 4
    assert sent['email'] == 'driver.ivanov@gmail.com' and sent['lang'] == 'en' and len(sent['code']) == 4
    # у базі - лише хеш, не сам код
    doc = db.login_codes.find_one({'user_id': ids['driver']})
    assert sent['code'] not in str(doc)

    wrong = '0000' if sent['code'] != '0000' else '1111'
    bad = client.post('/api/auth/email-code/verify', json={'username': 'driver', 'code': wrong})
    assert bad.status_code == 400 and bad.get_json()['attempts_left'] == 4

    ok = client.post('/api/auth/email-code/verify', json={'username': 'driver', 'code': sent['code']})
    assert ok.status_code == 200 and ok.get_json()['user']['username'] == 'driver'
    assert client.get('/api/auth/me').status_code == 200          # cookie встановлено - користувач увійшов
    assert db.login_codes.count_documents({}) == 0                # код одноразовий
    again = app.test_client().post('/api/auth/email-code/verify', json={'username': 'driver', 'code': sent['code']})
    assert again.status_code == 404


def test_resend_cooldown(app, db, ids, sent):
    set_email(db, ids, 'mech', 'mech@gmail.com')
    client = app.test_client()
    assert client.post('/api/auth/email-code/request', json={'username': 'mech'}).status_code == 200
    r = client.post('/api/auth/email-code/request', json={'username': 'mech'})
    assert r.status_code == 429 and 0 < r.get_json()['retry_after'] <= 30


def test_lock_after_five_wrong_attempts(app, db, ids, sent):
    set_email(db, ids, 'admin', 'boss@gmail.com')
    client = app.test_client()
    client.post('/api/auth/email-code/request', json={'username': 'admin'})
    wrong = '0000' if sent['code'] != '0000' else '1111'
    statuses = [client.post('/api/auth/email-code/verify', json={'username': 'admin', 'code': wrong}).status_code for _ in range(5)]
    assert statuses == [400, 400, 400, 400, 429]
    # навіть правильний код після блокування не приймається
    r = client.post('/api/auth/email-code/verify', json={'username': 'admin', 'code': sent['code']})
    assert r.status_code == 429


def test_expired_code(app, db, ids, sent):
    set_email(db, ids, 'driver2', 'd2@gmail.com')
    client = app.test_client()
    client.post('/api/auth/email-code/request', json={'username': 'driver2'})
    db.login_codes.update_one({'user_id': ids['driver2']}, {'$set': {'expires_at': datetime.utcnow() - timedelta(seconds=1)}})
    r = client.post('/api/auth/email-code/verify', json={'username': 'driver2', 'code': sent['code']})
    assert r.status_code == 410


def test_mailer_builds_letter(app, monkeypatch):
    """Лист через SMTP: перевіряємо адресу, тему, HTML і код (без реального з'єднання з Gmail)."""
    import services.mailer as mailer
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, context=None, timeout=None):
            captured['host'], captured['port'] = host, port
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, user, password): captured['login'] = (user, password)
        def send_message(self, msg): captured['msg'] = msg

    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', FakeSMTP)
    with app.app_context():
        app.config.update(MAIL_USERNAME='krutiitrans.system@gmail.com', MAIL_PASSWORD='abcdabcdabcdabcd')
        try:
            assert mailer.send_login_code('user@gmail.com', 'Іванов Петро', '4827', 'uk') == 'sent'
        finally:
            app.config.update(MAIL_USERNAME='', MAIL_PASSWORD='')
    msg = captured['msg']
    assert captured['host'] == 'smtp.gmail.com' and captured['port'] == 465
    assert captured['login'] == ('krutiitrans.system@gmail.com', 'abcdabcdabcdabcd')
    assert msg['To'] == 'user@gmail.com' and '4827' in msg['Subject']
    html = msg.get_body(('html',)).get_content()
    assert 'Іванов Петро' in html and all(f'>{d}</td>' in html for d in '4827')

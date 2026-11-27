"""
PDF путівного листа за зразком типової форми № 1 «Подорожній лист вантажного автомобіля»
(наказ Мінстату України від 17.02.1998 № 488).

Документ формується з даних системи: підприємство, автомобіль, водій, маршрут, пробіг, пальне,
графи для підписів і відміток (медогляд, технічний стан, виїзд / повернення), QR-код для перевірки
путівки в системі та відривний талон.
"""
import io
import os
from datetime import datetime, timezone

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
FONT, FONT_B = 'DejaVuSans', 'DejaVuSans-Bold'
_fonts_ready = False

STATUS_LABELS = {'issued': 'ВИДАНО', 'active': 'У РЕЙСІ', 'completed': 'ЗАВЕРШЕНО', 'cancelled': 'СКАСОВАНО'}
FUEL_LABELS = {'diesel': 'Дизель', 'petrol': 'Бензин', 'gas': 'Газ'}
INK = colors.HexColor('#111827')
MUTED = colors.HexColor('#6b7280')
LINE = colors.HexColor('#9ca3af')
ACCENT = colors.HexColor('#312e81')


def _register_fonts():
    global _fonts_ready
    if not _fonts_ready:
        pdfmetrics.registerFont(TTFont(FONT, os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont(FONT_B, os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
        _fonts_ready = True


def _to_dt(value):
    """Дата з бази (UTC) -> місцевий час сервера, як на сайті."""
    if isinstance(value, str) and value:
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().replace(tzinfo=None)


def _d(value, with_time=False):
    dt = _to_dt(value)
    if not dt:
        return '—'
    return dt.strftime('%d.%m.%Y %H:%M' if with_time else '%d.%m.%Y')


def _n(value, unit='', decimals=0):
    if value is None or value == '':
        return '—'
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f'{num:,.{decimals}f}'.replace(',', ' ').replace('.', ',')
    return f'{text} {unit}'.strip()


class _Sheet:
    """Невеликі помічники малювання поверх reportlab canvas (координати в мм від верхнього краю)."""

    def __init__(self, c):
        self.c = c
        self.w, self.h = A4

    def y(self, top_mm):
        return self.h - top_mm * mm

    def text(self, x, top, s, size=9, bold=False, color=INK, align='left'):
        self.c.setFont(FONT_B if bold else FONT, size)
        self.c.setFillColor(color)
        fn = {'left': self.c.drawString, 'right': self.c.drawRightString, 'center': self.c.drawCentredString}[align]
        fn(x * mm, self.y(top), str(s))

    def fit(self, s, width_mm, size, bold=False):
        """Обрізає текст, щоб він вміщався в клітинку."""
        s = str(s)
        font = FONT_B if bold else FONT
        while s and pdfmetrics.stringWidth(s, font, size) > width_mm * mm:
            s = s[:-2] + '…' if len(s) > 2 else ''
        return s

    def line(self, x1, top1, x2, top2, width=0.5, color=LINE, dash=None):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.setDash(*dash) if dash else self.c.setDash()
        self.c.line(x1 * mm, self.y(top1), x2 * mm, self.y(top2))
        self.c.setDash()

    def rect(self, x, top, w, h, fill=None, stroke=LINE, width=0.6):
        self.c.setLineWidth(width)
        self.c.setStrokeColor(stroke)
        if fill is not None:
            self.c.setFillColor(fill)
        self.c.rect(x * mm, self.y(top + h), w * mm, h * mm, stroke=1, fill=1 if fill is not None else 0)

    def section(self, x, top, w, title):
        self.rect(x, top, w, 6.5, fill=colors.HexColor('#eef2ff'), stroke=colors.HexColor('#c7d2fe'))
        self.text(x + 2.5, top + 4.6, title, 8.5, bold=True, color=ACCENT)
        return top + 6.5

    def grid(self, x, top, widths, rows, header=None, row_h=7.2, size=8.5):
        """Таблиця: rows - список рядків зі значеннями; header - підписи колонок (дрібним шрифтом)."""
        total = sum(widths)
        cur = top
        if header:
            self.rect(x, cur, total, 5.6, fill=colors.HexColor('#f9fafb'))
            cx = x
            for wdt, hdr in zip(widths, header):
                self.text(cx + 1.8, cur + 3.9, self.fit(hdr, wdt - 3, 6.8), 6.8, color=MUTED)
                cx += wdt
            cur += 5.6
        for row in rows:
            self.rect(x, cur, total, row_h)
            cx = x
            for i, (wdt, val) in enumerate(zip(widths, row)):
                bold = isinstance(val, tuple)
                val = val[0] if bold else val
                self.text(cx + 1.8, cur + row_h / 2 + 1.3, self.fit(val, wdt - 3, size, bold), size, bold=bold)
                cx += wdt
            cur += row_h
        cx = x
        for wdt in widths[:-1]:
            cx += wdt
            self.line(cx, top, cx, cur, 0.4)
        return cur

    def field(self, x, top, w, label, value, size=9):
        """Підпис зверху дрібним шрифтом, значення - жирним на лінії (довгий текст спершу зменшується)."""
        self.text(x, top, label, 6.8, color=MUTED)
        value = str(value)
        while size > 6.8 and pdfmetrics.stringWidth(value, FONT_B, size) > (w - 1) * mm:
            size -= 0.2
        self.text(x, top + 4.4, self.fit(value, w - 1, size, True), size, bold=True)
        self.line(x, top + 5.6, x + w, top + 5.6, 0.4)

    def signature(self, x, top, w, caption, name='', stamp=False):
        # ПІБ друкується над лінією праворуч (поруч залишається місце для підпису), підказка - під лінією
        if name:
            self.text(x + w, top - 1.4, self.fit(name, w * 0.55, 7.4), 7.4, align='right')
        self.line(x, top, x + w, top, 0.5, INK)
        self.text(x, top + 3.4, caption, 6.6, color=MUTED)
        if stamp:
            self.text(x + w, top + 3.4, 'М. П.', 6.6, color=MUTED, align='right')

    def qr(self, x, top, size_mm, data):
        widget = QrCodeWidget(data)
        b = widget.getBounds()
        bw, bh = b[2] - b[0], b[3] - b[1]
        d = Drawing(size_mm * mm, size_mm * mm, transform=[size_mm * mm / bw, 0, 0, size_mm * mm / bh, 0, 0])
        d.add(widget)
        renderPDF.draw(d, self.c, x * mm, self.y(top + size_mm))


def build_waybill_pdf(waybill, company_name='KRUTII TRANS', verify_url='', norm_liters=None):
    """Повертає байти PDF. waybill - документ путівки з вкладеними vehicle, driver, issuer."""
    _register_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    number = waybill.get('number', '—')
    c.setTitle(f'Подорожній лист {number}')
    c.setAuthor(company_name)
    c.setSubject('Подорожній лист вантажного автомобіля')
    s = _Sheet(c)
    v = waybill.get('vehicle') or {}
    drv = waybill.get('driver') or {}
    issuer = waybill.get('issuer') or {}
    status = waybill.get('status')
    L, R = 15, 195          # поля сторінки, мм
    W = R - L

    # ---------- шапка ----------
    s.text(R, 10, 'Складено за зразком типової форми № 1', 6.8, color=MUTED, align='right')
    s.text(R, 13.2, '(наказ Мінстату України від 17.02.1998 № 488)', 6.8, color=MUTED, align='right')
    s.rect(L, 8, 9, 9, fill=ACCENT, stroke=ACCENT)
    s.text(L + 4.5, 14.2, 'KT', 8, bold=True, color=colors.white, align='center')
    s.text(L + 12, 12, company_name, 11, bold=True)
    s.text(L + 12, 16, 'Код ЄДРПОУ ____________', 7, color=MUTED)

    s.text(105, 28, 'ПОДОРОЖНІЙ ЛИСТ ВАНТАЖНОГО АВТОМОБІЛЯ', 14, bold=True, align='center')
    s.text(105, 35, f'№ {number}', 13, bold=True, color=ACCENT, align='center')
    s.text(105, 40.5, f'Дата видачі: {_d(waybill.get("issue_date") or waybill.get("created_at"))}', 8.5, align='center')
    s.text(105, 44.5, f'Дійсний з {_d(waybill.get("valid_from"), True)} до {_d(waybill.get("valid_until"), True)}',
           8.5, align='center')

    # штамп статусу
    label = STATUS_LABELS.get(status)
    if label:
        tone = {'completed': colors.HexColor('#15803d'), 'cancelled': colors.HexColor('#b91c1c'),
                'active': colors.HexColor('#1d4ed8')}.get(status, ACCENT)
        c.saveState()
        c.translate(176 * mm, s.y(38))
        c.rotate(12)
        c.setStrokeColor(tone)
        c.setFillColor(tone)
        c.setLineWidth(1.4)
        tw = pdfmetrics.stringWidth(label, FONT_B, 11) + 6 * mm
        c.roundRect(-tw / 2, -4.2 * mm, tw, 8.4 * mm, 2 * mm, stroke=1, fill=0)
        c.setFont(FONT_B, 11)
        c.drawCentredString(0, -1.4 * mm, label)
        c.restoreState()

    # ---------- автомобіль і водій ----------
    top = 50
    half = (W - 4) / 2
    s.section(L, top, half, 'АВТОМОБІЛЬ')
    s.section(L + half + 4, top, half, 'ВОДІЙ')
    t = top + 11
    s.field(L, t, half * 0.58, 'Марка, модель', f"{v.get('brand', '')} {v.get('model', '')}".strip() or '—')
    s.field(L + half * 0.62, t, half * 0.38, 'Державний номерний знак', v.get('plate_number', '—'), 10)
    s.field(L, t + 10, half * 0.3, 'Рік випуску', v.get('year') or '—')
    s.field(L + half * 0.35, t + 10, half * 0.3, 'Пальне', FUEL_LABELS.get(v.get('fuel_type'), v.get('fuel_type') or '—'))
    s.field(L + half * 0.7, t + 10, half * 0.3, 'Норма, л/100 км', _n(v.get('fuel_norm'), decimals=1))
    x2 = L + half + 4
    s.field(x2, t, half, 'Прізвище, ім’я, по батькові', drv.get('full_name', '—'))
    s.field(x2, t + 10, half * 0.48, 'Посвідчення водія №', drv.get('license_number') or '—')
    s.field(x2 + half * 0.52, t + 10, half * 0.48, 'Дійсне до', _d(drv.get('license_expiry')))

    # ---------- завдання ----------
    top = t + 21
    top = s.section(L, top, W, 'ЗАВДАННЯ ВОДІЄВІ') + 4.5
    s.field(L, top, W * 0.48, 'Пункт відправлення', waybill.get('route_from') or '—')
    s.field(L + W * 0.52, top, W * 0.48, 'Пункт призначення', waybill.get('route_to') or '—')
    s.field(L, top + 10, W, 'Опис маршруту / примітки', waybill.get('route_description') or waybill.get('notes') or '—', 8.5)

    # ---------- робота водія й автомобіля ----------
    top += 21
    top = s.section(L, top, W, 'РОБОТА ВОДІЯ І АВТОМОБІЛЯ')
    start, end = waybill.get('odometer_start'), waybill.get('odometer_end')
    distance = (end - start) if (isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start) else None
    top = s.grid(L, top, [40, 52, 46, 42], [
        ['Виїзд з гаража', _d(waybill.get('valid_from'), True), _n(start, 'км'), ''],
        ['Повернення в гараж', _d(waybill.get('completed_at'), True) if status == 'completed' else '', _n(end, 'км') if end else '', ''],
        [('Пробіг за рейс',), '', (_n(distance, 'км'),) if distance is not None else '', ''],
    ], header=['Операція', 'Дата і час (факт)', 'Показник спідометра', 'Підпис диспетчера'])

    # ---------- рух пального ----------
    top += 4
    top = s.section(L, top, W, 'РУХ ПАЛЬНОГО, л')
    used = waybill.get('fuel_used')
    deviation = None
    if norm_liters and used is not None and norm_liters > 0:
        deviation = (used - norm_liters) / norm_liters * 100
    dev_text = '—' if deviation is None else f'{deviation:+.1f} %'.replace('.', ',')
    top = s.grid(L, top, [30, 30, 30, 30, 30, 30], [[
        _n(waybill.get('fuel_issued'), decimals=1), _n(waybill.get('fuel_remaining'), decimals=1) if status == 'completed' else '',
        _n(used, decimals=1) if used is not None else '', _n(norm_liters, decimals=1) if norm_liters else '',
        (dev_text,) if deviation is not None and deviation > 0 else dev_text, '',
    ]], header=['Видано', 'Залишок у баку', 'Витрачено (факт)', 'За нормою', 'Відхилення', 'Підпис заправника'])

    # ---------- відмітки та підписи ----------
    top += 4
    top = s.section(L, top, W, 'ВІДМІТКИ ТА ПІДПИСИ') + 3
    col = (W - 8) / 2
    blocks = [
        ('Водій за станом здоров’я до керування допущений', 'Медичний працівник', ''),
        ('Автомобіль технічно справний. Виїзд дозволено', 'Механік', ''),
        ('Путівку видав', 'Диспетчер / керівник', issuer.get('full_name', '')),
        ('Автомобіль у справному стані прийняв', 'Водій', drv.get('full_name', '')),
        ('При поверненні автомобіль: справний / несправний', 'Механік', ''),
        ('Автомобіль здав', 'Водій', drv.get('full_name', '')),
    ]
    for i, (title, who, name) in enumerate(blocks):
        bx = L if i % 2 == 0 else L + col + 8
        by = top + (i // 2) * 15
        s.text(bx, by + 3, s.fit(title, col, 7.6, True), 7.6, bold=True)
        s.signature(bx, by + 10, col, f'{who} (підпис, дата, час)', name,
                    stamp=who in ('Медичний працівник', 'Диспетчер / керівник'))
    top += 46

    # ---------- QR і примітка ----------
    if verify_url:
        s.qr(R - 26, top, 26, verify_url)
        s.text(R - 29, top + 8, 'Перевірити путівку', 8, bold=True, align='right')
        s.text(R - 29, top + 12, 'в системі: відскануйте', 7, color=MUTED, align='right')
        s.text(R - 29, top + 15.5, 'QR-код камерою телефона', 7, color=MUTED, align='right')
    if waybill.get('completion_notes'):
        s.text(L, top + 5, 'Примітки водія:', 7, color=MUTED)
        s.text(L, top + 9, s.fit(waybill['completion_notes'], 120, 8), 8)

    # ---------- відривний талон ----------
    cut = 258
    s.line(L - 5, cut, R + 5, cut, 0.6, MUTED, dash=(3, 3))
    s.text(105, cut - 1.2, '✂  лінія відриву', 6.5, color=MUTED, align='center')
    s.text(L, cut + 6, f'ТАЛОН ДО ПОДОРОЖНЬОГО ЛИСТА № {number}', 9, bold=True)
    s.text(L, cut + 11, s.fit(f"Автомобіль: {v.get('plate_number', '—')} {v.get('brand', '')} {v.get('model', '')}   "
                              f"Водій: {drv.get('full_name', '—')}", W, 8), 8)
    s.text(L, cut + 15.5, s.fit(f"Маршрут: {waybill.get('route_from') or '—'} — {waybill.get('route_to') or '—'}   "
                                f"Пробіг: {_n(distance, 'км') if distance is not None else '________'}", W, 8), 8)
    s.signature(L + W - 60, cut + 24, 60, 'Підпис відповідальної особи')

    # ---------- колонтитул ----------
    s.text(L, 290, f'Сформовано системою {company_name} {datetime.now().strftime("%d.%m.%Y %H:%M")}', 6.5, color=MUTED)
    s.text(R, 290, 'Аркуш 1 з 1', 6.5, color=MUTED, align='right')

    if status == 'cancelled':
        c.saveState()
        c.setFillColor(colors.Color(0.73, 0.11, 0.11, alpha=0.12))
        c.setFont(FONT_B, 80)
        c.translate(105 * mm, 150 * mm)
        c.rotate(35)
        c.drawCentredString(0, 0, 'СКАСОВАНО')
        c.restoreState()

    c.showPage()
    c.save()
    return buf.getvalue()

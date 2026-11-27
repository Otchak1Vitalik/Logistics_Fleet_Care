// Мінімальна система локалізації інтерфейсу (українська / англійська).
//
// - tr(text, ...args) - переклад тексту з коду; ключ - український текст,
//   {0}, {1} у ключі замінюються аргументами.
// - translateServer(text) - переклад текстів, які надходять із сервера
//   (статуси, категорії, помилки, сповіщення), зокрема з підстановками.
// - Мова зберігається в браузері; після перемикання сторінка перезавантажується,
//   тож увесь інтерфейс гарантовано відображається новою мовою.
import en from './en'

const STORAGE_KEY = 'krutii-lang'
export const LANGUAGES = ['uk', 'en']

function readLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (LANGUAGES.includes(saved)) return saved
  } catch (e) { /* localStorage недоступний - українська за замовчуванням */ }
  return 'uk'
}

export const lang = readLang()
if (typeof document !== 'undefined') document.documentElement.lang = lang

export function setLang(next) {
  if (!LANGUAGES.includes(next) || next === lang) return
  try { localStorage.setItem(STORAGE_KEY, next) } catch (e) { /* ignore */ }
  window.location.reload()
}

function fill(text, args) {
  return args.reduce((s, a, i) => s.split(`{${i}}`).join(a ?? ''), text)
}

export function tr(text, ...args) {
  const base = lang === 'en' && Object.prototype.hasOwnProperty.call(en, text) ? en[text] : text
  return args.length ? fill(base, args) : base
}

// --- Тексти з сервера ---------------------------------------------------
const CYR = /[А-Яа-яІіЇїЄєҐґ]/
const word = (s) => (s && Object.prototype.hasOwnProperty.call(en, s) ? en[s] : s)

// Повідомлення з підстановками, які формує сервер
const PATTERNS = [
  [/^Заплановано ТО: (\d+)\.$/, (m) => `Maintenance scheduled: ${m[1]}.`],
  [/^ТО прострочене на (\d+) дн\. - ставимо першочергово\.(.*)$/, (m) => `Maintenance is ${m[1]} days overdue - scheduled first.${m[2] ? ' ' + translateServer(m[2].trim()) : ''}`],
  [/^Ризик відмови (\d+) % - ТО на (\d+) дн\. раніше строку\.(.*)$/, (m) => `Failure risk ${m[1]} % - maintenance ${m[2]} days early.${m[3] ? ' ' + translateServer(m[3].trim()) : ''}`],
  [/^На (\d+) дн\. раніше строку - рівномірне завантаження сервісу\.(.*)$/, (m) => `${m[1]} days early - to balance the workshop load.${m[2] ? ' ' + translateServer(m[2].trim()) : ''}`],
  [/^На (\d+) дн\. пізніше строку - низький ризик, звільняємо місце для ризикованіших\.(.*)$/, (m) => `${m[1]} days late - low risk, making room for riskier vehicles.${m[2] ? ' ' + translateServer(m[2].trim()) : ''}`],
  [/^У строк\. (.+)$/, (m) => `On time. ${translateServer(m[1])}`],
  [/^Враховано рейс: (.+)\.$/, (m) => `Trip taken into account: ${m[1]}.`],
  [/^Високий ризик несправності: (.+)$/, (m) => `High failure risk: ${m[1]}`],
  [/^Ймовірність несправності протягом (\d+) днів - (\d+) %\. ?(.*)$/,
    (m) => `Probability of a fault within ${m[1]} days - ${m[2]} %.${m[3] ? ' ' + translateServer(m[3]) : ''}`],
  [/^ознака (\S+)$/, (m) => `feature ${m[1]}`],
  [/^Підозріла витрата пального: (.+)$/, (m) => `Suspicious fuel consumption: ${m[1]}`],
  [/^Нові підозрілі випадки витрати пального: (\d+)$/, (m) => `New suspicious fuel consumption cases: ${m[1]}`],
  [/^Витрата ([\d.]+) л\/100 км при нормі ([\d.]+) л\/100 км \(з урахуванням сезону\) - на (\d+) % вище норми \(поріг (\d+) %\)\.(.*)$/,
    (m) => `Consumption ${m[1]} l/100 km vs norm ${m[2]} l/100 km (season-adjusted) - ${m[3]} % above the norm (threshold ${m[4]} %).${m[5] ? ' ' + translateServer(m[5].trim()) : ''}`],
  [/^Звичайна витрата (цього автомобіля|автопарку) - близько (\d+) % від норми, у цьому рейсі - (\d+) % \(робастний z = ([\d.-]+) при порозі ([\d.]+)\)\.(.*)$/,
    (m) => `The ${m[1] === 'автопарку' ? 'fleet' : "vehicle's"} usual consumption is about ${m[2]} % of the norm, on this trip - ${m[3]} % (robust z = ${m[4]}, threshold ${m[5]}).${m[6] ? ' ' + translateServer(m[6].trim()) : ''}`],
  [/^Заправлено (\d+) л при об’ємі бака (\d+) л - на (\d+) л більше, ніж може вміститися\.(.*)$/,
    (m) => `Refuelled ${m[1]} l with a ${m[2]} l tank - ${m[3]} l more than it can hold.${m[4] ? ' ' + translateServer(m[4].trim()) : ''}`],
  [/^Повторна заправка (\d+) л через (\d+) год після попередньої, пробіг між ними лише (\d+) км\.(.*)$/,
    (m) => `Repeated refuel of ${m[1]} l ${m[2]} h after the previous one, only ${m[3]} km driven in between.${m[4] ? ' ' + translateServer(m[4].trim()) : ''}`],
  [/^Ціна ([\d.]+) грн\/л відрізняється від звичної \(([\d.]+) грн\/л\) на ([+-]\d+) %\.(.*)$/,
    (m) => `Price ${m[1]} UAH/l differs from the usual (${m[2]} UAH/l) by ${m[3]} %.${m[4] ? ' ' + translateServer(m[4].trim()) : ''}`],
  [/^Перевірте на сторінці «Аномалії витрати пального»\.$/, () => 'Review it on the «Fuel consumption anomalies» page.'],
  [/^Підозріла активність: вхід «(.+)»$/, (m) => `Suspicious activity: sign-in «${m[1]}»`],
  [/^(\d+) невдалих спроб входу для облікового запису «(.+)» за (\d+) хв\. Остання спроба з адреси (.+)\.$/,
    (m) => `${m[1]} failed sign-in attempts for account «${m[2]}» within ${m[3]} min. Last attempt from ${m[4]}.`],
  [/^Невірний код\. Залишилось спроб: (\d+)\.$/, (m) => `Wrong code. Attempts left: ${m[1]}.`],
  [/^Повторно надіслати код можна через (\d+) с\.$/, (m) => `You can resend the code in ${m[1]} s.`],
  [/^Нова несправність: (.+)$/, (m) => `New fault: ${m[1]}`],
  [/^Критична несправність: (.+)$/, (m) => `Critical fault: ${m[1]}`],
  [/^Серйозність: ([^.]+)\. (.*)$/, (m) => `Severity: ${word(m[1])}. ${translateServer(m[2])}`],
  [/^(.+?): (.+)\. Потрібне термінове рішення\.$/, (m) => `${m[1]}: ${translateServer(m[2])}. Urgent action required.`],
  [/^Несправність без відповіді: (.+)$/, (m) => `Fault without response: ${m[1]}`],
  [/^Несправність (\S+) чекає на відповідь понад (\d+) годин(?:и)?\.(?: Категорія: (\S+)\. Критичність: (\S+)\.)?$/,
    (m) => `Fault ${m[1]} has been waiting for a response for over ${m[2]} hours.` +
      (m[3] ? ` Category: ${word(m[3])}. Severity: ${word(m[4])}.` : '')],
  [/^Несправність (\S+) \((.+)\) не має відповіді понад (\d+) годин(?:и)?! ?(Потрібне термінове втручання\.)?$/,
    (m) => `Fault ${m[1]} (${m[2]}) has had no response for over ${m[3]} hours!${m[4] ? ' Urgent intervention required.' : ''}`],
  [/^Перевитрата пального: (.+)$/, (m) => `Fuel overspend: ${m[1]}`],
  [/^Путівка (\S+): ([\d.]+) л\/100 км при нормі ([\d.]+) л\/100 км \(\+([\d.]+)%\)\.$/,
    (m) => `Waybill ${m[1]}: ${m[2]} l/100 km against a norm of ${m[3]} l/100 km (+${m[4]}%).`],
  [/^Закінчується (страховий поліс|техогляд): (.+)$/, (m) => `${word(m[1]) === m[1] ? m[1] : word(m[1]).charAt(0).toUpperCase() + word(m[1]).slice(1)} expires soon: ${m[2]}`],
  [/^Термін дії спливає через (-?\d+) дн\.$/, (m) => `Expires in ${m[1]} days.`],
  [/^(УВАГА: )?ТО для (.+)$/, (m) => `${m[1] ? 'WARNING: ' : ''}Maintenance for ${m[2]}`],
  [/^Транспорт (.+) потребує технічного обслуговування: (.+)\.$/,
    (m) => `Vehicle ${m[1]} needs maintenance: ${m[2].split(', ').map(translateServer).join(', ')}.`],
  [/^перевищено на (\d+) км$/, (m) => `exceeded by ${m[1]} km`],
  [/^за прогнозом через (\d+) дн\. \(≈(\d+) км\/добу\)$/, (m) => `forecast in ${m[1]} days (≈${m[2]} km/day)`],
  [/^Закінчується запчастина: (.+)$/, (m) => `Part running low: ${word(m[1])}`],
  [/^Залишок: ([\d.]+) (\S+) \(мінімум ([\d.]+)\)\.$/, (m) => `In stock: ${m[1]} ${word(m[2])} (minimum ${m[3]}).`],
  [/^Недостатньо запчастини «(.+)»: на складі ([\d.]+) (\S+), потрібно ([\d.]+)\.$/,
    (m) => `Not enough "${word(m[1])}": ${m[2]} ${word(m[3])} in stock, ${m[4]} required.`],
  [/^Недостатньо запчастини «(.+)»\.$/, (m) => `Not enough "${word(m[1])}".`],
  [/^прострочено на (\d+) днів$/, (m) => `overdue by ${m[1]} days`],
  [/^залишилось (\d+) км$/, (m) => `${m[1]} km left`],
  [/^залишилось (\d+) днів$/, (m) => `${m[1]} days left`],
  [/^(Січ|Лют|Бер|Кві|Тра|Чер|Лип|Сер|Вер|Жов|Лис|Гру) (\d{2})$/, (m) => `${word(m[1])} ${m[2]}`],
  [/^([^→]+) → ([^→]+)$/, (m) => `${word(m[1])} → ${word(m[2])}`],
  [/^ТО: (.+)$/, (m) => `Maint.: ${m[1]}`],
  [/^Рем\.: (.+)$/, (m) => `Rep.: ${m[1]}`],
  [/^Огл\.: (.+)$/, (m) => `Insp.: ${m[1]}`],
  [/^(.*), план: (.+) км$/, (m) => `${m[1]}, planned at: ${m[2]} km`],
  [/^Доступ заборонено\. Потрібна роль: (.+)\.$/, (m) => `Access denied. Required role: ${m[1]}.`],
  [/^Користувач з логіном "(.+)" вже існує\.$/, (m) => `A user with username "${m[1]}" already exists.`],
  [/^Транспорт з номером "(.+)" вже існує\.$/, (m) => `A vehicle with plate "${m[1]}" already exists.`],
  [/^(Звіт|Ремонт|Накладну|Путівку) (\S+) створено\.$/,
    (m) => `${{ 'Звіт': 'Report', 'Ремонт': 'Repair', 'Накладну': 'Invoice', 'Путівку': 'Waybill' }[m[1]]} ${m[2]} created.`],
  [/^Неможливо змінити статус ремонту з «(.+)» на «(.+)»\.$/, (m) => `Cannot change repair status from "${m[1]}" to "${m[2]}".`],
  [/^Недостатньо пального\. Залишок: (.+) л\.$/, (m) => `Not enough fuel. Remaining: ${m[1]} l.`],
  [/^Прочитано (\d+) сповіщень\.$/, (m) => `${m[1]} notifications marked as read.`],
  [/^Перевитрата ([\d.]+)% \(поріг ([\d.]+)%\)$/, (m) => `Overspend ${m[1]}% (threshold ${m[2]}%)`],
  [/^Незначне перевищення ([\d.]+)%$/, (m) => `Slight excess ${m[1]}%`],
  [/^Економія ([\d.]+)%$/, (m) => `Saving ${m[1]}%`],
]

export function translateServer(text) {
  if (lang !== 'en' || typeof text !== 'string' || !CYR.test(text)) return text
  if (Object.prototype.hasOwnProperty.call(en, text)) return en[text]
  for (const [re, fn] of PATTERNS) {
    const m = text.match(re)
    if (m) return fn(m)
  }
  return text
}

// Рекурсивний переклад відповіді API (лише рядкові значення, ключі не змінюються)
export function translateResponse(data) {
  if (lang !== 'en' || data === null || data === undefined) return data
  if (typeof data === 'string') return translateServer(data)
  if (Array.isArray(data)) return data.map(translateResponse)
  if (typeof data === 'object') {
    const out = {}
    for (const [k, v] of Object.entries(data)) out[k] = translateResponse(v)
    return out
  }
  return data
}

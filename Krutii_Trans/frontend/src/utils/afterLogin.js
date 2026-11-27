// Куди перейти після входу: якщо користувач відкрив посилання (наприклад, QR-код путівки), не увійшовши,
// після входу повертаємо його туди, інакше - на головну сторінку ролі.
const KEY = 'krutii-after-login'

export function rememberAfterLogin(path) {
  try { sessionStorage.setItem(KEY, path) } catch (e) { /* ignore */ }
}

export function afterLoginPath(role) {
  let path = null
  try { path = sessionStorage.getItem(KEY); sessionStorage.removeItem(KEY) } catch (e) { /* ignore */ }
  return path && path.startsWith('/w/') ? path : `/${role}`
}

// Без видалення: для перенаправлення вже авторизованого користувача зі сторінки входу
export function peekAfterLogin(role) {
  let path = null
  try { path = sessionStorage.getItem(KEY) } catch (e) { /* ignore */ }
  return path && path.startsWith('/w/') ? path : `/${role}`
}

export function clearAfterLogin() {
  try { sessionStorage.removeItem(KEY) } catch (e) { /* ignore */ }
}

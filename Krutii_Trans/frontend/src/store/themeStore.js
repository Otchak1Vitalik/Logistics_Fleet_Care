import { create } from 'zustand'

const STORAGE_KEY = 'krutii-theme'

function readSavedTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch (e) {
    // localStorage може бути недоступний (приватний режим) - тоді просто світла тема
  }
  return 'light'
}

export function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

// Глобальна тема інтерфейсу (світла / темна), зберігається між сесіями
export const useThemeStore = create((set, get) => ({
  theme: readSavedTheme(),
  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem(STORAGE_KEY, next) } catch (e) { /* ignore */ }
    applyTheme(next)
    set({ theme: next })
  },
}))

// Застосовуємо збережену тему ще до першого рендеру, щоб не було «спалаху» світлої теми
applyTheme(useThemeStore.getState().theme)

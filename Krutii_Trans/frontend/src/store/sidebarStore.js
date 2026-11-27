import { create } from 'zustand'

const STORAGE_KEY = 'krutii-sidebar'

function readSaved() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'collapsed'
  } catch (e) {
    return false
  }
}

export function applySidebar(collapsed) {
  document.documentElement.setAttribute('data-sidebar', collapsed ? 'collapsed' : 'expanded')
}

// Стан бічної панелі (розгорнута / згорнута до іконок), зберігається між сесіями
export const useSidebarStore = create((set, get) => ({
  collapsed: readSaved(),
  toggle: () => {
    const next = !get().collapsed
    try { localStorage.setItem(STORAGE_KEY, next ? 'collapsed' : 'expanded') } catch (e) { /* ignore */ }
    applySidebar(next)
    set({ collapsed: next })
  },
}))

applySidebar(useSidebarStore.getState().collapsed)

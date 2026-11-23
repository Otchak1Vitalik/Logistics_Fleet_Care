import { useLocation } from 'react-router-dom'

// Сторінки несправностей і ремонтів спільні для механіка й керівника:
// базовий шлях визначаємо з поточної адреси, щоб переходи лишалися в розділі своєї ролі.
export function useRoleBase() {
  const { pathname } = useLocation()
  return pathname.startsWith('/manager') ? '/manager' : '/mechanic'
}

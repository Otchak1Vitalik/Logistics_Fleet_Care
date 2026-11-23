import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './styles/index.css'
import './store/themeStore'
import { registerLocale, setDefaultLocale } from 'react-datepicker'
import { uk, enUS } from 'date-fns/locale'
import { lang } from './i18n'

// Календарі вибору дат - мовою інтерфейсу
registerLocale('uk', uk)
registerLocale('en', enUS)
setDefaultLocale(lang)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#333',
            color: '#fff',
          },
          success: {
            style: {
              background: '#22c55e',
            },
          },
          error: {
            style: {
              background: '#ef4444',
            },
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)

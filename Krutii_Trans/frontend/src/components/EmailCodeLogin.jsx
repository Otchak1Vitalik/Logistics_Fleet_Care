import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { tr, lang } from '../i18n'

const LENGTH = 4
const EMPTY = Array(LENGTH).fill('')

const fmt = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`

// Конфеті на canvas: прямокутники різних кольорів падають і обертаються
function Confetti() {
  const ref = useRef(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const w = canvas.offsetWidth
    const h = canvas.offsetHeight
    canvas.width = w * dpr
    canvas.height = h * dpr
    ctx.scale(dpr, dpr)
    const colors = ['#22c55e', '#6366f1', '#f59e0b', '#ec4899', '#06b6d4', '#facc15', '#f97316']
    const parts = Array.from({ length: 130 }, () => ({
      x: w / 2 + (Math.random() - 0.5) * 60,
      y: h * 0.55,
      vx: (Math.random() - 0.5) * 7,
      vy: -Math.random() * 7 - 3.5,
      size: Math.random() * 5 + 4,
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.2,
      color: colors[Math.floor(Math.random() * colors.length)],
    }))
    let frame
    const start = performance.now()
    const tick = (now) => {
      const t = now - start
      ctx.clearRect(0, 0, w, h)
      ctx.globalAlpha = t > 2400 ? Math.max(0, 1 - (t - 2400) / 900) : 1
      parts.forEach((p) => {
        p.vy += 0.12
        p.vx *= 0.99
        p.vy = Math.min(p.vy, 3.2)   // повільне «пурхання» вниз
        p.x += p.vx
        p.y += p.vy
        p.rot += p.vr
        ctx.save()
        ctx.translate(p.x, p.y)
        ctx.rotate(p.rot)
        ctx.fillStyle = p.color
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2)
        ctx.restore()
      })
      if (t < 3300) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [])
  return <canvas ref={ref} className="otp-confetti" aria-hidden="true" />
}

// Вхід за кодом з пошти: логін -> лист з 4-значним кодом -> автоперевірка після 4-ї цифри
function EmailCodeLogin({ onBack }) {
  const navigate = useNavigate()
  const { setLoggedIn } = useAuthStore()

  const [step, setStep] = useState('request')      // request | code | success
  const [username, setUsername] = useState('')
  const [sending, setSending] = useState(false)
  const [info, setInfo] = useState(null)            // { email, mode }
  const [digits, setDigits] = useState(EMPTY)
  const [phase, setPhase] = useState('row')         // row | grid | error
  const [error, setError] = useState('')
  const [expiresIn, setExpiresIn] = useState(0)
  const [resendIn, setResendIn] = useState(0)
  const inputs = useRef([])
  // актуальні цифри в ref: швидкий набір / вставка не залежать від того, чи встиг React перемалювати стан
  const digitsRef = useRef(EMPTY)
  const busy = useRef(false)
  const updateDigits = (arr) => { digitsRef.current = arr; setDigits(arr) }

  // таймери терміну дії і повторного надсилання
  useEffect(() => {
    if (step !== 'code') return undefined
    const id = setInterval(() => {
      setExpiresIn((s) => Math.max(0, s - 1))
      setResendIn((s) => Math.max(0, s - 1))
    }, 1000)
    return () => clearInterval(id)
  }, [step])

  const focus = (i) => setTimeout(() => inputs.current[i]?.focus(), 0)
  const focusNow = (i) => inputs.current[i]?.focus()

  const sendCode = async (e) => {
    e?.preventDefault()
    if (!username.trim()) { setError(tr("Введіть логін.")); return }
    setSending(true)
    setError('')
    try {
      const res = await authApi.requestEmailCode(username.trim(), lang)
      setInfo({ email: res.data.email, mode: res.data.mode })
      setExpiresIn(res.data.expires_in)
      setResendIn(res.data.resend_in)
      updateDigits(EMPTY)
      busy.current = false
      setPhase('row')
      setStep('code')
      focus(0)
    } catch (err) {
      setError(err.response?.data?.error || tr("Сталася помилка"))
      if (err.response?.data?.retry_after) setResendIn(err.response.data.retry_after)
    }
    setSending(false)
  }

  const verify = async (code) => {
    setPhase('grid')
    setError('')
    const started = Date.now()
    let result
    try {
      const res = await authApi.verifyEmailCode(username.trim(), code)
      result = { ok: true, user: res.data.user }
    } catch (err) {
      result = { ok: false, error: err.response?.data?.error || tr("Сталася помилка"), reason: err.response?.data?.reason }
    }
    // даємо анімації «замка» відпрацювати: клітинки з'їжджаються, лінії малюються по колу
    await new Promise((r) => setTimeout(r, Math.max(0, 1900 - (Date.now() - started))))
    if (result.ok) {
      setPhase('ok')                                         // квадрат загоряється зеленим
      await new Promise((r) => setTimeout(r, 800))
      setStep('success')
      setTimeout(() => {
        setLoggedIn(result.user)
        navigate(`/${result.user.role}`)
      }, 3200)
    } else {
      setPhase('error')
      setError(result.error)
      setTimeout(() => {
        updateDigits(EMPTY)
        busy.current = false
        setPhase('row')
        if (result.reason === 'wrong') focus(0)
      }, 650)
      if (result.reason && result.reason !== 'wrong') setExpiresIn(0)
    }
  }

  const setDigit = (i, value) => {
    if (busy.current) return
    const cur = digitsRef.current
    let clean = value.replace(/\D/g, '')
    if (!clean) {
      updateDigits(cur.map((x, k) => (k === i ? '' : x)))
      return
    }
    // друк у вже заповнену клітинку замінює її цифру
    if (clean.length > 1 && cur[i] && clean.startsWith(cur[i])) clean = clean.slice(1)
    // вставка або автозаповнення кількох цифр
    const next = [...cur]
    clean.slice(0, LENGTH - i).split('').forEach((ch, k) => { next[i + k] = ch })
    updateDigits(next)
    const filled = next.findIndex((x) => !x)
    if (filled === -1) {
      busy.current = true
      inputs.current.forEach((el) => el?.blur())
      verify(next.join(''))
    } else {
      focusNow(Math.max(Math.min(i + clean.length, LENGTH - 1), filled))
    }
  }

  const onKeyDown = (i, e) => {
    if (e.key === 'Backspace' && !digitsRef.current[i] && i > 0) {
      e.preventDefault()
      updateDigits(digitsRef.current.map((x, k) => (k === i - 1 ? '' : x)))
      focusNow(i - 1)
    } else if (e.key === 'ArrowLeft' && i > 0) focus(i - 1)
    else if (e.key === 'ArrowRight' && i < LENGTH - 1) focus(i + 1)
  }

  const onPaste = (i, e) => {
    const text = e.clipboardData.getData('text')
    if (/\d/.test(text)) {
      e.preventDefault()
      setDigit(i, text)
    }
  }

  if (step === 'success') {
    return (
      <div className="otp-screen otp-success">
        <Confetti />
        <h2>{tr("Вхід підтверджено!")}</h2>
        <p className="otp-sub">{tr("Особу підтверджено. Переходимо в систему...")}</p>
        <div className="otp-check">
          <svg viewBox="0 0 52 52"><polyline points="15 27 23 35 38 18" /></svg>
        </div>
      </div>
    )
  }

  if (step === 'request') {
    return (
      <form className="otp-screen" onSubmit={sendCode}>
        <div className="otp-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <polyline points="22 6 12 13 2 6" />
          </svg>
        </div>
        <h2>{tr("Вхід за кодом з пошти")}</h2>
        <p className="otp-sub">{tr("Введіть логін - ми надішлемо 4-значний код на пошту, вказану у вашому профілі.")}</p>
        <div className="form-field">
          <label htmlFor="otp-username">{tr("Логін")}</label>
          <input id="otp-username" className="form-control" value={username} autoFocus autoComplete="username"
            onChange={(e) => setUsername(e.target.value)} placeholder={tr("Введіть логін")} />
        </div>
        {error && <div className="otp-error" role="alert">{error}</div>}
        <button type="submit" className="btn btn-primary btn-block" disabled={sending}>
          {sending ? tr("Надсилаємо...") : tr("Надіслати код")}
        </button>
        <button type="button" className="otp-back" onClick={onBack}>← {tr("Увійти за паролем")}</button>
      </form>
    )
  }

  const expired = expiresIn <= 0
  return (
    <div className="otp-screen">
      <h2>{tr("Підтвердіть вхід")}</h2>
      <p className="otp-sub">
        {tr("Введіть 4-значний код, надісланий на")} <b>{info?.email}</b>.<br />
        {tr("Перевірка почнеться автоматично.")}
      </p>

      <div className={`otp-boxes ${phase}`}>
        {digits.map((d, i) => (
          <input key={i} ref={(el) => { inputs.current[i] = el }} className={`otp-cell c${i}`}
            value={d} inputMode="numeric" autoComplete={i === 0 ? 'one-time-code' : 'off'} maxLength={LENGTH}
            aria-label={tr("Цифра {0}", i + 1)} disabled={expired} readOnly={phase !== 'row'}
            onChange={(e) => setDigit(i, e.target.value)} onKeyDown={(e) => onKeyDown(i, e)}
            onPaste={(e) => onPaste(i, e)} onFocus={(e) => e.target.select()} />
        ))}
        <span className="otp-link h top" /><span className="otp-link h bottom" />
        <span className="otp-link v left" /><span className="otp-link v right" />
      </div>

      <div className="otp-status" aria-live="polite">
        {error ? <span className="otp-error">{error}</span>
          : phase === 'ok' ? <span className="otp-ok-text">{tr("Код правильний!")}</span>
          : phase === 'grid' ? <span>{tr("Перевіряємо код...")}</span>
            : expired ? <span className="otp-error">{tr("Термін дії коду минув. Надішліть новий код.")}</span>
              : <span>{tr("Код дійсний ще")} <b>{fmt(expiresIn)}</b></span>}
      </div>

      {info?.mode === 'demo' && (
        <div className="otp-demo">{tr("Демо-режим: пошту не налаштовано, код виведено у вікні Backend.")}</div>
      )}

      <p className="otp-resend">
        {tr("Не отримали код?")}{' '}
        <button type="button" onClick={sendCode} disabled={resendIn > 0 || sending}>
          {resendIn > 0 ? tr("Надіслати ще раз через {0} с", resendIn) : tr("Надіслати ще раз")}
        </button>
      </p>
      <button type="button" className="otp-back" onClick={() => { setStep('request'); setError('') }}>← {tr("Змінити логін")}</button>
    </div>
  )
}

export default EmailCodeLogin

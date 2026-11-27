import { useState } from 'react'
import toast from 'react-hot-toast'
import { tr } from '../i18n'

// Дві дії з PDF путівного листа: переглянути / надрукувати в новій вкладці та одразу завантажити файл
function WaybillPdfButton({ id }) {
  const [state, setState] = useState('idle')   // idle -> busy -> done

  const download = async () => {
    if (state !== 'idle') return
    setState('busy')
    const started = Date.now()
    try {
      const res = await fetch(`/api/waybills/${id}/pdf?download=1`, { credentials: 'include' })
      if (!res.ok) throw new Error(String(res.status))
      const blob = await res.blob()
      const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '')?.[1] || 'putivka.pdf'
      // коротка пауза, щоб анімація «стрілка вниз» встигла відпрацювати
      await new Promise((r) => setTimeout(r, Math.max(0, 650 - (Date.now() - started))))
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = name
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      setState('done')
      setTimeout(() => setState('idle'), 2200)
    } catch (e) {
      setState('idle')
      toast.error(tr("Не вдалося завантажити PDF"))
    }
  }

  return (
    <>
      <a className="btn btn-secondary" href={`/api/waybills/${id}/pdf`} target="_blank" rel="noopener noreferrer"
        title={tr("Подорожній лист для друку (за зразком типової форми № 1)")}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 6 2 18 2 18 9" />
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
          <rect x="6" y="14" width="12" height="8" />
        </svg>
        {tr("Друк путівки (PDF)")}
      </a>
      <button type="button" className={`btn btn-secondary btn-export ${state}`} onClick={download}
        disabled={state === 'busy'} title={tr("Зберегти PDF путівки на комп’ютер")}>
        {state === 'done' ? (
          <svg className="export-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="4 12 10 18 20 6" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <g className="export-arrow">
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </g>
          </svg>
        )}
        <span>{state === 'done' ? tr("Завантажено") : state === 'busy' ? tr("Готуємо файл...") : tr("Завантажити PDF")}</span>
      </button>
    </>
  )
}

export default WaybillPdfButton

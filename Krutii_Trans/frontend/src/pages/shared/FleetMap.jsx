import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts'
import { telematicsApi } from '../../api/telematics'
import { useAuthStore } from '../../store/authStore'
import { useThemeStore } from '../../store/themeStore'
import { useRoleBase } from '../../utils/useRoleBase'
import { formatDate, formatNumber, timeAgo } from '../../utils/formatters'
import ukraine from '../../assets/ukraine.json'
import { tr } from '../../i18n'

const POLL_MS = 5000
const CONN = {
  moving: { label: tr("У русі"), color: '#16a34a' },
  idle: { label: tr("Стоїть"), color: '#f59e0b' },
  offline: { label: tr("Немає зв'язку"), color: '#94a3b8' },
  none: { label: tr("Без трекера"), color: '#cbd5e1' },
}
const ALARMS = {
  overheat: tr("Перегрів двигуна"), low_battery: tr("Низька напруга"), no_waybill: tr("Рух без путівки"),
}
const EVENT_ICONS = { overheat: '🌡', low_battery: '🔋', dtc: '⚠', fuel_drain: '⛽', refuel: '⛽', no_waybill: '🚫' }
const EVENT_LABELS = {
  overheat: tr("Перегрів двигуна"), low_battery: tr("Низька напруга"), dtc: tr("Код помилки"),
  fuel_drain: tr("Злив пального"), refuel: tr("Заправка"), no_waybill: tr("Рух без путівки"),
}
const DTC = {
  P0217: tr("Перегрів двигуна (датчик температури ОР)"), P0300: tr("Пропуски запалювання в циліндрах"),
  P0087: tr("Низький тиск палива в рампі"), P0401: tr("Недостатня рециркуляція відпрацьованих газів (EGR)"),
  P2463: tr("Надмірне накопичення сажі в сажовому фільтрі (DPF)"), P0562: tr("Низька напруга бортової мережі"),
  P0128: tr("Двигун не прогрівається до робочої температури (термостат)"), U0100: tr("Втрата зв’язку з блоком керування двигуном"),
}

function markerIcon(item, selected) {
  const s = item.state || {}
  const color = item.alarms.length ? '#dc2626' : CONN[item.connection].color
  const arrow = item.connection === 'moving'
    ? `<svg viewBox="0 0 24 24" style="transform:rotate(${Math.round(s.heading || 0)}deg)"><path d="M12 3l6 16-6-4-6 4z" fill="#fff"/></svg>`
    : '<span class="fm-dot-inner"></span>'
  return L.divIcon({
    className: '',
    html: `<div class="fm-marker ${item.connection} ${selected ? 'selected' : ''} ${item.alarms.length ? 'alarm' : ''}" style="--c:${color}">${arrow}</div>
           <div class="fm-marker-label ${item.connection === 'moving' || selected || item.alarms.length ? 'always' : ''}">${item.plate}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
}

function Metric({ label, value, warn, sub }) {
  return (
    <div className={`fm-metric ${warn ? 'warn' : ''}`}>
      <span>{label}</span><b>{value}</b>{sub && <small>{sub}</small>}
    </div>
  )
}

function MiniChart({ data, dataKey, color, unit, limit, title }) {
  const theme = useThemeStore((s) => s.theme)
  const axis = theme === 'dark' ? '#9aa4b2' : '#6b7280'
  const grid = theme === 'dark' ? '#263044' : '#eef0f3'
  return (
    <div className="fm-chart">
      <div className="fm-chart-title">{title}</div>
      <ResponsiveContainer width="100%" height={96}>
        <LineChart data={data} margin={{ top: 4, right: 6, bottom: 0, left: -24 }}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} hide />
          <YAxis stroke={axis} fontSize={10} domain={['auto', 'auto']} width={48} />
          <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-gray-200)', borderRadius: 8, fontSize: 12 }}
            labelFormatter={(t) => formatDate(new Date(t), 'HH:mm:ss')} formatter={(v) => [`${v} ${unit}`, title]} />
          {limit && <ReferenceLine y={limit} stroke="#dc2626" strokeDasharray="4 3" />}
          <Line dataKey={dataKey} stroke={color} dot={false} strokeWidth={1.6} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function VehiclePanel({ item, detail, onBack, onProvision, canProvision, base }) {
  const s = item.state || {}
  const w = item.waybill
  const series = (detail?.points || []).map((p) => ({ ...p, t: new Date(p.ts).getTime() }))
  const fuelPct = s.fuel_level != null && item.tank ? s.fuel_level / item.tank : null
  const voltLimit = item.heavy ? 23.0 : 11.6
  return (
    <div className="fm-panel">
      <button className="btn btn-text btn-sm fm-back" onClick={onBack}>← {tr("Усі автомобілі")}</button>
      <div className="fm-panel-head">
        <div>
          <Link to={`${base}/vehicles/${item.vehicle_id}`} className="fm-plate">{item.plate}</Link>
          <div className="text-muted">{item.label.replace(item.plate, '').trim()}</div>
        </div>
        <span className="fm-conn" style={{ '--c': CONN[item.connection].color }}>{CONN[item.connection].label}</span>
      </div>
      {s.ts && <div className="text-muted fm-updated">{tr("Оновлено")} {timeAgo(s.ts)}</div>}

      {item.alarms.length > 0 && (
        <div className="fm-alarms">{item.alarms.map((a) => <span key={a}>{ALARMS[a] || a}</span>)}</div>
      )}

      {w ? (
        <div className="fm-waybill">
          <div><Link to={base === '/manager' ? `/manager/waybills/${w.id}` : '#'}>{w.number}</Link> · {w.from} → {w.to}</div>
          <div className="text-muted">{w.driver || '—'}{w.route_km ? ` · ${tr("{0} км", formatNumber(w.route_km))}` : ''}</div>
        </div>
      ) : <div className="fm-waybill text-muted">{tr("Активної путівки немає")}</div>}

      {item.state ? (
        <>
          <div className="fm-metrics">
            <Metric label={tr("Швидкість")} value={tr("{0} км/год", Math.round(s.speed || 0))} />
            <Metric label={tr("Пальне")} value={s.fuel_level != null ? tr("{0} л", Math.round(s.fuel_level)) : '—'}
              sub={fuelPct != null ? `${Math.round(fuelPct * 100)} %` : null} warn={fuelPct != null && fuelPct < 0.15} />
            <Metric label={tr("Двигун")} value={s.engine_temp != null ? `${Math.round(s.engine_temp)} °C` : '—'} warn={s.engine_temp >= 105} />
            <Metric label={tr("Напруга")} value={s.battery_v != null ? `${formatNumber(s.battery_v, 1)} ${tr("В")}` : '—'} warn={s.battery_v < voltLimit} />
            <Metric label={tr("Одометр")} value={tr("{0} км", formatNumber(Math.round(s.odometer || 0)))} />
            <Metric label={tr("Оберти")} value={s.rpm ? formatNumber(s.rpm) : '0'} />
          </div>
          {s.dtc?.length > 0 && (
            <div className="fm-dtc">
              {s.dtc.map((c) => <div key={c}><b>{c}</b> {DTC[c] || tr("невідомий код")}</div>)}
            </div>
          )}
          {series.length > 1 && (
            <div className="fm-charts">
              <div className="text-muted fm-charts-title">
                {tr("Останні {0} год", detail.hours)}{detail.distance_km ? ` · ${tr("пройдено {0} км", formatNumber(detail.distance_km))}` : ''}
              </div>
              <MiniChart data={series} dataKey="speed" color="#6366f1" unit={tr("км/год")} title={tr("Швидкість")} />
              <MiniChart data={series} dataKey="fuel_level" color="#f59e0b" unit={tr("л")} title={tr("Пальне в баку")} />
              <MiniChart data={series} dataKey="engine_temp" color="#ef4444" unit="°C" limit={105} title={tr("Температура двигуна")} />
            </div>
          )}
          <div className="fm-events">
            <h4>{tr("Події")}</h4>
            {(detail?.events || []).length === 0 ? <div className="text-muted">{tr("Подій немає")}</div> : (
              <ul>
                {detail.events.slice(0, 12).map((e) => (
                  <li key={e._id} className={`fm-ev ${e.type}`}>
                    <span className="fm-ev-icon">{EVENT_ICONS[e.type]}</span>
                    <div><b>{EVENT_LABELS[e.type]}</b> <span className="text-muted">{formatDate(e.ts, 'dd.MM HH:mm')}</span>
                      <div>{tr(e.message)}</div></div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : (
        <div className="fm-empty-vehicle">
          {item.tracker ? tr("Трекер встановлено, але даних ще не надходило.") : tr("Трекер не підключено.")}
        </div>
      )}
      {canProvision && (
        <div className="fm-provision">
          <button className="btn btn-secondary btn-sm" onClick={() => onProvision(item)}>
            {item.tracker ? tr("Новий ключ трекера") : tr("Підключити трекер")}
          </button>
          {item.key_hint && <span className="text-muted">{tr("ключ …{0}", item.key_hint)}</span>}
        </div>
      )}
    </div>
  )
}

function FleetMap() {
  const base = useRoleBase()
  const role = useAuthStore((s) => s.user?.role)
  const mapEl = useRef(null)
  const map = useRef(null)
  const layers = useRef({})
  const markers = useRef({})
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [newKey, setNewKey] = useState(null)

  // карта: контур України і міста видно навіть без інтернету, тайли OpenStreetMap - поверх
  useEffect(() => {
    const m = L.map(mapEl.current, { zoomControl: true, attributionControl: true, minZoom: 5, maxZoom: 17, zoomSnap: 0.25 })
      .setView([48.5, 31.5], 6)
    // підписи машин на стоянці - лише при наближенні, щоб не захаращувати карту країни
    const zoomClass = () => mapEl.current?.classList.toggle('fm-zoomed', m.getZoom() >= 8)
    m.on('zoomend', zoomClass)
    zoomClass()
    const border = L.geoJSON(ukraine, { style: { color: '#6366f1', weight: 1.5, fillColor: '#6366f1', fillOpacity: 0.04 }, interactive: false }).addTo(m)
    m.fitBounds(border.getBounds(), { padding: [10, 10] })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, subdomains: 'abc', attribution: '© OpenStreetMap', opacity: 0.85,
    }).addTo(m)
    layers.current.cities = L.layerGroup().addTo(m)
    layers.current.route = L.layerGroup().addTo(m)
    layers.current.vehicles = L.layerGroup().addTo(m)
    map.current = m
    setTimeout(() => m.invalidateSize(), 50)
    return () => { m.remove(); map.current = null; markers.current = {} }
  }, [])

  // опитування сервера
  useEffect(() => {
    let alive = true
    const load = () => telematicsApi.fleet().then((r) => alive && setData(r.data)).catch(() => {})
    load()
    const id = setInterval(load, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])
  useEffect(() => {
    if (!selected) { setDetail(null); return undefined }
    let alive = true
    const load = () => telematicsApi.vehicle(selected).then((r) => alive && setDetail(r.data)).catch(() => {})
    load()
    const id = setInterval(load, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [selected])

  // міста
  useEffect(() => {
    if (!data || !map.current || layers.current.citiesDone) return
    data.cities.forEach((c) => {
      L.circleMarker([c.lat, c.lon], { radius: c.major ? 3 : 2, color: '#64748b', weight: 1, fillOpacity: 0.8, interactive: false })
        .addTo(layers.current.cities)
      if (c.major) {
        L.marker([c.lat, c.lon], { interactive: false, icon: L.divIcon({ className: 'fm-city', html: c.name, iconSize: [90, 14], iconAnchor: [-5, 7] }) })
          .addTo(layers.current.cities)
      }
    })
    layers.current.citiesDone = true
  }, [data])

  // маркери авто
  useEffect(() => {
    if (!data || !map.current) return
    const seen = new Set()
    data.items.filter((i) => i.state?.lat != null).forEach((i) => {
      seen.add(i.vehicle_id)
      const ll = [i.state.lat, i.state.lon]
      const icon = markerIcon(i, i.vehicle_id === selected)
      let mk = markers.current[i.vehicle_id]
      if (!mk) {
        mk = L.marker(ll, { icon, riseOnHover: true }).addTo(layers.current.vehicles)
        mk.on('click', () => setSelected(i.vehicle_id))
        markers.current[i.vehicle_id] = mk
      } else {
        mk.setLatLng(ll)
        mk.setIcon(icon)
      }
      mk.setZIndexOffset(i.vehicle_id === selected ? 1000 : i.alarms.length ? 500 : 0)
    })
    Object.keys(markers.current).forEach((id) => {
      if (!seen.has(id)) { markers.current[id].remove(); delete markers.current[id] }
    })

  }, [data, selected])

  // маршрут і трек обраного авто
  useEffect(() => {
    const g = layers.current.route
    if (!g) return
    g.clearLayers()
    const item = data?.items.find((i) => i.vehicle_id === selected)
    if (!item) return
    if (item.waybill?.route) {
      L.polyline(item.waybill.route, { color: '#6366f1', weight: 3, opacity: 0.5, dashArray: '6 8' }).addTo(g)
    }
    const track = (detail?.points || []).map((p) => [p.lat, p.lon])
    if (track.length > 1) L.polyline(track, { color: '#16a34a', weight: 4, opacity: 0.85 }).addTo(g)
  }, [selected, detail, data])

  const select = (id) => {
    setSelected(id)
    const item = data?.items.find((i) => i.vehicle_id === id)
    if (item?.state && map.current) {
      const pts = [[item.state.lat, item.state.lon], ...(item.waybill?.route || [])]
      if (pts.length > 1) map.current.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 9 })
      else map.current.setView(pts[0], 8)
    }
  }

  const provision = async (item) => {
    try {
      const r = await telematicsApi.provision(item.vehicle_id)
      setNewKey({ plate: item.plate, key: r.data.key })
    } catch { /* interceptor */ }
  }

  const items = useMemo(() => {
    const list = (data?.items || []).filter((i) =>
      (filter === 'all' || (filter === 'alarm' ? i.alarms.length > 0 : i.connection === filter))
      && (!query || `${i.label} ${i.waybill?.driver || ''}`.toLowerCase().includes(query.toLowerCase())))
    const order = { moving: 0, idle: 1, offline: 2, none: 3 }
    return list.sort((a, b) => (b.alarms.length - a.alarms.length) || (order[a.connection] - order[b.connection]) || a.plate.localeCompare(b.plate))
  }, [data, filter, query])

  const current = data?.items.find((i) => i.vehicle_id === selected)
  const s = data?.summary
  const noData = data && !data.items.some((i) => i.state)

  return (
    <div className="page-container fm-page">
      <div className="page-header">
        <div>
          <h1>{tr("Карта автопарку")}</h1>
          <p className="text-muted">{tr("Положення і стан автомобілів за даними GPS-трекерів. Оновлюється кожні 5 секунд.")}</p>
        </div>
      </div>
      {s && (
        <div className="fm-summary">
          {[['all', tr("Усі"), data.items.length], ['moving', CONN.moving.label, s.moving], ['idle', CONN.idle.label, s.idle],
            ['offline', CONN.offline.label, s.offline], ['none', CONN.none.label, s.none], ['alarm', tr("Тривоги"), s.alarms]].map(([k, l, n]) => (
            <button key={k} className={`fm-chip ${filter === k ? 'active' : ''} ${k === 'alarm' && n ? 'danger' : ''}`} onClick={() => setFilter(k)}>
              {k !== 'all' && k !== 'alarm' && <i style={{ background: CONN[k].color }} />}{l} <b>{n}</b>
            </button>
          ))}
        </div>
      )}
      {noData && (
        <div className="pm-warn fm-hint">
          {tr("Даних телематики ще немає. Щоб побачити автомобілі на карті, запустіть симулятор трекерів у папці backend:")}{' '}
          <code>venv\Scripts\python.exe simulator.py</code>
        </div>
      )}
      <div className="fm-layout">
        <div className="fm-map card" ref={mapEl} />
        <div className="fm-side card">
          {current ? (
            <VehiclePanel item={current} detail={detail} base={base} onBack={() => setSelected(null)}
              onProvision={provision} canProvision={role === 'manager'} />
          ) : (
            <>
              <input type="search" className="form-control" placeholder={tr("Пошук: номер, модель, водій")} value={query}
                onChange={(e) => setQuery(e.target.value)} />
              <ul className="fm-list">
                {items.map((i) => {
                  const st = i.state || {}
                  const pct = st.fuel_level != null && i.tank ? Math.min(1, st.fuel_level / i.tank) : null
                  return (
                    <li key={i.vehicle_id} onClick={() => select(i.vehicle_id)} className={i.alarms.length ? 'alarm' : ''}>
                      <span className="fm-dot" style={{ background: i.alarms.length ? '#dc2626' : CONN[i.connection].color }} />
                      <div className="fm-li-main">
                        <div className="fm-li-top"><b>{i.plate}</b>
                          <span className="text-muted">{i.connection === 'moving' ? tr("{0} км/год", Math.round(st.speed)) : CONN[i.connection].label}</span></div>
                        <div className="text-muted fm-li-sub">
                          {i.alarms.length ? <span className="fm-li-alarm">{i.alarms.map((a) => ALARMS[a]).join(', ')}</span>
                            : i.waybill ? `${i.waybill.from} → ${i.waybill.to}` : i.label.replace(i.plate, '').trim()}
                        </div>
                        {pct != null && <div className="fm-fuel"><span style={{ width: `${pct * 100}%` }} className={pct < 0.15 ? 'low' : ''} /></div>}
                      </div>
                    </li>
                  )
                })}
                {items.length === 0 && <li className="fm-none text-muted">{tr("Автомобілів не знайдено")}</li>}
              </ul>
            </>
          )}
        </div>
      </div>
      {newKey && (
        <div className="modal-overlay" onClick={() => setNewKey(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header"><h3>{tr("Ключ трекера: {0}", newKey.plate)}</h3>
              <button className="modal-close" onClick={() => setNewKey(null)}>&times;</button></div>
            <div className="modal-body">
              <p>{tr("Вкажіть цей ключ у налаштуваннях трекера (заголовок X-Device-Key). Повторно він не показується.")}</p>
              <pre className="pm-code fm-key">{newKey.key}</pre>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => { navigator.clipboard?.writeText(newKey.key); toast.success(tr("Скопійовано")) }}>{tr("Копіювати")}</button>
              <button className="btn btn-primary" onClick={() => setNewKey(null)}>{tr("Готово")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default FleetMap

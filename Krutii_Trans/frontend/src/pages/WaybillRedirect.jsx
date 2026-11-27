import { useEffect } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { rememberAfterLogin, clearAfterLogin } from '../utils/afterLogin'
import { tr } from '../i18n'

// Адреса з QR-коду на PDF-путівці: /w/<id> -> картка путівки відповідно до ролі
function WaybillRedirect() {
  const { id } = useParams()
  const { isAuthenticated, user } = useAuthStore()
  const role = isAuthenticated ? user?.role : null

  useEffect(() => {
    if (role) clearAfterLogin()
    if (role === 'mechanic') toast(tr("Картку путівки переглядають керівник і водій. PDF путівки доступний і механіку."))
  }, [role])

  if (!role) {
    rememberAfterLogin(`/w/${id}`)
    return <Navigate to="/login" replace />
  }
  if (role === 'manager') return <Navigate to={`/manager/waybills/${id}`} replace />
  if (role === 'driver') return <Navigate to={`/driver/waybills/${id}`} replace />
  return <Navigate to={`/${role}`} replace />
}

export default WaybillRedirect

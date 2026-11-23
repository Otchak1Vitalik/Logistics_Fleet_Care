import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { usersApi } from '../../api/users'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'

const ROLES = {
  manager: 'Керівник',
  mechanic: 'Механік',
  driver: 'Водій'
}

function ManagerUsers() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  const roleFilter = searchParams.get('role') || ''
  const activeFilter = searchParams.get('is_active') || ''

  useEffect(() => {
    loadUsers()
  }, [roleFilter, activeFilter])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const params = {}
      if (roleFilter) params.role = roleFilter
      if (activeFilter) params.is_active = activeFilter

      const response = await usersApi.getAll(params)
      setUsers(response.data.users)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      key: 'full_name',
      label: "Ім'я",
      render: (_, row) => (
        <div>
          <div className="font-medium">{row.full_name}</div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {row.username}
          </div>
        </div>
      )
    },
    {
      key: 'role',
      label: 'Роль',
      render: (role) => ROLES[role] || role
    },
    {
      key: 'phone',
      label: 'Телефон'
    },
    {
      key: 'email',
      label: 'Email'
    },
    {
      key: 'is_active',
      label: 'Статус',
      render: (isActive) => (
        <StatusBadge status={isActive ? 'active' : 'decommissioned'} />
      )
    }
  ]

  const handleFilterChange = (key, value) => {
    const params = new URLSearchParams(searchParams)
    if (value) {
      params.set(key, value)
    } else {
      params.delete(key)
    }
    setSearchParams(params)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Користувачі</h1>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/manager/users/new')}
        >
          Додати користувача
        </button>
      </div>

      {/* Фільтри */}
      <div className="filters">
        <div className="filter-group">
          <label>Роль</label>
          <select
            className="form-control"
            value={roleFilter}
            onChange={(e) => handleFilterChange('role', e.target.value)}
          >
            <option value="">Всі ролі</option>
            <option value="manager">Керівник</option>
            <option value="mechanic">Механік</option>
            <option value="driver">Водій</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Статус</label>
          <select
            className="form-control"
            value={activeFilter}
            onChange={(e) => handleFilterChange('is_active', e.target.value)}
          >
            <option value="">Всі</option>
            <option value="true">Активні</option>
            <option value="false">Неактивні</option>
          </select>
        </div>
      </div>

      {/* Таблиця */}
      <div className="card">
        <DataTable
          columns={columns}
          data={users}
          isLoading={loading}
          onRowClick={(row) => navigate(`/manager/users/${row._id}`)}
          emptyMessage="Користувачів не знайдено"
        />
      </div>
    </div>
  )
}

export default ManagerUsers

function FormField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  error,
  options, // Для select
  rows, // Для textarea
  min,
  max,
  step
}) {
  const handleChange = (e) => {
    let val = e.target.value
    if (type === 'number' && val !== '') {
      val = parseFloat(val)
    }
    onChange(name, val)
  }

  const inputProps = {
    id: name,
    name,
    value: value ?? '',
    onChange: handleChange,
    placeholder,
    required,
    disabled,
    className: `form-control ${error ? 'error' : ''}`
  }

  let input

  if (type === 'select') {
    input = (
      <select {...inputProps}>
        <option value="">{placeholder || 'Оберіть...'}</option>
        {options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    )
  } else if (type === 'textarea') {
    input = <textarea {...inputProps} rows={rows || 4} />
  } else if (type === 'checkbox') {
    input = (
      <label className="checkbox-label">
        <input
          type="checkbox"
          id={name}
          name={name}
          checked={value || false}
          onChange={(e) => onChange(name, e.target.checked)}
          disabled={disabled}
        />
        <span>{placeholder}</span>
      </label>
    )
  } else {
    input = (
      <input {...inputProps} type={type} min={min} max={max} step={step} />
    )
  }

  return (
    <div className="form-field">
      {label && type !== 'checkbox' && (
        <label htmlFor={name}>
          {label}
          {required && <span className="required">*</span>}
        </label>
      )}
      {input}
      {error && <span className="field-error">{error}</span>}
    </div>
  )
}

export default FormField

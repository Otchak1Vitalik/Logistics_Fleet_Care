function Loader({ size = 'medium', text }) {
  return (
    <div className={`loader-container loader-${size}`}>
      <div className="loader"></div>
      {text && <span className="loader-text">{text}</span>}
    </div>
  )
}

export default Loader

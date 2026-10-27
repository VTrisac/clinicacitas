// Mensajes de carga, error y lista vacía reutilizables.
export function Cargando({ texto = 'Cargando…' }) {
  return <p className="estado" aria-busy="true">{texto}</p>
}

export function Error({ mensaje, onReintentar }) {
  return (
    <div className="aviso aviso--error" role="alert">
      {mensaje}
      {onReintentar && <button className="enlace" onClick={onReintentar}>Reintentar</button>}
    </div>
  )
}

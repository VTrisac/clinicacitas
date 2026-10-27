import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Cargando, Error } from './Estado.jsx'

export default function ElegirServicio({ onElegir }) {
  const [servicios, setServicios] = useState(null)
  const [error, setError] = useState('')

  function cargar() {
    setError('')
    api.servicios().then(setServicios).catch((e) => setError(e.message))
  }
  useEffect(cargar, [])

  if (error) return <Error mensaje={error} onReintentar={cargar} />
  if (!servicios) return <Cargando />

  return (
    <section className="panel">
      <h2>¿Qué necesitas?</h2>
      <div className="opciones">
        {servicios.map((s) => (
          <button key={s.id} className="opcion" onClick={() => onElegir(s)}>
            <strong>{s.nombre}</strong>
            {s.descripcion && <span>{s.descripcion}</span>}
            <span className="opcion__meta">{s.duracion_min} min · {Number(s.precio).toFixed(2)} €</span>
          </button>
        ))}
      </div>
    </section>
  )
}

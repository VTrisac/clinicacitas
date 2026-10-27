import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Cargando, Error } from './Estado.jsx'

const iniciales = (nombre) => nombre.split(' ').slice(0, 2).map((p) => p[0]).join('')

export default function ElegirProfesional({ servicio, onElegir }) {
  const [profesionales, setProfesionales] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.profesionales(servicio.id).then(setProfesionales).catch((e) => setError(e.message))
  }, [servicio.id])

  if (error) return <Error mensaje={error} />
  if (!profesionales) return <Cargando />

  return (
    <section className="panel">
      <h2>¿Con quién?</h2>
      {profesionales.length === 0 && <p className="estado">Ahora mismo nadie ofrece este servicio.</p>}
      <div className="opciones">
        {profesionales.map((p) => (
          <button key={p.id} className="opcion opcion--persona" onClick={() => onElegir(p)}>
            <span className="avatar" style={{ background: p.color }}>{iniciales(p.nombre)}</span>
            <span><strong>{p.nombre}</strong><span>{p.especialidad}</span></span>
          </button>
        ))}
      </div>
    </section>
  )
}

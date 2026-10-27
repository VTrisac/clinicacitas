import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { formatoLargo } from '../fechas.js'
import { Cargando, Error } from './Estado.jsx'

export default function MisCitas({ onReservar }) {
  const [citas, setCitas] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  function cargar() {
    api.misCitas().then(setCitas).catch((e) => setError(e.message))
  }
  useEffect(cargar, [])

  async function cancelar(cita) {
    if (!window.confirm(`¿Cancelar la cita de ${cita.servicio_nombre} del ${formatoLargo(cita.inicio)}?`)) return
    setError('')
    try {
      await api.cancelar(cita.id)
      setAviso('Cita cancelada.')
      cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  if (!citas && !error) return <Cargando />
  const ahora = new Date()
  const proximas = (citas || []).filter((c) => new Date(c.inicio) >= ahora && c.estado !== 'cancelada').reverse()
  const pasadas = (citas || []).filter((c) => !proximas.includes(c))

  return (
    <section className="panel">
      {aviso && <p className="aviso aviso--ok" role="status">{aviso}</p>}
      {error && <Error mensaje={error} />}
      <h2>Próximas</h2>
      {proximas.length === 0 ? (
        <p className="estado">No tienes citas próximas. <button className="enlace" onClick={onReservar}>Reservar una</button></p>
      ) : (
        <ul className="citas">
          {proximas.map((c) => (
            <li key={c.id} className="cita">
              <div>
                <strong>{formatoLargo(c.inicio)}</strong>
                <span>{c.servicio_nombre} con {c.profesional_nombre}</span>
              </div>
              {c.cancelable
                ? <button className="boton boton--peligro" onClick={() => cancelar(c)}>Cancelar</button>
                : <span className="muted">Para cancelar, llama a la clínica</span>}
            </li>
          ))}
        </ul>
      )}
      {pasadas.length > 0 && (
        <>
          <h2>Historial</h2>
          <ul className="citas citas--pasadas">
            {pasadas.map((c) => (
              <li key={c.id} className="cita">
                <div><strong>{formatoLargo(c.inicio)}</strong><span>{c.servicio_nombre} con {c.profesional_nombre}</span></div>
                <span className={`etiqueta etiqueta--${c.estado}`}>{c.estado_texto}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

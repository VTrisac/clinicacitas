import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { aISO, formatoDia, hora, lunesDe, sumarDias } from '../fechas.js'
import { Cargando, Error } from './Estado.jsx'

// Semana de lunes a domingo con los huecos libres que calcula el backend.
export default function Calendario({ servicio, profesional, onElegir }) {
  const lunesActual = lunesDe(new Date())
  const [lunes, setLunes] = useState(lunesActual)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let vigente = true
    setDatos(null)
    setError('')
    api.huecos(profesional.id, servicio.id, aISO(lunes))
      .then((d) => { if (vigente) setDatos(d) })
      .catch((e) => { if (vigente) setError(e.message) })
    return () => { vigente = false } // si se cambia de semana rápido, se ignora la respuesta vieja
  }, [lunes, profesional.id, servicio.id])

  const hayAnterior = lunes > lunesActual
  const haySiguiente = !datos || sumarDias(lunes, 7) <= new Date(datos.ultimo_dia)
  const totalHuecos = datos ? datos.dias.reduce((n, d) => n + d.huecos.length, 0) : 0

  return (
    <section className="panel">
      <div className="calendario__cabecera">
        <h2>Elige día y hora</h2>
        <div className="calendario__nav">
          <button className="boton boton--secundario" disabled={!hayAnterior} onClick={() => setLunes(sumarDias(lunes, -7))} aria-label="Semana anterior">←</button>
          <span>Semana del {formatoDia(aISO(lunes))}</span>
          <button className="boton boton--secundario" disabled={!haySiguiente} onClick={() => setLunes(sumarDias(lunes, 7))} aria-label="Semana siguiente">→</button>
        </div>
      </div>
      <p className="muted">{servicio.nombre} ({servicio.duracion_min} min) con {profesional.nombre}</p>

      {error && <Error mensaje={error} />}
      {!datos && !error && <Cargando texto="Buscando huecos libres…" />}
      {datos && (
        <>
          <div className="semana">
            {datos.dias.map((d) => (
              <div key={d.fecha} className="dia">
                <h3>{formatoDia(d.fecha)}</h3>
                {d.huecos.length === 0
                  ? <p className="dia__vacio">—</p>
                  : d.huecos.map((h) => (
                    <button key={h} className="hueco" onClick={() => onElegir(h)}>{hora(h)}</button>
                  ))}
              </div>
            ))}
          </div>
          {totalHuecos === 0 && <p className="estado">No quedan huecos esta semana. Prueba con la siguiente.</p>}
        </>
      )}
    </section>
  )
}

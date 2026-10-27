import { useState } from 'react'
import { api } from '../api.js'
import { formatoLargo } from '../fechas.js'
import { Cargando, Error } from './Estado.jsx'

export default function Confirmar({ usuario, servicio, profesional, hueco, loginUrl, registroUrl, onReservada, onCambiarHora }) {
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function confirmar() {
    setEnviando(true)
    setError('')
    try {
      const cita = await api.reservar({ profesional: profesional.id, servicio: servicio.id, inicio: hueco })
      onReservada(cita)
    } catch (e) {
      setError(e.message)
      setEnviando(false)
    }
  }

  return (
    <section className="panel">
      <h2>Confirma tu cita</h2>
      <dl className="resumen">
        <dt>Servicio</dt><dd>{servicio.nombre} · {servicio.duracion_min} min · {Number(servicio.precio).toFixed(2)} €</dd>
        <dt>Profesional</dt><dd>{profesional.nombre}</dd>
        <dt>Fecha</dt><dd>{formatoLargo(hueco)}</dd>
      </dl>

      {error && <Error mensaje={error} />}

      {!usuario ? <Cargando /> : usuario.puede_reservar ? (
        <div className="acciones">
          <button className="boton" onClick={confirmar} disabled={enviando}>{enviando ? 'Reservando…' : 'Confirmar reserva'}</button>
          <button className="boton boton--secundario" onClick={onCambiarHora} disabled={enviando}>Cambiar hora</button>
        </div>
      ) : usuario.autenticado ? (
        <p className="aviso">Estás conectado como personal de la clínica. Para dar citas a pacientes usa la pantalla de Recepción.</p>
      ) : (
        <div className="aviso">
          Para reservar necesitas una cuenta. <a href={loginUrl}>Inicia sesión</a> o <a href={registroUrl}>crea una cuenta</a>; tardas un minuto.
        </div>
      )}
    </section>
  )
}

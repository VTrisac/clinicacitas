import { useEffect, useState } from 'react'
import { api } from './api.js'
import Pasos from './components/Pasos.jsx'
import ElegirServicio from './components/ElegirServicio.jsx'
import ElegirProfesional from './components/ElegirProfesional.jsx'
import Calendario from './components/Calendario.jsx'
import Confirmar from './components/Confirmar.jsx'
import MisCitas from './components/MisCitas.jsx'

const PASOS = ['Servicio', 'Profesional', 'Día y hora', 'Confirmar']

export default function App({ loginUrl, registroUrl }) {
  const [usuario, setUsuario] = useState(null)
  const [pestana, setPestana] = useState('reservar')
  const [paso, setPaso] = useState(0)
  const [servicio, setServicio] = useState(null)
  const [profesional, setProfesional] = useState(null)
  const [hueco, setHueco] = useState(null)
  const [reservada, setReservada] = useState(null)

  useEffect(() => {
    api.yo().then(setUsuario).catch(() => setUsuario({ autenticado: false }))
  }, [])

  function volverA(n) {
    setPaso(n)
    if (n < 3) setHueco(null)
    if (n < 2) setProfesional(null)
    if (n < 1) setServicio(null)
  }

  function empezarDeNuevo() {
    setReservada(null)
    volverA(0)
  }

  return (
    <div className="reserva">
      <div className="reserva__cabecera">
        <h1>{pestana === 'reservar' ? 'Reservar cita' : 'Mis citas'}</h1>
        {usuario?.puede_reservar && (
          <div className="tabs" role="tablist">
            <button role="tab" aria-selected={pestana === 'reservar'} onClick={() => setPestana('reservar')}>Reservar</button>
            <button role="tab" aria-selected={pestana === 'citas'} onClick={() => setPestana('citas')}>Mis citas</button>
          </div>
        )}
      </div>

      {pestana === 'citas' ? (
        <MisCitas onReservar={() => { setPestana('reservar'); empezarDeNuevo() }} />
      ) : reservada ? (
        <section className="panel exito" aria-live="polite">
          <h2>¡Cita reservada!</h2>
          <p><strong>{reservada.servicio_nombre}</strong> con {reservada.profesional_nombre}</p>
          <p className="exito__fecha">{new Intl.DateTimeFormat('es-ES', { dateStyle: 'full', timeStyle: 'short' }).format(new Date(reservada.inicio))}</p>
          <div className="acciones">
            <button className="boton" onClick={() => setPestana('citas')}>Ver mis citas</button>
            <button className="boton boton--secundario" onClick={empezarDeNuevo}>Reservar otra</button>
          </div>
        </section>
      ) : (
        <>
          <Pasos pasos={PASOS} actual={paso} onIr={volverA} />
          {paso === 0 && <ElegirServicio onElegir={(s) => { setServicio(s); setPaso(1) }} />}
          {paso === 1 && <ElegirProfesional servicio={servicio} onElegir={(p) => { setProfesional(p); setPaso(2) }} />}
          {paso === 2 && <Calendario servicio={servicio} profesional={profesional} onElegir={(h) => { setHueco(h); setPaso(3) }} />}
          {paso === 3 && (
            <Confirmar
              usuario={usuario} servicio={servicio} profesional={profesional} hueco={hueco}
              loginUrl={loginUrl} registroUrl={registroUrl}
              onReservada={setReservada} onCambiarHora={() => volverA(2)}
            />
          )}
        </>
      )}
    </div>
  )
}

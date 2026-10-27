// Indicador de pasos. Se puede volver a un paso anterior pulsándolo.
export default function Pasos({ pasos, actual, onIr }) {
  return (
    <ol className="pasos">
      {pasos.map((nombre, i) => (
        <li key={nombre} className={i === actual ? 'activo' : i < actual ? 'hecho' : ''}>
          {i < actual
            ? <button type="button" onClick={() => onIr(i)}><span>{i + 1}</span>{nombre}</button>
            : <span className="pasos__item" aria-current={i === actual ? 'step' : undefined}><span>{i + 1}</span>{nombre}</span>}
        </li>
      ))}
    </ol>
  )
}

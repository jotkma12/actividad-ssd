import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';
import { addDuration, formatDuration, RESERVATION_DURATIONS } from './reservationTime.js';

const AVAILABILITY_LABELS = {
  available: 'Disponible',
  occupied: 'Ocupado',
  blocked: 'Bloqueado',
};

export default function AvailabilityPage({ session, onBack, onRequest }) {
  const [spaces, setSpaces] = useState([]);
  const [date, setDate] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('30');
  const [results, setResults] = useState([]);
  const [loadingSpaces, setLoadingSpaces] = useState(true);
  const [checking, setChecking] = useState(false);
  const [queried, setQueried] = useState(false);
  const [error, setError] = useState('');
  const end = addDuration(date, startsAt, durationMinutes);

  useEffect(() => {
    let active = true;
    apiRequest('/spaces', { token: session.token })
      .then((result) => { if (active) setSpaces(result.filter((space) => space.is_active)); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoadingSpaces(false); });
    return () => { active = false; };
  }, [session.token]);

  async function checkAvailability(event) {
    event.preventDefault();
    if (!end || end.date !== date) {
      setQueried(false);
      setResults([]);
      setError('La reserva debe terminar el mismo día que inicia.');
      return;
    }
    setChecking(true); setQueried(true); setError(''); setResults([]);
    const start = `${date}T${startsAt}:00`;
    const endDateTime = `${end.date}T${end.time}:00`;
    const checks = await Promise.all(spaces.map(async (space) => {
      const params = new URLSearchParams({ starts_at: start, ends_at: endDateTime });
      try {
        const result = await apiRequest(`/availability/spaces/${space.id}?${params}`, { token: session.token });
        return { space, result, error: '' };
      } catch (requestError) {
        return { space, result: null, error: requestError.message, status: requestError.status };
      }
    }));
    setResults(checks);
    if (checks.every((item) => item.error)) {
      setError(checks[0]?.status === 0
        ? 'No fue posible confirmar la disponibilidad. Revisa la conexión e intenta de nuevo.'
        : checks[0]?.error ?? 'No fue posible consultar disponibilidad.');
    }
    else if (checks.some((item) => item.error)) {
      setError('No fue posible confirmar la disponibilidad de uno o más espacios. Revisa los resultados marcados y vuelve a consultar.');
    }
    setChecking(false);
  }

  return (
    <main className="dashboard-content availability-page">
      <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
      <header className="page-heading"><div><p className="eyebrow">Consulta de horarios</p><h1>Disponibilidad</h1>
        <p>Los resultados se consultan al servicio para cada espacio activo.</p></div></header>
      {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
      <section className="availability-search" aria-labelledby="availability-search-title">
        <h2 id="availability-search-title">Elige un intervalo</h2>
        <form className="availability-form" onSubmit={checkAvailability}>
          <label>Fecha<input aria-label="Fecha de consulta" required type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
          <label>Hora de inicio<input aria-label="Hora de inicio" required step="60" type="time" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label>
          <label>Duración<select aria-label="Duración de la reserva" onChange={(event) => setDurationMinutes(event.target.value)} value={durationMinutes}>{RESERVATION_DURATIONS.map((minutes) => <option key={minutes} value={minutes}>{formatDuration(minutes)}</option>)}</select></label>
          <p className="selected-interval" aria-live="polite">{end ? `Fin calculado: ${end.time}` : 'Elige la hora de inicio para calcular el fin.'}</p>
          <button className="primary-button" disabled={checking || loadingSpaces || spaces.length === 0} type="submit">
            {checking ? 'Consultando…' : 'Consultar disponibilidad'}
          </button>
        </form>
        <p className="policy-hint">La zona horaria de la consulta es America/Bogota. Las reglas de fecha y horario las valida el servicio.</p>
      </section>
      {loadingSpaces && <p role="status">Cargando espacios activos…</p>}
      {!loadingSpaces && spaces.length === 0 && !error && <p className="empty-state">No hay espacios activos para consultar.</p>}
      {queried && !checking && results.length > 0 && <section className="availability-results" aria-labelledby="availability-results-title">
        <div className="section-heading"><div><p className="eyebrow">Respuesta del sistema</p><h2 id="availability-results-title">Resultados</h2></div></div>
        <div className="table-scroll"><table><thead><tr><th>Espacio</th><th>Tipo</th><th>Capacidad</th><th>Estado</th><th>Acción</th></tr></thead>
          <tbody>{results.map(({ space, result, error: rowError }) => <tr key={space.id} data-testid={`availability-row-${space.id}`}>
            <td><strong>{space.name}</strong><span className="table-secondary">{space.location}</span></td>
            <td>{space.type}</td><td>{space.capacity}</td>
            <td>{rowError ? <><span className="status-pill unconfirmed">No confirmado</span><span className="table-secondary">{rowError}</span></>
              : <span className={`status-pill ${result.availability === 'available' ? 'active' : 'inactive'}`}>{AVAILABILITY_LABELS[result.availability]}</span>}</td>
            <td>{session.user.role === 'requester' && !rowError && result.availability === 'available' && result.is_available
              ? <button className="text-button" onClick={() => onRequest({
                spaceId: space.id, spaceName: space.name, date, startsAt,
                endsAt: end.time, durationMinutes: Number(durationMinutes),
              })} type="button">Solicitar reserva</button>
              : <span className="table-secondary">—</span>}</td>
          </tr>)}</tbody></table></div>
      </section>}
    </main>
  );
}

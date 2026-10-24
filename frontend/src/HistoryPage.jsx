import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';

const ENTITY_LABELS = { user: 'Usuario', space: 'Espacio', reservation: 'Reserva', maintenance_block: 'Bloqueo de mantenimiento' };
const showValue = (value) => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);

export default function HistoryPage({ session, onBack }) {
  const [entityType, setEntityType] = useState('');
  const [entityId, setEntityId] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load(filters = {}) {
    setLoading(true); setError('');
    const params = new URLSearchParams();
    if (filters.entityType) params.set('entity_type', filters.entityType);
    if (filters.entityId) params.set('entity_id', filters.entityId);
    try {
      const result = await apiRequest(`/history${params.size ? `?${params}` : ''}`, { token: session.token });
      setEvents(result);
    } catch (requestError) { setEvents([]); setError(requestError.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [session.token]);

  async function submit(event) {
    event.preventDefault();
    if (entityId && !entityType) { setError('Selecciona el tipo de entidad para filtrar por identificador.'); return; }
    if (entityId && (!Number.isInteger(Number(entityId)) || Number(entityId) < 1)) { setError('El identificador debe ser un número positivo.'); return; }
    await load({ entityType, entityId });
  }

  const role = session.user.role;
  const entityOptions = role === 'administrator'
    ? Object.keys(ENTITY_LABELS)
    : role === 'requester' ? ['reservation'] : ['reservation', 'space', 'maintenance_block'];

  return <main className="dashboard-content history-page">
    <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
    <header className="page-heading"><div><p className="eyebrow">Auditoría del sistema</p><h1>Historial autorizado</h1><p>Los resultados y el alcance los determina el servicio según tu rol.</p></div></header>
    {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
    <section className="history-filters"><h2>Filtrar eventos</h2><form className="availability-form" onSubmit={submit}>
      <label>Tipo de entidad<select aria-label="Tipo de entidad" value={entityType} onChange={(event) => setEntityType(event.target.value)}><option value="">Todos los tipos permitidos</option>{entityOptions.map((type) => <option key={type} value={type}>{ENTITY_LABELS[type]}</option>)}</select></label>
      <label>Identificador<input aria-label="Identificador de entidad" inputMode="numeric" value={entityId} onChange={(event) => setEntityId(event.target.value)} /></label>
      <button className="primary-button" disabled={loading} type="submit">Aplicar filtros</button><button className="secondary-button" disabled={loading} onClick={() => { setEntityType(''); setEntityId(''); load(); }} type="button">Limpiar filtros</button>
    </form></section>
    <section className="history-results" aria-label="Eventos de historial">
      {loading ? <p role="status">Cargando historial…</p> : events.length === 0 ? <p className="empty-state">No hay eventos disponibles para estos filtros.</p> : <div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Entidad</th><th>Acción</th><th>Actor</th><th>Detalle</th></tr></thead><tbody>{events.map((item) => <tr key={item.id}>
        <td>{new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' }).format(new Date(item.occurred_at_utc))}</td>
        <td>{ENTITY_LABELS[item.entity_type] ?? item.entity_type} #{item.entity_id}</td><td>{item.action}</td><td>{item.actor_full_name ?? 'Sistema'}</td><td>{item.reason || [item.old_values, item.new_values].filter(Boolean).map(showValue).join(' → ') || '—'}</td>
      </tr>)}</tbody></table></div>}
    </section>
  </main>;
}

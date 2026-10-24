import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';

const showDate = (value) => new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota',
}).format(new Date(value));

export default function ApprovalsPage({ session, onBack }) {
  const [requests, setRequests] = useState([]);
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [reason, setReason] = useState({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function refresh() {
    const [nextRequests, nextChanges] = await Promise.all([
      apiRequest('/approvals/pending', { token: session.token }),
      apiRequest('/approvals/pending-changes', { token: session.token }),
    ]);
    setRequests(nextRequests);
    setChanges(nextChanges);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      apiRequest('/approvals/pending', { token: session.token }),
      apiRequest('/approvals/pending-changes', { token: session.token }),
    ]).then(([nextRequests, nextChanges]) => {
      if (active) { setRequests(nextRequests); setChanges(nextChanges); }
    }).catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.token]);

  async function decide(kind, id, decision) {
    const key = `${kind}-${id}`;
    const decisionReason = reason[key]?.trim() ?? '';
    if (decision === 'reject' && !decisionReason) {
      setError('Escribe un motivo para rechazar la solicitud.'); setNotice(''); return;
    }
    setBusy(key); setError(''); setNotice('');
    try {
      const path = kind === 'reservation' ? `/approvals/reservations/${id}/decision` : `/approvals/change-requests/${id}/decision`;
      const updated = await apiRequest(path, {
        token: session.token, method: 'POST',
        body: { decision, reason: decision === 'reject' ? decisionReason : null },
      });
      await refresh();
      setNotice(kind === 'reservation'
        ? `Solicitud ${id}: ${updated.status === 'approved' ? 'aprobada' : 'rechazada'} por el servicio.`
        : `Cambio ${id}: ${decision === 'approve' ? 'aprobado' : 'rechazado'}. Horario vigente: ${showDate(updated.starts_at_utc)} – ${showDate(updated.ends_at_utc)}.`);
      setReason((current) => ({ ...current, [key]: '' }));
    } catch (requestError) {
      setError(requestError.message);
      if ([404, 409].includes(requestError.status)) {
        try { await refresh(); } catch { /* conserva el error original */ }
      }
    } finally { setBusy(null); }
  }

  if (session.user.role !== 'approver') return <main className="dashboard-content"><p role="alert">No tienes permiso para consultar las aprobaciones.</p><button className="text-button" onClick={onBack} type="button">← Volver al panel</button></main>;

  function controls(kind, id) {
    const key = `${kind}-${id}`;
    return <><label className="approval-reason">Motivo para rechazar<textarea aria-label={`Motivo para rechazar ${kind === 'reservation' ? 'solicitud' : 'cambio'} ${id}`} value={reason[key] ?? ''} onChange={(event) => setReason((current) => ({ ...current, [key]: event.target.value }))} /></label>
      <div className="form-actions"><button className="primary-button" disabled={busy !== null} onClick={() => decide(kind, id, 'approve')} type="button">Aprobar</button>
        <button className="secondary-button" disabled={busy !== null} onClick={() => decide(kind, id, 'reject')} type="button">Rechazar</button></div></>;
  }

  return <main className="dashboard-content approvals-page">
    <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
    <header className="page-heading"><div><p className="eyebrow">Espacios asignados</p><h1>Aprobaciones</h1><p>Las decisiones se validan y confirman en el servicio.</p></div></header>
    {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
    {notice && <p className="feedback feedback-success page-feedback" role="status">{notice}</p>}
    {loading ? <p role="status">Cargando bandejas…</p> : <>
      <section className="approval-section"><div className="section-heading"><div><p className="eyebrow">Solicitudes nuevas</p><h2>Reservas pendientes</h2></div><span className="account-count">{requests.length}</span></div>
        {!requests.length ? <p className="empty-state">No hay solicitudes pendientes en tus espacios asignados.</p> : <div className="reservation-card-list">{requests.map((item) => <article className="reservation-card" key={item.id}>
          <div className="reservation-card-heading"><div><p className="eyebrow">Solicitud #{item.id}</p><h3>{item.space_name}</h3></div><span className="status-pill status-pending">Pendiente</span></div>
          <p>{showDate(item.starts_at_utc)} – {showDate(item.ends_at_utc)}</p>{controls('reservation', item.id)}</article>)}</div>}
      </section>
      <section className="approval-section"><div className="section-heading"><div><p className="eyebrow">Cambios solicitados</p><h2>Modificaciones pendientes</h2></div><span className="account-count">{changes.length}</span></div>
        {!changes.length ? <p className="empty-state">No hay cambios pendientes en tus espacios asignados.</p> : <div className="reservation-card-list">{changes.map((item) => <article className="reservation-card" key={item.id}>
          <div className="reservation-card-heading"><div><p className="eyebrow">Cambio #{item.id} · Reserva #{item.reservation_id}</p><h3>{item.space_name}</h3></div><span className="status-pill status-pending">Pendiente</span></div>
          <p><strong>Horario vigente:</strong> {showDate(item.starts_at_utc)} – {showDate(item.ends_at_utc)}</p><p><strong>Horario propuesto:</strong> {showDate(item.proposed_starts_at_utc)} – {showDate(item.proposed_ends_at_utc)}</p>{controls('change', item.id)}</article>)}</div>}
      </section>
    </>}
  </main>;
}

import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';

const STATUS_LABELS = {
  pending: 'Pendiente', approved: 'Aprobada', rejected: 'Rechazada',
  rejected_expired: 'Vencida', cancelled: 'Cancelada', finished: 'Finalizada',
};

function bogotaDateTime(value) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(value)).reduce((values, part) => ({ ...values, [part.type]: part.value }), {});
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

function showDate(value) {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota',
  }).format(new Date(value));
}

function draftDateTime(date, time) {
  return `${date}T${time}:00`;
}

function canCancel(reservation) {
  const startsIn = new Date(reservation.starts_at_utc).getTime() - Date.now();
  const active = ['pending', 'approved'].includes(reservation.status) && startsIn > 0;
  const approvedIsInTime = reservation.status !== 'approved' || startsIn >= 2 * 60 * 60 * 1000;
  return active && approvedIsInTime;
}

function canModify(reservation) {
  return canCancel(reservation) && !reservation.pending_change;
}

export default function ReservationsPage({ session, initialDraft, onDraftConsumed, onBack }) {
  const isRequester = session.user.role === 'requester';
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState(initialDraft);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ starts_at: '', ends_at: '' });

  async function refreshReservations() {
    const result = await apiRequest('/reservations', { token: session.token });
    setReservations(result);
  }

  useEffect(() => {
    let active = true;
    apiRequest('/reservations', { token: session.token })
      .then((result) => { if (active) setReservations(result); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.token]);

  async function submitRequest(event) {
    event.preventDefault(); if (!draft || !isRequester) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const created = await apiRequest('/reservations', {
        token: session.token, method: 'POST',
        body: {
          space_id: draft.spaceId,
          starts_at: draftDateTime(draft.date, draft.startsAt),
          ends_at: draftDateTime(draft.date, draft.endsAt),
        },
      });
      await refreshReservations();
      setDraft(null); onDraftConsumed();
      setNotice(`Solicitud ${created.id} registrada con estado: ${STATUS_LABELS[created.status]}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function saveChange(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const updated = await apiRequest(`/reservations/${editingId}`, {
        token: session.token, method: 'PUT',
        body: { starts_at: `${editForm.starts_at}:00`, ends_at: `${editForm.ends_at}:00` },
      });
      await refreshReservations(); setEditingId(null);
      setNotice(updated.pending_change
        ? 'El cambio quedó pendiente de aprobación. El horario original se conserva mientras se revisa.'
        : `Reserva ${updated.id} actualizada: ${STATUS_LABELS[updated.status]}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function cancelReservation(reservation) {
    if (!window.confirm(`¿Confirmas cancelar la reserva de ${reservation.space_name}?`)) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await apiRequest(`/reservations/${reservation.id}/cancel`, {
        token: session.token, method: 'POST', body: { reason: null },
      });
      await refreshReservations();
      setNotice(`Reserva ${updated.id}: ${STATUS_LABELS[updated.status]}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  function beginEdit(reservation) {
    setEditingId(reservation.id);
    setEditForm({ starts_at: bogotaDateTime(reservation.starts_at_utc), ends_at: bogotaDateTime(reservation.ends_at_utc) });
    setError(''); setNotice('');
  }

  return (
    <main className="dashboard-content reservations-page">
      <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
      <header className="page-heading"><div><p className="eyebrow">Solicitudes personales</p><h1>{isRequester ? 'Mis reservas' : 'Reservas visibles'}</h1>
        <p>Estados y horarios confirmados por el servicio.</p></div></header>
      {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
      {notice && <p className="feedback feedback-success page-feedback" role="status">{notice}</p>}

      {draft && isRequester && <section className="reservation-request-panel" aria-labelledby="reservation-request-title">
        <div className="section-heading"><div><p className="eyebrow">Intervalo confirmado disponible</p><h2 id="reservation-request-title">Solicitar reserva</h2></div></div>
        <p><strong>{draft.spaceName}</strong> · {draft.date} · {draft.startsAt}–{draft.endsAt}</p>
        <p className="policy-hint">La disponibilidad se vuelve a validar al guardar. El servicio aplicará el horario, anticipación y límite acumulado de cuatro horas.</p>
        <form onSubmit={submitRequest} className="form-actions">
          <button className="primary-button" disabled={busy} type="submit">{busy ? 'Enviando…' : 'Enviar solicitud'}</button>
          <button className="secondary-button" disabled={busy} onClick={() => { setDraft(null); onDraftConsumed(); }} type="button">Cancelar</button>
        </form>
      </section>}

      <section className="reservation-list-section" aria-labelledby="reservation-list-title">
        <div className="section-heading"><div><p className="eyebrow">Historial personal</p><h2 id="reservation-list-title">Reservas registradas</h2></div>
          {!loading && <span className="account-count">{reservations.length} reservas</span>}</div>
        {loading ? <p role="status">Cargando reservas…</p> : reservations.length === 0
          ? <p className="empty-state">Todavía no tienes reservas registradas.</p>
          : <div className="reservation-card-list">{reservations.map((reservation) => <article className="reservation-card" key={reservation.id}>
            {editingId === reservation.id ? <form className="reservation-edit-form" onSubmit={saveChange}>
              <h3>Modificar reserva · {reservation.space_name}</h3>
              <label>Inicio<input required type="datetime-local" value={editForm.starts_at} onChange={(event) => setEditForm({ ...editForm, starts_at: event.target.value })} /></label>
              <label>Fin<input required type="datetime-local" value={editForm.ends_at} onChange={(event) => setEditForm({ ...editForm, ends_at: event.target.value })} /></label>
              <div className="form-actions"><button className="primary-button" disabled={busy} type="submit">Guardar cambio</button>
                <button className="secondary-button" disabled={busy} onClick={() => setEditingId(null)} type="button">Cancelar edición</button></div>
            </form> : <>
              <div className="reservation-card-heading"><div><p className="eyebrow">Reserva #{reservation.id}</p><h3>{reservation.space_name}</h3></div>
                <span className={`status-pill reservation-status status-${reservation.status}`}>{STATUS_LABELS[reservation.status] ?? reservation.status}</span></div>
              <p>{showDate(reservation.starts_at_utc)} – {showDate(reservation.ends_at_utc)}</p>
              {reservation.pending_change && <p className="pending-change-note">Cambio pendiente: {showDate(reservation.pending_change.starts_at_utc)} – {showDate(reservation.pending_change.ends_at_utc)}. El horario original sigue vigente hasta que se decida.</p>}
              {isRequester && (canModify(reservation) || canCancel(reservation)) && <div className="form-actions reservation-actions">
                {canModify(reservation) && <button className="secondary-button" disabled={busy} onClick={() => beginEdit(reservation)} type="button">Modificar</button>}
                {canCancel(reservation) && <button className="text-button danger-text" disabled={busy} onClick={() => cancelReservation(reservation)} type="button">Cancelar reserva</button>}
              </div>}
              {reservation.cancellation_reason && <p className="table-secondary">Motivo: {reservation.cancellation_reason}</p>}
            </>}
          </article>)}</div>}
      </section>
    </main>
  );
}

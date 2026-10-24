import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';

const emptySpace = {
  name: '', type: '', capacity: '', location: '', equipment: '',
  is_active: true, requires_approval: true,
};

function localDateTime(value) {
  const date = new Date(value);
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).reduce((values, part) => ({ ...values, [part.type]: part.value }), {});
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

function displayDate(value) {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota',
  }).format(new Date(value));
}

export default function SpacesPage({ session, onBack }) {
  const isAdmin = session.user.role === 'administrator';
  const [spaces, setSpaces] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [blocks, setBlocks] = useState([]);
  const [form, setForm] = useState(emptySpace);
  const [blockForm, setBlockForm] = useState({ starts_at: '', ends_at: '', reason: '' });
  const [editingId, setEditingId] = useState(null);
  const [showSpaceForm, setShowSpaceForm] = useState(false);
  const [editingBlockId, setEditingBlockId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function refreshSpaces(preferredId = selectedId) {
    const result = await apiRequest('/spaces', { token: session.token });
    setSpaces(result);
    if (preferredId && result.some((space) => space.id === preferredId)) setSelectedId(preferredId);
    else setSelectedId(result[0]?.id ?? null);
  }

  async function refreshBlocks(spaceId = selectedId) {
    if (!isAdmin || !spaceId) { setBlocks([]); return; }
    const result = await apiRequest(`/spaces/${spaceId}/maintenance-blocks`, { token: session.token });
    setBlocks(result);
  }

  useEffect(() => {
    let active = true;
    apiRequest('/spaces', { token: session.token })
      .then((result) => { if (active) { setSpaces(result); setSelectedId(result[0]?.id ?? null); } })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.token]);

  useEffect(() => {
    let active = true;
    if (isAdmin && selectedId) {
      apiRequest(`/spaces/${selectedId}/maintenance-blocks`, { token: session.token })
        .then((result) => { if (active) setBlocks(result); })
        .catch((requestError) => { if (active) setError(requestError.message); });
    } else setBlocks([]);
    return () => { active = false; };
  }, [isAdmin, selectedId, session.token]);

  function editSpace(space) {
    setEditingId(space.id);
    setShowSpaceForm(true);
    setForm({ ...space, capacity: String(space.capacity), equipment: space.equipment.join(', ') });
    setError(''); setNotice('');
  }

  async function saveSpace(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    const payload = {
      name: form.name, type: form.type, capacity: Number(form.capacity), location: form.location,
      equipment: form.equipment.split(',').map((item) => item.trim()).filter(Boolean),
      ...(editingId ? {} : { is_active: form.is_active, requires_approval: form.requires_approval }),
    };
    try {
      const saved = await apiRequest(editingId ? `/spaces/${editingId}` : '/spaces', {
        token: session.token, method: editingId ? 'PUT' : 'POST', body: payload,
      });
      await refreshSpaces(saved.id);
      setForm(emptySpace); setEditingId(null); setShowSpaceForm(false); setNotice('Los datos del espacio se guardaron correctamente.');
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function changeStatus(space) {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await apiRequest(`/spaces/${space.id}/status`, {
        token: session.token, method: 'PATCH', body: { is_active: !space.is_active },
      });
      await refreshSpaces(space.id);
      const count = result.future_reservations_to_review;
      setNotice(count
        ? `Espacio actualizado. Hay ${count} ${count === 1 ? 'reserva futura que requiere' : 'reservas futuras que requieren'} revisión manual; no se cancelaron.`
        : `El espacio ahora está ${result.space.is_active ? 'activo' : 'inactivo'}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function toggleApproval(space) {
    setBusy(true); setError(''); setNotice('');
    try {
      await apiRequest(`/spaces/${space.id}/approval-policy`, {
        token: session.token, method: 'PATCH', body: { requires_approval: !space.requires_approval },
      });
      await refreshSpaces(space.id);
      setNotice('La política se guardó para las nuevas solicitudes. Las reservas existentes no cambian.');
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function saveBlock(event) {
    event.preventDefault(); if (!selectedId) return;
    setBusy(true); setError(''); setNotice('');
    const payload = { ...blockForm };
    try {
      await apiRequest(editingBlockId
        ? `/spaces/${selectedId}/maintenance-blocks/${editingBlockId}`
        : `/spaces/${selectedId}/maintenance-blocks`, {
        token: session.token, method: editingBlockId ? 'PUT' : 'POST', body: payload,
      });
      await refreshBlocks(selectedId);
      setBlockForm({ starts_at: '', ends_at: '', reason: '' }); setEditingBlockId(null);
      setNotice('El bloqueo de mantenimiento se guardó correctamente.');
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function removeBlock(block) {
    setBusy(true); setError(''); setNotice('');
    try {
      await apiRequest(`/spaces/${selectedId}/maintenance-blocks/${block.id}`, {
        token: session.token, method: 'DELETE',
      });
      await refreshBlocks(selectedId); setNotice('El bloqueo se retiró correctamente.');
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  const selectedSpace = spaces.find((space) => space.id === selectedId);
  return (
    <main className="dashboard-content spaces-page">
      <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
      <header className="page-heading">
        <div><p className="eyebrow">Catálogo institucional</p><h1>Espacios académicos</h1>
          <p>Consulta disponibilidad general y características de cada espacio.</p></div>
        {isAdmin && <button className="primary-button" onClick={() => { setEditingId(null); setForm(emptySpace); setShowSpaceForm(true); setError(''); setNotice(''); }} type="button">Nuevo espacio</button>}
      </header>
      {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
      {notice && <p className="feedback feedback-success page-feedback" role="status">{notice}</p>}
      {loading ? <p role="status">Cargando espacios…</p> : spaces.length === 0
        ? <p className="empty-state">No hay espacios registrados en el servicio.</p>
        : <div className="spaces-layout">
          <section className="spaces-list" aria-label="Espacios">
            {spaces.map((space) => <button className={`space-option ${space.id === selectedId ? 'selected' : ''}`} key={space.id} onClick={() => setSelectedId(space.id)} type="button">
              <span className="space-option-name">{space.name}</span><span>{space.location}</span>
              <span className={`status-pill ${space.is_active ? 'active' : 'inactive'}`}>{space.is_active ? 'Activo' : 'Inactivo'}</span>
            </button>)}
          </section>
          {selectedSpace && <section className="space-detail" aria-label={`Detalle de ${selectedSpace.name}`}>
            <div className="space-detail-heading"><div><p className="eyebrow">{selectedSpace.type} · {selectedSpace.capacity} personas</p><h2>{selectedSpace.name}</h2><p>{selectedSpace.location}</p></div>
              <span className={`status-pill ${selectedSpace.is_active ? 'active' : 'inactive'}`}>{selectedSpace.is_active ? 'Activo' : 'Inactivo'}</span></div>
            <p><strong>Equipamiento:</strong> {selectedSpace.equipment.length ? selectedSpace.equipment.join(', ') : 'Sin equipamiento registrado'}</p>
            <p><strong>Política:</strong> {selectedSpace.requires_approval ? 'Requiere aprobación para nuevas solicitudes' : 'Aprobación automática de nuevas solicitudes'}</p>
            {isAdmin && <div className="space-actions">
              <button className="secondary-button" disabled={busy} onClick={() => editSpace(selectedSpace)} type="button">Editar datos</button>
              <button className="secondary-button" disabled={busy} onClick={() => toggleApproval(selectedSpace)} type="button">{selectedSpace.requires_approval ? 'Desactivar aprobación' : 'Requerir aprobación'}</button>
              <button className="secondary-button" disabled={busy} onClick={() => changeStatus(selectedSpace)} type="button">{selectedSpace.is_active ? 'Desactivar espacio' : 'Activar espacio'}</button>
            </div>}
            {isAdmin && <section className="maintenance-section"><div className="section-heading"><div><p className="eyebrow">Agenda técnica</p><h3>Mantenimiento</h3></div></div>
              <form className="maintenance-form" onSubmit={saveBlock}>
                <label>Inicio<input required type="datetime-local" value={blockForm.starts_at} onChange={(e) => setBlockForm({ ...blockForm, starts_at: e.target.value })} /></label>
                <label>Fin<input required type="datetime-local" value={blockForm.ends_at} onChange={(e) => setBlockForm({ ...blockForm, ends_at: e.target.value })} /></label>
                <label>Motivo<input required maxLength={500} value={blockForm.reason} onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })} /></label>
                <button className="primary-button" disabled={busy} type="submit">{editingBlockId ? 'Guardar cambios' : 'Crear bloqueo'}</button>
                {editingBlockId && <button className="secondary-button" onClick={() => { setEditingBlockId(null); setBlockForm({ starts_at: '', ends_at: '', reason: '' }); }} type="button">Cancelar edición</button>}
              </form>
              {blocks.length ? <ul className="maintenance-list">{blocks.map((block) => <li key={block.id}>
                <div><strong>{block.reason}</strong><span>{displayDate(block.starts_at_utc)} – {displayDate(block.ends_at_utc)}</span></div>
                <button className="text-button" disabled={busy} onClick={() => { setEditingBlockId(block.id); setBlockForm({ starts_at: localDateTime(block.starts_at_utc), ends_at: localDateTime(block.ends_at_utc), reason: block.reason }); }} type="button">Editar</button>
                <button className="text-button danger-text" disabled={busy} onClick={() => removeBlock(block)} type="button">Retirar</button>
              </li>)}</ul> : <p className="empty-inline">No hay bloqueos registrados.</p>}
              <p className="maintenance-note">Si existe un conflicto, la API conserva el bloqueo actual y devuelve las reservas que deben revisarse. El contacto con las personas afectadas es manual.</p>
            </section>}
          </section>}
        </div>}
      {isAdmin && showSpaceForm && <section className="space-form-panel" aria-label={editingId ? 'Editar espacio' : 'Crear espacio'}>
        <h2>{editingId ? 'Editar espacio' : 'Registrar espacio'}</h2>
        <form className="space-form" onSubmit={saveSpace}>
          <label>Nombre<input required maxLength={160} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Tipo<input required maxLength={80} value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} /></label>
          <label>Capacidad<input required min="1" type="number" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} /></label>
          <label>Ubicación<input required maxLength={200} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label>
          <label className="wide-field">Equipamiento separado por comas<input value={form.equipment} onChange={(e) => setForm({ ...form, equipment: e.target.value })} /></label>
          {!editingId && <><label className="check-field"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />Activo</label>
            <label className="check-field"><input type="checkbox" checked={form.requires_approval} onChange={(e) => setForm({ ...form, requires_approval: e.target.checked })} />Requiere aprobación</label></>}
          <div className="wide-field form-actions"><button className="primary-button" disabled={busy} type="submit">{busy ? 'Guardando…' : 'Guardar espacio'}</button>
            <button className="secondary-button" onClick={() => { setForm(emptySpace); setEditingId(null); setShowSpaceForm(false); }} type="button">Cancelar</button></div>
        </form>
      </section>}
    </main>
  );
}

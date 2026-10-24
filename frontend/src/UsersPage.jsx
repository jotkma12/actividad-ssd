import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';

const ROLE_LABELS = {
  administrator: 'Administrador',
  requester: 'Solicitante',
  approver: 'Aprobador',
};

const emptyCreateForm = {
  full_name: '', institutional_email: '', identification: '', password: '', role: 'requester',
};

export default function UsersPage({ session, onBack }) {
  const [users, setUsers] = useState([]);
  const [spaces, setSpaces] = useState([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState('');
  const [assignedApprovers, setAssignedApprovers] = useState([]);
  const [selectedApproverId, setSelectedApproverId] = useState('');
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [editingUserId, setEditingUserId] = useState(null);
  const [editForm, setEditForm] = useState({ full_name: '', institutional_email: '', identification: '' });
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function refreshUsers() {
    const result = await apiRequest('/users', { token: session.token });
    setUsers(result);
  }

  async function refreshAssignments(spaceId = selectedSpaceId) {
    if (!spaceId) { setAssignedApprovers([]); return; }
    const result = await apiRequest(`/permissions/spaces/${spaceId}/approvers`, { token: session.token });
    setAssignedApprovers(result);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      apiRequest('/users', { token: session.token }),
      apiRequest('/spaces', { token: session.token }),
    ]).then(([accountList, spaceList]) => {
      if (active) {
        setUsers(accountList);
        setSpaces(spaceList);
        setSelectedSpaceId(spaceList[0] ? String(spaceList[0].id) : '');
      }
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [session.token]);

  useEffect(() => {
    let active = true;
    if (selectedSpaceId) {
      apiRequest(`/permissions/spaces/${selectedSpaceId}/approvers`, { token: session.token })
        .then((result) => { if (active) setAssignedApprovers(result); })
        .catch((requestError) => { if (active) setError(requestError.message); });
    } else setAssignedApprovers([]);
    return () => { active = false; };
  }, [selectedSpaceId, session.token]);

  async function createAccount(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const account = await apiRequest('/users', {
        token: session.token, method: 'POST', body: createForm,
      });
      await refreshUsers();
      setCreateForm(emptyCreateForm); setShowCreateForm(false);
      setNotice(`Cuenta creada como inactiva: ${account.full_name}. Actívala desde la lista para permitir el inicio de sesión.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  function beginEdit(account) {
    setEditingUserId(account.id);
    setEditForm({
      full_name: account.full_name,
      institutional_email: account.institutional_email,
      identification: account.identification ?? '',
    });
    setError(''); setNotice('');
  }

  async function saveProfile(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const updated = await apiRequest(`/users/${editingUserId}`, {
        token: session.token, method: 'PUT', body: editForm,
      });
      await refreshUsers(); setEditingUserId(null);
      setNotice(`Datos de ${updated.full_name} actualizados.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function changeStatus(account) {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await apiRequest(`/users/${account.id}/status`, {
        token: session.token, method: 'PATCH', body: { is_active: !account.is_active },
      });
      await refreshUsers();
      const count = result.future_reservations_to_review;
      setNotice(!result.user.is_active && count
        ? `${result.user.full_name} fue desactivado. Hay ${count} ${count === 1 ? 'reserva futura que requiere' : 'reservas futuras que requieren'} revisión manual; no se cancelaron.`
        : `${result.user.full_name} ahora está ${result.user.is_active ? 'activo' : 'inactivo'}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function changeRole(account, role) {
    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await apiRequest(`/users/${account.id}/role`, {
        token: session.token, method: 'PATCH', body: { role },
      });
      await refreshUsers(); setNotice(`Rol de ${updated.full_name} actualizado a ${ROLE_LABELS[updated.role]}.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function assignApprover(event) {
    event.preventDefault(); if (!selectedSpaceId || !selectedApproverId) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await apiRequest(`/permissions/spaces/${selectedSpaceId}/approvers/${selectedApproverId}`, {
        token: session.token, method: 'PUT',
      });
      await refreshAssignments(); setSelectedApproverId('');
      setNotice('Aprobador asignado al espacio.');
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function removeApprover(approver) {
    setBusy(true); setError(''); setNotice('');
    try {
      await apiRequest(`/permissions/spaces/${selectedSpaceId}/approvers/${approver.id}`, {
        token: session.token, method: 'DELETE',
      });
      await refreshAssignments(); setNotice(`Se retiró a ${approver.full_name} del espacio.`);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  const eligibleApprovers = users.filter((account) =>
    account.role === 'approver' && !assignedApprovers.some((assigned) => assigned.id === account.id));

  return (
    <main className="dashboard-content users-page">
      <button className="text-button" onClick={onBack} type="button">← Volver al panel</button>
      <header className="page-heading">
        <div><p className="eyebrow">Administración institucional</p><h1>Cuentas de usuario</h1>
          <p>Administra perfiles, acceso, roles y aprobadores asignados.</p></div>
        <button className="primary-button" onClick={() => { setShowCreateForm((open) => !open); setError(''); setNotice(''); }} type="button">
          {showCreateForm ? 'Cerrar formulario' : 'Crear cuenta'}
        </button>
      </header>
      {error && <p className="feedback feedback-error page-feedback" role="alert">{error}</p>}
      {notice && <p className="feedback feedback-success page-feedback" role="status">{notice}</p>}

      {showCreateForm && <section className="user-form-panel" aria-labelledby="create-user-title">
        <h2 id="create-user-title">Nueva cuenta</h2>
        <p>Las cuentas nuevas quedan inactivas hasta que un administrador las active.</p>
        <form className="user-form" onSubmit={createAccount}>
          <label>Nombre completo<input required maxLength={200} value={createForm.full_name} onChange={(event) => setCreateForm({ ...createForm, full_name: event.target.value })} /></label>
          <label>Correo institucional<input required type="email" placeholder="persona@universidad.edu.co" value={createForm.institutional_email} onChange={(event) => setCreateForm({ ...createForm, institutional_email: event.target.value })} /></label>
          <label>Identificación<input required maxLength={100} value={createForm.identification} onChange={(event) => setCreateForm({ ...createForm, identification: event.target.value })} /></label>
          <label>Contraseña inicial<input required minLength={12} type="password" autoComplete="new-password" value={createForm.password} onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })} /><span className="field-hint">Mínimo 12 caracteres.</span></label>
          <label>Rol inicial<select value={createForm.role} onChange={(event) => setCreateForm({ ...createForm, role: event.target.value })}>
            <option value="administrator">Administrador</option><option value="requester">Solicitante</option><option value="approver">Aprobador</option>
          </select></label>
          <div className="wide-field form-actions"><button className="primary-button" disabled={busy} type="submit">{busy ? 'Guardando…' : 'Crear cuenta inactiva'}</button></div>
        </form>
      </section>}

      <section className="users-table-section" aria-labelledby="account-list-title">
        <div className="section-heading"><div><p className="eyebrow">Directorio</p><h2 id="account-list-title">Cuentas registradas</h2></div>
          {!loading && <span className="account-count">{users.length} cuentas</span>}</div>
        {loading ? <p role="status">Cargando cuentas…</p> : users.length === 0
          ? <p className="empty-state">No hay cuentas en el servicio.</p>
          : <div className="user-card-list">{users.map((account) => <article className="user-card" key={account.id}>
            {editingUserId === account.id ? <form className="user-edit-form" onSubmit={saveProfile}>
              <h3>Editar datos de {account.full_name}</h3>
              <label>Nombre completo<input required maxLength={200} value={editForm.full_name} onChange={(event) => setEditForm({ ...editForm, full_name: event.target.value })} /></label>
              <label>Correo institucional<input required type="email" value={editForm.institutional_email} onChange={(event) => setEditForm({ ...editForm, institutional_email: event.target.value })} /></label>
              <label>Identificación<input required maxLength={100} value={editForm.identification} onChange={(event) => setEditForm({ ...editForm, identification: event.target.value })} /></label>
              <div className="form-actions"><button className="primary-button" disabled={busy} type="submit">Guardar datos</button>
                <button className="secondary-button" onClick={() => setEditingUserId(null)} type="button">Cancelar</button></div>
            </form> : <>
              <div className="user-card-identity"><div><h3>{account.full_name}</h3><p>{account.institutional_email}</p><span>Identificación: {account.identification || 'Sin registrar'}</span></div>
                <span className={`status-pill ${account.is_active ? 'active' : 'inactive'}`}>{account.is_active ? 'Activa' : 'Inactiva'}</span></div>
              <div className="user-card-controls">
                <label>Rol<select aria-label={`Rol de ${account.full_name}`} disabled={busy} value={account.role} onChange={(event) => changeRole(account, event.target.value)}>
                  <option value="administrator">Administrador</option><option value="requester">Solicitante</option><option value="approver">Aprobador</option>
                </select></label>
                <button className="secondary-button" disabled={busy} onClick={() => beginEdit(account)} type="button">Editar perfil</button>
                <button className="secondary-button" disabled={busy} onClick={() => changeStatus(account)} type="button">{account.is_active ? 'Desactivar' : 'Activar'}</button>
              </div>
            </>}
          </article>)}</div>}
      </section>

      <section className="assignment-panel" aria-labelledby="assignment-title">
        <div className="section-heading"><div><p className="eyebrow">Permisos por espacio</p><h2 id="assignment-title">Asignación de aprobadores</h2></div></div>
        <label className="space-select-label">Espacio<select aria-label="Espacio para asignaciones" value={selectedSpaceId} onChange={(event) => setSelectedSpaceId(event.target.value)}>
          <option value="">Selecciona un espacio</option>{spaces.map((space) => <option key={space.id} value={space.id}>{space.name}</option>)}
        </select></label>
        {!spaces.length && !loading && <p className="empty-inline">Registra un espacio antes de asignar aprobadores.</p>}
        {selectedSpaceId && <>
          <form className="assign-form" onSubmit={assignApprover}>
            <label>Aprobador<select aria-label="Cuenta de aprobador" value={selectedApproverId} onChange={(event) => setSelectedApproverId(event.target.value)}>
              <option value="">Selecciona una cuenta con rol aprobador</option>
              {eligibleApprovers.map((approver) => <option key={approver.id} value={approver.id}>{approver.full_name}{approver.is_active ? '' : ' (inactivo)'}</option>)}
            </select></label>
            <button className="primary-button" disabled={busy || !selectedApproverId} type="submit">Asignar</button>
          </form>
          {assignedApprovers.length ? <ul className="assigned-list">{assignedApprovers.map((approver) => <li key={approver.id}>
            <div><strong>{approver.full_name}</strong><span>{approver.institutional_email} · {approver.is_active ? 'Activa' : 'Inactiva'}</span></div>
            <button className="text-button danger-text" disabled={busy} onClick={() => removeApprover(approver)} type="button">Retirar asignación</button>
          </li>)}</ul> : <p className="empty-inline">Este espacio no tiene aprobadores asignados.</p>}
        </>}
      </section>
    </main>
  );
}

import { useEffect, useState } from 'react';
import { apiRequest } from './api/client.js';
import SpacesPage from './SpacesPage.jsx';
import UsersPage from './UsersPage.jsx';
import AvailabilityPage from './AvailabilityPage.jsx';
import ReservationsPage from './ReservationsPage.jsx';
import ApprovalsPage from './ApprovalsPage.jsx';
import HistoryPage from './HistoryPage.jsx';

const ROLE_LABELS = {
  administrator: 'Administrador',
  requester: 'Solicitante',
  approver: 'Aprobador',
};

function SignIn({ onAuthenticated }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const result = await apiRequest('/auth/login', {
        method: 'POST',
        body: { institutional_email: email, password },
      });
      onAuthenticated({ token: result.access_token, user: result.user });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="sign-in-layout">
      <section className="sign-in-aside" aria-label="Información institucional">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">U</span>
          <span>Universidad</span>
        </div>
        <div className="aside-copy">
          <p className="eyebrow">Espacios académicos</p>
          <h1>Un lugar para cada idea.</h1>
          <p>Consulta espacios, organiza actividades y gestiona tus reservas desde un solo lugar.</p>
        </div>
        <p className="aside-footnote">Plataforma institucional de reservas</p>
      </section>

      <section className="sign-in-panel" aria-labelledby="sign-in-title">
        <div className="sign-in-card">
          <div className="mobile-brand brand-lockup">
            <span className="brand-mark" aria-hidden="true">U</span>
            <span>Universidad</span>
          </div>
          <p className="eyebrow">Bienvenido</p>
          <h2 id="sign-in-title">Inicia sesión</h2>
          <p className="form-intro">Usa tu cuenta institucional para continuar.</p>
          <form onSubmit={submit} noValidate>
            <label htmlFor="institutional-email">Correo institucional</label>
            <input
              autoComplete="username"
              id="institutional-email"
              name="institutional_email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="nombre@universidad.edu.co"
              required
              type="email"
              value={email}
            />
            <label htmlFor="password">Contraseña</label>
            <input
              autoComplete="current-password"
              id="password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {error && <p className="feedback feedback-error" role="alert">{error}</p>}
            <button className="primary-button sign-in-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? 'Validando…' : 'Ingresar'}
            </button>
          </form>
          <p className="sign-in-help">¿Necesitas una cuenta? Contacta al administrador de tu institución.</p>
        </div>
      </section>
    </main>
  );
}

function roleSummaries(role) {
  if (role === 'administrator') {
    return [
      { label: 'Espacios registrados', path: '/spaces' },
      { label: 'Cuentas de usuario', path: '/users' },
    ];
  }
  if (role === 'approver') {
    return [{ label: 'Solicitudes y cambios pendientes', path: '/approvals' }];
  }
  return [{ label: 'Mis reservas', path: '/reservations' }];
}

async function loadSummary(session) {
  if (session.user.role === 'administrator') {
    const [spaces, users] = await Promise.all([
      apiRequest('/spaces', { token: session.token }),
      apiRequest('/users', { token: session.token }),
    ]);
    return [
      { label: 'Espacios registrados', value: spaces.length },
      { label: 'Cuentas de usuario', value: users.length },
    ];
  }
  if (session.user.role === 'approver') {
    const [requests, changes] = await Promise.all([
      apiRequest('/approvals/pending', { token: session.token }),
      apiRequest('/approvals/pending-changes', { token: session.token }),
    ]);
    return [
      { label: 'Solicitudes pendientes', value: requests.length },
      { label: 'Cambios por revisar', value: changes.length },
    ];
  }
  const reservations = await apiRequest('/reservations', { token: session.token });
  const pending = reservations.filter((reservation) => reservation.status === 'pending').length;
  const approved = reservations.filter((reservation) => reservation.status === 'approved').length;
  return [
    { label: 'Reservas pendientes', value: pending },
    { label: 'Reservas aprobadas', value: approved },
  ];
}

function Dashboard({ session, onSignOut }) {
  const [view, setView] = useState('home');
  const [reservationDraft, setReservationDraft] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    loadSummary(session)
      .then((result) => {
        if (active) setSummary(result);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [session]);

  const role = session.user.role;
  const areas = roleSummaries(role);

  if (view === 'spaces') {
    return <>
      <header className="topbar">
        <a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}>
          <span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span>
        </a>
        <div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div>
          <button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div>
      </header>
      <SpacesPage session={session} onBack={() => setView('home')} />
    </>;
  }

  if (view === 'users' && role === 'administrator') {
    return <>
      <header className="topbar">
        <a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}>
          <span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span>
        </a>
        <div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div>
          <button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div>
      </header>
      <UsersPage session={session} onBack={() => setView('home')} />
    </>;
  }

  if (view === 'availability') {
    return <>
      <header className="topbar">
        <a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}>
          <span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span>
        </a>
        <div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div>
          <button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div>
      </header>
      <AvailabilityPage session={session} onBack={() => setView('home')} onRequest={(draft) => { setReservationDraft(draft); setView('reservations'); }} />
    </>;
  }

  if (view === 'approvals' && role === 'approver') {
    return <><header className="topbar"><a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}><span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span></a><div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div><button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div></header><ApprovalsPage session={session} onBack={() => setView('home')} /></>;
  }

  if (view === 'history') {
    return <><header className="topbar"><a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}><span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span></a><div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div><button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div></header><HistoryPage session={session} onBack={() => setView('home')} /></>;
  }

  if (view === 'reservations' && role === 'requester') {
    return <>
      <header className="topbar">
        <a className="brand-lockup brand-link" href="#inicio" onClick={(event) => { event.preventDefault(); setView('home'); }}>
          <span className="brand-mark" aria-hidden="true">U</span><span>Reservas académicas</span>
        </a>
        <div className="account-menu"><div className="account-copy"><span className="account-name">{session.user.full_name}</span><span className="role-badge">{ROLE_LABELS[role]}</span></div>
          <button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button></div>
      </header>
      <ReservationsPage session={session} initialDraft={reservationDraft} onDraftConsumed={() => setReservationDraft(null)} onBack={() => { setReservationDraft(null); setView('home'); }} />
    </>;
  }

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <a className="brand-lockup brand-link" href="#inicio" aria-label="Inicio de Reservas académicas">
          <span className="brand-mark" aria-hidden="true">U</span>
          <span>Reservas académicas</span>
        </a>
        <div className="account-menu">
          <div className="account-copy">
            <span className="account-name">{session.user.full_name}</span>
            <span className="role-badge">{ROLE_LABELS[role]}</span>
          </div>
          <button className="secondary-button" onClick={onSignOut} type="button">Cerrar sesión</button>
        </div>
      </header>

      <main className="dashboard-content" id="inicio">
        <section className="welcome-heading">
          <p className="eyebrow">Panel principal</p>
          <h1>Hola, {session.user.full_name.split(' ')[0]}</h1>
          <p>Este es el resumen de actividad disponible para tu perfil.</p>
        </section>

        <section aria-label="Resumen de actividad" className="summary-grid">
          {isLoading && <p className="loading-state" role="status">Cargando información del sistema…</p>}
          {error && <p className="feedback feedback-error summary-error" role="alert">{error}</p>}
          {!isLoading && !error && summary?.map((item) => (
            <article className="summary-card" key={item.label}>
              <span className="summary-value">{item.value}</span>
              <span className="summary-label">{item.label}</span>
            </article>
          ))}
        </section>

        <section className="role-panel" aria-labelledby="role-panel-title">
          <div>
            <p className="eyebrow">Tu perfil</p>
            <h2 id="role-panel-title">{ROLE_LABELS[role]}</h2>
            <p>Las acciones disponibles se determinan por tu rol y las asignaciones registradas en el sistema.</p>
          </div>
          <ul className="area-list">
            {areas.map((area) => <li key={area.path}>{role === 'administrator' && area.path === '/users'
              ? <button className="area-link" onClick={() => setView('users')} type="button">Administrar cuentas de usuario</button>
              : role === 'requester' && area.path === '/reservations'
                ? <button className="area-link" onClick={() => setView('reservations')} type="button">Mis reservas</button>
                : role === 'approver' && area.path.startsWith('/approvals')
                  ? <button className="area-link" onClick={() => setView('approvals')} type="button">Revisar solicitudes y cambios pendientes</button>
                  : area.label}</li>)}
            <li><button className="area-link" onClick={() => setView('history')} type="button">Consultar historial autorizado</button></li>
            <li><button className="area-link" onClick={() => setView('spaces')} type="button">Consultar espacios académicos</button></li>
            <li><button className="area-link" onClick={() => setView('availability')} type="button">Consultar disponibilidad</button></li>
          </ul>
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    function handleExpiredSession() {
      setSession(null);
      setNotice('Tu sesión venció o dejó de ser válida. Inicia sesión nuevamente.');
    }
    window.addEventListener('academic-session-expired', handleExpiredSession);
    return () => window.removeEventListener('academic-session-expired', handleExpiredSession);
  }, []);

  async function signOut() {
    const current = session;
    setSession(null);
    try {
      await apiRequest('/auth/logout', { token: current.token, method: 'POST' });
    } catch {
      setNotice('La sesión local se cerró. No se pudo confirmar el cierre con el servidor.');
    }
  }

  if (!session) {
    return (
      <>
        {notice && <p className="logout-notice" role="status">{notice}</p>}
        <SignIn onAuthenticated={(nextSession) => { setNotice(''); setSession(nextSession); }} />
      </>
    );
  }
  return <Dashboard onSignOut={signOut} session={session} />;
}

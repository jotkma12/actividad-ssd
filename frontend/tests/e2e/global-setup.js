import { existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const projectDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

export default async function globalSetup() {
  const databasePath = process.env.E2E_DATABASE_PATH;
  if (!databasePath) throw new Error('E2E_DATABASE_PATH no está configurada');

  const localPython = process.platform === 'win32'
    ? path.join(projectDirectory, '.venv', 'Scripts', 'python.exe')
    : path.join(projectDirectory, '.venv', 'bin', 'python');
  const configuredPython = process.env.PYTHON_EXECUTABLE
    || (existsSync(localPython) ? localPython : process.platform === 'win32' ? 'py' : 'python3');
  const pythonArguments = configuredPython === 'py' ? ['-3', '-c'] : ['-c'];
  const setupScript = [
    'from datetime import datetime, timedelta',
    'from backend.database import initialize_database',
    'from backend.espacios.maintenance import create_maintenance_block',
    'from backend.espacios.service import create_space',
    'from backend.reservas.service import create_reservation',
    'from backend.usuarios.service import assign_approver, create_account, create_initial_admin, set_account_status',
    'initialize_database()',
    "admin = create_initial_admin(full_name='Admin E2E', institutional_email='admin.e2e@universidad.edu.co', password='clave-admin-e2e-larga')",
    "requester = create_account(actor_user_id=admin['id'], full_name='Ana Solicitante', institutional_email='solicitante.e2e@universidad.edu.co', identification='e2e-requester', password='clave-solicitante-e2e', role='requester')",
    "set_account_status(requester['id'], True, actor_user_id=admin['id'])",
    "approver = create_account(actor_user_id=admin['id'], full_name='Ariel Aprobador', institutional_email='aprobador.e2e@universidad.edu.co', identification='e2e-approver', password='clave-aprobador-e2e', role='approver')",
    "set_account_status(approver['id'], True, actor_user_id=admin['id'])",
    "create_account(actor_user_id=admin['id'], full_name='Cuenta Inactiva', institutional_email='inactiva.e2e@universidad.edu.co', identification='e2e-inactive', password='clave-inactiva-e2e', role='requester')",
    "available = create_space(actor_user_id=admin['id'], name='Sala disponible E2E', type='Aula', capacity=20, location='Edificio E2E', equipment=[], is_active=True, requires_approval=True)",
    "occupied = create_space(actor_user_id=admin['id'], name='Sala ocupada E2E', type='Aula', capacity=20, location='Edificio E2E', equipment=[], is_active=True, requires_approval=False)",
    "blocked = create_space(actor_user_id=admin['id'], name='Sala bloqueada E2E', type='Laboratorio', capacity=20, location='Edificio E2E', equipment=[], is_active=True, requires_approval=True)",
    "limit_space = create_space(actor_user_id=admin['id'], name='Sala límite E2E', type='Aula', capacity=20, location='Edificio E2E', equipment=[], is_active=True, requires_approval=True)",
    "booking_start = datetime.now() + timedelta(days=5)",
    "booking_start = booking_start.replace(hour=13, minute=0, second=0, microsecond=0)",
    "booking_start += timedelta(days=1) if booking_start.weekday() == 6 else timedelta(0)",
    "booking_end = booking_start + timedelta(hours=1)",
    "assign_approver(available['id'], approver['id'], actor_user_id=admin['id'])",
    "create_reservation(user_id=requester['id'], space_id=available['id'], starts_at=booking_start + timedelta(hours=2), ends_at=booking_end + timedelta(hours=2))",
    "create_reservation(user_id=requester['id'], space_id=occupied['id'], starts_at=booking_start, ends_at=booking_end)",
    "create_reservation(user_id=requester['id'], space_id=limit_space['id'], starts_at=booking_start, ends_at=booking_end)",
    "create_maintenance_block(actor_user_id=admin['id'], space_id=blocked['id'], starts_at=booking_start, ends_at=booking_end, reason='Mantenimiento E2E')",
  ].join('\n');
  const result = spawnSync(configuredPython, [...pythonArguments, setupScript], {
    cwd: projectDirectory,
    encoding: 'utf8',
    env: { ...process.env, ACADEMIC_RESERVATIONS_DB_PATH: databasePath },
  });
  if (result.error || result.status !== 0) {
    throw new Error(`No se pudo preparar SQLite para Playwright: ${result.stderr || result.error}`);
  }
}

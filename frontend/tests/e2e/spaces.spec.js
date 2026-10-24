import { expect, test } from '@playwright/test';

async function signIn(page, email = 'admin.e2e@universidad.edu.co', password = 'clave-admin-e2e-larga') {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: /Hola,/ })).toBeVisible();
}

async function openSpaces(page) {
  await page.getByRole('button', { name: 'Consultar espacios académicos' }).click();
  await expect(page.getByRole('heading', { name: 'Espacios académicos' })).toBeVisible();
}

test('administra espacios mediante la API y conserva los datos tras volver a cargarlos', async ({ page }) => {
  await signIn(page);
  await openSpaces(page);
  await page.getByRole('button', { name: 'Nuevo espacio' }).click();
  const form = page.getByRole('region', { name: 'Crear espacio' });
  await form.getByLabel('Nombre').fill('Laboratorio E2E');
  await form.getByLabel('Tipo').fill('Laboratorio');
  await form.getByLabel('Capacidad').fill('24');
  await form.getByLabel('Ubicación').fill('Edificio de pruebas');
  await form.getByLabel('Equipamiento separado por comas').fill('Proyector, Microscopios');
  await form.getByRole('button', { name: 'Guardar espacio' }).click();
  await expect(page.getByText('Los datos del espacio se guardaron correctamente.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Laboratorio E2E' })).toBeVisible();

  await page.getByRole('button', { name: 'Editar datos' }).click();
  const editForm = page.getByRole('region', { name: 'Editar espacio' });
  await editForm.getByLabel('Capacidad').fill('28');
  await editForm.getByRole('button', { name: 'Guardar espacio' }).click();
  await expect(page.getByText('Laboratorio · 28 personas')).toBeVisible();

  await page.getByRole('button', { name: 'Desactivar aprobación' }).click();
  await expect(page.getByText(/Las reservas existentes no cambian/)).toBeVisible();
  await expect(page.getByText('Aprobación automática de nuevas solicitudes')).toBeVisible();
  await page.reload();
  await signIn(page);
  await openSpaces(page);
  await expect(page.getByRole('heading', { name: 'Laboratorio E2E' })).toBeVisible();
  await expect(page.getByText('Aprobación automática de nuevas solicitudes')).toBeVisible();
});

test('permite consultar espacios al solicitante sin mostrar acciones administrativas', async ({ page }) => {
  await signIn(page, 'solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e');
  await openSpaces(page);
  await expect(page.getByRole('button', { name: 'Nuevo espacio' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Desactivar espacio' })).toHaveCount(0);
});

test('informa el conflicto con una reserva al crear mantenimiento y permite retirar bloqueos', async ({ page }) => {
  await signIn(page);
  await openSpaces(page);
  await page.getByRole('button', { name: 'Nuevo espacio' }).click();
  const form = page.getByRole('region', { name: 'Crear espacio' });
  await form.getByLabel('Nombre').fill('Sala con reserva');
  await form.getByLabel('Tipo').fill('Aula');
  await form.getByLabel('Capacidad').fill('20');
  await form.getByLabel('Ubicación').fill('Edificio E2E');
  await form.getByRole('button', { name: 'Guardar espacio' }).click();
  await expect(page.getByRole('heading', { name: 'Sala con reserva' })).toBeVisible();
  // The creation response is read from the real catalog to avoid relying on seeded IDs.
  const spacesResponse = await page.request.get('http://127.0.0.1:8000/spaces');
  const spaces = await spacesResponse.json();
  const space = spaces.find((item) => item.name === 'Sala con reserva');
  expect(space).toBeTruthy();
  const loginResponse = await page.request.post('http://127.0.0.1:8000/auth/login', {
    data: { institutional_email: 'solicitante.e2e@universidad.edu.co', password: 'clave-solicitante-e2e' },
  });
  const { access_token: token } = await loginResponse.json();
  const start = new Date();
  start.setDate(start.getDate() + 3);
  if (start.getDay() === 0) start.setDate(start.getDate() + 1);
  start.setHours(11, 0, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  const localISO = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:00`;
  const reservationResponse = await page.request.post('http://127.0.0.1:8000/reservations', {
    headers: { Authorization: `Bearer ${token}` },
    data: { space_id: space.id, starts_at: localISO(start), ends_at: localISO(end) },
  });
  expect(reservationResponse.ok(), await reservationResponse.text()).toBeTruthy();

  const starts = page.getByLabel('Inicio');
  const ends = page.getByLabel('Fin');
  await starts.fill(localISO(start).slice(0, 16)); await ends.fill(localISO(end).slice(0, 16));
  await page.getByLabel('Motivo').fill('Mantenimiento preventivo');
  await page.getByRole('button', { name: 'Crear bloqueo' }).click();
  await expect(page.getByRole('alert')).toContainText('El intervalo se cruza con reservas pendientes o aprobadas');
  await expect(page.getByText('No hay bloqueos registrados.')).toBeVisible();

  const laterStart = new Date(start.getTime() + 2 * 60 * 60 * 1000);
  const laterEnd = new Date(laterStart.getTime() + 60 * 60 * 1000);
  await starts.fill(localISO(laterStart).slice(0, 16)); await ends.fill(localISO(laterEnd).slice(0, 16));
  await page.getByRole('button', { name: 'Crear bloqueo' }).click();
  await expect(page.getByText('El bloqueo de mantenimiento se guardó correctamente.')).toBeVisible();
  await page.getByRole('button', { name: 'Editar', exact: true }).click();
  await page.getByLabel('Motivo').fill('Mantenimiento preventivo actualizado');
  await page.getByRole('button', { name: 'Guardar cambios' }).click();
  await expect(page.getByText('Mantenimiento preventivo actualizado')).toBeVisible();
  await expect(page.getByText('El bloqueo de mantenimiento se guardó correctamente.')).toBeVisible();
  await page.getByRole('button', { name: 'Retirar' }).click();
  await expect(page.getByText('El bloqueo se retiró correctamente.')).toBeVisible();
  await page.getByRole('button', { name: 'Desactivar espacio' }).click();
  await expect(page.getByRole('status')).toContainText('Hay 1 reserva futura que requiere revisión manual; no se cancelaron.');
  await expect(page.getByRole('button', { name: 'Activar espacio' })).toBeVisible();
});

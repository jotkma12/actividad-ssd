import { expect, test } from '@playwright/test';

function bookingDate(daysAhead = 5) {
  const date = new Date();
  date.setDate(date.getDate() + daysAhead);
  while (date.getDay() === 0) date.setDate(date.getDate() + 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

async function signInRequester(page) {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill('solicitante.e2e@universidad.edu.co');
  await page.getByLabel('Contraseña').fill('clave-solicitante-e2e');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: 'Hola, Ana' })).toBeVisible();
}

async function openAvailability(page) {
  await page.getByRole('button', { name: 'Consultar disponibilidad' }).click();
  await expect(page.getByRole('heading', { name: 'Disponibilidad' })).toBeVisible();
}

async function search(page, { date = bookingDate(), starts = '13:00', duration = '60' } = {}) {
  await page.getByLabel('Fecha de consulta').fill(date);
  await page.getByLabel('Hora de inicio').fill(starts);
  await page.getByLabel('Duración de la reserva').selectOption(duration);
  await page.getByRole('button', { name: 'Consultar disponibilidad' }).click();
  await expect(page.getByRole('heading', { name: 'Resultados' })).toBeVisible();
}

async function spaceId(page, name) {
  const spaces = await (await page.request.get('http://127.0.0.1:8000/spaces')).json();
  return spaces.find((space) => space.name === name).id;
}

test('muestra estados del backend y permite enviar una reserva solo para un horario disponible', async ({ page }) => {
  await signInRequester(page);
  await openAvailability(page);
  const date = bookingDate();
  await search(page, { date, starts: '13:17', duration: '30' });
  await expect(page.getByText('Fin calculado: 13:47')).toBeVisible();
  await expect(page.getByLabel('Duración de la reserva').locator('option')).toHaveCount(8);
  await expect(page.getByLabel('Duración de la reserva').locator('option').last()).toHaveAttribute('value', '240');

  const availableId = await spaceId(page, 'Sala disponible E2E');
  const occupiedId = await spaceId(page, 'Sala ocupada E2E');
  const blockedId = await spaceId(page, 'Sala bloqueada E2E');
  const availableRow = page.getByTestId(`availability-row-${availableId}`);
  const occupiedRow = page.getByTestId(`availability-row-${occupiedId}`);
  const blockedRow = page.getByTestId(`availability-row-${blockedId}`);
  await expect(availableRow.getByText('Disponible', { exact: true })).toBeVisible();
  await expect(occupiedRow.getByText('Ocupado', { exact: true })).toBeVisible();
  await expect(blockedRow.getByText('Bloqueado', { exact: true })).toBeVisible();
  await expect(occupiedRow.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);
  await expect(blockedRow.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);

  await availableRow.getByRole('button', { name: 'Solicitar reserva' }).click();
  await expect(page.getByRole('heading', { name: 'Solicitar reserva' })).toBeVisible();
  await expect(page.getByText('Sala disponible E2E ·', { exact: false })).toBeVisible();
  await expect(page.getByText('13:17–13:47 (30 minutos)')).toBeVisible();
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.getByRole('status')).toContainText('registrada con estado: Pendiente');

  await page.getByRole('button', { name: '← Volver al panel' }).click();
  await openAvailability(page);
  await search(page, { date, starts: '13:17', duration: '30' });
  await expect(page.getByTestId(`availability-row-${availableId}`).getByText('Ocupado', { exact: true })).toBeVisible();
  await expect(page.getByTestId(`availability-row-${availableId}`).getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);
});
test('no presenta disponibilidad si el intervalo es inválido o falla la consulta', async ({ page }) => {
  await signInRequester(page);
  await openAvailability(page);
  const nextSunday = bookingDate();
  const sunday = new Date(`${nextSunday}T12:00:00`);
  sunday.setDate(sunday.getDate() + ((7 - sunday.getDay()) % 7 || 7));
  const sundayText = `${sunday.getFullYear()}-${String(sunday.getMonth() + 1).padStart(2, '0')}-${String(sunday.getDate()).padStart(2, '0')}`;
  await search(page, { date: sundayText, starts: '13:17', duration: '30' });
  const spaces = await (await page.request.get('http://127.0.0.1:8000/spaces')).json();
  const available = spaces.find((space) => space.name === 'Sala disponible E2E');
  await page.getByTestId(`availability-row-${available.id}`).getByRole('button', { name: 'Solicitar reserva' }).click();
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.getByRole('alert')).toContainText('No se permiten reservas los domingos');
  await expect(page.getByRole('heading', { name: 'Resultados' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);

  await page.getByRole('button', { name: '← Volver al panel' }).click();
  await page.getByRole('button', { name: 'Consultar disponibilidad' }).click();
  await page.route('**/api/availability/spaces/**', (route) => route.abort());
  await search(page, { starts: '16:00', duration: '60' });
  await expect(page.getByRole('alert')).toContainText('No fue posible confirmar la disponibilidad');
  await expect(page.getByText('No confirmado').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);
});

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

async function search(page, { date = bookingDate(), starts = '13:00', ends = '14:00' } = {}) {
  await page.getByLabel('Fecha de consulta').fill(date);
  await page.getByLabel('Hora de inicio').fill(starts);
  await page.getByLabel('Hora de fin').fill(ends);
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
  await search(page, { date });

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
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  await expect(page.getByRole('status')).toContainText('registrada con estado: Pendiente');

  await page.getByRole('button', { name: '← Volver al panel' }).click();
  await openAvailability(page);
  await search(page, { date });
  await expect(page.getByTestId(`availability-row-${availableId}`).getByText('Ocupado', { exact: true })).toBeVisible();
  await expect(page.getByTestId(`availability-row-${availableId}`).getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);
});

test('no presenta disponibilidad si el intervalo es inválido o falla la consulta', async ({ page }) => {
  await signInRequester(page);
  await openAvailability(page);
  await search(page, { starts: '15:00', ends: '14:00' });
  await expect(page.getByRole('alert')).toContainText('El inicio debe ser anterior al fin');
  await expect(page.getByText('No confirmado').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);

  await page.route('**/api/availability/spaces/**', (route) => route.abort());
  await search(page, { starts: '16:00', ends: '17:00' });
  await expect(page.getByRole('alert')).toContainText('No fue posible confirmar la disponibilidad');
  await expect(page.getByText('No confirmado').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Solicitar reserva' })).toHaveCount(0);
});

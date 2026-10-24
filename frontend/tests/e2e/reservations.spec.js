import { expect, test } from '@playwright/test';

function bookingDate() {
  const date = new Date();
  date.setDate(date.getDate() + 5);
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

async function searchAvailable(page, start, durationMinutes, name = 'Sala disponible E2E') {
  await page.getByRole('button', { name: 'Consultar disponibilidad' }).click();
  await page.getByLabel('Fecha de consulta').fill(bookingDate());
  await page.getByLabel('Hora de inicio').fill(start);
  await page.getByLabel('Duración de la reserva').selectOption(String(durationMinutes));
  await page.getByRole('button', { name: 'Consultar disponibilidad' }).click();
  const spaces = await (await page.request.get('http://127.0.0.1:8000/spaces')).json();
  const target = spaces.find((space) => space.name === name);
  const row = page.getByTestId(`availability-row-${target.id}`);
  await expect(row.getByText('Disponible', { exact: true })).toBeVisible();
  await row.getByRole('button', { name: 'Solicitar reserva' }).click();
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
}

test('rechaza el exceso del límite acumulado y conserva las reservas confirmadas', async ({ page }) => {
  await signInRequester(page);
  await page.getByRole('button', { name: 'Mis reservas' }).click();
  await expect(page.getByRole('heading', { name: 'Mis reservas' })).toBeVisible();
  const initialReservations = await page.locator('.reservation-card').count();
  await page.getByRole('button', { name: '← Volver al panel' }).click();
  await searchAvailable(page, '14:00', 210, 'Sala límite E2E');
  await expect(page.getByRole('alert')).toContainText('no puede superar cuatro horas');
  await expect(page.locator('.reservation-card')).toHaveCount(initialReservations);
});

test('consulta, modifica y cancela una reserva propia conservando respuestas reales', async ({ page }) => {
  await signInRequester(page);
  await searchAvailable(page, '16:17', 30);
  await expect(page.getByRole('status')).toContainText('registrada con estado: Pendiente');

  const createdMessage = await page.getByRole('status').textContent();
  const reservationId = createdMessage.match(/Solicitud (\d+)/)[1];
  const reservation = page.getByRole('article').filter({ hasText: `Reserva #${reservationId}` });
  await expect(reservation.getByText('Pendiente')).toBeVisible();
  await reservation.getByRole('button', { name: 'Modificar' }).click();
  await page.getByLabel('Inicio').fill(`${bookingDate()}T17:17`);
  await page.getByLabel('Duración del cambio').selectOption('60');
  await page.getByRole('button', { name: 'Guardar cambio' }).click();
  await expect(page.getByRole('status')).toContainText('Reserva');
  await expect(page.getByRole('alert')).toHaveCount(0);

  page.on('dialog', (dialog) => dialog.accept());
  const updatedReservation = page.getByRole('article').filter({ hasText: `Reserva #${reservationId}` });
  await updatedReservation.getByRole('button', { name: 'Cancelar reserva' }).click();
  await expect(page.getByRole('status')).toContainText('Cancelada');
  await expect(updatedReservation.getByText('Cancelada')).toBeVisible();
});

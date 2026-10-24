import { expect, test } from '@playwright/test';

async function createPendingReservation(page, hour = '10') {
  const login = await page.request.post('http://127.0.0.1:8000/auth/login', { data: {
    institutional_email: 'solicitante.e2e@universidad.edu.co', password: 'clave-solicitante-e2e',
  } });
  const token = (await login.json()).access_token;
  const spaces = await (await page.request.get('http://127.0.0.1:8000/spaces')).json();
  const date = new Date(); date.setDate(date.getDate() + 5);
  while (date.getDay() === 0) date.setDate(date.getDate() + 1);
  const day = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const response = await page.request.post('http://127.0.0.1:8000/reservations', {
    headers: { Authorization: `Bearer ${token}` },
    data: { space_id: spaces.find((space) => space.name === 'Sala disponible E2E').id, starts_at: `${day}T${hour}:00:00`, ends_at: `${day}T${String(Number(hour) + 1).padStart(2, '0')}:00:00` },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return { reservation: await response.json(), day };
}

async function signInApprover(page) {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill('aprobador.e2e@universidad.edu.co');
  await page.getByLabel('Contraseña').fill('clave-aprobador-e2e');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: 'Hola, Ariel' })).toBeVisible();
}

test('muestra solo al aprobador sus bandejas reales y exige motivo para rechazar', async ({ page }) => {
  const { reservation: created } = await createPendingReservation(page);
  await signInApprover(page);
  await page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' }).first().click();
  const request = page.getByRole('article').filter({ hasText: `Solicitud #${created.id}` });
  await expect(request).toBeVisible();
  await request.getByRole('button', { name: 'Rechazar' }).click();
  await expect(page.getByRole('alert')).toContainText('motivo');
  await request.getByRole('textbox', { name: `Motivo para rechazar solicitud ${created.id}` }).fill('La actividad requiere otro espacio.');
  await request.getByRole('button', { name: 'Rechazar' }).click();
  await expect(page.getByRole('status')).toContainText(`Solicitud ${created.id}: rechazada`);
  await expect(request).toHaveCount(0);
});

test('un rol solicitante no ve aprobaciones y el backend rechaza una decisión no autorizada', async ({ page }) => {
  const { reservation: created } = await createPendingReservation(page, '11');
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill('solicitante.e2e@universidad.edu.co');
  await page.getByLabel('Contraseña').fill('clave-solicitante-e2e');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: 'Solicitante' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' })).toHaveCount(0);
  const login = await page.request.post('http://127.0.0.1:8000/auth/login', { data: {
    institutional_email: 'solicitante.e2e@universidad.edu.co', password: 'clave-solicitante-e2e',
  } });
  const token = (await login.json()).access_token;
  const denied = await page.request.post(`http://127.0.0.1:8000/approvals/reservations/${created.id}/decision`, {
    headers: { Authorization: `Bearer ${token}` }, data: { decision: 'approve' },
  });
  expect(denied.status()).toBe(403);
});

test('presenta y aplica un cambio de horario conservando la reserva original hasta la decisión', async ({ page }) => {
  const { reservation, day } = await createPendingReservation(page, '12');
  const approverLogin = await page.request.post('http://127.0.0.1:8000/auth/login', { data: {
    institutional_email: 'aprobador.e2e@universidad.edu.co', password: 'clave-aprobador-e2e',
  } });
  const approverToken = (await approverLogin.json()).access_token;
  const initialApproval = await page.request.post(`http://127.0.0.1:8000/approvals/reservations/${reservation.id}/decision`, {
    headers: { Authorization: `Bearer ${approverToken}` }, data: { decision: 'approve' },
  });
  expect(initialApproval.ok()).toBeTruthy();

  const requesterLogin = await page.request.post('http://127.0.0.1:8000/auth/login', { data: {
    institutional_email: 'solicitante.e2e@universidad.edu.co', password: 'clave-solicitante-e2e',
  } });
  const requesterToken = (await requesterLogin.json()).access_token;
  const nextDate = new Date(`${day}T12:00:00`); nextDate.setDate(nextDate.getDate() + 1);
  const proposedDay = `${nextDate.getFullYear()}-${String(nextDate.getMonth() + 1).padStart(2, '0')}-${String(nextDate.getDate()).padStart(2, '0')}`;
  const changeResponse = await page.request.put(`http://127.0.0.1:8000/reservations/${reservation.id}`, {
    headers: { Authorization: `Bearer ${requesterToken}` },
    data: { starts_at: `${proposedDay}T12:00:00`, ends_at: `${proposedDay}T13:00:00` },
  });
  expect(changeResponse.ok()).toBeTruthy();
  const changed = await changeResponse.json();
  expect(changed.pending_change).not.toBeNull();
  expect(changed.starts_at_utc).toContain(`${day}T`);

  await signInApprover(page);
  await page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' }).first().click();
  const changeCard = page.getByRole('article').filter({ hasText: `Cambio #${changed.pending_change.id}` });
  await expect(changeCard).toContainText('Horario vigente:');
  await expect(changeCard).toContainText('Horario propuesto:');
  await changeCard.getByRole('button', { name: 'Aprobar' }).click();
  await expect(page.getByRole('status')).toContainText(`Cambio ${changed.pending_change.id}: aprobado`);
});

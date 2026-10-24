import { expect, test } from '@playwright/test';

const accounts = {
  administrator: ['admin.e2e@universidad.edu.co', 'clave-admin-e2e-larga', 'Admin'],
  requester: ['solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e', 'Ana'],
  approver: ['aprobador.e2e@universidad.edu.co', 'clave-aprobador-e2e', 'Ariel'],
};

async function signIn(page, role) {
  const [email, password, firstName] = accounts[role];
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: `Hola, ${firstName}` })).toBeVisible();
}

async function tokenFor(page, role) {
  const [institutional_email, password] = accounts[role];
  const response = await page.request.post('http://127.0.0.1:8000/auth/login', {
    data: { institutional_email, password },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token;
}

test('cada rol ve sus ventanas autorizadas y comparte las consultas comunes', async ({ page }) => {
  await signIn(page, 'administrator');
  await expect(page.getByRole('button', { name: 'Administrar cuentas de usuario' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mis reservas' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Consultar espacios académicos' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Consultar disponibilidad' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Consultar historial autorizado' })).toBeVisible();
  const administratorToken = await tokenFor(page, 'administrator');
  expect((await page.request.get('http://127.0.0.1:8000/users', {
    headers: { Authorization: `Bearer ${administratorToken}` },
  })).status()).toBe(200);

  await signIn(page, 'requester');
  await expect(page.getByRole('button', { name: 'Mis reservas' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Administrar cuentas de usuario' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' })).toHaveCount(0);
  const requesterToken = await tokenFor(page, 'requester');
  expect((await page.request.get('http://127.0.0.1:8000/users', {
    headers: { Authorization: `Bearer ${requesterToken}` },
  })).status()).toBe(403);
  expect((await page.request.get('http://127.0.0.1:8000/approvals/pending', {
    headers: { Authorization: `Bearer ${requesterToken}` },
  })).status()).toBe(403);

  await signIn(page, 'approver');
  await expect(page.getByRole('button', { name: 'Revisar solicitudes y cambios pendientes' })).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Administrar cuentas de usuario' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Mis reservas' })).toHaveCount(0);
  const approverToken = await tokenFor(page, 'approver');
  expect((await page.request.get('http://127.0.0.1:8000/approvals/pending', {
    headers: { Authorization: `Bearer ${approverToken}` },
  })).status()).toBe(200);
  expect((await page.request.get('http://127.0.0.1:8000/users', {
    headers: { Authorization: `Bearer ${approverToken}` },
  })).status()).toBe(403);
});

test('una URL directa de una ventana protegida no muestra contenido sin sesión', async ({ page }) => {
  for (const path of ['/users', '/approvals', '/reservations', '/history']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Cuentas de usuario' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Aprobaciones' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Mis reservas' })).toHaveCount(0);
  }
});

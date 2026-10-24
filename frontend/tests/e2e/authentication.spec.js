import { expect, test } from '@playwright/test';

async function signIn(page, email, password) {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
}

test('rechaza credenciales inválidas y cuentas inactivas del backend', async ({ page }) => {
  await signIn(page, 'inactiva.e2e@universidad.edu.co', 'clave-inactiva-e2e');
  await expect(page.getByRole('alert')).toContainText('cuenta está inactiva');
  await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();

  await page.getByLabel('Correo institucional').fill('admin.e2e@universidad.edu.co');
  await page.getByLabel('Contraseña').fill('contraseña-incorrecta');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('alert')).toContainText('Correo o contraseña incorrectos');
});

test('abre el panel administrativo con datos reales y cierra sesión en el servicio', async ({ page }) => {
  await signIn(page, 'admin.e2e@universidad.edu.co', 'clave-admin-e2e-larga');
  await expect(page.getByRole('heading', { name: 'Hola, Admin' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Administrador' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Resumen de actividad' }).getByText('Cuentas de usuario')).toBeVisible();
  const summary = page.getByRole('region', { name: 'Resumen de actividad' });
  await expect(summary.locator('.summary-card').filter({ hasText: 'Espacios registrados' }).getByText('4', { exact: true })).toBeVisible();
  await expect(summary.locator('.summary-card').filter({ hasText: 'Cuentas de usuario' }).getByText('4', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();
  await expect(page.getByLabel('Contraseña')).toBeVisible();
});

test('presenta el panel de solicitante con el resumen de sus reservas', async ({ page }) => {
  await signIn(page, 'solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e');
  await expect(page.getByRole('heading', { name: 'Hola, Ana' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Solicitante' })).toBeVisible();
  await expect(page.getByText('Reservas pendientes')).toBeVisible();
  await expect(page.getByText('Reservas aprobadas')).toBeVisible();
});

test('presenta el panel de aprobador con sus bandejas reales', async ({ page }) => {
  await signIn(page, 'aprobador.e2e@universidad.edu.co', 'clave-aprobador-e2e');
  await expect(page.getByRole('heading', { name: 'Hola, Ariel' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Aprobador' })).toBeVisible();
  const summary = page.getByRole('region', { name: 'Resumen de actividad' });
  await expect(summary.getByText('Solicitudes pendientes')).toBeVisible();
  await expect(summary.getByText('Cambios por revisar')).toBeVisible();
});

test('muestra un mensaje claro si no se puede conectar al servicio', async ({ page }) => {
  await page.route('**/api/auth/login', (route) => route.abort());
  await signIn(page, 'admin.e2e@universidad.edu.co', 'clave-admin-e2e-larga');
  await expect(page.getByRole('alert')).toContainText('No fue posible conectar con el sistema');
});

test('retira la sesión y solicita volver a ingresar cuando el servicio responde 401', async ({ page }) => {
  await page.route('**/api/reservations', (route) => route.fulfill({
    status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'La sesión venció' }),
  }));
  await signIn(page, 'solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e');
  await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Tu sesión venció');
});

import { expect, test } from '@playwright/test';

async function signIn(page, email, password, heading) {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: heading })).toBeVisible();
}

test('el historial muestra eventos permitidos y aplica filtros del servicio', async ({ page }) => {
  await signIn(page, 'admin.e2e@universidad.edu.co', 'clave-admin-e2e-larga', 'Administrador');
  await page.getByRole('button', { name: 'Consultar historial autorizado' }).click();
  await expect(page.getByRole('heading', { name: 'Historial autorizado' })).toBeVisible();
  await expect(page.getByRole('table').getByText('space_created').first()).toBeVisible();
  await page.getByLabel('Tipo de entidad').selectOption('space');
  await page.getByLabel('Identificador de entidad').fill('1');
  await page.getByRole('button', { name: 'Aplicar filtros' }).click();
  await expect(page.getByRole('table').getByText('Espacio #1').first()).toBeVisible();

  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await signIn(page, 'solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e', 'Solicitante');
  await page.getByRole('button', { name: 'Consultar historial autorizado' }).click();
  await expect(page.getByRole('table').getByText('reservation_created').first()).toBeVisible();
  await expect(page.getByRole('table').getByText('Espacio #1')).toHaveCount(0);

  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await signIn(page, 'aprobador.e2e@universidad.edu.co', 'clave-aprobador-e2e', 'Aprobador');
  await page.getByRole('button', { name: 'Consultar historial autorizado' }).click();
  await expect(page.getByRole('table').getByText('reservation_created').first()).toBeVisible();
  await expect(page.getByRole('table').getByText('Usuario #', { exact: false })).toHaveCount(0);
});

import { expect, test } from '@playwright/test';

async function signIn(page, email = 'admin.e2e@universidad.edu.co', password = 'clave-admin-e2e-larga') {
  await page.goto('/');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: /Hola,/ })).toBeVisible();
}

async function openUsers(page) {
  await page.getByRole('button', { name: 'Administrar cuentas de usuario' }).click();
  await expect(page.getByRole('heading', { name: 'Cuentas de usuario' })).toBeVisible();
}

async function adminToken(page) {
  const response = await page.request.post('http://127.0.0.1:8000/auth/login', {
    data: { institutional_email: 'admin.e2e@universidad.edu.co', password: 'clave-admin-e2e-larga' },
  });
  return (await response.json()).access_token;
}

test('crea cuentas inactivas, comunica errores y permite activarlas para iniciar sesión', async ({ page }) => {
  await signIn(page);
  await openUsers(page);
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  const form = page.getByRole('region', { name: 'Nueva cuenta' });
  await form.getByLabel('Nombre completo').fill('Cuenta de Prueba UI');
  await form.getByLabel('Correo institucional').fill('prueba.ui@universidad.edu.co');
  await form.getByLabel('Identificación').fill('UI-ACCOUNT-1');
  await form.getByLabel('Contraseña inicial').fill('clave-de-prueba-ui');
  await form.getByLabel('Rol inicial').selectOption('requester');
  await form.getByRole('button', { name: 'Crear cuenta inactiva' }).click();
  await expect(page.getByRole('status')).toContainText('Cuenta creada como inactiva');

  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  const duplicateForm = page.getByRole('region', { name: 'Nueva cuenta' });
  await duplicateForm.getByLabel('Nombre completo').fill('Cuenta Duplicada');
  await duplicateForm.getByLabel('Correo institucional').fill('admin.e2e@universidad.edu.co');
  await duplicateForm.getByLabel('Identificación').fill('UI-ACCOUNT-DUPLICATE');
  await duplicateForm.getByLabel('Contraseña inicial').fill('clave-de-prueba-ui');
  await duplicateForm.getByRole('button', { name: 'Crear cuenta inactiva' }).click();
  await expect(page.getByRole('alert')).toContainText('El correo institucional ya está registrado');
  await expect(duplicateForm.getByLabel('Nombre completo')).toHaveValue('Cuenta Duplicada');
  await page.getByRole('button', { name: 'Cerrar formulario' }).click();

  const account = page.getByRole('article').filter({ hasText: 'prueba.ui@universidad.edu.co' });
  await expect(account.getByText('Inactiva')).toBeVisible();
  await account.getByRole('button', { name: 'Activar' }).click();
  await expect(page.getByRole('status')).toContainText('ahora está activo');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await page.getByLabel('Correo institucional').fill('prueba.ui@universidad.edu.co');
  await page.getByLabel('Contraseña').fill('clave-de-prueba-ui');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page.getByRole('heading', { name: 'Hola, Cuenta' })).toBeVisible();
});

test('edita perfil y rol, asigna y retira un aprobador de un espacio', async ({ page }) => {
  await signIn(page);
  const token = await adminToken(page);
  const spaceResponse = await page.request.post('http://127.0.0.1:8000/spaces', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      name: 'Espacio de Asignación UI', type: 'Aula', capacity: 18,
      location: 'Edificio de pruebas', equipment: [], is_active: true, requires_approval: true,
    },
  });
  expect(spaceResponse.ok(), await spaceResponse.text()).toBeTruthy();
  const space = await spaceResponse.json();

  await openUsers(page);
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  const form = page.getByRole('region', { name: 'Nueva cuenta' });
  await form.getByLabel('Nombre completo').fill('Aprobador UI');
  await form.getByLabel('Correo institucional').fill('aprobador.ui@universidad.edu.co');
  await form.getByLabel('Identificación').fill('UI-APPROVER-1');
  await form.getByLabel('Contraseña inicial').fill('clave-aprobador-ui');
  await form.getByLabel('Rol inicial').selectOption('requester');
  await form.getByRole('button', { name: 'Crear cuenta inactiva' }).click();
  const account = page.getByRole('article').filter({ hasText: 'aprobador.ui@universidad.edu.co' });
  await account.getByRole('button', { name: 'Editar perfil' }).click();
  const editForm = page.locator('.user-edit-form');
  await editForm.getByLabel('Nombre completo').fill('Ariel Aprobador UI');
  await editForm.getByLabel('Correo institucional').fill('ariel.aprobador.ui@universidad.edu.co');
  await editForm.getByLabel('Identificación').fill('UI-APPROVER-2');
  await editForm.getByRole('button', { name: 'Guardar datos' }).click();
  await expect(page.getByRole('status')).toContainText('Datos de Ariel Aprobador UI actualizados');

  const updatedAccount = page.getByRole('article').filter({ hasText: 'ariel.aprobador.ui@universidad.edu.co' });
  await updatedAccount.getByLabel('Rol de Ariel Aprobador UI').selectOption('approver');
  await expect(page.getByRole('status')).toContainText('actualizado a Aprobador');
  await updatedAccount.getByRole('button', { name: 'Activar' }).click();

  await page.getByRole('combobox', { name: 'Espacio para asignaciones' }).selectOption(String(space.id));
  const accounts = await (await page.request.get('http://127.0.0.1:8000/users', {
    headers: { Authorization: `Bearer ${token}` },
  })).json();
  const approver = accounts.find((user) => user.institutional_email === 'ariel.aprobador.ui@universidad.edu.co');
  await page.getByRole('combobox', { name: 'Cuenta de aprobador' }).selectOption(String(approver.id));
  await page.getByRole('button', { name: 'Asignar' }).click();
  await expect(page.getByText('Aprobador asignado al espacio.')).toBeVisible();
  await expect(page.getByText('ariel.aprobador.ui@universidad.edu.co · Activa', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '← Volver al panel' }).click();
  await openUsers(page);
  await page.getByRole('combobox', { name: 'Espacio para asignaciones' }).selectOption(String(space.id));
  await expect(page.getByText('ariel.aprobador.ui@universidad.edu.co · Activa', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Retirar asignación' }).click();
  await expect(page.getByText('Se retiró a Ariel Aprobador UI del espacio.')).toBeVisible();
  await expect(page.getByText('Este espacio no tiene aprobadores asignados.')).toBeVisible();
});

test('el solicitante no ve acceso a la administración de cuentas', async ({ page }) => {
  await signIn(page, 'solicitante.e2e@universidad.edu.co', 'clave-solicitante-e2e');
  await expect(page.getByRole('button', { name: 'Administrar cuentas de usuario' })).toHaveCount(0);
});

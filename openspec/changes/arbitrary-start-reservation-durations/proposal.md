# Proposal

## Why

La búsqueda actual permite elegir horas arbitrarias, pero el backend rechaza reservas si el inicio no cae en `:00` o `:30`. Se necesita que el inicio pueda elegirse a cualquier minuto y que la duración se seleccione en tramos de 30 minutos, para que disponibilidad, solicitud y validación del servidor sean coherentes.

## What Changes

- Reemplazar la alineación obligatoria del inicio y fin con el reloj por una hora de inicio con precisión de minuto.
- Mantener duraciones como múltiplos de 30 minutos y ofrecer opciones de 30 minutos hasta 4 horas.
- Mantener las restricciones de horario, anticipación, disponibilidad y límite acumulado consecutivo de cuatro horas por usuario y espacio.
- Actualizar la consulta de disponibilidad y el formulario de reserva para calcular el fin desde el inicio y la duración seleccionada.
- Actualizar las pruebas de política, API y Playwright para intervalos con inicios arbitrarios y duraciones alineadas.

## Capabilities

### New Capabilities

- `flexible-reservation-starts`: selección de inicio a cualquier minuto con duración en múltiplos de 30 minutos, hasta cuatro horas.

### Modified Capabilities

No hay capacidades publicadas en `openspec/specs/`. Esta capacidad reemplaza el requisito de alineación del inicio y fin a `:00` o `:30` definido en `initial-academic-reservations`; las demás políticas existentes permanecen vigentes.

## Impact

Backend: `backend/politicas/validation.py`, servicios de reservas y pruebas en `backend/tests/test_policies.py`, `test_reservations.py` y `test_integration_workflow.py`. Frontend: `AvailabilityPage.jsx`, `ReservationsPage.jsx` y sus pruebas Playwright. No requiere cambios de base de datos ni endpoints nuevos. `PLAN_INGENIERIA.md` no se modifica.

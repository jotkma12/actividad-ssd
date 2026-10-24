# Proposal

## Why

La institución requiere limitar a cuatro horas consecutivas el tiempo que cada usuario puede reservar un mismo espacio. El comportamiento documentado y probado actualmente permite reservas mayores, así que debe cambiarse antes de que el límite pueda aplicarse en el sistema.

## What Changes

- **BREAKING:** limitar a cuatro horas consecutivas la suma de reservas pendientes y aprobadas del mismo usuario para el mismo espacio cuando sus intervalos se tocan exactamente.
- Reiniciar el cómputo cuando exista una pausa; no acumular reservas del usuario en espacios diferentes.
- Comprobar el límite al crear o modificar una reserva y al aprobar un cambio de horario pendiente.
- Tratar el intervalo propuesto para un cambio pendiente como alternativa al intervalo original, sin contar ambos a la vez. Si la aprobación supera el límite, conservar la reserva original aprobada y su horario.
- Reemplazar en las especificaciones y pruebas los ejemplos que permiten reservas de más de cuatro horas.
- Conservar sin cambios las reservas existentes que superen el límite; aplicar la regla a nuevas reservas y modificaciones posteriores. Rechazar una modificación incompatible y conservar la reserva original.

## Capabilities

No hay capacidades publicadas en `openspec/specs/`. El cambio inicial completado define estas capacidades en sus deltas, aún no sincronizados. Se reutilizan las mismas rutas para conservar sus responsabilidades:

### New Capabilities

- `policies`: definir el máximo de cuatro horas consecutivas y cómo se agregan intervalos.
- `reservations`: exigir la regla al crear y modificar reservas.
- `approvals`: volver a validar el intervalo alternativo cuando se aprueba un cambio pendiente.

### Modified Capabilities

Ninguna capacidad está publicada actualmente en `openspec/specs/`; los deltas de este cambio agregan requisitos a las capacidades descritas en el cambio inicial.

## Impact

La implementación afecta el validador compartido `backend/politicas/validation.py`, las operaciones de creación y modificación en `backend/reservas/service.py`, y la aprobación de cambios pendientes en `backend/aprobaciones/service.py`. La acumulación entre varias reservas se comprueba con los datos existentes dentro de la transacción SQLite que protege la operación. Los casos anteriores que aceptaban cinco horas y una jornada completa se reemplazaron por `test_rejects_five_hour_reservation_under_consecutive_limit` y `test_rejects_full_allowed_day_under_consecutive_limit`, además de las pruebas de secuencias consecutivas. No se requieren cambios de esquema ni integraciones nuevas. Las reservas ya existentes que excedan el límite se conservarán; si se intenta modificarlas y el resultado propuesto incumple la regla, se rechazará el cambio y la reserva original quedará intacta.

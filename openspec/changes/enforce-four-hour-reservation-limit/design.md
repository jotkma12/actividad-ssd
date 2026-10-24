# Design

## Context

La regla actual se valida en `backend/politicas/validation.py`, que conoce el intervalo candidato, pero no consulta otras reservas. `create_reservation` y `update_reservation` ya serializan escrituras con SQLite; la aprobación de un cambio pendiente también usa una transacción `BEGIN IMMEDIATE`. Las fechas se guardan en UTC y la regla de calendario se interpreta en `America/Bogota`.

## Goals / Non-Goals

**Goals:**

- Calcular la secuencia de reservas activas del mismo usuario y espacio con los datos más recientes dentro de la transacción que persiste la operación.
- Aplicar el mismo criterio a creación, modificación y aprobación de cambios de horario.
- Mantener la reserva original y el cambio propuesto como alternativas mientras el cambio espera decisión.

**Non-Goals:**

- Limitar el tiempo reservado por una persona entre espacios diferentes.
- Cambiar políticas de horario, anticipación, cancelación o disponibilidad.
- Migrar, cancelar o modificar automáticamente reservas existentes que superen cuatro horas consecutivas.
- Añadir tablas, servicios externos o dependencias.

## Decisions

### Cálculo de la secuencia

Se considerarán únicamente reservas `pending` y `approved` del mismo usuario y espacio. Los intervalos se ordenarán por inicio y solo formarán una misma secuencia cuando el fin de uno coincida exactamente con el inicio del siguiente. Cualquier pausa inicia otra secuencia. La comparación se hará sobre los instantes UTC que ya almacena la aplicación. Una secuencia de cuatro horas exactas es válida; cualquier duración mayor no lo es.

El intervalo candidato de una creación se agrega a las reservas activas de ese usuario y espacio. En una modificación, la reserva que se modifica se excluye de los intervalos existentes y se agrega el horario candidato; así no se suman la versión anterior y la nueva de la misma reserva.

### Transacción y concurrencia

La consulta de intervalos activos y el guardado o decisión se harán bajo la misma transacción de escritura SQLite existente. Así, dos operaciones simultáneas para el mismo usuario y espacio no pueden validar ambas contra un conjunto obsoleto y superar juntas el límite. Las operaciones en espacios diferentes se evalúan de manera independiente.

### Cambios de horario con aprobación

Al solicitar el cambio se calculará la secuencia con el intervalo propuesto en lugar del intervalo original. Al aprobar, se repetirá el cálculo dentro de la transacción decisoria, excluyendo el intervalo original e insertando como candidato el propuesto. Si el resultado supera cuatro horas, la transacción no sustituirá el intervalo original; conforme al comportamiento transaccional actual, el intento fallido no resuelve el cambio pendiente. La solicitud de cambio no debe sumar simultáneamente ambos intervalos al calcular la duración.

La validación al aprobar es necesaria aunque la solicitud haya pasado al crearse: reservas nuevas o cambios simultáneos podrían alterar desde entonces la secuencia del usuario.

### Reservas existentes

La regla anterior permitía duraciones superiores a cuatro horas. Esas reservas se conservarán vigentes sin cancelación ni modificación automática. El límite nuevo se aplicará a las reservas nuevas y a las modificaciones realizadas después de implementar la regla. Si una modificación propuesta para una reserva existente deja una secuencia superior a cuatro horas, se rechazará y la reserva original conservará su estado e intervalo. Una reserva existente que ya exceda el límite seguirá vigente mientras no se intente una modificación incompatible.

## Risks / Trade-offs

- [La consulta del usuario y espacio puede crecer con el historial] → Usar la consulta dentro de la transacción y evaluar un índice solo si las mediciones lo requieren; no cambiar el esquema de antemano.
- [Escrituras paralelas podrían superar el límite si la suma se calcula fuera de la transacción] → Mantener consulta, validación y persistencia dentro del `BEGIN IMMEDIATE` existente.
- [Registros antiguos pueden exceder la nueva regla] → Conservarlos sin cambios y comprobar que toda modificación posterior cumpla el límite; no ejecutar cancelaciones ni ajustes automáticos.
- [El aprobador puede revisar un cambio que dejó de cumplir el límite por otras reservas] → Revalidar al decidir y conservar el intervalo original cuando la aprobación no sea válida.

## Migration Plan

No se espera una migración de esquema. Las reservas preexistentes que excedan el máximo se conservan tal como están. Las futuras solicitudes y modificaciones aplicarán el límite en las transacciones existentes; una modificación que incumpla la regla no alterará la reserva original.

## Open Questions

No quedan decisiones de negocio abiertas para este cambio.

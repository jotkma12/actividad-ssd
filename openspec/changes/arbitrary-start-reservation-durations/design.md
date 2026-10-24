# Design

## Context

El backend centraliza la validación en `backend/politicas/validation.py`: actualmente exige minuto `:00`/`:30` tanto para inicio como fin, además de duraciones múltiplos de 30 minutos. La vista React de disponibilidad tiene dos controles de hora independientes y deriva el borrador directamente del intervalo consultado. No se requiere migración de datos ni endpoint nuevo.

## Goals / Non-Goals

**Goals:**

- Hacer que el backend acepte cualquier minuto de inicio con precisión de minuto y duración en múltiplos de 30 minutos, máximo cuatro horas por solicitud.
- Hacer que la interfaz seleccione inicio y duración y calcule el fin coherentemente para consulta y reserva.
- Conservar las políticas diarias, anticipación, conflictos y límite consecutivo acumulado de cuatro horas.

**Non-Goals:**

- Permitir segundos, duraciones de 15 o 45 minutos, reservas que crucen medianoche o cambios a reglas de anticipación y días/horarios permitidos.
- Cambiar esquemas de SQLite o introducir endpoints/dependencias.

## Decisions

- Mantener `BLOCK_MINUTES = 30` para validar la duración; retirar solo la alineación de cada extremo al reloj. Se conservará la precisión a minuto, rechazando segundos y microsegundos no nulos.
- La interfaz tendrá un campo `datetime-local` o fecha más inicio con minuto libre y un selector de duraciones 30–240 en pasos de 30; calculará el fin a partir de estos valores. La consulta de disponibilidad y el borrador de reserva compartirán el mismo intervalo calculado.
- El límite de duración individual de cuatro horas se comprueba en la política del servidor, mientras el validador consecutivo existente sigue comprobando las reservas contiguas del mismo usuario y espacio. La interfaz nunca reemplaza esos controles.
- Las pruebas modificarán los casos de alineación de extremos para demostrar aceptación de inicios arbitrarios, conservarán rechazo de duración de 45 minutos y probarán máximo individual/acumulado.

## Risks / Trade-offs

- Una consulta puede extenderse más allá del cierre diario al sumar duración al inicio → el servicio seguirá rechazando ese intervalo y la interfaz presentará su error; el selector no altera el horario institucional.
- Un cliente antiguo puede seguir ofreciendo un extremo separado → el backend acepta únicamente lo definido en la especificación y sigue aplicando duración y políticas.

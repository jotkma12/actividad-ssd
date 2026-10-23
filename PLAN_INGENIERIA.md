# Plan de ingeniería de software
## Sistema de gestión de reservas de espacios académicos

## 1. Análisis del problema

### 1.1 ¿Cuál es el problema?

Actualmente, la universidad gestiona las reservas de laboratorios, auditorios y salas de cómputo mediante correos electrónicos y hojas de cálculo. Esta forma de trabajo puede generar varios problemas:

- **Solicitudes repetidas:** una misma persona puede enviar varias solicitudes y no queda claro cuál es la válida.
- **Choques de horario:** dos personas pueden solicitar el mismo espacio para la misma fecha y hora.
- **Poca visibilidad:** para saber si un espacio está libre, hay que preguntar y esperar una respuesta.
- **Falta de historial:** puede ser difícil saber quién aprobó, canceló o modificó una reserva.
- **Reglas diferentes:** las solicitudes pueden atenderse de distintas maneras según la persona que las gestione.

### 1.2 ¿Qué necesita la institución?

El sistema debe permitir:

1. Consultar un listado de espacios con información como tipo, capacidad, ubicación y equipos disponibles.
2. Revisar qué espacios están libres para una fecha y una hora determinadas.
3. Solicitar reservas sin permitir que se crucen con otras reservas activas.
4. Aprobar o rechazar las solicitudes que lo necesiten.
5. Modificar o cancelar reservas según las reglas establecidas.
6. Consultar el historial de las reservas y sus cambios.
7. Asignar permisos diferentes según el tipo de usuario.
8. Bloquear espacios temporalmente cuando estén en mantenimiento.


### 1.3 ¿Quiénes participan?

| Actor | Responsabilidades |
|---|---|
| **Solicitante** (docente, personal o estudiante autorizado) | Consultar espacios, solicitar reservas y gestionar sus propias reservas según las reglas del sistema. |
| **Aprobador** (coordinador del espacio) | Revisar solicitudes y aprobarlas o rechazarlas cuando corresponda. |
| **Administrador** | Gestionar espacios, usuarios, permisos y bloqueos por mantenimiento. |
| **Directivo o auditor** | Consultar reportes sobre el uso de los espacios, de acuerdo con sus permisos. |

### 1.4 Alcance y limitaciones

#### Incluye por ahora

- Registro e inicio de sesión de usuarios.
- Roles y permisos.
- Gestión de espacios académicos.
- Consulta de disponibilidad mediante un calendario.
- Creación, aprobación, rechazo, modificación y cancelación de reservas.
- Prevención de reservas que se crucen en el mismo espacio.
- Bloqueos de espacios por mantenimiento.
- Historial de cambios.
- Reportes básicos de uso, si el tiempo de desarrollo lo permite.

#### No incluye por ahora

- Conexión con el sistema de notas o con los horarios académicos de la universidad.
- Cobros por el uso de los espacios.
- Apertura o cierre físico de puertas.
- Aplicación móvil instalada en el teléfono. La página web sí se adaptará a pantallas pequeñas.
- Reserva de equipos por separado, como proyectores o computadores portátiles.
- Avisos automáticos por correo. Se podrán considerar para más adelante.

#### Limitaciones y supuestos

- Es un proyecto académico individual y tiene un tiempo limitado de desarrollo.
- Se dará prioridad a las funciones principales y a que estén bien probadas.
- Se supone que el sistema se usará inicialmente en un solo campus y con la hora de Colombia.
- Se espera un uso moderado, con cientos de espacios y miles de reservas por semestre.
- Las reservas se realizarán en bloques de 30 minutos.
- Las reglas sobre la duración máxima, la anticipación necesaria y los plazos de cancelación se definirán antes de implementar las funciones correspondientes.

---

## 2. Propuesta de solución

### 2.1 Descripción general

Se propone crear una página web donde las personas puedan consultar los espacios disponibles y gestionar sus reservas. El sistema tendrá un servidor que revisará las reglas y una base de datos donde se guardará la información.

Se utilizará SQLite, que guarda los datos en un archivo y es sencilla de configurar.

```text
Usuario
   |
   v
Página web
   |
   v
Servidor: valida las reglas y procesa las solicitudes
   |
   v
Base de datos SQLite
```

#### Estados de una reserva

Una reserva podrá pasar por los siguientes estados:

- **Pendiente:** espera la decisión de una persona autorizada.
- **Aprobada:** la solicitud fue aceptada.
- **Rechazada:** la solicitud no fue aceptada.
- **Cancelada:** una reserva fue cancelada.
- **Finalizada:** la reserva ya terminó.

Los espacios que no requieren aprobación podrán pasar directamente a **Aprobada**. Los que sí la requieren permanecerán como **Pendiente** hasta que una persona autorizada tome una decisión.

Las reservas pendientes y aprobadas bloquearán temporalmente el horario para evitar que otra persona solicite el mismo espacio al mismo tiempo. Si una solicitud se rechaza o una reserva se cancela, el horario volverá a estar disponible, siempre que no exista otra reserva activa que lo ocupe.

### 2.2 Funcionalidades prioritarias

| Prioridad | Funcionalidad |
|---|---|
| Indispensable | Inicio de sesión, usuarios, roles y permisos. |
| Indispensable | Listado y consulta de espacios. |
| Indispensable | Consultar disponibilidad. |
| Indispensable | Crear y cancelar reservas. |
| Indispensable | Evitar reservas con horarios cruzados. |
| Importante | Aprobar y rechazar solicitudes. |
| Importante | Modificar reservas. |
| Importante | Consultar el historial de cambios. |
| Importante | Bloquear espacios por mantenimiento. |
| Deseable | Consultar reportes básicos de uso. |
| Para una versión posterior | Enviar avisos automáticos por correo. |

### 2.3 Módulos del sistema

| Módulo | Para qué sirve |
|---|---|
| **Usuarios y permisos** | Gestionar el acceso y definir qué puede hacer cada tipo de usuario. |
| **Espacios** | Registrar y administrar laboratorios, auditorios y salas. |
| **Disponibilidad** | Mostrar los horarios libres, ocupados y bloqueados. |
| **Reservas** | Crear, modificar y cancelar reservas, evitando cruces de horario. |
| **Aprobaciones** | Permitir que las personas autorizadas revisen solicitudes. |
| **Historial** | Guardar quién realizó una acción y cuándo ocurrió. |
| **Reportes** | Mostrar información básica sobre el uso de los espacios. |

La organización del código servirá como guía para definir las capacidades de OpenSpec. No es obligatorio que cada módulo tenga una capacidad independiente: la división se decidirá según las responsabilidades de cada parte del sistema.

### 2.4 Desarrollo progresivo

| Paso | Resultado esperado |
|---|---|
| 1. Preparación | Proyecto organizado y con una base que pueda ejecutarse. |
| 2. Usuarios y permisos | Inicio de sesión y control de acceso. |
| 3. Espacios | Crear, consultar, editar y desactivar espacios. |
| 4. Reservas | Crear y cancelar reservas sin cruces de horario. |
| 5. Disponibilidad | Consultar horarios libres y ocupados. |
| 6. Aprobaciones | Aprobar o rechazar las solicitudes que lo necesiten. |
| 7. Historial y modificaciones | Registrar cambios y permitir modificaciones autorizadas. |
| 8. Cierre y mejoras | Bloqueos por mantenimiento, reportes, pruebas finales y documentación. |

---

## 3. Decisiones de arquitectura y tecnología

### 3.1 Arquitectura elegida

Se utilizará una sola aplicación organizada en módulos. Esto significa que el sistema funcionará como una unidad, pero el código estará separado por responsabilidades para que sea más fácil de entender y mantener.

**¿Por qué se elige esta opción?**

- El proyecto está pensado inicialmente para una sola institución.
- Una sola persona desarrollará el sistema.
- Es más sencillo de instalar, probar y corregir que una solución formada por muchos servicios separados.
- Permite trabajar cada parte por etapas sin perder de vista el funcionamiento general.

### 3.2 Tecnologías propuestas

| Parte | Tecnología | Motivo |
|---|---|---|
| Servidor | Python y FastAPI | Permite crear las funciones del sistema y validar los datos recibidos. |
| Base de datos | SQLite | Guarda la información en un archivo y es sencilla de configurar. |
| Página web | React | Facilita crear pantallas interactivas, como el calendario de reservas. |
| Pruebas del servidor | pytest | Permite comprobar automáticamente las reglas del sistema. |
| Pruebas de la página web | Playwright | Permite probar recorridos completos, como iniciar sesión y hacer una reserva. |
| Control de versiones | Git y GitHub | Permite guardar los cambios y recuperar versiones anteriores del proyecto. |
| Especificaciones | OpenSpec | Ayuda a definir y revisar lo que debe hacer el sistema antes de programarlo. |

### 3.3 Cómo se guardarán los datos

La información se guardará en un archivo de base de datos SQLite. Las principales tablas previstas son:

- Usuarios.
- Espacios.
- Reservas.
- Bloqueos por mantenimiento.
- Historial de eventos.

Se tendrán en cuenta las siguientes decisiones:

**Las reservas no se borrarán normalmente.** Cuando una reserva se cancele o se rechace, se actualizará su estado para conservar el registro de lo ocurrido.

**Las fechas y horas tendrán un formato uniforme.** Los momentos se guardarán en UTC y se mostrarán en la hora de Colombia. La aplicación interpretará las fechas ingresadas usando la zona `America/Bogota`.

**Se evitarán los cruces de horario.** Antes de guardar una reserva, el sistema revisará si ya existe una reserva activa para el mismo espacio y horario. Esta revisión y el registro se harán dentro de una misma operación de base de datos para reducir el riesgo de que dos solicitudes simultáneas sean aceptadas.

La aplicación utilizará una transacción que adquiera el bloqueo de escritura antes de comprobar la disponibilidad, mediante una opción de SQLite como `BEGIN IMMEDIATE`. Si otra operación mantiene ocupada la base de datos, el sistema gestionará la espera o mostrará un mensaje claro, sin guardar una reserva incorrecta.

Dos reservas se cruzan cuando la hora de inicio de una ocurre antes de que termine la otra y la hora de finalización de la primera ocurre después del inicio de la segunda. Por tanto, una reserva que termina a las 10:00 y otra que empieza a las 10:00 pueden estar una después de la otra sin considerarse cruzadas.

Las reservas pendientes y aprobadas se considerarán activas para revisar la disponibilidad. Las reservas rechazadas, canceladas o finalizadas no bloquearán nuevos horarios.

**Se harán copias de seguridad.** Como los datos estarán en un archivo, se establecerá una rutina de respaldo. No se guardarán copias de la base de datos con información real dentro del repositorio público.

**Los cambios en las tablas se controlarán.** Cuando sea necesario modificar la estructura de la base de datos, se utilizarán cambios versionados para poder identificar qué se modificó.

### 3.4 Organización de los componentes

La estructura inicial prevista es la siguiente:

```text
proyecto/
├── PLAN_INGENIERIA.md
├── openspec/
│   ├── specs/
│   └── changes/
├── backend/
│   ├── usuarios/
│   ├── espacios/
│   ├── disponibilidad/
│   ├── reservas/
│   ├── aprobaciones/
│   ├── historial/
│   └── tests/
└── frontend/
```

El archivo de la base de datos se ubicará en una ruta de datos local configurada para el proyecto y no necesariamente dentro de la carpeta del código. Esto ayuda a separar los datos del programa.

La estructura es una propuesta inicial y podrá ajustarse durante la preparación del proyecto, siempre que se mantengan claras las responsabilidades de cada parte.

### 3.5 Decisiones técnicas y alternativas

#### Decisión 1. Tipo de arquitectura

| Aspecto | Una aplicación organizada en módulos (elegida) | Varios servicios separados |
|---|---|---|
| Complejidad | Menor | Mayor |
| Trabajo individual | Adecuado | Más difícil de coordinar |
| Pruebas y puesta en marcha | Más sencillas | Requieren coordinar varios servicios |
| Control de las reservas | Se concentra en una aplicación | Requiere coordinar los servicios que intervienen |
| Resultado | Elegida para el alcance actual | No se considera necesaria por ahora |

#### Decisión 2. Base de datos

| Aspecto | SQLite (elegida) | PostgreSQL | Hojas de cálculo |
|---|---|---|---|
| Preparación inicial | Sencilla | Requiere configurar un servidor de base de datos | Sencilla |
| Uso con varias escrituras simultáneas | Tiene limitaciones | Está mejor preparada para una mayor concurrencia | No es adecuada para controlar reservas simultáneas de forma confiable |
| Organización de la información | Tablas y relaciones | Tablas y relaciones | Más difícil de controlar |
| Resultado | Adecuada para el proyecto académico inicial | Alternativa si el sistema crece | No resuelve los problemas actuales |

SQLite es una elección para la primera versión, no una garantía de que sea suficiente para cualquier cantidad de usuarios. Si el uso aumenta, se evaluará migrar a PostgreSQL.

#### Decisión 3. Cómo evitar reservas cruzadas

| Alternativa | Ventaja o problema | Decisión |
|---|---|---|
| Comprobar disponibilidad y guardar dentro de una transacción | Reduce el riesgo de aceptar solicitudes que se cruzan, incluso cuando llegan casi al mismo tiempo. | Elegida |
| Comprobar disponibilidad y guardar después, por separado | Dos solicitudes podrían comprobar que el espacio está libre antes de que alguna lo guarde. | Descartada |
| Confiar solo en la página web | No evita que una persona envíe solicitudes por otros medios o intente saltarse las comprobaciones. | Descartada |

#### Decisión 4. Tecnología del servidor

| Alternativa | Ventaja o consideración | Decisión |
|---|---|---|
| FastAPI | Permite crear servicios web y ofrece documentación automática de sus funciones. | Elegida |
| Django | Incluye muchas herramientas útiles, aunque puede ser más de lo que necesita esta primera versión. | No elegida para este proyecto |
| Express con Node.js | Es otra opción válida, pero supondría trabajar con un entorno distinto al elegido para el servidor. | No elegida para este proyecto |

Estas alternativas no son malas tecnologías. Se seleccionan las opciones que mejor se ajustan al tamaño, al tiempo y a las necesidades del proyecto.

---

## 4. Estrategia de desarrollo

### 4.1 Metodología de trabajo

Se trabajará por pasos pequeños. Cada paso debe dejar una parte del sistema que se pueda revisar y probar.

Se utilizará el enfoque de desarrollo guiado por especificaciones (SDD), con apoyo de OpenSpec. El proceso será:

1. Definir qué se quiere agregar o cambiar.
2. Escribir los requisitos y ejemplos de cómo debe comportarse.
3. Dividir el trabajo en tareas pequeñas.
4. Programar con ayuda de la IA cuando sea útil.
5. Ejecutar las pruebas y revisar el resultado.
6. Archivar el cambio en OpenSpec cuando esté completo y aprobado.

También se utilizará Git para guardar el trabajo y facilitar la revisión de los cambios. Se crearán ramas cuando sea conveniente y se usarán mensajes de commit que expliquen qué se modificó.

### 4.2 Etapas de implementación

| Etapa | Contenido |
|---|---|
| E0. Preparación | Organización del proyecto, configuración y base de datos. |
| E1. Usuarios y permisos | Inicio de sesión y control de acceso. |
| E2. Espacios | Crear, editar, consultar y desactivar espacios. |
| E3. Reservas | Crear y cancelar reservas, evitando cruces de horario. |
| E4. Disponibilidad | Mostrar horarios libres, ocupados y bloqueados. |
| E5. Aprobaciones | Aprobar o rechazar solicitudes según las reglas. |
| E6. Historial y cambios | Registrar acciones y permitir modificaciones autorizadas. |
| E7. Cierre y mejoras | Bloqueos por mantenimiento, reportes, pruebas finales y documentación. |

### 4.3 Orden de desarrollo

El orden propuesto es:

1. Preparar la base del proyecto.
2. Crear usuarios y permisos, porque las acciones deben identificar quién las realiza.
3. Crear la gestión de espacios.
4. Desarrollar las reservas y la prevención de cruces de horario.
5. Mostrar la disponibilidad.
6. Agregar las aprobaciones.
7. Completar el historial y las modificaciones.
8. Terminar los bloqueos por mantenimiento, los reportes y la documentación.

Este orden podrá ajustarse si las especificaciones revelan alguna dependencia adicional.

### 4.4 Dependencias entre componentes

| Componente | Necesita de |
|---|---|
| Usuarios y permisos | Base del proyecto |
| Espacios | Usuarios y permisos para las operaciones administrativas |
| Reservas | Usuarios, permisos y espacios |
| Disponibilidad | Espacios, reservas y bloqueos por mantenimiento |
| Aprobaciones | Reservas, usuarios y permisos |
| Historial | Usuarios y operaciones que generan eventos |
| Reportes | Reservas y espacios |

### 4.5 ¿Cuándo se considera terminada una etapa?

#### Condiciones generales

- [ ] Los requisitos y ejemplos están escritos en OpenSpec.
- [ ] Los ejemplos importantes tienen pruebas relacionadas.
- [ ] Las pruebas correspondientes se ejecutan correctamente.
- [ ] Revisé el código generado o modificado con ayuda de la IA.
- [ ] El resultado cumple con lo definido en la especificación.
- [ ] El cambio se archiva en OpenSpec cuando corresponde.
- [ ] Se actualiza la tabla de trazabilidad del proyecto.

#### Condiciones específicas

| Etapa | Se considera terminada cuando… |
|---|---|
| E0 | El proyecto inicia y la base de datos se crea sin errores. |
| E1 | Las funciones protegidas rechazan a quienes no han iniciado sesión y a quienes no tienen permisos suficientes. |
| E2 | Los administradores autorizados pueden gestionar espacios y los demás usuarios solo pueden realizar las acciones permitidas. |
| E3 | Ante 20 solicitudes simultáneas para el mismo espacio y horario, como máximo una reserva compatible queda aceptada y no se crean registros inconsistentes. |
| E4 | El calendario refleja correctamente las reservas activas y los bloqueos por mantenimiento. |
| E5 | Las reservas que requieren aprobación no se aprueban sin la decisión de una persona autorizada. |
| E6 | Cada cambio importante queda registrado con quién lo realizó, cuándo y qué cambió. |
| E7 | Los recorridos principales funcionan, las pruebas acordadas pasan y la documentación está lista. |

---

## 5. Estrategia de calidad

### 5.1 Tipos de pruebas

| Tipo de prueba | Qué comprueba |
|---|---|
| **Pruebas unitarias** | Reglas específicas, como duración permitida, horarios válidos y cambios de estado. |
| **Pruebas de integración** | Que el servidor y la base de datos funcionen correctamente juntos. |
| **Pruebas de reservas simultáneas** | Que las solicitudes que se cruzan no terminen creando reservas incompatibles. |
| **Pruebas de permisos** | Que cada tipo de usuario solo pueda realizar las acciones autorizadas. |
| **Pruebas de recorrido completo** | Que una persona pueda iniciar sesión, consultar espacios, reservar y cancelar según las reglas. |
| **Revisión manual** | Que las pantallas sean comprensibles y los mensajes de error ayuden al usuario. |

### 5.2 Riesgos y cómo reducirlos

| # | Riesgo | Cómo se reducirá |
|---|---|---|
| R1 | Dos personas consiguen el mismo espacio a la misma hora. | Comprobar disponibilidad y guardar la reserva dentro de una transacción; probar solicitudes simultáneas. |
| R2 | Una reserva queda con una hora incorrecta. | Usar un formato uniforme de fecha y hora y probar límites como la medianoche y el cambio de mes. |
| R3 | El código generado por la IA tiene errores o fallos de seguridad. | Revisar el código, ejecutar pruebas y no aceptar cambios que no pueda explicar. |
| R4 | Las reglas no están claras. | Definir en las especificaciones quién aprueba, cuánto puede durar una reserva y cuándo se puede cancelar. |
| R5 | El proyecto crece demasiado y no se termina. | Completar primero las funciones indispensables y dejar las mejoras para después. |
| R6 | Una persona ve o cambia reservas ajenas sin permiso. | Revisar los permisos en cada operación y probar intentos de acceso no autorizado. |
| R7 | SQLite deja de ser suficiente si aumenta el uso. | Mantener organizado el acceso a los datos y evaluar otra base de datos si las necesidades cambian. |
| R8 | Se pierde el archivo de la base de datos. | Establecer copias de seguridad y comprobar que se puedan recuperar. |
| R9 | Se pierde la relación entre el plan, las especificaciones, el código y las pruebas. | Mantener actualizada la tabla de trazabilidad en cada cambio. |

### 5.3 Cómo se comprobará que se cumplen los requisitos

Cada requisito tendrá un código identificador, por ejemplo, `RF-03`. Ese código ayudará a relacionar lo que se necesita con las especificaciones, las pruebas y los cambios de código.

Los requisitos se describirán con ejemplos concretos que indiquen qué debe ocurrir en una situación determinada.

Ejemplo:

- **Cuando** una persona solicita un espacio que ya está reservado en ese horario,
- **entonces** el sistema rechaza la solicitud,
- **y** muestra un mensaje claro sin crear una reserva incompatible.

#### Ejemplo de tabla de trazabilidad

| Requisito | Qué solicita | Capacidad de OpenSpec | Pruebas previstas |
|---|---|---|---|
| RF-01 | Gestionar espacios | `spaces` | Crear, consultar, editar y desactivar espacios según los permisos. |
| RF-02 | Consultar disponibilidad | `availability` | Horarios libres, horarios ocupados y bloqueos por mantenimiento. |
| RF-03 | Reservar sin cruces | `reservations` | Reserva válida, rechazo por cruce y solicitudes simultáneas. |
| RF-04 | Aprobar o rechazar solicitudes | `reservations` o una capacidad específica de aprobaciones, según se defina en OpenSpec | Solo una persona autorizada puede decidir; el rechazo registra el motivo si la regla lo exige. |
| RF-05 | Controlar el acceso | `users` y `permissions` | Acciones permitidas y rechazadas según el usuario y su rol. |
| RF-06 | Consultar el historial | Capacidad de historial que se defina en OpenSpec | Se registra quién realizó cada cambio importante y cuándo ocurrió. |

Los nombres de las capacidades son una propuesta inicial. Se confirmarán al definir las especificaciones en OpenSpec.

Al cerrar cada etapa, se compararán los requisitos con las pruebas ejecutadas. En la demostración final se intentará realizar dos reservas para el mismo espacio y horario para comprobar que el sistema impide el conflicto.

---

## 6. Uso de SDD e inteligencia artificial

### 6.1 ¿Cómo se utilizará OpenSpec?

OpenSpec permitirá organizar las especificaciones del sistema y los cambios que se preparan.

- En `specs` se guardarán las especificaciones que describen el comportamiento establecido del sistema.
- En `changes` se organizarán las propuestas de cambio que todavía se están preparando o revisando.

Para cada funcionalidad se seguirá este proceso:

1. **Proponer:** explicar qué se quiere agregar o mejorar y por qué.
2. **Especificar:** escribir los requisitos y ejemplos de comportamiento esperado.
3. **Planificar:** dividir el trabajo en tareas pequeñas.
4. **Programar y probar:** desarrollar las tareas y comprobar el resultado.
5. **Revisar:** confirmar que el sistema cumple los ejemplos definidos.
6. **Archivar:** incorporar el cambio a las especificaciones vigentes cuando haya sido completado y aprobado.

### 6.2 ¿Cómo se convertirá el plan en especificaciones?

| En el plan de ingeniería | Se transformará en |
|---|---|
| Los módulos del sistema | Una referencia para definir las capacidades de OpenSpec. |
| Las funcionalidades prioritarias | Cambios que se implementarán por etapas. |
| Las necesidades de la institución | Requisitos que describen lo que debe hacer el sistema. |
| Las reglas de las reservas | Ejemplos de comportamiento correcto y de situaciones que deben rechazarse. |
| Los riesgos | Pruebas específicas para detectar problemas. |
| Los criterios para terminar cada etapa | Una lista de comprobación para revisar el resultado. |

El proceso general será:

**Plan de ingeniería → Especificaciones → Tareas → Código → Pruebas → Revisión**

#### Ejemplo de una especificación

```markdown
### Requirement: Evitar reservas cruzadas

El sistema SHALL rechazar una reserva que se cruce con otra
reserva activa del mismo espacio.

#### Scenario: El espacio ya está reservado

- WHEN una persona solicita un espacio en un horario ocupado
- THEN el sistema rechaza la solicitud con un mensaje claro
- AND no registra una reserva incompatible
```

Este ejemplo muestra cómo una necesidad del plan se convierte en una regla que después se puede probar. En OpenSpec se respetará el formato requerido por la herramienta.

### 6.3 ¿Qué actividades se delegarán a la IA?

| La IA puede ayudar con… | Actividades que revisaré con cuidado | Responsabilidades que conservaré |
|---|---|---|
| Preparar borradores de especificaciones. | Revisar los ejemplos de reservas y aprobaciones. | Decidir el alcance y las prioridades del proyecto. |
| Dividir funcionalidades en tareas. | Comprobar que las tareas respeten las reglas del sistema. | Aprobar las reglas de negocio finales. |
| Escribir código  | Revisar la lógica que evita reservas cruzadas. | Elegir la arquitectura y las tecnologías. |
| Proponer pruebas a partir de los requisitos. | Revisar los permisos y el manejo de fechas. | Aceptar o rechazar el código. |
| Preparar datos de prueba y documentación. | Verificar que los resultados de las pruebas sean correctos. | Responder por las decisiones y la calidad de la entrega. |
| Ayudar a explicar errores. | Comprobar que las soluciones propuestas no generen nuevos problemas. | Proteger los datos y explicar el funcionamiento del proyecto. |
| Ayudar a explicar errores y complementar documentos. | Asegura que la información sea clara, precisa, completa y fácil de interpretar | Explicar el funcionamiento del proyecto a los interesados. |

### 6.4 ¿Cómo se revisará el código generado?

1. Leeré el código antes de aceptarlo. Si no entiendo una parte, pediré una explicación y comprobaré que sea correcta.
2. Compararé el resultado con los requisitos y las especificaciones.
3. Revisaré que las pruebas se basen en el comportamiento esperado, no solamente en lo que hace el código.
4. Ejecutaré las pruebas y analizaré los errores.
5. Revisaré especialmente las reservas, los permisos y las fechas.
6. Comprobaré que las librerías sugeridas existan y sean necesarias.
7. Haré pruebas en las que el sistema deba rechazar una operación incorrecta.
8. Cuando sea posible, modificaré temporalmente una regla para confirmar que las pruebas detectan el error.

**Regla principal:** la IA puede proponer soluciones, pero yo debo revisarlas, comprobarlas y entenderlas antes de aceptarlas.

### 6.5 ¿Qué decisiones serán responsabilidad del estudiante?

Serán mi responsabilidad:

- Definir el problema, el alcance y las prioridades.
- Elegir las tecnologías y explicar por qué son adecuadas.
- Establecer las reglas de las reservas, los permisos y las aprobaciones.
- Revisar las especificaciones antes de implementarlas.
- Comprobar que el sistema cumpla los requisitos.
- Aceptar o rechazar el código generado con ayuda de la IA.
- Decidir qué funcionalidades dejar para después si falta tiempo.
- Proteger los datos y controlar los accesos.
- Explicar qué partes recibieron ayuda de la IA y defender las decisiones del proyecto.

La meta es utilizar la IA como apoyo, sin dejar de comprender ni asumir la responsabilidad por el trabajo entregado.

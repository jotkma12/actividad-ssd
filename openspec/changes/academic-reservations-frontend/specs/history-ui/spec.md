# Spec Delta

## Purpose

Define la consulta en pantalla de los eventos de auditoría que el backend autoriza para cada cuenta.

## ADDED Requirements

### Requirement: Consultar historial autorizado
La interfaz SHALL solicitar y mostrar eventos de historial del servicio, respetando los filtros y permisos que este aplique.

#### Scenario: Administrador consulta historial
- **WHEN** un administrador abre el historial
- **THEN** la interfaz muestra los eventos que el servicio autoriza para todos los espacios

#### Scenario: Solicitante consulta su historial
- **WHEN** un solicitante abre el historial
- **THEN** la interfaz muestra únicamente los eventos asociados a sus reservas devueltos por el servicio

#### Scenario: Aprobador consulta historial asignado
- **WHEN** un aprobador abre el historial
- **THEN** la interfaz muestra únicamente eventos de los espacios asignados que el servicio devuelve

#### Scenario: Error al consultar historial
- **WHEN** el servicio rechaza o no puede completar la consulta
- **THEN** la interfaz informa el error y no muestra eventos fuera del alcance autorizado

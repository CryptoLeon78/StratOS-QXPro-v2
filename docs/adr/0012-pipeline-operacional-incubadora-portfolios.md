# ADR 0012 — Pipeline operacional: Incubadora y portfolios reales

## Contexto

El operador retira F1, F2 y F3 de la superficie Pipeline. La minería, el
Tester y la validación previa pertenecen al entorno de investigación y no al
plano de control diario. Pipeline debe servir para gobernar la Incubadora demo
y observar los dos portfolios reales registrados, BEPB y JJTI.

## Decisión

La página Pipeline muestra únicamente tres carriles operativos:

1. instalación demo con plan sellado y confirmación individual;
2. observación contractual de Incubadora;
3. evaluación de cartera, staging y comparación challenger/champion.

Debajo presenta una tarjeta por cada cuenta `BROKER_REAL` registrada. La
identidad del portfolio procede de `Account.name`, no de una lista de cuentas
insertada en frontend. Las tarjetas permanecen read-only: no existe una ruta
de comando, sizing o despliegue para BEPB/JJTI.

F1--F3, sus items de trabajo, la cola Tester y evidencias archivadas se
conservan como registro histórico y compatibilidad de importación, pero no se
solicitan ni renderizan en el tablero operativo. Esta decisión no borra
artefactos, comandos ni transiciones append-only.

## Consecuencias

La admisión futura de una estrategia a Incubadora necesita una ruta explícita
de `incubator_admission` basada en evidencia sellada y perfil/identidad
declarados, sin recrear F1--F3 como fases visibles. Hasta implementarla, el
tablero opera las candidatas de Incubadora ya registradas y no interpreta una
evidencia de investigación como autorización de instalación.

F6 continúa emitiendo una propuesta auditable. La incorporación a un
portfolio real requiere una decisión humana posterior y permanece fuera de
MetaTrader y de cualquier automatismo de Pipeline.

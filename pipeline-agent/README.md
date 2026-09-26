# Agente Windows de Pipeline

El agente se ejecuta en la sesión Windows interactiva del VPS Contabo. Lee una
configuración fuera de Git y la clave `PIPELINE_AGENT_API_KEY` desde el entorno.
Rechaza rutas fuera de la allow-list y terminales que no coincidan exactamente
con la configuración. `SQX_VS_MT5_TESTER` sólo ejecuta Tester con AutoTrading
desactivado; `CONTABO_INCUBATOR_DEMO` es el único destino de instalación.
JJTI/BEPB no son destinos ejecutables. No contiene funciones de trading.

Antes de compilar una candidata adicional, `preserve_magics` debe declarar los
dos magics ya adjuntos a la Incubadora. El agente recorre los `.chr` UTF-16 y
falla cerrado si cualquiera falta o aparece en más de una serialización; nunca
reemplaza ni recrea un perfil existente.

F1 dispone de handlers para `FORJA_GENERATE`, `SQX_START` y `SQX_STOP`, todos
limitados al grupo `ANALYSIS`. FORJA usa una sintaxis fija de catálogo y SQX
usa únicamente los lanzadores declarados en la configuración local; una ruta
de proyecto fuera de `allowed_source_roots` se rechaza. Cada respuesta es un
evento terminal inmutable en el core. No se ha instalado ni probado aún esta
configuración en Contabo, por lo que esos handlers no se consideran operativos
en el VPS hasta completar el preflight manual.

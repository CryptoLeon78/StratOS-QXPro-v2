
32 bots operando en trading automático 24/7: el panel al descubierto
0:00
Estos son 179,643
0:03
€ gestionados por 32 bots, 24 horas al
0:07
día, 7 días a la semana. Yo llevo meses
0:10
sin tocar ni una sola orden en esta
0:13
cuenta de trading. La pregunta que me
0:15
hace todo el mundo es, ¿cómo controlas
0:17
32 bots sin volverte loco ni quemar la
0:20
cuenta? La verdad es que en total entre
0:23
todas las cuentas tengo más de 120 bots
0:26
y hoy te abro el setup entero, pestaña a
0:29
pestaña, sin guardarme nada porque la
0:32
diferencia entre esto y una cuenta
0:34
quemada no son los bots, es el sistema
0:37
que los vigila. Me llamo Ignacio Lago,
0:39
soy graduado en ADE, ingeniero
0:41
informático y llevo más de 15 años
0:43
ejerciendo como analista de mercado y
0:45
operando los mismos como trader
0:47
cuantitativo profesional. y vivo
0:49
operando con voz de trading que yo mismo
0:51
diseño, construyo y valido. Y esta
0:53
cuenta lleva operativa desde enero de
0:56
2021 en un broker regulado. Comenzó
0:59
operando con un bot y 30,000 € hoy tiene
1:03
32 bots y casi 200,000 € No es magia y
1:06
desde luego no es suerte, es solo
1:09
trading cuantitativo profesional y te
1:11
voy a desvelar su secreto para que tú
1:13
también puedas aplicarlo desde hoy
Track record verificado desde 2021 en MetaTrader 5 y qué te llevas hoy
1:15
mismo. Al final del vídeo te lleva mi
1:18
protocolo exacto de decisiones, el mismo
1:21
que me permite retirar dinero cada mes,
1:24
replicable con tres bots y una cuenta
1:26
pequeña. El plan completo que cambiará
1:29
tu resultado para siempre tiene cinco
1:31
capas. Una, la sala de máquinas. Dos, el
1:35
equipo de bots. Tres, los sistemas de
1:38
control, que es donde casi todos fallan.
1:41
Cuatro, la fábrica, ¿de dónde salen
1:43
estos bots? y cinco, cómo salen los
1:46
retiros. Así que vamos dentro. Carta
1:49
sobre la mesa desde el principio. Esto
1:52
no es mi portfolio principal ni mucho
1:54
menos. De hecho, es uno de los más
1:56
pequeños. Lo uso como filtro. Aquí se
1:59
prueban los bots después de haber pasado
2:01
por todo el pipeline de validación
2:03
riguroso que todos mis bots, sin
2:06
excepción deben pasar para operar con
2:08
dinero real. Si tras unos meses aquí
2:11
consiguen batir a alguno de mis bot
2:13
principales en una cuenta mayor, lo
2:15
sustituyen. Si no, se quedan en este
2:18
portfolio mientras sigan siendo
2:20
rentables. Y por eso te lo enseño,
2:22
porque el proceso es idéntico al de los
2:25
grandes y este es el que suelo tener
2:27
siempre más vigilado.
Fase 1: infraestructura de trading algorítmico con VPS y auditoría de datos
2:30
Los datos duros. Operativa desde el 4 de
2:32
enero de 2021. Capital inicial, 30,000 €
2:36
Equity hoy 179,642
2:39
€ Todo corre en un VPS en Alemania. Un
2:43
ordenador en la nube encendido las 24
2:46
horas del día. ¿Por qué un VPS? Porque
2:49
un corte de luz en tu casa es una
2:51
anécdota si operas a mano, pero con bots
2:54
es una orden que no se envía en el peor
2:57
momento posible. El uptime de este
2:59
terminal en los últimos 7 días es del
3:02
99.6. 6%. Ahora la parte que casi nadie
3:07
entiende bien, la alimentación de datos.
3:10
Cada voz lleva su magic number, que es
3:12
algo así como la matrícula de un coche.
3:14
El terminal reporta cada operación aquí
3:17
al app deator de forma automática desde
3:20
el Metatrader con esa matrícula. Yo no
3:23
escribo ni un número a mano, ni uno.
3:25
Aquí todo es totalmente automático. El
3:28
usuario no puede intervenir. Todas las
3:30
métricas que vas a ver hoy vienen
3:32
directas del Metatrader y todos los
3:35
cálculos son 100% automáticos. Si un
3:38
dato no cuadra, el sistema me avisa
3:41
antes incluso de que yo lo note. Y sobre
3:44
todo eso porque hay un Watch Dog. Piensa
3:47
en un pulsómetro. No te dice si vas a
3:50
ganar la carrera, te dice si el corazón
3:52
late a su ritmo normal. El Watch Dog
3:55
básicamente lo que hace es comparar los
3:57
trades esperados de cada bot con los
3:59
trade observados en los últimos 30 días.
4:02
Atlas Trend, uno de mis bot en euroólar,
4:05
espera unos siete al mes y lleva ya seis
4:07
y solo un día sin operativa. Lira
4:10
Scalperaba 58 y lleva 59. También dentro
4:14
los 32 bots activos en verde técnico. Y
4:18
aquí va el primer cambio de mentalidad,
4:20
el más importante del vídeo. Yo por la
4:23
mañana no miro gráfico, me da
4:25
exactamente igual como está el mercado,
4:27
no miro indicadores, no dibujo líneas de
4:30
tendencia ni de soporte, ni busco SMC,
4:33
no, nada de todo eso. Solo miro tres
4:37
números: equity, drynow y decisiones
4:40
pendientes. Hoy downown del 0.4 4% y dos
4:44
decisiones pendientes en alertas. Ese es
4:47
mi trading diario, 10 minutos con el
4:50
café. Pero estos datos son la parte
4:52
fácil. Lo difícil es lo que va encima. Y
4:55
te adelanto algo, hay un error que
4:58
comete casi todo el mundo que junta
5:00
varios bots y no tiene nada que ver con
5:02
las estrategias. Lo vas a ver con tus
5:05
propios ojos en cuanto abra una matriz
5:07
concreta. Pero antes vamos a conocer al
Fase 2: los 32 bots en producción y los tres bloques del portfolio (convexo, cóncavo, híbrido)
5:10
equipo. Aquí están los 32 bots, cada uno
5:14
con su nombre, su mercado, su
5:16
temporalidad y su perfil. Y son
5:19
deliberadamente distintos entre sí.
5:22
Mira, por ejemplo, dos extremos. Elius
5:25
momentum DAX en H1 siguiendo tendencia.
5:28
acierta solo el 45% de las veces, pero
5:31
cuando gana gana más de lo que pierde
5:33
cuando pierde. Lira scalper es lo
5:36
contrario. Eurodólar en M5 acierta el
5:39
87.2%.
5:41
Pero cada ganancia es muy pequeña, pero
5:44
tiene 0,4 RS, dos bots opuestos. Y esa
5:49
es la clave, un portfolio profesional se
5:51
organiza siempre en tres bloques macro.
5:53
Te lo enseño. Bloque convexo. Aquí van
5:56
los bot de tendencia y momentum. Son
5:59
como pescadores de atún. Pasan semana
6:02
sin captura y de repente traen una pieza
6:04
enorme. Ganan poco a menudo, pero ganan
6:07
a lo grande y protegen en las crisis.
6:10
Bloque cóncavo. Aquí viven los bots de
6:13
reversión a la media y gritados.
6:16
Son como la panadería del barrio, venta
6:18
pequeña, diaria constante, aportan flujo
6:21
de caja estable y el bloque híbrido
6:24
Orderflow y botch de inteligencia
6:26
artificial que suman descorrelación.
6:29
¿Por qué? Porque no hay nada igual a
6:31
ellos. El objetivo de este reparto es 40
6:34
convexo, 40 cóncavo, 20 híbrido.
6:38
Cuadrarlo 100% es complejo. Si hay que
6:41
intentar que esté lo más cuadrado
6:43
posible. No voy a entrar en teoría de
6:45
gestión de por qué esto es así, pues
6:47
daría para otro vídeo completo, pero
6:49
créeme que cuando te mantienes en esta
6:52
proporción, no solo consigues un
6:54
portfolio mucho más estable y con menor
6:56
volatilidad, sino que además es
6:59
muchísimo y digo muchísimo más rentable
7:02
a largo plazo y con un riesgo mucho más
7:04
bajo. La foto real hoy 45.7, 32.6 y 21.7
7:10
7 desviado, pero dentro de la banda de
7:13
confianza. El sistema lo vigila todo con
7:16
alertas suaves y rebalancea en la
7:18
revisión mensual, no cuando a mí me
7:20
apetece. Ahora los tamaños, porque aquí
7:23
es donde el retail destroza todo. Cada
7:26
voz tiene entre un 3 y un 5% del capital
7:30
asignado y cada operación individual
7:33
arriesga entre el 0.3 y el 0.6% 6% de la
7:37
cuenta. Es decir, si un bote entero se
7:40
equivoca 10 veces seguida, el daño sería
7:43
de unos pocos puntos porcentuales. ¿Qué
7:46
quiere decir esto? Que ningún bot,
7:48
ningún boto, puede hundir el barco. El
7:52
sizing total en producción es del 89%
7:55
y el resto queda de margen. Y para que
7:58
veas cómo es un día normal, aquí vemos
8:01
las posiciones abiertas de cada bot.
8:03
Ahora mismo, una en el Bitcoin con -59,
8:07
otra en el DAX con -91 y otra en el
8:10
petróleo con más 217,
8:13
impulsada fuertemente por los últimos
8:15
eventos de los conflictos bélicos de
8:17
Irán. Cero posiciones sin stop loss,
8:20
cero. [música]
8:21
Eso no es negociable en este ni en
8:23
ninguno de mis portfolios. Y ahora sí,
Fase 3: la matriz de correlaciones 32x32 y la falsa diversificación de estrategias
8:26
el error que te debía desde el
8:28
principio. Casi todo el que monta varios
8:31
bots cree que está diversificando porque
8:33
tiene nombres distintos en la lista o
8:35
los está poniendo en mercados o time
8:37
frame diferentes. Es como un empresario
8:39
que presume de tener cinco empleados y
8:42
resulta que son cinco hermanos gemelos.
8:44
hacen lo mismo, fallan a la vez y el día
8:47
malo es cinco veces más malo. Eso en
8:50
trading cuantitativo se llama
8:52
correlación y es invisible hasta que la
8:55
mides. Esta es la matriz de
8:58
correlaciones de mis 32 bots, calculada
9:01
sobre 1240 días de datos reales. La
9:05
correlación media del portfolio es de
9:06
0.16, 16 muy baja. Eso significa que
9:10
cuando unos pierden, otros están en otra
9:12
película diferente ganando. Pero fíjate
9:15
en esta celda. Lira scalper en eurodólar
9:18
y Phenix Scalper en el SP500.
9:21
Correlación 0.52.
9:23
Tres veces la media del portfolio. Dos
9:26
mercados distintos, dos bot distinto y
9:30
aún así se parecen demasiado. Son medio
9:32
gemelos. El sistema lo marca como par
9:36
redundante y en la próxima
9:38
reestructuración uno de los dos
9:40
probablemente cederá riesgo para
9:42
descorrelacionar el portfolio. Sin la
9:44
matriz jamás lo habría visto y esta
9:47
descorrelación explica el resultado
9:49
agregado. En 60 meses este portfolio ha
9:53
hecho un 37.31%
9:56
anual sobre interés compuesto contra un
9:59
11.90 90 del SP500 en el mismo periodo
10:02
con una beta de solo 0.18, lo que indica
10:06
que casi no depende de lo que haga la
10:08
bolsa. Y con un alfa estadísticamente
10:11
significativo, T de 3.42.
10:14
Ojo que ningún bot es una máquina de
10:17
imprimir dinero sin riesgo. El trading
10:19
tiene riesgo y nada de esto garantiza
10:22
rentabilidad de futura. De hecho, fíjate
10:25
en esto. De unos 66 meses, 14 fueron
10:29
negativos. algo así como uno de cada
10:31
cinco. Guárdate ese dato porque al final
10:34
del vídeo es la pieza que explica los
10:37
retiros mensuales. Cuando comenzamos en
Por qué los bots de trading envejecen: el alpha decay explicado
10:39
el trading con bot retail, lo que se
10:42
conoce como trading algorítmico, la
10:44
mayoría piensa que con diversificar
10:46
basta, pero el mercado te enseñará que
10:49
no si no lo has hecho ya, porque los
10:52
bots no se rompen de golpe, se apagan
10:55
poco a poco como una pila. Esto es lo
10:58
que nadie me contó cuando yo empecé y es
11:00
la capa que de verdad protege esta
11:02
cuenta. Fíjate en la rentabilidad media
11:05
de este portfolio, una media del 4 al 5%
11:09
mensual, es decir, en torno a un 50 60%
11:12
anual. Sé que para muchos, sobre todo en
11:15
el sector retail, esto puede parecer
11:17
poco si venís de, como digo, del
11:19
marketing de redes sociales, donde se
11:21
comparten porcentajes del 400 o 500%.
11:24
Pero esto es trading real, rentable, del
11:27
que se puede vivir, del que no te da
11:29
quebraderos de cabeza y te permite
11:30
construir un futuro mejor
11:32
financieramente hablando. Cierto es que
11:35
lo tengo con un lotaje muy conservador
11:37
para mantener un dryown muy bajo y
11:39
dormir tranquilos por las noches. lo
11:41
podría subir un por tr o un por cu y
11:43
aumentaría exponencialmente la
11:45
rentabilidad y aún así podría seguir
11:47
manteniendo un dryout bajo, pero
11:49
sinceramente tengo más portfolio y no
11:51
tengo la necesidad de exprimir más la
11:53
maquinaria porque algo que hay que tener
11:56
presente y que nadie te cuenta es lo
11:58
siguiente: para ganar más hay que
12:00
arriesgar más y arriesgar más es
12:03
aumentar las probabilidades del fallo y
12:05
yo ya pasé suficientes veces por esa
12:07
época como para volver a ella de nuevo.
12:10
Lo que veis aquí es el poder del interés
12:12
compuesto de cómo con poco se puede
12:15
hacer mucho en muy poco tiempo
12:17
reinvirtiendo todo. Toda estrategia
12:20
pierde siempre su ventaja. Tarde o
12:22
temprano, sí o sí. Esto se conoce, está
12:25
documentado profesionalmente y se llama
12:28
Alfa Deai. La pregunta no es si te
12:31
pasará, sino si lo detectarás antes de
12:34
que te cueste todo tu dinero. Mi sistema
Fase 4: semáforos de salud para detectar el deterioro de cada estrategia
12:36
lo hace con semáforos. Te lo enseño.
12:39
Funciona como una analítica de sangre.
12:41
Tú no decides si estás sano por
12:43
sensaciones. Mira los marcadores contra
12:46
sus valores de referencia. Aquí cada bot
12:48
se compara en una ventana móvil contra
12:51
su línea base, la del back test y la de
12:53
su histórico. Y el protocolo es de tres
12:56
colores escrito en piedra. Verde, no
12:59
tocar nada, ni para bien ni para mal.
13:01
Amarillo, reducir el tamaño al 50% y
13:04
vigilar más de cerca. naranja, el bot
13:07
pasa a paper trading, es decir, va a
13:10
operar en virtual sin dinero real hasta
13:12
que pueda demostrar nuevamente con 30
13:15
operaciones limpias que se merecen
13:17
volver a real. Y hoy tienes los tres
13:19
casos aquí en directo. ¿Te habrás fijado
13:22
en que el semáforo global de la cabecera
13:24
está en naranja? Crisis, ¿no? El drown
13:27
del portfolio es del 0.4%.
13:30
Es un solo bot arrastrando el peor
13:32
estado. Tengo el aviso en alerta en el
13:34
menú superior. Y en resumen, Poseidón
13:37
Trend. En el DAX lleva 12 días en
13:40
naranja. Su profit factor rodante es de
13:43
1.18 cuando su línea base era 1.94.
13:47
El sistema no me pregunta qué opino. Me
13:50
da la instrucción exacta en el EA con
13:53
matrícula 1186 85. desactivar la
13:56
apertura de nuevas posiciones y dejar
13:58
que las existentes cierren por sus
14:01
reglas. Posidón se va a paper trading.
14:03
Segundo caso, Vega Grid en libradólar en
14:06
amarillo desde hace 6 días, sizing
14:09
reducido al 50% y alerta activa. Me pide
14:14
confirmar que el cambio está aplicado en
14:15
Metatrader. Y tercero, todo lo restante
14:18
en verde. No tengo que hacer nada ni me
14:21
acerco a ello. Fíjate en lo que acaba de
14:23
pasar. Un trader descrirecional con un
14:26
bot 12 días flojos discutiría consigo
14:29
mismo cada noche. Yo no discuto, el
14:32
semáforo decide y yo ejecuto. Esa es la
14:35
diferencia entre tener bots y tener un
14:38
sistema. Esto es solo una muestra más de
14:40
por qué las cosas tienen que conocerse y
14:43
hacerse bien. No podemos descargar bot
14:45
de internet o comprarlo en Marketplace y
14:47
esperar que podamos ser rentables con
14:49
ello y sobre todo a largo plazo. La idea
14:51
está clara. Puedes pasar un par de meses
14:53
o años dando vueltas por el trading,
14:55
perdiendo tiempo y dinero tontamente,
14:57
con cursillos de gurú o buscando la
15:00
solución mágica por tu cuenta a un
15:02
problema que ya la tiene y es esta,
15:04
hacer las cosas bien de forma
15:06
profesional y con conocimiento. Yo no me
15:08
altero ni me molesto por ver a Elios
15:10
perder dinero un mes ni cinco, porque lo
15:13
construí, yo sé que hace, cómo lo hace y
15:17
por qué lo hace. Antes de llegar a este
15:19
portfolio estuvo 6 meses, medio año en
15:23
un proceso de auditoría en el pipeline
15:26
de validación donde el 80 90% de los
15:29
bots caen por el camino. Helio no cayó,
15:32
superó el pipeline y las métricas le
15:35
hicieron ganarse un puesto en este
15:37
portfolio. En el pipeline ya tuvo algún
15:39
mes que perdió dinero, no es un secreto
15:42
para mí. El gran problema del sector
15:44
retail es que casi nadie sabe aplicar
15:46
los procesos correctamente, solo se
15:49
persiguen estrategias milagrosas de
15:51
redes sociales, gurús con sistemas
15:53
mágicos que te prometen dinero fácil y
15:55
rápido, etcétera, etcétera. Y cuando se
15:57
decide utilizar un bot o una estrategia,
16:00
rara vez se hace en demo y desde luego
16:03
nunca se ejecuta un pipeline de
16:05
validación profesional riguroso.
16:07
Normalmente si se usa la demo son solo
16:09
unos días y directamente cuando se ve
16:11
que gana se tiene la sensación de que se
16:13
está dejando de perder dinero y va
16:15
directamente a la cuenta real y ahí
16:18
viene el problema porque cuando ejecutas
16:20
un bot o una estrategia en real claro
16:23
realmente qué hace y cómo lo hace,
16:26
aunque creas que lo sabes, no lo sabes.
16:28
En cuanto comience a perder, te
16:30
abordarán las dudas, dudas de todo tipo.
16:34
Y con cada nueva operación perdedora,
16:36
esas dudas empezarán a crecer y crecer
16:39
la idea de que debes pararlo porque no
16:42
funciona. Esto te lleva a un bucle
16:44
infinito de perder tiempo y dinero que
16:47
puede durar desde meses hasta años si no
16:50
le pones solución ya y decides hacer las
16:53
cosas bien. Cuando realizas los procesos
16:55
correctos con rigor, todo se calcula
16:58
automáticamente y se te muestra cómo es,
17:01
sin endulzar. Y ahí es cuando conoces a
17:04
tus bots, a tus estrategias. Y cuando
17:07
conoces perfectamente a tu bot y sabes
17:09
lo bueno y lo malo y pasa todas las
17:12
pruebas y llega al portfolio real, no
17:14
hay problema ninguno. No hay miedo, no
17:16
hay dudas, no hay incertidumbre, no hay
17:19
angustia, no hay nada. Y si hubiese
17:21
algún problema, el más mínimo, el propio
17:24
sistema te avisaría y te diría qué
17:27
acción concreta debes tomar. Fin. Eso es
17:30
trading cuantitativo. Prof. profesional.
17:32
Todo está medido, todo está controlado,
17:35
todo es objetivo y todo es escalable.
17:39
Este panel no son más que las métricas
17:41
de tu negocio como trader. Veamos
17:43
algunos ejemplos más y vas a entender
17:45
esto muy rápido y sobre todo vas a ver
17:48
por qué la velocidad máxima es hacer las
17:51
cosas bien y por qué las prisas no te
17:53
llevan a nada más que a la casilla de
17:55
salida una y otra vez. Ya hemos visto
Fase 5: kill-switch de 4 niveles y simulación Monte Carlo del riesgo de cola
17:58
los semáforos que vigilan bot a bot.
18:01
Pero, ¿y si todo se tuerce a la vez?
18:04
Para eso existe la escalera Kill switch.
18:07
Es el cuadro de diferenciales de tu
18:09
casa. Si hay una pequeña subida de
18:12
tensión, salta un fusible. Si hay un
18:14
cortocircuito serio, se corta la luz
18:16
entera. Aquí igual con cuatro niveles
18:20
sobre el dry down del portfolio. Al 8%
18:23
alerta, vigilar sin intervenir. Al 12%
18:26
reducir el tamaño de todos los bots a la
18:29
mitad. Al 15 cerrar todas las posiciones
18:32
abiertas y al 20% cerrar y desactivar
18:36
todos los seas. Apagón total. Estado
18:39
actual cero, sin activación porque el
18:42
dry máximo de esta cuenta en 5 años y
18:45
medio no ha pasado del 4.8%.
18:49
La escalera existe precisamente para que
18:52
el día que la estadística falle poder
18:54
saberlo y la estadística se mide con
18:56
filtros serios y profesionales. El bar
18:59
diario al 95% es del 0.54.
19:03
El CBAR al 99% que mide el día realmente
19:07
feo, está al 0.91.
19:10
Todo en verde, dentro de los umbrales,
19:12
pero mi herramienta favorita es otra,
19:15
Monte Carlo. Y no es el típico Monte
19:17
Carlo que estás acostumbrado a ver, es
19:19
un Monte Carlo específico para esta
19:21
sección. Coge el historial de trade de
19:23
cada bot y lo baraja 300 veces como una
19:26
baraja de cartas para ver 300 vidas
19:29
alternativas del mismo bot. De ahí sale
19:31
su contrato de drynow. Ejemplo real,
19:34
Atlas Trent tiene un DD histórico del
19:37
2.20%.
19:38
Supercentil 95 en Monte Carlos dice
19:41
3.94,
19:43
así que su contrato firmado de máximo
19:46
ddown es de 3.9. Si algún día lo supera,
19:49
no está teniendo mala suerte, está
19:51
incumpliendo contrato y se le aplica
19:54
protocolo. No hay más misterio que el
19:56
control riguroso. El que haya buena
19:58
cifra no es por suerte ni por
20:00
casualidad, es porque lo que no da buena
20:02
cifra se elimina. El propio sistema ya
20:05
está diseñado por capas y si en alguna
20:08
de ellas algún bot alguna métrica suelta
20:11
no cuadra, salta alerta y se ejecutan
20:14
acciones concretas y específicas para
20:16
remediarlo. El resultado, el que estás
20:19
viendo en pantalla, control orientado a
20:22
resultados. Hoy los 32 bots están dentro
20:25
del perfil, no hay que tocar nada en
20:28
este campo. Y ahora la última capa, el
20:31
escudo de noticias. En este apartado veo
20:34
las noticias que van a llegar desde
20:36
ahora hasta 48 horas hábiles. ¿Para qué
20:38
lo utilizo? Pues como referencia, por si
20:41
es necesario cambiar la ventana
20:43
operativa de alguno de los bots para que
20:45
no opere en noticias, pues porque no le
20:47
siente bien, porque un bot profesional
20:49
también sabe cuándo no operar. Y ahora
Fase 6: pipeline de validación F1-F7 y el cementerio de bots retirados
20:52
la pregunta que debes estar haciéndote.
20:54
Ignacio, ¿de dónde han salido estos 32
20:58
bots? Ninguno de ellos viene de
21:00
estrategia de redes sociales, ni de
21:02
compra a gurú ni nada de eso. Todos han
21:05
sido diseñados, creados y validados en
21:07
estratos. Todos pasaron por una fábrica
21:10
en la que la mayoría de los candidatos
21:12
muere. Y te voy a enseñar hasta el
21:15
cementerio porque sí, hay un cementerio
21:17
de bots. Esto funciona como la cantera
21:20
de un club deportivo. Nadie debuta en el
21:22
primer equipo por caerle bien al
21:24
entrenador. Sube categoría a categoría
21:27
demostrando números y aquí hay siete
21:29
fases. De la F1ción en paper hasta la f
21:35
producción con capital real. Ahora mismo
21:37
tengo unos 32 bots en producción y unos
21:40
25 candidatos repartidos por la cantera.
21:43
Y a partir de la fase cuatro, los
21:45
ascensos no los decido yo, los deciden
21:48
las puertas automáticas con criterios
21:50
fijos, es decir, las métricas. Estas
21:52
métricas se calculan automáticamente con
21:55
los datos que se reciben desde el
21:56
Metatrader. Es decir, todos estos bots
21:59
están ahora mismo en un VPS operando en
22:02
cuentas demo sobre el mercado real. En
22:04
este pipeline lo voy monitorizando con
22:07
métricas como, por ejemplo, el Profit
22:09
Factor mayor de 1.5, expectativa por
22:12
operación mayor a 0.15R, Share mayor de
22:15
1, drynow del 20% y el criterio que casi
22:20
todos ignoran muestra suficiente de
22:23
operaciones y mira por qué importa.
22:25
Stitch Trend luce un profitifor de
22:28
32.75.
22:30
Espectacular, ¿verdad? Pues sigue
22:32
retenido. ¿Por qué? nueve trades
22:35
demuestra nueve. Con nueve operaciones
22:38
no saben nada, puede haber sido pura
22:40
suerte. En cambio, mira este. Sigma MR,
22:44
reversión a la media en el SP500, Profit
22:47
Factor 2.6, 51 operaciones fuera de
22:50
muestra 95 días de incubación. Veredicto
22:54
de la puerta. Go, avance hacia la
22:56
siguiente fase. Hoy asciende a Staging
22:59
con un 10% de su tamaño objetivo. Esa es
23:02
la segunda decisión pendiente que vistes
23:05
en la cabecera. Recuerda que todo esto
23:07
se calcula automáticamente, es decir, no
23:09
tienes que hacer nada más que poner el
23:12
bot en una cuenta demo y dejarlo hacer.
23:14
Y si te estás preguntando que cómo
23:16
aprendes a gestionar todo esto y a crear
23:19
tu propio negocio dentro del trading
23:20
cuantitativo, tengo preparado una
23:22
formación de 14 días gratuito en mi
23:25
comunidad privada de school, donde
23:26
juntos construimos las base de tu futuro
23:29
como trader cuantitativo profesional. En
23:32
el primer comentario fijado y en la
23:34
descripción tienes el enlace directo. Es
23:36
gratis por el momento, no te quedes
23:38
fuera. Pero esta fase del pipeline es la
23:40
bonita. Y luego está el cementerio, el
23:43
lugar donde los bots con horas, días o
23:45
incluso semanas de trabajo y desarrollo
23:47
encima de ellos terminan muriendo y
23:50
siendo olvidados. En este caso, nueve
23:52
bots retirados, cada uno con su autopsia
23:56
escrita. Uno por el express nocturno del
23:58
broker, que se comió su expectativa de
24:00
0.19R
24:02
hasta 0.04.
24:04
Era rentable, pero el mercado real lo
24:06
destrozó. Lección. Los scalpers se
24:09
validan con costes reales por sesión,
24:13
importante, imprescindible. Otro bot,
24:15
por ejemplo, pues por el overfeitting
24:17
puro. El modelo memorizó su ventana de
24:19
entrenamiento y murió al salir de ella.
24:22
Este otro de aquí, niove, en el yen, la
24:24
intervención del Banco Central de Japón,
24:27
le cambió el mercado bajo los pies.
24:29
salió por protocolo de detección de
24:31
régimen sin discutir y la regla de oro
24:34
del cementerio, un bot retirado jamás
24:37
vuelve sin pasar a la cantera otra vez
24:40
de nuevo por toda la fase, especialmente
24:42
la fase tres. Sin excepciones, sin
24:44
nostalgia, cada lápida es una lección
24:47
que el portfolio no repite. Y llegamos
Fase 7: el mayor riesgo del setup y el diario de impulsos cuantificado
24:50
al componente más peligroso de todo el
24:52
sistema. No es un bot, somos nosotros
24:55
mismos. Aunque llevemos años en los
24:57
mercados, somos humanos y seguimos
25:00
sintiendo los mismos impulsos. Apagar lo
25:03
que va mal, cortar la pérdida que duele,
25:06
subir el riesgo cuando el mes va bien.
25:09
La diferencia es que ahora yo los apunto
25:11
y le pongo precio. Cada vez que quieras
25:14
intervenir, regístralo aquí. El sistema
25:17
registrará la acción y la monitorizará.
25:20
Tras 7 días te enseñará qué hubiera
25:22
pasado si hubiese ejecutado realmente. Y
25:25
aquí tienen los resultados. Este
25:27
trimestre, tres impulsos registrados. Un
25:30
bot llevaba 3 días en rojo y sentí que
25:33
algo se había roto. Quise apagarlo, lo
25:35
registré. No lo hice porque el semáforo
25:38
decía amarillo, no naranja, pero lo
25:40
registré. Los 7 días siguientes generó
25:43
418 €. El segundo, un swing de titán. 2
25:48
días en negativo. El impulso era
25:50
cortarlo porque no lo había hecho antes,
25:52
pero terminó cerrando en positivo por
25:54
sus propias reglas, 236 € más. Coste
25:57
evitado del trimestre por no hacerme
25:59
caso a mí mismo, 654,80
26:03
€ son multas que no llegué a pagar y las
26:06
tengo cuantificadas. Y como la confianza
26:08
también hay que ganársela con los datos,
26:11
existe la pestaña auditoría. Balance
26:13
inicial más flujo neto igual a balance
26:16
final. Discrepancia 0, 0% sobre 15,486
26:23
operaciones desde 2021. Lo que ves en el
26:26
panel es exactamente lo que pasó en el
26:28
broker, sin capturas maquilladas, sin
26:31
Excel retocado, rigor y nada más. Y
El protocolo de retiros mensuales que lo une todo
26:35
ahora la pieza que lo une todo. ¿Cómo
26:37
salen los retiros cada mes? Porque yo
26:40
retiro todos los meses sin excepción. Y
26:43
aquí viene lo que casi nadie entiende.
26:45
Eso no significa que todos los meses se
26:48
gane. Ya lo viste, 14 de 66 meses fueron
26:51
negativos. La clave es que el retiro no
26:54
es una celebración del mes. Bueno, es
26:56
una nómina que la empresa se paga a sí
26:59
misma. ¿Y por qué puede pagarse? Por dos
27:02
números que ya conoces. Retorno medio
27:04
mensual del 2.69%
27:07
y dedown máximo del 4.76.
27:11
Cuando tus meses malos son pequeños y
27:13
controlados, el acumulado soporta una
27:16
nómina estable. El retiro no lo genera
27:18
ningún bot, lo genera la estructura
27:20
completa. Y la estructura, esto es lo
27:23
que te vas a llevar, mi calendario de
27:25
decisiones, literal para que lo copies a
27:27
tu escala. Domingo, cada semana, mercado
27:30
cerrado, revisión técnica de 20 minutos,
27:33
solo ejecución, errores de LEA,
27:35
desconexiones, órdenes rechazadas y
27:38
copiar las noticias de la semana
27:39
entrante al filtro horario. Prohibido
27:41
mirar la rentabilidad. Cada 15 días
27:44
semáforos contra línea base y confirmar
27:46
que los amarillos tienen el sizing al
27:49
50%. Primer domingo de cada mes.
27:52
Comparar cada bot con su back test.
27:54
Rebalancear los bloques si se desvían
27:56
más de 10 puntos. revisar correlaciones
27:59
y ejecutar el retiro. El retiro es una
28:02
línea del checklist, entre otras dos.
28:05
Nunca un impulso. Cada trimestre,
28:08
robustez completa, chequeo del alfa de
28:11
Kai y el informe del coste de mis
28:13
impulsos. Y enero, reestructuración
28:16
anual. Ahora tu revisión. Imagina a un
Tu primer paso para construir un bot de trading validado
28:19
trader típico con 5000 € o $5,000 y tres
28:23
bots validados. Riesgo por operación
28:26
0.5%.
28:27
Un bot tendencial, uno de reversión,
28:30
correlación medida entre ambos. Semáforo
28:33
simple contra el Beline de su back test.
28:36
[música] Escalera de emergencia, alerta
28:38
al 8% de dryown. Mitad de tamaño al 12,
28:42
todo fuera al 15. Revisión dominical de
28:45
20 minutos. Decisión de retiro solo el
28:48
primer domingo de cada mes. Con eso
28:51
trader ya opera con más disciplina que
28:53
el 95% del sector retail. No necesita 32
28:57
bots, necesita el protocolo. El tamaño
29:00
llega después, el sistema va primero. Te
29:03
prometí enseñarte el setup sin guardarme
29:06
nada y ahí lo tienes. Infraestructura,
29:09
equipo, semáforo, kill switch, cantera,
29:12
cementerio y la nómina mensual.
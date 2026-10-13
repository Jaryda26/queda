# Planes: qué hace Queda con IA y sin IA

## Resumen

| | Básico $25 | Individual $49 | Familiar $99 |
|---|---|---|---|
| Movimientos, presupuesto, historial, dashboard | ✅ | ✅ | ✅ |
| Recordatorios | hasta 5 | ilimitados | ilimitados |
| Comandos de voz ("abre el dashboard", "ya pagué la luz", "pon mi presupuesto semanal en 2000", "aprende que…") | ✅ | ✅ | ✅ |
| Registro simple por reglas ("gasté 150 en gasolina", "ayer compré café 45", "cobré 3000") | ✅ | ✅ | ✅ |
| Consultas calculadas ("¿en qué he gastado más?", "¿qué está afectando mi presupuesto?", "¿cuánto llevo?", "¿cuánto gasté en comida esta semana?") | ✅ | ✅ | ✅ |
| Consejos según tus números (calculados) | ✅ | ✅ | ✅ |
| Metas de ahorro (crear, abonar, retirar, progreso) | ✅ | ✅ | ✅ |
| Frases libres con IA (fechas raras, varios datos, recordatorios hablando) | 🔒 | ✅ | ✅ |
| Consejos personalizados redactados por IA | 🔒 | ✅ | ✅ |
| Consultas con IA por día (por cuenta) | — | 30 | 80 |
| Miembros | 1 | 1 | 5 |

El tope de IA es por cuenta y por día (hora de México) y se reinicia a medianoche.
**Nunca gastan cupo:** comandos, consultas calculadas, metas, consejos calculados ni el registro por reglas.

## Cómo decide Queda cada frase (en este orden)

1. Frases que el usuario enseñó en Aprendizaje.
2. Comandos y consultas por reglas (gratis, todos los planes).
3. Registro simple por reglas. Con IA, si la regla está segura (categoría reconocida) se usa la regla y **no se gasta IA**; si no, entra la IA.
4. IA (solo Individual/Familiar y si queda cupo). Si la IA falla, se devuelve el cupo y se usa la lectura por reglas si existía.

Sin IA (Básico), lo que las reglas no entienden recibe un mensaje con ejemplos de lo que sí puede decir.
Sin cupo (Individual/Familiar), igual: sigue todo lo gratis y se avisa que el cupo se reinicia a medianoche.

## Respuestas personalizadas (todas calculadas con tus datos)

- **¿En qué he gastado más?** Top 3 categorías con monto y %, y el gasto individual más grande.
- **¿Qué está afectando mi presupuesto?** % usado, categoría que más pesa, categorías que subieron contra el periodo anterior, pagos pendientes antes de que cierre el periodo y proyección (solo con suficientes días de datos).
- **¿Cuánto llevo / cuánto puedo gastar al día?**
- **Dame un consejo.** Básico: hasta 3 consejos por reglas. Individual/Familiar: la IA los redacta con tus cifras y metas (1 consulta de cupo; si la IA falla o no hay cupo, se dan los calculados).

Un abono a una meta **no** es un gasto: no mueve el presupuesto.

## Periodos de calendario

- **Semanal:** 7 días que empiezan el día que el usuario elige (p. ej. viernes a jueves). Se cambia en Presupuesto o diciendo "mi semana inicia el viernes".
- **Quincenal:** del 1 al 15 y del 16 al último día del mes.
- **Mensual:** el mes natural (28, 29, 30 o 31 días).
- El dashboard, el presupuesto y todas las respuestas usan el MISMO periodo. Sin presupuesto se usa el mes natural.

## Asesor en el celular y en la web

- Pantalla **Más → Asesor financiero** (chat). El nombre del agente se edita tocándolo en la barra superior (el mismo de la web) y se puede usar al hablar ("Trobi, cómo voy").
- Gratis (todos los planes, sin IA): cómo voy, cuánto llevo, en qué gasto más, qué día de la semana gasto más, qué categoría diluye mi ingreso, qué afecta mi presupuesto, metas.
- Con IA (Individual/Familiar, gasta 1 del cupo diario): cómo ves mis finanzas, consejo financiero, qué reducir para llegar a mi meta, si puedo invertir (orientación educativa, sin prometer rendimientos).
- Si la IA falla o no hay cupo, el asesor contesta con la versión calculada y no cobra cupo.

## Dónde cambiar los límites

`services/plan_ia_service.py` → `LIMITES_IA_DIARIO` (por `slug` del plan). También se puede
sobrescribir sin tocar código con variables de entorno en Render:
`QUEDA_IA_LIMITE_INDIVIDUAL=40`, `QUEDA_IA_LIMITE_FAMILIAR=100`.

## Pasos para activarlo

0. En Supabase → SQL Editor, correr `sql/periodos.sql` (día de inicio de la semana).
1. En Supabase → SQL Editor, correr `sql/metas_ia.sql` (metas, abonos y contador de IA).
   Sin esto las metas muestran "no disponibles" y la IA funciona **sin tope** (queda aviso en el log).
2. Subir los archivos y hacer `git push` (Render redespliega solo).

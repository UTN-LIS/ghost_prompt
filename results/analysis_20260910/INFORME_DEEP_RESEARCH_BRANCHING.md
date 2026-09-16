# Branching adaptativo y eficiente para generación de código con LLMs

**Revisión de estado del arte y propuesta de investigación**  
**Autor del proyecto:** Matias Koroch  
**Fecha de búsqueda:** 10 de septiembre de 2026

## Resumen ejecutivo

La idea general de “detectar una posición incierta, abrir una rama con otro token, mirar unos pasos hacia adelante y continuar con la alternativa más prometedora” **ya fue propuesta de forma muy cercana**. AdaDec activa un mecanismo *pause-then-rerank* cuando la entropía supera un umbral aprendido y compara continuaciones de corto alcance; reporta mejoras en HumanEval+, MBPP+ y DevEval.[^1] Por lo tanto, no conviene presentar como novedad ni la entropía como disparador, ni el reemplazo top-1/top-2, ni el lookahead corto, ni la selección posterior de una rama.

La oportunidad diferenciadora está en cambiar la pregunta. En vez de estimar “¿esta posición es incierta?” o “¿qué continuación parece más probable?”, propongo estimar:

> **¿Cuánto aumenta la probabilidad de corrección funcional si se explora aquí una alternativa, por cada unidad adicional de cómputo?**

Esto conduce a un decodificador de **valor contrafactual de recuperación**, provisionalmente llamado **CRV-Decode** (*Counterfactual Recovery Value Decoding*). El sistema aprende con pares top-1/top-2 etiquetados por tests una función de valor específica para la intervención: la probabilidad de que la rama alternativa pase cuando la rama original falla. La rama se abre solamente cuando su utilidad esperada neta supera su costo. Un segundo aporte posible es hacer la comparación y eventual reunificación en unidades propias del código —tokens léxicos, eventos del parser o estado AST— para no confundir inserciones o desplazamientos con divergencia semántica.

La conclusión de novedad debe expresarse con cautela: **en la literatura primaria revisada no encontré la combinación exacta de entrenamiento con etiquetas contrafactuales top-1→top-2, decisión explícita por ganancia funcional esperada/costo y reunificación por estado de código**. Esto es una hipótesis de novedad académica, no una garantía mundial ni una búsqueda de patentes.

## 1. Qué muestran los datos propios

La validación del proyecto usa Qwen2.5-Coder-7B-Instruct sobre 20 fallos elegibles de HumanEval, con cinco intervenciones por selector. La sustitución top-2 recuperó 10/20 problemas tanto con entropía como con margen y con la versión semántica alineada. El control aleatorio recuperó 6/20. Sin embargo, la muestra es pequeña: ninguna comparación pareada individual fue significativa después de multiplicidad.

El resultado más útil para diseñar el próximo método no es solamente el 10/20, sino la curva de presupuesto:

| Ramas por problema | Entropía | Semántico alineado |
|---:|---:|---:|
| 1 | 8/20 | 4/20 |
| 2 | 10/20 | 6/20 |
| 3 | 10/20 | 8/20 |
| 4 | 10/20 | 8/20 |
| 5 | 10/20 | 10/20 |

Entropía obtuvo toda su cobertura observada con dos ramas. El selector semántico requirió cinco. Además, los lookaheads semánticos consumieron aproximadamente 29,4 minutos y las ramas completas del selector 5,59 minutos; la suma reconstruida fue 4,81 veces el costo de las ramas de entropía para la misma cobertura final. Esto desaconseja usar un lookahead semántico costoso sobre todas las posiciones.

La alineación, no obstante, sigue siendo metodológicamente importante. El desfase afectó 679/1.649 ventanas (41,2%) y reemplazó 33/100 posiciones del top-5. Después de alinear las continuaciones, la precisión de rama subió de 15/100 a 17/100, aunque se recuperaron los mismos diez problemas. Esto sugiere que la alineación mejora la validez de la medición, pero todavía no aporta un selector más eficiente que entropía.

También aparece complementariedad: entropía y el selector semántico recuperaron un problema exclusivo cada uno; su unión alcanzó 11/20, pero con mayor presupuesto. Por eso el objetivo correcto es aprender **cuándo pagar** por la señal adicional, no sumarla siempre.

Fuentes internas: [informe estadístico](./INFORME_ESTADISTICO.md) e [informe de alineamiento](./INFORME_ALINEAMIENTO.md).

## 2. Antecedente más cercano: AdaDec

AdaDec es el trabajo que más restringe lo que puede reclamarse. Su motivación también es que errores de código provienen de decisiones token a token en puntos de alta incertidumbre. El método aprende un umbral de entropía específico del modelo, pausa cuando lo supera, explora candidatos con lookahead y los reordena antes de continuar.[^1] Su implementación pública expone un largo de lookahead por defecto de 5 y un ancho de 3, además del umbral aprendido por regresión logística.[^2]

Consecuencias para el posicionamiento:

- “Branching activado por entropía” no es novedoso.
- “Explorar top-k solamente en posiciones inciertas” no es novedoso.
- “Mirar algunos tokens hacia adelante y quedarse con una rama” no es novedoso.
- Comparar solamente contra greedy, beam search o muestreo tampoco alcanzaría: AdaDec ya lo hace.

La diferencia defendible debe estar en el **objetivo de decisión**, las **etiquetas de entrenamiento**, la **contabilidad del costo** y/o la **estructura semántica del código**.

## 3. Mapa del estado del arte

### 3.1 Decodificación adaptativa por dificultad o incertidumbre

AdapT observó que ciertos tokens de código son más difíciles, especialmente al comienzo de bloques, y ajustó dinámicamente la temperatura: más exploración en posiciones difíciles y menos ruido en las confiables.[^3] UnCert-CoT decide entre generación directa y múltiples caminos de razonamiento usando entropía o diferencia de probabilidades, con la intención explícita de concentrar cómputo en problemas difíciles.[^4] Estos trabajos hacen que “usar incertidumbre para asignar cómputo” tampoco sea una novedad suficiente.

Un trabajo reciente sobre estimación de incertidumbre para código separa señales léxicas, algorítmicas y funcionales, y muestra que combinarlas puede ser más informativo que tratar el código como texto plano.[^5] Esto apoya conceptualmente incorporar semántica, pero también exige demostrar que la señal nueva mejora decisiones y no solo correlaciones.

### 3.2 Búsqueda con ejecución o verificadores

Planning-Guided Transformer Decoding usa lookahead y tests públicos para guiar la generación hacia programas de mayor calidad.[^6] LEVER aprende un verificador a partir del programa y sus resultados de ejecución, combina ese puntaje con la probabilidad generativa y marginaliza programas con el mismo resultado.[^7] µCODE aprende un verificador con recompensas de ejecución y lo usa en búsqueda Best-of-N de múltiples turnos.[^8] Trabajos de supervisión de proceso para código asignan señales a segmentos o estados intermedios, no solo al programa final.[^9]

También existe una formulación teórica de generación asistida por verificadores donde el valor de un prefijo representa si puede completarse hasta una solución válida y se permite *backtracking* cuando el proceso queda atascado.[^10] En consecuencia, tampoco son nuevos por sí solos los verificadores de prefijos, la poda, el retroceso o la ejecución como guía.

### 3.3 Búsqueda estructurada y semántica

Los *semantic scaffolds* ya demostraron que representar estructura sintáctica/semántica de alto nivel antes de un beam search puede mejorar cobertura y eficiencia en síntesis de programas.[^11] TokenScope ofrece métricas por token, reemplazo interactivo, branching contrafactual y agregación basada en AST para analizar modelos de código.[^12] Por eso “usar AST” o “hacer branching contrafactual” tampoco bastan como reclamo aislado.

La reunificación de hipótesis equivalentes tiene antecedentes generales en decodificación: en traducción neuronal se han recombinado prefijos considerados equivalentes para mantener calidad con haces menores.[^13] No encontré en la búsqueda una aplicación que combine reunificación por estado léxico/parser/AST con branching contrafactual top-2 destinado a recuperar código funcionalmente correcto. Aun así, el reclamo debe ser sobre esa combinación concreta, no sobre la idea general de recombinación.

### 3.4 Asignación adaptativa de cómputo

La literatura reciente de inferencia con búsqueda usa modelos de valor o proceso para decidir qué estados expandir, podar o priorizar.[^14] V-Star también estudia verificadores y cómputo adaptativo en matemática y código.[^15] Esto vuelve riesgoso afirmar “primer método que asigna cómputo adaptativamente”. La contribución tiene que ser más estrecha: **una función de valor contrafactual específica de la acción de ramificar en un token de código**, calibrada contra costo real.

## 4. Propuesta: CRV-Decode

### 4.1 Variable objetivo

Para una tarea (x), un prefijo (p_t), la continuación greedy original (y^{(1)}) y una intervención que fuerza el token top-2 y luego continúa (y^{(2)}), definir:

\[
R_t = \mathbb{1}[\text{tests}(y^{(2)})=1 \land \text{tests}(y^{(1)})=0].
\]

La función de recuperación es:

\[
q_t = P(R_t=1 \mid \phi_t),
\]

donde \(\phi_t\) contiene solamente señales disponibles en el momento de decidir: entropía, margen, probabilidades top-k, tipo de token, estado del lexer/parser, posición dentro de línea/bloque, historial local de incertidumbre y, si se habilita una segunda etapa, rasgos de lookahead alineado.

Esto difiere de predecir simplemente si el programa final falla. También difiere de estimar la probabilidad de que una rama aislada sea correcta. La etiqueta pregunta por el **beneficio causal-operacional de una intervención concreta respecto de la alternativa que se habría seguido**.

### 4.2 Decisión sensible al costo

Sea \(C_t(a)\) el costo esperado de la acción (a\): no ramificar, hacer un lookahead corto, abrir una rama completa o ejecutar un verificador. La política elige:

\[
a_t^* = \arg\max_a \left[\widehat{\Delta P}_{t,a}(\text{PASS}) - \lambda C_t(a)\right].
\]

Una versión interpretable para top-2 sería ramificar si:

\[
\frac{\widehat{q}_t \cdot V_{\text{PASS}}}{\widehat{C}_{\text{branch},t}} > \tau.
\]

El presupuesto puede expresarse en tokens generados, llamadas forward, FLOPs aproximados, joules o latencia de pared. Reportar solo cantidad de ramas sería insuficiente, porque el experimento propio ya mostró que igualar ramas no iguala cómputo.

### 4.3 Cascada de evaluación

El mecanismo recomendado tiene tres niveles:

1. **Filtro barato en cada token.** Calcular entropía, margen y rasgos estructurales incrementales. La evidencia propia favorece entropía para presupuestos pequeños.
2. **Diagnóstico selectivo.** Solo para el pequeño conjunto con alto valor preliminar, generar 4–8 tokens para top-1 y top-2, alinearlos por tokens léxicos o eventos de parser y actualizar \(q_t\).
3. **Expansión funcional.** Solo si la utilidad esperada sigue siendo positiva, mantener ambas ramas hasta un límite estructural —fin de expresión, línea o bloque— y evaluarlas con un verificador de prefijo, análisis estático o tests parciales disponibles.

Así, la semántica no desaparece: deja de ser un impuesto global y se convierte en una prueba diagnóstica adquirida cuando puede cambiar la decisión.

### 4.4 Poda, detención y reunificación

Cada rama mantiene una estimación calibrada de probabilidad de éxito y un intervalo o medida de incertidumbre. Se detiene la exploración cuando:

- una rama domina a la otra por encima de un umbral;
- el costo marginal de seguir mirando supera la mejora máxima posible;
- una rama llega a un estado imposible del parser o falla una verificación barata;
- ambas ramas vuelven a un mismo estado observable de código.

La reunificación debe definirse conservadoramente. Coincidencia textual o embeddings similares no bastan. Un primer criterio reproducible puede exigir simultáneamente: mismo estado del parser incremental, mismo conjunto de nombres definidos/referenciados en el alcance local, misma profundidad de bloque y sufijo léxico compatible. La equivalencia funcional completa es indecidible en general; el método debe llamarlo “estado abstracto equivalente”, no equivalencia semántica probada.

### 4.5 Ingeniería de eficiencia

- Reutilizar el KV-cache del prefijo común.
- Evaluar top-1 y top-2 en batch.
- No generar lookahead para posiciones descartadas por el filtro barato.
- Operar en límites de lexer/parser para reducir comparaciones desfasadas.
- Guardar una sola rama de reserva; evitar un árbol ancho permanente.
- Usar *successive halving*: poca profundidad para muchos candidatos y mayor profundidad solo para los supervivientes.
- Medir tiempo end-to-end, tokens procesados y memoria pico, además de pass@1.

## 5. Qué sería realmente nuevo y qué no

| Componente | Estado de novedad tras la revisión |
|---|---|
| Entropía como disparador | No: AdaDec y otros métodos adaptativos |
| Top-k/top-2 branching | No: búsqueda y AdaDec |
| Lookahead corto | No: AdaDec y PG-TD |
| Verificador o ejecución | No: LEVER, µCODE, PG-TD y otros |
| AST o estructura de código | No por sí solo: TokenScope, scaffolds y modelos estructurales |
| Asignación adaptativa de cómputo | No como formulación amplia |
| Etiqueta “top-2 pasa y top-1 falla” para decidir dónde intervenir | **Aparentemente diferenciadora** en lo revisado |
| Optimizar recuperación funcional esperada por unidad de costo | **Aparentemente diferenciadora** en esta aplicación concreta |
| Cascada barata→semántica→funcional entrenada para esa intervención | **Posible contribución**, debe validarse contra AdaDec |
| Reunificación conservadora por estado abstracto de código | **Posible segunda contribución**, con antecedentes de recombinación general |

La afirmación aconsejada para un artículo sería:

> “Proponemos una política de decodificación sensible al costo que aprende, a partir de intervenciones contrafactuales top-1/top-2 verificadas por tests, el valor esperado de abrir una rama en cada decisión. A diferencia de métodos que activan lookahead por incertidumbre y reordenan por probabilidad, la política optimiza directamente la recuperación funcional por unidad de cómputo e incorpora señales estructurales alineadas de código.”

No conviene usar “somos los primeros” hasta actualizar la búsqueda justo antes de enviar el trabajo y revisar también citas de AdaDec, literatura no indexada y patentes si la prioridad fuera protección intelectual.

## 6. Diseño experimental para defender la contribución

### 6.1 Separación de datos

Los 20 fallos actuales sirven para formular hipótesis, no para confirmar el nuevo método. Las reglas elegidas después de observarlos deben congelarse. Se necesita:

- conjunto de entrenamiento para la función \(q_t\);
- validación para umbrales, calibración y costo \(\lambda\);
- test final con tareas y, preferiblemente, familias de benchmark no vistas.

Usar HumanEval+, MBPP+, EvalPlus y al menos un benchmark distinto en estilo o dificultad. AdaDec ya evalúa HumanEval+, MBPP+ y DevEval, por lo cual repetir solo HumanEval base dejaría una comparación débil.[^1]

### 6.2 Etiquetado

En entrenamiento, muestrear posiciones estratificadas por entropía, margen, tipo estructural y posición. Evaluar ambas acciones top-1/top-2 bajo exactamente el mismo límite de tokens y tests. No etiquetar como FAIL las posiciones nunca ejecutadas. Registrar:

- cuatro resultados posibles: ambos pasan, solo top-1, solo top-2, ninguno;
- costo de lookahead, rama y verificación;
- EOS, truncamiento, excepción y timeout por separado;
- probabilidades y ranks obtenidos en la misma pasada;
- trazas de alineamiento sin redondeo.

El muestreo no debe limitarse al top de un selector, porque eso produciría sesgo de selección para entrenar \(q_t\). Puede usarse *importance weighting* si no es viable evaluar uniformemente todas las posiciones.

### 6.3 Baselines imprescindibles

1. Greedy.
2. Muestreo con temperatura fija.
3. AdapT.[^3]
4. Beam search con presupuesto comparable.
5. AdaDec, usando su implementación pública.[^2]
6. Entropía top-k bajo el mismo presupuesto.
7. Selector semántico alineado actual.
8. Oracle retrospectivo, claramente marcado como cota y no método ejecutable.

### 6.4 Ablaciones

- Entropía sola vs. entropía + estructura.
- Predictor de fallo general vs. predictor de recuperación contrafactual.
- Sin costo vs. costo por tokens vs. costo por latencia.
- Sin lookahead vs. lookahead fijo vs. adquisición adaptativa.
- Alineamiento por subtoken vs. lexer vs. eventos de parser.
- Sin reunificación vs. reunificación conservadora.
- Top-2 fijo vs. número adaptativo de candidatos.

La ablation crucial compara dos objetivos con idénticas features: \(P(\text{FAIL original})\) frente a \(P(\text{top-2 PASS}\land\text{top-1 FAIL})\). Si el segundo no selecciona mejores intervenciones a igual costo, la principal hipótesis queda refutada.

### 6.5 Métricas

- pass@1 end-to-end;
- recuperación condicional de fallos;
- área bajo la curva PASS vs. tokens/FLOPs/latencia;
- costo medio y percentiles de cola;
- ramas abiertas por problema;
- precisión y recall de posiciones recuperables;
- calibración de \(q_t\): Brier, ECE y curvas de confiabilidad;
- pruebas pareadas por tarea y bootstrap agrupado por problema;
- robustez por modelo, lenguaje y benchmark.

El resultado principal debería ser una frontera de Pareto: para cada presupuesto, qué método logra mayor corrección. Una mejora de accuracy sin contabilidad end-to-end no demostraría eficiencia.

## 7. Secuencia de trabajo recomendada

### Fase 1 — baseline reproducible

Implementar AdaDec o adaptar su repositorio al mismo Qwen y benchmarks. Repetir el protocolo actual con HumanEval+ y presupuestos homogéneos. Esta fase evita redescubrir su resultado.

### Fase 2 — dataset contrafactual

Expandir de 20 fallos a varios cientos de tareas y muestrear posiciones más allá del top-5. Construir las etiquetas de cuatro estados. Antes de usar una red compleja, entrenar regresión logística o gradient boosting con validación por tarea.

### Fase 3 — política costo-beneficio

Calibrar \(q_t\) y elegir acciones mediante utilidad neta. Comparar contra un umbral de entropía ajustado para consumir el mismo presupuesto. Si no supera AdaDec en la curva costo-calidad, detener o revisar features.

### Fase 4 — alineación estructural y reunificación

Agregar lexer/parser solo después de demostrar que el objetivo contrafactual aporta. Medir por separado cuánto mejora selección y cuánto reduce cómputo la reunificación. No mezclar todas las innovaciones en el primer resultado.

### Fase 5 — generalización

Congelar política y evaluar en nuevos modelos, tamaños y benchmarks. La novedad será mucho más creíble si el predictor transfiere o puede recalibrarse con pocos ejemplos.

## 8. Riesgos y criterios de abandono

1. **AdaDec puede absorber la ganancia.** Si una réplica fuerte iguala CRV-Decode a mismo costo, el aporte debe concentrarse en análisis causal/diagnóstico o reunificación, no en performance.
2. **El top-2 puede ser demasiado restrictivo.** Algunas recuperaciones requerirán top-3 o una alternativa estructural. Probar número adaptativo de candidatos.
3. **Las etiquetas son caras.** Se puede usar muestreo activo, pero sin convertir posiciones no observadas en negativas.
4. **El verificador puede aprender el benchmark.** Separar familias de problemas y evaluar bajo cambio de distribución.
5. **La similitud semántica puede no predecir corrección.** Los datos actuales ya advierten que mejorar alineamiento no mejoró cobertura.
6. **Reunificar puede borrar diferencias relevantes.** Exigir condiciones conservadoras y reportar falsos merges.

## 9. Recomendación final

La propuesta con mejor equilibrio entre originalidad, viabilidad y evidencia disponible es:

> **Decodificación con valor contrafactual de recuperación:** un LLM genera greedy y usa señales baratas para identificar decisiones candidatas. Un predictor entrenado con tests estima la ganancia funcional específica de sustituir top-1 por top-2. Solo cuando esa ganancia esperada supera el costo se adquiere un lookahead alineado o se abre una rama. Las ramas se evalúan progresivamente y se podan o reúnen en límites estructurales del código.

Para una presentación breve, el mensaje central puede ser:

> “No ramificamos donde el modelo simplemente duda; ramificamos donde los datos indican que una alternativa puede rescatar el programa y donde el beneficio justifica el costo.”

## Fuentes

[^1]: He et al., “AdaDec: A Uncertainty-Guided Lookahead Decoding Framework for LLM-Based Code Generation,” FSE 2026 / arXiv. https://arxiv.org/abs/2506.08980
[^2]: SYSUSELab, implementación oficial de AdaDec. https://github.com/SYSUSELab/AdaDec
[^3]: Zhu et al., “Hot or Cold? Adaptive Temperature Sampling for Code Generation with Large Language Models,” AAAI 2024. https://arxiv.org/abs/2309.02772
[^4]: Zhu et al., “Uncertainty-Guided Chain-of-Thought for Code Generation with LLMs.” https://arxiv.org/abs/2503.15341
[^5]: Shi et al., “Code Is More Than Text: Uncertainty Estimation for Code Generation.” https://arxiv.org/abs/2606.09577
[^6]: Zhang et al., “Planning with Large Language Models for Code Generation.” https://arxiv.org/abs/2303.05510
[^7]: Ni et al., “LEVER: Learning to Verify Language-to-Code Generation with Execution.” https://arxiv.org/abs/2302.08468
[^8]: “Multi-Turn Code Generation Through Single-Step Rewards (µCODE).” https://openreview.net/pdf/a0694f554eebc1ceeed0763be980698c9def09fe.pdf
[^9]: “Process-Supervised Reinforcement Learning for Code Generation.” https://openreview.net/pdf?id=uRZftun4hg
[^10]: “On the Query Complexity of Verifier-Assisted Language Generation.” https://openreview.net/pdf?id=9oIjvaDhoN
[^11]: Zhong, Stern y Klein, “Semantic Scaffolds for Pseudocode-to-Code Generation,” ACL 2020. https://aclanthology.org/2020.acl-main.208/
[^12]: Esmaeili y Fard, “TokenScope: Token-Level Explainability and Interpretability for Code-Oriented Tasks in Large Language Models.” https://arxiv.org/abs/2607.01235
[^13]: Zhang et al., “Exploring Recombination for Efficient Decoding of Neural Machine Translation,” EMNLP 2018. https://aclanthology.org/D18-1511/
[^14]: “What If We Allocate Test-Time Compute Adaptively?” https://arxiv.org/abs/2602.01070
[^15]: “V-Star: Training Verifiers for Self-Taught Reasoners.” https://openreview.net/pdf?id=stmqBSW2dV

## Nota metodológica de la búsqueda

Se buscaron trabajos hasta el 10 de septiembre de 2026 mediante consultas combinando *code generation*, *adaptive decoding*, *uncertainty*, *top-2 branching*, *counterfactual token*, *lookahead*, *prefix verifier*, *process reward*, *compute allocation*, *AST*, *semantic equivalence*, *recombination* y *branch merging*. Se priorizaron artículos primarios, páginas oficiales de conferencias, arXiv, OpenReview, ACL Anthology y el repositorio oficial de AdaDec. La búsqueda cubrió trabajos académicos en inglés accesibles e indexados; no constituye una revisión sistemática exhaustiva de todas las bases, literatura no pública ni patentes.

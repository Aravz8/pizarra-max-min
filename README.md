# 📐 Pizarra Interactiva: Máximos y Mínimos

Aplicación web interactiva para el análisis de funciones matemáticas: calcula
derivadas, encuentra puntos críticos y de inflexión, los clasifica, y grafica
todo el comportamiento de la función — replicando el procedimiento que se
hace a mano en una pizarra de clase de Cálculo Diferencial.

**App en vivo:** _(pega aquí el link que te da Streamlit Cloud después de desplegar)_

## ¿Qué hace?

Dada una función f(x), la pizarra calcula y muestra paso a paso:

1. **Función original**
2. **Primera derivada f'(x)** — detecta automáticamente si aplica la regla
   de la potencia, del producto, del cociente o de la cadena, y muestra el
   desarrollo antes de simplificar
3. **Igualar f'(x) = 0 y resolver** — prioriza factorización completa sobre
   la fórmula cuadrática, mostrando el método usado
4. **Evaluar f(x) en cada punto crítico** — con la sustitución completa
5. **Segunda derivada f''(x)** — con el mismo desarrollo paso a paso, y su
   evaluación en cada punto crítico
6. **Clasificación** — máximo, mínimo, o punto de inflexión, justificado
   con el criterio de la segunda (o primera) derivada
7. **Puntos de inflexión** — resolviendo f''(x) = 0, con sus coordenadas
   exactas y aproximadas

Además, en el resumen junto a la gráfica se incluyen:
- **Dominio** de la función
- **Intervalos de crecimiento y decrecimiento**
- **Intervalos de concavidad**

La gráfica se dibuja con escala 1:1 real en ambos ejes, zoom automático
hacia la zona relevante, y una animación tipo "escáner" opcional.

## Cómo usarla

1. Escribe tu función en el campo `f(x) =` usando sintaxis de Python:
   - Potencias: `x**2`, `x**4`
   - Funciones: `sin(x)`, `cos(x)`, `exp(x)`, `sqrt(x)`, `log(x)`
2. Presiona **Analizar**.
3. Explora la gráfica (izquierda) y el procedimiento completo (derecha,
   con scroll independiente).

### Ejemplos para probar

```
x**4 + 2*x**3 - 2*x**2 + 4
x**3 - 3*x + 1
x**2/(x-1)
sin(x) + x/2
```

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run pizarra_max_min.py
```

Esto abre la app en `http://localhost:8501`.

## Tecnologías

- [Streamlit](https://streamlit.io) — interfaz web
- [SymPy](https://www.sympy.org) — cálculo simbólico (derivadas, factorización, dominio)
- [Plotly](https://plotly.com/python/) — gráficas interactivas
- [NumPy](https://numpy.org) — evaluación numérica para graficar

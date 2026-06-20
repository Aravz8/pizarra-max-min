"""
PIZARRA INTERACTIVA — MÁXIMOS Y MÍNIMOS
=========================================
Aplicación educativa en Streamlit que permite al usuario escribir una
función f(x), y el programa:
  1. Calcula f'(x) y f''(x) (paso a paso, mostrado en pantalla)
  2. Encuentra los puntos críticos resolviendo f'(x) = 0
  3. Clasifica cada punto crítico como máximo o mínimo (criterio de la
     segunda derivada, con respaldo del criterio de la primera derivada
     cuando f''(x) = 0)
  4. Grafica f(x) con escala real 1:1 en ambos ejes, haciendo zoom
     automático e inteligente a la zona donde están los puntos
     críticos (para que no se "aplasten" contra valores enormes de x^n)
  5. Muestra en un panel lateral, en tema oscuro, el proceso matemático
     paso a paso, como en una pizarra de clase.
"""

import time
import re

import streamlit as st
import sympy as sp
import numpy as np
import plotly.graph_objects as go

# ----------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Pizarra: Máximos y Mínimos",
    page_icon="📈",
    layout="wide",
)

# ----------------------------------------------------------------------
# PALETA — TEMA OSCURO LEGIBLE
# ----------------------------------------------------------------------
BG_APP = "#14161c"
BG_CARD = "#1c1f29"
BORDE_CARD = "#3a3f52"
TEXTO_PRINCIPAL = "#eef0f5"
TEXTO_SECUNDARIO = "#a9b0c3"
AZUL_TITULO = "#5ab0ff"
ROJO_MAX = "#ff5d5d"
AZUL_MIN = "#5ab0ff"
AMARILLO_INFLEX = "#e0c341"
VERDE_ACENTO = "#3ddc97"
CURVA_COLOR = "#7fd1ff"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BG_APP};
    }}
    h1, h2, h3, h4, h5, p, span, label, .stMarkdown, .stCaption, div[data-testid="stCaptionContainer"] {{
        color: {TEXTO_PRINCIPAL} !important;
    }}
    .stCaption, [data-testid="stCaptionContainer"] p {{
        color: {TEXTO_SECUNDARIO} !important;
    }}
    .board-box {{
        background-color: {BG_CARD};
        border: 1px solid {BORDE_CARD};
        border-radius: 10px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }}
    .board-box p, .board-box span, .board-box div {{
        color: {TEXTO_PRINCIPAL} !important;
    }}
    .step-title {{
        color: {AZUL_TITULO} !important;
        font-weight: 700;
        font-size: 0.92rem;
        margin: 0 0 2px 0;
    }}
    .crit-max {{ color: {ROJO_MAX} !important; font-weight: 700; margin: 2px 0; }}
    .crit-min {{ color: {AZUL_MIN} !important; font-weight: 700; margin: 2px 0; }}
    .crit-none {{ color: {AMARILLO_INFLEX} !important; font-weight: 700; margin: 2px 0; }}
    .stTextInput input {{
        color: {TEXTO_PRINCIPAL} !important;
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDE_CARD} !important;
    }}
    .stSlider label, .stCheckbox label p {{ color: {TEXTO_PRINCIPAL} !important; }}
    div[data-baseweb="slider"] {{ padding-top: 4px; }}
    .stButton button {{
        background-color: {AZUL_TITULO} !important;
        color: #0a0a0f !important;
        font-weight: 700;
        border: none;
    }}
    table {{ color: {TEXTO_PRINCIPAL} !important; }}
    thead tr th {{ color: {AZUL_TITULO} !important; background-color: {BG_CARD} !important; }}
    tbody tr td {{ background-color: {BG_CARD} !important; }}
    hr {{ border-color: {BORDE_CARD}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"<h1 style='margin-bottom:0; font-size:1.5rem; font-weight:600;'>Máximos y Mínimos</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:{TEXTO_SECUNDARIO}; margin-top:2px; margin-bottom:18px; font-size:0.85rem;'>"
    "Escribe una función para encontrar y clasificar sus puntos críticos.</p>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# ENTRADA DEL USUARIO (EL "TABLERO")
# ----------------------------------------------------------------------
x = sp.symbols("x")

func_str = st.text_input(
    "f(x) =",
    value="",
    placeholder="Ej: x**4 + 2*x**3 - 2*x**2 + 4",
    help="Usa sintaxis de Python: ** potencia, * multiplicación, sin(x), cos(x), exp(x), sqrt(x).",
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    zoom_auto = st.checkbox("🔍 Zoom automático", value=True)
with col_b:
    animar = st.checkbox("🖥️ Animar como escáner", value=True)
with col_c:
    calcular = st.button("Analizar", type="primary", use_container_width=True)

rango = st.slider(
    "Rango manual del eje x (se usa si el zoom automático está desactivado)",
    min_value=-20, max_value=20, value=(-5, 5),
    disabled=zoom_auto,
)

# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------------------
def parse_function(expr_str):
    """Convierte el texto del usuario en una expresión simbólica de sympy."""
    transformations = sp.parsing.sympy_parser.standard_transformations + (
        sp.parsing.sympy_parser.implicit_multiplication_application,
    )
    local_dict = {
        "x": x, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
        "exp": sp.exp, "sqrt": sp.sqrt, "log": sp.log, "ln": sp.log,
        "pi": sp.pi, "e": sp.E, "Abs": sp.Abs,
    }
    return sp.parsing.sympy_parser.parse_expr(
        expr_str, local_dict=local_dict, transformations=transformations
    )


def _limpiar_latex(latex_str):
    """Normaliza espacios y signos en una cadena LaTeX al unir términos."""
    s = latex_str.replace("+ -", "- ")
    s = re.sub(r"-\s+", "- ", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s


def derivar_paso_a_paso(f_expr, x, nombre_funcion="f'", simplificar_entrada=False):
    """
    Devuelve (metodo:str, pasos:list[str]) mostrando la derivada de f_expr
    aplicando la regla correspondiente (potencia, cociente, producto, o
    cadena) ANTES de simplificar del todo, para que se vea como un
    procedimiento manual y no como un resultado ya "mágico".

    nombre_funcion: el lado izquierdo a mostrar en cada paso (por ejemplo
        "f'" cuando estamos derivando f(x) para obtener f'(x), o "f''"
        cuando estamos derivando f'(x) para obtener f''(x)).
    simplificar_entrada: si True, simplifica f_expr ANTES de aplicar la
        regla -- pero solo cuando f_expr no es ya un polinomio puro, para
        no arriesgarnos a que sympy lo factorice en un "producto" y
        cambie el método pedagógico (un polinomio siempre se deriva por
        la regla de la potencia, nunca por la regla del producto).
    """
    if simplificar_entrada and not f_expr.is_polynomial(x):
        f_expr = sp.simplify(f_expr)

    pasos = []

    # ---- CASO 1: POLINOMIO PURO -> derivar término a término con la
    #              regla de la potencia. Se revisa PRIMERO y de forma
    #              aislada porque sp.simplify puede factorizar un
    #              polinomio (ej. 4x^3+24x^2 -> 4x^2(x+6)) y eso NO debe
    #              hacer que se trate como "producto". ----
    if f_expr.is_polynomial(x):
        expr_expandida = sp.expand(f_expr)
        poly = sp.Poly(expr_expandida, x)
        terminos = [coeff * x**monom[0] for monom, coeff in poly.terms()]

        partes_derivada = []
        for t in terminos:
            dt = sp.diff(t, x)
            if dt == 0:
                continue
            partes_derivada.append(sp.latex(dt))
        if partes_derivada:
            cuerpo = _limpiar_latex(" + ".join(partes_derivada))
            pasos.append(f"{nombre_funcion}(x) = {cuerpo}")
        f_simpl = sp.expand(sp.diff(f_expr, x))
        pasos.append(f"{nombre_funcion}(x) = {_limpiar_latex(sp.latex(f_simpl))}")
        return "regla de la potencia", pasos

    # ---- CASO 2: COCIENTE REAL  f = u/v  (con v polinomial en x,
    #              para no confundir con exp(-x^2) = 1/exp(x^2)) ----
    f_together = sp.together(f_expr)
    num, den = sp.fraction(f_together)
    if den != 1 and not den.is_number and den.is_polynomial(x):
        u, v = num, den
        du, dv = sp.diff(u, x), sp.diff(v, x)
        pasos.append(
            f"{nombre_funcion}(x) = \\dfrac{{({sp.latex(du)})({sp.latex(v)}) - ({sp.latex(u)})({sp.latex(dv)})}}"
            f"{{({sp.latex(v)})^2}}"
        )
        numerador_sin_simpl = sp.expand(du * v - u * dv)
        denominador_sin_simpl = sp.expand(v**2)
        pasos.append(
            f"{nombre_funcion}(x) = \\dfrac{{{_limpiar_latex(sp.latex(numerador_sin_simpl))}}}"
            f"{{{sp.latex(denominador_sin_simpl)}}}"
        )
        f_final = formatear_expresion(sp.simplify(sp.diff(f_expr, x)), x)
        pasos.append(f"{nombre_funcion}(x) = {sp.latex(f_final)}")
        return "regla del cociente", pasos

    # ---- CASO 3: PRODUCTO  f = u·v  (dos factores "estructurales", el
    #              coeficiente numérico se absorbe dentro de uno de ellos
    #              para no perderlo) ----
    if f_expr.is_Mul:
        coeficiente = sp.Integer(1)
        factores = []
        for a in f_expr.args:
            if a.is_Number:
                coeficiente *= a
            else:
                factores.append(a)
        tiene_exponente_negativo = any(
            fac.is_Pow and fac.args[1].is_negative for fac in f_expr.args
        )
        if len(factores) == 2 and not tiene_exponente_negativo:
            u, v = coeficiente * factores[0], factores[1]
            du, dv = sp.diff(u, x), sp.diff(v, x)
            pasos.append(
                f"{nombre_funcion}(x) = ({sp.latex(du)})({sp.latex(v)}) + ({sp.latex(u)})({sp.latex(dv)})"
            )
            fexpandida = sp.expand(du * v + u * dv)
            pasos.append(f"{nombre_funcion}(x) = {_limpiar_latex(sp.latex(fexpandida))}")
            return "regla del producto", pasos

    # ---- CASO 4: SUMA DE TÉRMINOS NO POLINOMIAL -> derivar término a
    #              término (cubre mezclas como sin(x) + x/2) ----
    expr_expandida = sp.expand(f_expr)
    if expr_expandida.is_Add:
        terminos = list(expr_expandida.args)
        partes_derivada = []
        for t in terminos:
            dt = sp.diff(t, x)
            if dt == 0:
                continue
            partes_derivada.append(sp.latex(dt))
        if partes_derivada:
            cuerpo = _limpiar_latex(" + ".join(partes_derivada))
            pasos.append(f"{nombre_funcion}(x) = {cuerpo}")
        f_simpl = sp.expand(sp.diff(f_expr, x))
        pasos.append(f"{nombre_funcion}(x) = {_limpiar_latex(sp.latex(f_simpl))}")
        return "regla de la suma", pasos

    # ---- CASO 5: caso general (potencia compuesta / cadena / función sola) ----
    f_simpl = sp.simplify(sp.diff(f_expr, x))
    pasos.append(f"{nombre_funcion}(x) = {sp.latex(f_simpl)}")
    return "regla de la cadena", pasos


def formatear_expresion(expr, x):
    """
    Da formato "de pizarra" a una expresión derivada:
    - Si es polinomial pura, la expande (términos separados, como
      4x^3 + 6x^2 - 4x), que es como se ve a mano en un polinomio.
    - Si es una fracción/cociente, la combina en una sola fracción con
      denominador común factorizado (como 2/(x-1)^3), en vez de dejarla
      como varios términos fraccionarios sueltos.
    """
    if expr.is_polynomial(x):
        return sp.expand(expr)
    combinada = sp.together(sp.simplify(expr))
    num, den = sp.fraction(combinada)
    if den != 1:
        den = sp.factor(den)
    return num / den


def clasificar_punto(fpp_expr, x0, fprime_expr):
    """
    Clasifica un punto crítico x0 usando el criterio de la segunda derivada.
    Si f''(x0) = 0, usa el criterio de la primera derivada (cambio de signo).
    """
    try:
        val_fpp = fpp_expr.subs(x, x0)
        val_fpp_num = complex(val_fpp.evalf())
    except Exception:
        val_fpp_num = None

    if val_fpp_num is not None and abs(val_fpp_num.imag) < 1e-9:
        val_real = val_fpp_num.real
        if val_real > 1e-9:
            return "mínimo", f"f''({sp.nsimplify(x0)}) = {sp.nsimplify(val_fpp)} > 0 → concavidad hacia arriba"
        elif val_real < -1e-9:
            return "máximo", f"f''({sp.nsimplify(x0)}) = {sp.nsimplify(val_fpp)} < 0 → concavidad hacia abajo"

    delta = 1e-3
    try:
        x0_f = float(x0)
        izq = float(fprime_expr.subs(x, x0_f - delta).evalf())
        der = float(fprime_expr.subs(x, x0_f + delta).evalf())
    except Exception:
        return "punto de inflexión / no concluyente", "No fue posible evaluar el entorno del punto."

    if izq > 0 and der < 0:
        return "máximo", "f' cambia de + a − (criterio de la primera derivada)"
    elif izq < 0 and der > 0:
        return "mínimo", "f' cambia de − a + (criterio de la primera derivada)"
    else:
        return "punto de inflexión (no es extremo)", "f' no cambia de signo alrededor del punto"


def analizar_metodo_resolucion(fprime_expr, x):
    """
    Determina qué método de resolución usar para f'(x) = 0, priorizando
    SIEMPRE la factorización completa (factor común + factores lineales
    con raíces racionales), y recurriendo a la fórmula cuadrática /
    general solo cuando la factorización no llega a raíces exactas.

    Devuelve: (metodo:str, pasos:list[str])  -- pasos en formato LaTeX
    """
    expr = sp.expand(fprime_expr)
    pasos = []

    poly = sp.Poly(expr, x) if expr.is_polynomial(x) else None
    grado = poly.degree() if poly else None

    # Caso trivial: ecuación lineal
    if grado is not None and grado <= 1:
        return "ecuación lineal", [f"{sp.latex(expr)} = 0"]

    pasos.append(f"{sp.latex(expr)} = 0")

    # ---- PASO A: sacar factor común (incluye potencias de x) ----
    resto = expr
    factor_comun_txt = None
    if poly is not None:
        coeffs = poly.all_coeffs()
        n_ceros_al_final = 0
        for c in reversed(coeffs):
            if c == 0:
                n_ceros_al_final += 1
            else:
                break
        # también buscamos un coeficiente numérico común (mcd) además de x^k
        gcd_num = sp.gcd([sp.Integer(c) for c in coeffs if c != 0]) if coeffs else 1

        if n_ceros_al_final > 0 or (gcd_num not in (0, 1)):
            resto = sp.expand(sp.cancel(expr / (gcd_num * x**n_ceros_al_final)))
            partes_factor = []
            if gcd_num not in (0, 1):
                partes_factor.append(sp.latex(gcd_num))
            if n_ceros_al_final > 0:
                partes_factor.append(f"x^{{{n_ceros_al_final}}}" if n_ceros_al_final > 1 else "x")
            factor_comun_txt = "".join(partes_factor) if partes_factor else None
            if factor_comun_txt:
                pasos.append(f"{factor_comun_txt}\\,({sp.latex(resto)}) = 0")

    # ---- PASO B: intentar factorizar "resto" en factores lineales con
    #              raíces racionales (esto es lo que prioriza el método) ----
    factorizado_resto = sp.factor(resto)
    es_producto_de_factores = factorizado_resto.is_Mul or (
        factorizado_resto.is_Pow and factorizado_resto.args[1].is_Integer
    )

    if es_producto_de_factores and factorizado_resto != resto:
        # sympy logró factorizar "resto" en partes más simples
        if factor_comun_txt:
            pasos.append(f"{factor_comun_txt}\\,{sp.latex(factorizado_resto)} = 0")
        else:
            pasos[-1] = f"{sp.latex(factorizado_resto)} = 0"
        metodo = "factorización" if not factor_comun_txt else "factor común + factorización"
        return metodo, pasos

    # ---- PASO B.2: si "resto" ya quedó de grado <= 1 tras el factor
    #              común, no hace falta fórmula cuadrática -- las raíces
    #              salen directo del factor común y el resto lineal ----
    if factor_comun_txt and resto.is_polynomial(x) and sp.Poly(resto, x).degree() <= 1:
        return "factor común", pasos

    # ---- PASO C: si "resto" es cuadrático y no factorizó en racionales,
    #              usar la fórmula general (cuadrática) ----
    if resto.is_polynomial(x) and sp.Poly(resto, x).degree() == 2:
        a, b, c_ = sp.Poly(resto, x).all_coeffs()
        disc = sp.simplify(b**2 - 4*a*c_)
        pasos.append(
            f"x = \\dfrac{{-({sp.latex(b)}) \\pm \\sqrt{{{sp.latex(disc)}}}}}{{2({sp.latex(a)})}}"
        )
        metodo = "fórmula cuadrática" if not factor_comun_txt else "factor común + fórmula cuadrática"
        return metodo, pasos

    # ---- PASO D: cuadrática pura sobre la expresión completa (sin haber
    #              pasado por factor común) ----
    if grado == 2:
        a, b, c_ = poly.all_coeffs()
        disc = sp.simplify(b**2 - 4*a*c_)
        pasos.append(
            f"x = \\dfrac{{-({sp.latex(b)}) \\pm \\sqrt{{{sp.latex(disc)}}}}}{{2({sp.latex(a)})}}"
        )
        return "fórmula cuadrática", pasos

    # ---- PASO E: caso general, sin factorización elemental ----
    factorizado_total = sp.factor(expr)
    if factorizado_total != expr and not factorizado_total.is_Atom:
        pasos.append(f"{sp.latex(factorizado_total)} = 0")
        return "factorización", pasos

    return "métodos generales de resolución de ecuaciones", pasos


def _sustituir_texto(expr, x, x0):
    """
    Sustituye x por x0 a nivel de texto LaTeX, preservando el orden y la
    forma original de la expresión (sin que sympy reordene ni evalúe
    automáticamente al estilo "0 - 1" en vez de "-1 + 0").
    """
    latex_original = sp.latex(expr)
    x0_str = sp.latex(x0)
    if x0 < 0:
        x0_str = f"\\left({x0_str}\\right)"
    return re.sub(r"\bx\b", lambda m: x0_str, latex_original)


def evaluar_paso_a_paso(f_expr, x0, x):
    """
    Genera los pasos en LaTeX de evaluar f(x0): sustitución y resultado,
    igual a como se hace a mano. Maneja tanto sumas/polinomios
    (f(-2) = 3·16 + 4·(-8) - 12·4 + 5 = -27) como cocientes
    (f(0) = 0²/(0-1) = 0), mostrando siempre la sustitución real antes
    de operar, no solo el resultado final.
    """
    x0_simpl = sp.nsimplify(x0)
    resultado = sp.nsimplify(sp.simplify(f_expr.subs(x, x0_simpl)))

    f_together = sp.together(f_expr)
    num, den = sp.fraction(f_together)

    # ---- CASO COCIENTE: numerador y denominador sustituidos, sin operar ----
    if den != 1 and not den.is_number:
        num_latex = _sustituir_texto(num, x, x0_simpl)
        den_latex = _sustituir_texto(den, x, x0_simpl)
        paso_sustitucion = f"\\dfrac{{{num_latex}}}{{{den_latex}}}"
        return paso_sustitucion, resultado

    # ---- CASO SUMA / POLINOMIO: término a término ----
    expr_expandida = sp.expand(f_expr)
    if expr_expandida.is_polynomial(x):
        poly = sp.Poly(expr_expandida, x)
        terminos = [coeff * x**monom[0] for monom, coeff in poly.terms()]
    elif expr_expandida.is_Add:
        terminos = expr_expandida.args
    else:
        terminos = [expr_expandida]

    terminos_sustituidos = []
    for t in terminos:
        t_sub = t.subs(x, x0_simpl, simultaneous=True)
        terminos_sustituidos.append(sp.latex(t_sub))

    paso_sustitucion = " + ".join(terminos_sustituidos).replace("+ -", "- ").replace("-  ", "- ")
    return paso_sustitucion, resultado


def calcular_dominio(f_expr, x):
    """
    Calcula el dominio real de continuidad de f_expr. Devuelve un string
    en LaTeX (ej. "\\mathbb{R}" o "(-\\infty, 1) \\cup (1, \\infty)"),
    o None si no se pudo determinar.
    """
    try:
        dominio = sp.calculus.util.continuous_domain(f_expr, x, sp.S.Reals)
        return sp.latex(dominio)
    except Exception:
        return None


def encontrar_discontinuidades(f_expr, x):
    """
    Encuentra los puntos reales finitos donde f_expr no está definida
    (fuera del dominio continuo), para usarlos como puntos de división
    adicionales al analizar signos por intervalos (ej. la asíntota x=1
    en x²/(x-1), o el límite de dominio x=0 en sqrt(x)).
    """
    try:
        dominio = sp.calculus.util.continuous_domain(f_expr, x, sp.S.Reals)
    except Exception:
        return []
    if dominio == sp.S.Reals:
        return []
    try:
        complemento = sp.S.Reals - dominio
        if complemento.is_FiniteSet:
            return [p for p in complemento.args if p.is_finite]
        puntos = []
        for boundary in complemento.boundary.args:
            if boundary.is_finite:
                puntos.append(boundary)
        return puntos
    except Exception:
        return []


def calcular_intervalos_signo(expr, puntos_division, x):
    """
    Evalúa el signo de expr en el punto medio de cada intervalo entre
    puntos_division (incluye puntos críticos/inflexión y discontinuidades
    del dominio), y agrupa intervalos consecutivos con el mismo signo en
    uno solo. Devuelve una lista de tuplas (a, b, signo) con
    signo en {"positivo", "negativo"}; los tramos donde expr no está
    definida (NaN, complejo, infinito) se omiten del resultado.
    """
    if not puntos_division:
        try:
            valor = complex(expr.subs(x, 0).evalf())
            if abs(valor.imag) < 1e-9 and np.isfinite(valor.real) and valor.real != 0:
                signo = "positivo" if valor.real > 0 else "negativo"
                return [(sp.S.NegativeInfinity, sp.S.Infinity, signo)]
        except Exception:
            pass
        return []

    todos_los_puntos = sorted(set(float(p) for p in puntos_division))
    extremos = [sp.S.NegativeInfinity] + [sp.nsimplify(p) for p in todos_los_puntos] + [sp.S.Infinity]

    intervalos_crudos = []
    for i in range(len(extremos) - 1):
        a, b = extremos[i], extremos[i + 1]
        if a == sp.S.NegativeInfinity and b == sp.S.Infinity:
            punto_prueba = 0.0
        elif a == sp.S.NegativeInfinity:
            punto_prueba = float(b) - 1
        elif b == sp.S.Infinity:
            punto_prueba = float(a) + 1
        else:
            punto_prueba = (float(a) + float(b)) / 2

        try:
            valor = complex(expr.subs(x, punto_prueba).evalf())
            if abs(valor.imag) > 1e-9 or not np.isfinite(valor.real):
                signo = None
            else:
                signo = "positivo" if valor.real > 0 else "negativo" if valor.real < 0 else None
        except Exception:
            signo = None

        if signo is not None:
            intervalos_crudos.append((a, b, signo))

    if not intervalos_crudos:
        return []

    combinados = [list(intervalos_crudos[0])]
    for a, b, signo in intervalos_crudos[1:]:
        if signo == combinados[-1][2]:
            combinados[-1][1] = b
        else:
            combinados.append([a, b, signo])
    return [tuple(c) for c in combinados]


def calcular_rango_inteligente(resultados, rango_manual, zoom_auto, xs_inflexion=None):
    """
    Si zoom_auto está activo, calcula un rango de x centrado en los puntos
    críticos reales y los puntos de inflexión (con margen), para que la
    zona interesante de la curva sea siempre visible sin que valores
    enormes de x^n la aplasten. Si no hay puntos críticos ni de inflexión,
    recurre al rango manual.
    """
    if not zoom_auto:
        return rango_manual

    xs_criticos = []
    for r in resultados:
        try:
            xs_criticos.append(float(r["x"]))
        except Exception:
            continue

    if xs_inflexion:
        for xv in xs_inflexion:
            try:
                xs_criticos.append(float(xv))
            except Exception:
                continue

    if not xs_criticos:
        return rango_manual

    x_min, x_max = min(xs_criticos), max(xs_criticos)
    spread = x_max - x_min
    margen = max(spread * 0.6, 1.5)  # margen mínimo para que no quede muy apretado
    return (x_min - margen, x_max + margen)


def construir_figura(xs, ys_plot, frac_visible, resultados, a_lim, b_lim, mostrar_puntos, puntos_inflexion=None):
    """
    Construye la figura de Plotly con tema oscuro y ejes en escala 1:1
    real (misma cantidad de unidades por pixel en x que en y), mostrando
    la curva solo hasta frac_visible (simulación de escáner), los puntos
    críticos que el escáner ya alcanzó, y los puntos de inflexión reales
    (donde f''(x) = 0), con etiquetas separadas para que no se
    superpongan entre sí.

    puntos_inflexion: lista opcional de tuplas (x, y) con las coordenadas
        de inflexión reales (calculadas resolviendo f''(x) = 0), distintas
        de los puntos críticos de f'(x) = 0.
    """
    puntos_inflexion = puntos_inflexion or []
    n_total = len(xs)
    n_visible = max(2, int(n_total * frac_visible))

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=xs[:n_visible], y=ys_plot[:n_visible],
            mode="lines",
            line=dict(color=CURVA_COLOR, width=3),
            name="f(x)",
        )
    )

    if frac_visible < 1.0 and n_visible < n_total:
        fig.add_shape(
            type="line",
            x0=xs[n_visible - 1], x1=xs[n_visible - 1],
            y0=min(ys_plot), y1=max(ys_plot),
            line=dict(color=VERDE_ACENTO, width=2, dash="dot"),
        )

    fig.add_hline(y=0, line_color="#5a6075", line_width=1)
    fig.add_vline(x=0, line_color="#5a6075", line_width=1)

    x_frontera = xs[n_visible - 1]
    leyenda_max_hecha = False
    leyenda_min_hecha = False

    # Para separar etiquetas que caigan muy cerca, alternamos arriba/abajo
    # según el orden en x de los puntos visibles.
    puntos_para_dibujar = []
    if mostrar_puntos:
        for r in resultados:
            try:
                xv = float(r["x"])
                yv = float(r["y"])
            except Exception:
                continue
            if not (a_lim <= xv <= b_lim):
                continue
            if xv > x_frontera:
                continue
            puntos_para_dibujar.append((xv, yv, r["tipo"]))

    puntos_para_dibujar.sort(key=lambda p: p[0])
    rango_y_total = (max(ys_plot) - min(ys_plot)) or 1
    offset_etiqueta = rango_y_total * 0.07

    for idx, (xv, yv, tipo) in enumerate(puntos_para_dibujar):
        # Alternar posición vertical de la etiqueta para que no se encimen
        # cuando dos puntos están muy cerca en x.
        alterna_arriba = (idx % 2 == 0)

        if tipo == "máximo":
            color = ROJO_MAX
            etiqueta = f"Máx ({xv:.2f}, {yv:.2f})"
            ypos = yv + offset_etiqueta if alterna_arriba else yv - offset_etiqueta
            textpos = "top center" if alterna_arriba else "bottom center"
            fig.add_trace(
                go.Scatter(
                    x=[xv], y=[yv], mode="markers+text",
                    marker=dict(color=color, size=13, line=dict(color="#0e1016", width=1.5)),
                    text=[etiqueta], textposition=textpos,
                    textfont=dict(color=color, size=11),
                    name="Máximo" if not leyenda_max_hecha else None,
                    showlegend=not leyenda_max_hecha,
                )
            )
            leyenda_max_hecha = True
        elif tipo == "mínimo":
            color = AZUL_MIN
            etiqueta = f"Mín ({xv:.2f}, {yv:.2f})"
            textpos = "bottom center" if alterna_arriba else "top center"
            fig.add_trace(
                go.Scatter(
                    x=[xv], y=[yv], mode="markers+text",
                    marker=dict(color=color, size=13, line=dict(color="#0e1016", width=1.5)),
                    text=[etiqueta], textposition=textpos,
                    textfont=dict(color=color, size=11),
                    name="Mínimo" if not leyenda_min_hecha else None,
                    showlegend=not leyenda_min_hecha,
                )
            )
            leyenda_min_hecha = True
        else:
            fig.add_trace(
                go.Scatter(
                    x=[xv], y=[yv], mode="markers",
                    marker=dict(color=AMARILLO_INFLEX, size=10, symbol="square"),
                    showlegend=False,
                )
            )

        fig.add_shape(
            type="line", x0=xv, x1=xv, y0=0, y1=yv,
            line=dict(color="#5a6075", width=1, dash="dash"),
        )

    # ---- PUNTOS DE INFLEXIÓN REALES (f''(x) = 0), distintos de los
    #      puntos críticos de f'(x) = 0 ----
    leyenda_inflex_hecha = False
    inflex_para_dibujar = [
        (xv, yv) for (xv, yv) in puntos_inflexion
        if a_lim <= xv <= b_lim and xv <= x_frontera
    ]
    inflex_para_dibujar.sort(key=lambda p: p[0])

    for idx, (xv, yv) in enumerate(inflex_para_dibujar):
        alterna_arriba = (idx % 2 == 0)
        textpos = "top center" if alterna_arriba else "bottom center"
        fig.add_trace(
            go.Scatter(
                x=[xv], y=[yv], mode="markers+text",
                marker=dict(
                    color=AMARILLO_INFLEX, size=12, symbol="diamond",
                    line=dict(color="#0e1016", width=1.5),
                ),
                text=[f"Inf ({xv:.2f}, {yv:.2f})"], textposition=textpos,
                textfont=dict(color=AMARILLO_INFLEX, size=11),
                name="Inflexión" if not leyenda_inflex_hecha else None,
                showlegend=not leyenda_inflex_hecha,
            )
        )
        leyenda_inflex_hecha = True
        fig.add_shape(
            type="line", x0=xv, x1=xv, y0=0, y1=yv,
            line=dict(color="#5a6075", width=1, dash="dot"),
        )

    # ---- ESCALA 1:1 REAL EN AMBOS EJES ----
    # scaleanchor + scaleratio=1 fuerza que una unidad en x ocupe el mismo
    # número de píxeles que una unidad en y, como en una cuadrícula real.
    y_centro = (max(ys_plot) + min(ys_plot)) / 2
    y_rango_mitad = max((max(ys_plot) - min(ys_plot)) / 2, 1) * 1.15

    fig.update_layout(
        xaxis=dict(
            range=[a_lim, b_lim], title="x",
            color=TEXTO_PRINCIPAL, gridcolor="#2a2e3d", zerolinecolor="#5a6075",
            scaleanchor="y", scaleratio=1,
        ),
        yaxis=dict(
            range=[y_centro - y_rango_mitad, y_centro + y_rango_mitad], title="f(x)",
            color=TEXTO_PRINCIPAL, gridcolor="#2a2e3d", zerolinecolor="#5a6075",
        ),
        plot_bgcolor=BG_CARD,
        paper_bgcolor=BG_CARD,
        font=dict(color=TEXTO_PRINCIPAL),
        margin=dict(l=40, r=20, t=20, b=40),
        height=460,
        legend=dict(font=dict(color=TEXTO_PRINCIPAL), bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ----------------------------------------------------------------------
# PROCESO PRINCIPAL
# ----------------------------------------------------------------------
if calcular:
    if not func_str or not func_str.strip():
        st.warning("✍️ Escribe una función en el campo f(x) = antes de analizar.")
        st.stop()

    try:
        f_expr = parse_function(func_str)
    except Exception as e:
        st.error(f"⚠️ No se pudo interpretar la función. Revisa la sintaxis.\n\nDetalle: {e}")
        st.stop()

    fprime_expr = sp.diff(f_expr, x)
    fprime_expr_simpl = formatear_expresion(fprime_expr, x)
    fpp_expr = sp.diff(fprime_expr, x)
    fpp_expr_simpl = formatear_expresion(fpp_expr, x)

    try:
        criticos = sp.solve(sp.Eq(fprime_expr, 0), x)
    except Exception:
        criticos = []

    criticos_reales = []
    for c in criticos:
        try:
            c_val = complex(c.evalf())
            if abs(c_val.imag) < 1e-8:
                criticos_reales.append(sp.nsimplify(c_val.real))
        except Exception:
            continue
    criticos_reales = sorted(set(criticos_reales), key=lambda v: float(v))

    resultados = []
    for c in criticos_reales:
        tipo, detalle = clasificar_punto(fpp_expr, c, fprime_expr)
        y_val = f_expr.subs(x, c)
        resultados.append({"x": c, "y": y_val, "tipo": tipo, "detalle": detalle})

    # ---- Puntos de inflexión reales: f''(x) = 0 (distintos de los
    #      puntos críticos de f'(x) = 0). Se calculan aquí para poder
    #      usarlos tanto en el zoom automático como en la gráfica. ----
    try:
        soluciones_inflex = sp.solve(sp.Eq(fpp_expr, 0), x)
    except Exception:
        soluciones_inflex = []

    inflexion_reales = []
    for c in soluciones_inflex:
        try:
            c_val = complex(c.evalf())
            if abs(c_val.imag) < 1e-8:
                inflexion_reales.append(sp.nsimplify(c_val.real))
        except Exception:
            continue
    inflexion_reales = sorted(set(inflexion_reales), key=lambda v: float(v))

    puntos_inflexion_coords = []
    for c in inflexion_reales:
        try:
            y_val_inflex = float(sp.simplify(f_expr.subs(x, c)))
            puntos_inflexion_coords.append((float(c), y_val_inflex))
        except Exception:
            continue

    # ====================================================================
    # LAYOUT: GRÁFICA (IZQUIERDA) + PROCESO PASO A PASO (DERECHA)
    # ====================================================================
    col_graf, col_proceso = st.columns([3, 2])

    with col_graf:
        a_lim, b_lim = calcular_rango_inteligente(
            resultados, rango, zoom_auto, xs_inflexion=inflexion_reales
        )
        margen_extra = (b_lim - a_lim) * 0.08
        a_lim -= margen_extra
        b_lim += margen_extra

        xs = np.linspace(a_lim, b_lim, 400)

        f_lambd = sp.lambdify(x, f_expr, modules=["numpy"])
        try:
            ys = f_lambd(xs)
            ys = np.array(ys, dtype=float)
        except Exception:
            ys = np.array([float(f_expr.subs(x, xv)) for xv in xs])

        ys_finite = ys[np.isfinite(ys)]
        if len(ys_finite) > 0:
            y_med = np.nanpercentile(ys_finite, 50)
            y_std = np.nanstd(ys_finite)
            cota = y_std * 6 + 1
            ys_plot = np.clip(ys, y_med - cota, y_med + cota)
        else:
            ys_plot = ys

        if zoom_auto and resultados:
            st.caption(f"🔍 Zoom automático activo: mostrando x ∈ [{a_lim:.2f}, {b_lim:.2f}]")

        grafica_placeholder = st.empty()

        if animar:
            n_frames = 30
            for i in range(1, n_frames + 1):
                frac = i / n_frames
                fig = construir_figura(
                    xs, ys_plot, frac, resultados, a_lim, b_lim,
                    mostrar_puntos=True, puntos_inflexion=puntos_inflexion_coords,
                )
                grafica_placeholder.plotly_chart(fig, use_container_width=True, key=f"frame_{i}")
                time.sleep(0.035)
        else:
            fig = construir_figura(
                xs, ys_plot, 1.0, resultados, a_lim, b_lim,
                mostrar_puntos=True, puntos_inflexion=puntos_inflexion_coords,
            )
            grafica_placeholder.plotly_chart(fig, use_container_width=True, key="frame_final")

        # ---- RESUMEN ORDENADO, debajo de la gráfica (aprovecha el espacio
        # que antes quedaba vacío en esta columna) ----
        if resultados or True:
            st.markdown(
                f"<p class='step-title' style='font-size:0.95rem; margin-top:10px;'>📋 Resumen</p>",
                unsafe_allow_html=True,
            )

            # ---- DOMINIO ----
            dominio_latex = calcular_dominio(f_expr, x)
            if dominio_latex:
                st.markdown(
                    f"<p style='font-size:0.82rem; margin-bottom:2px;'>"
                    f"<b style='color:{AZUL_TITULO};'>Dominio:</b></p>",
                    unsafe_allow_html=True,
                )
                st.latex(dominio_latex)

            # ---- INTERVALOS DE CRECIMIENTO / DECRECIMIENTO ----
            discontinuidades = encontrar_discontinuidades(f_expr, x)
            puntos_para_crecimiento = criticos_reales + discontinuidades
            intervalos_crecimiento = calcular_intervalos_signo(fprime_expr, puntos_para_crecimiento, x)

            if intervalos_crecimiento:
                st.markdown(
                    f"<p style='font-size:0.82rem; margin:8px 0 2px 0;'>"
                    f"<b style='color:{AZUL_TITULO};'>Crecimiento / decrecimiento:</b></p>",
                    unsafe_allow_html=True,
                )
                for a, b, signo in intervalos_crecimiento:
                    etiqueta = "Creciente" if signo == "positivo" else "Decreciente"
                    color_etq = VERDE_ACENTO if signo == "positivo" else ROJO_MAX
                    col_etq, col_int = st.columns([1, 1])
                    with col_etq:
                        st.markdown(
                            f"<p style='font-size:0.8rem; margin:6px 0;'>"
                            f"<span style='color:{color_etq}; font-weight:600;'>{etiqueta}</span> en</p>",
                            unsafe_allow_html=True,
                        )
                    with col_int:
                        st.latex(f"({sp.latex(a)}, {sp.latex(b)})")

            # ---- INTERVALOS DE CONCAVIDAD ----
            puntos_para_concavidad = inflexion_reales + discontinuidades
            intervalos_concavidad = calcular_intervalos_signo(fpp_expr, puntos_para_concavidad, x)

            if intervalos_concavidad:
                st.markdown(
                    f"<p style='font-size:0.82rem; margin:8px 0 2px 0;'>"
                    f"<b style='color:{AZUL_TITULO};'>Concavidad:</b></p>",
                    unsafe_allow_html=True,
                )
                for a, b, signo in intervalos_concavidad:
                    etiqueta = "Cóncava hacia arriba" if signo == "positivo" else "Cóncava hacia abajo"
                    color_etq = VERDE_ACENTO if signo == "positivo" else ROJO_MAX
                    col_etq, col_int = st.columns([1, 1])
                    with col_etq:
                        st.markdown(
                            f"<p style='font-size:0.8rem; margin:6px 0;'>"
                            f"<span style='color:{color_etq}; font-weight:600;'>{etiqueta}</span> en</p>",
                            unsafe_allow_html=True,
                        )
                    with col_int:
                        st.latex(f"({sp.latex(a)}, {sp.latex(b)})")

        if resultados:
            st.markdown(
                f"<p style='font-size:0.82rem; margin:10px 0 4px 0;'>"
                f"<b style='color:{AZUL_TITULO};'>Puntos críticos:</b></p>",
                unsafe_allow_html=True,
            )
            col_x, col_fx, col_tipo = st.columns([1, 1, 1])
            with col_x:
                st.markdown(f"<p style='color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:4px;'>x</p>", unsafe_allow_html=True)
            with col_fx:
                st.markdown(f"<p style='color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:4px;'>f(x)</p>", unsafe_allow_html=True)
            with col_tipo:
                st.markdown(f"<p style='color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:4px;'>Tipo</p>", unsafe_allow_html=True)

            for r in resultados:
                color_tipo = (
                    ROJO_MAX if r["tipo"] == "máximo"
                    else AZUL_MIN if r["tipo"] == "mínimo"
                    else AMARILLO_INFLEX
                )
                col_x, col_fx, col_tipo = st.columns([1, 1, 1])
                with col_x:
                    st.latex(f"x = {sp.latex(sp.nsimplify(r['x']))}")
                with col_fx:
                    st.latex(f"f(x) = {sp.latex(sp.nsimplify(r['y']))}")
                with col_tipo:
                    st.markdown(
                        f"<p style='color:{color_tipo}; font-weight:700; margin-top:10px; font-size:0.85rem;'>{r['tipo'].upper()}</p>",
                        unsafe_allow_html=True,
                    )

    with col_proceso:
        with st.container(height=780):
            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">1️⃣ Función original</p>', unsafe_allow_html=True)
            st.latex(f"f(x) = {sp.latex(f_expr)}")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">2️⃣ Primera derivada f\'(x)</p>', unsafe_allow_html=True)
            metodo_deriv, pasos_deriv = derivar_paso_a_paso(f_expr, x)
            st.markdown(
                f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:6px;">'
                f'Método: <b style="color:{AZUL_TITULO};">{metodo_deriv}</b></p>',
                unsafe_allow_html=True,
            )
            for paso in pasos_deriv:
                st.latex(paso)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">3️⃣ Igualar f\'(x) = 0 y resolver</p>', unsafe_allow_html=True)

            metodo, pasos_metodo = analizar_metodo_resolucion(fprime_expr, x)
            st.markdown(
                f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:6px;">'
                f'Método: <b style="color:{AZUL_TITULO};">{metodo}</b></p>',
                unsafe_allow_html=True,
            )
            for paso in pasos_metodo:
                st.latex(paso)

            st.markdown(
                f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin:4px 0 2px 0;">Puntos críticos:</p>',
                unsafe_allow_html=True,
            )
            if criticos_reales:
                sol_latex = ", \\;".join([f"x = {sp.latex(c)}" for c in criticos_reales])
                st.latex(sol_latex)
            else:
                st.write("No se encontraron puntos críticos reales.")
            st.markdown("</div>", unsafe_allow_html=True)

            # ---- NUEVO PASO: evaluar f(x) en cada punto crítico, mostrando
            # la sustitución término a término (como se hace a mano) ----
            if criticos_reales:
                st.markdown('<div class="board-box">', unsafe_allow_html=True)
                st.markdown(
                    '<p class="step-title">4️⃣ Evaluar f(x) en cada punto crítico</p>',
                    unsafe_allow_html=True,
                )
                for c in criticos_reales:
                    paso_sust, valor = evaluar_paso_a_paso(f_expr, c, x)
                    st.latex(f"f({sp.latex(c)}) = {paso_sust} = {sp.latex(valor)}")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">5️⃣ Segunda derivada f\'\'(x)</p>', unsafe_allow_html=True)

            metodo_deriv2, pasos_deriv2 = derivar_paso_a_paso(
                fprime_expr, x, nombre_funcion="f''", simplificar_entrada=True
            )
            st.markdown(
                f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:6px;">'
                f'Método: <b style="color:{AZUL_TITULO};">{metodo_deriv2}</b></p>',
                unsafe_allow_html=True,
            )
            for paso in pasos_deriv2:
                st.latex(paso)

            if criticos_reales:
                st.markdown(
                    f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin:6px 0 2px 0;">'
                    f'Evaluando en cada punto crítico:</p>',
                    unsafe_allow_html=True,
                )
                for c in criticos_reales:
                    paso_sust, valor = evaluar_paso_a_paso(fpp_expr_simpl, c, x)
                    st.latex(f"f''({sp.latex(c)}) = {paso_sust} = {sp.latex(valor)}")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">6️⃣ Clasificación</p>', unsafe_allow_html=True)
            if not resultados:
                st.write("No hay puntos críticos para clasificar.")
            else:
                for r in resultados:
                    css_class = (
                        "crit-max" if r["tipo"] == "máximo"
                        else "crit-min" if r["tipo"] == "mínimo"
                        else "crit-none"
                    )
                    etiqueta_html = (
                        f'<p class="{css_class}" style="font-size:0.85rem; margin-bottom:0;">'
                        f'x = {sp.latex(r["x"])} &nbsp;<u>{r["tipo"].upper()}</u></p>'
                    )
                    st.markdown(etiqueta_html, unsafe_allow_html=True)
                    st.markdown(
                        f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.75rem; margin-top:-2px;">{r["detalle"]}</p>',
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

            # ---- NUEVO PASO: puntos de inflexión, resolviendo f''(x) = 0 ----
            st.markdown('<div class="board-box">', unsafe_allow_html=True)
            st.markdown('<p class="step-title">7️⃣ Puntos de inflexión: f\'\'(x) = 0</p>', unsafe_allow_html=True)

            metodo_inflex, pasos_inflex = analizar_metodo_resolucion(fpp_expr, x)
            st.markdown(
                f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin-bottom:6px;">'
                f'Método: <b style="color:{AZUL_TITULO};">{metodo_inflex}</b></p>',
                unsafe_allow_html=True,
            )
            for paso in pasos_inflex:
                st.latex(paso)

            # inflexion_reales ya se calculó arriba (antes de la gráfica), se
            # reutiliza aquí para no calcularlo dos veces.
            if not inflexion_reales:
                st.markdown(
                    f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.8rem; margin-top:6px;">'
                    f'No hay puntos de inflexión reales (f\'\'(x) nunca se anula).</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.78rem; margin:6px 0 2px 0;">'
                    f'Coordenadas de inflexión:</p>',
                    unsafe_allow_html=True,
                )
                for c in inflexion_reales:
                    paso_sust, valor = evaluar_paso_a_paso(f_expr, c, x)
                    st.latex(f"f({sp.latex(c)}) = {paso_sust} = {sp.latex(valor)}")
                    if not valor.is_rational:
                        st.markdown(
                            f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.75rem; margin-top:-6px; margin-bottom:4px;">'
                            f'≈ {round(float(valor), 4)}</p>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f'<p style="color:{TEXTO_SECUNDARIO}; font-size:0.8rem; margin-top:-4px; margin-bottom:2px;">Punto de inflexión:</p>',
                        unsafe_allow_html=True,
                    )
                    if not c.is_rational or not valor.is_rational:
                        c_aprox = round(float(c), 4) if not c.is_rational else c
                        valor_aprox = round(float(valor), 4) if not valor.is_rational else valor
                        st.latex(f"({sp.latex(c)}, \\; {sp.latex(valor)}) \\;\\approx\\; ({c_aprox}, \\; {valor_aprox})")
                    else:
                        st.latex(f"({sp.latex(c)}, \\; {sp.latex(valor)})")
            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("👆 Escribe una función arriba y presiona **Analizar** para comenzar.")

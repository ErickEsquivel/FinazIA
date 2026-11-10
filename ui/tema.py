"""
ui/tema.py
----------
Estilos propios que complementan el tema de .streamlit/config.toml.

Todo usa colores semitransparentes o "inherit" para verse bien tanto en el
tema claro como en el oscuro, sin tener que detectar cuál está activo.
"""

import streamlit as st

# Colores semánticos (iguales en ambos temas; contrastan sobre fondo claro y oscuro)
VERDE = "#12A150"
ROJO = "#E5484D"
AMBAR = "#E59A00"
PRIMARIO = "#0E9F6E"

_CSS = f"""
<style>
:root {{
  --fz-verde: {VERDE};
  --fz-rojo: {ROJO};
  --fz-ambar: {AMBAR};
  --fz-primario: {PRIMARIO};
  --fz-pista: rgba(128, 128, 128, 0.18);
  --fz-suave: rgba(128, 128, 128, 0.08);
}}

/* Más aire arriba y ancho máximo cómodo en pantallas grandes */
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1180px; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; }}

/* Tarjetas: st.container(border=True, key="card_...") */
[class*="st-key-card"] {{
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06);
}}

/* Bloque centrado para formularios (registro, bienvenida) */
[class*="st-key-centrado"] {{ max-width: 600px; margin: 0 auto; }}

/* Filas de la lista de movimientos: columnas lado a lado también en móvil */
[class*="st-key-fila_"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 0.5rem; align-items: center; }}
[class*="st-key-fila_"] [data-testid="stColumn"] {{ min-width: 0 !important; }}
[class*="st-key-fila_"] {{ padding: 0.15rem 0; border-bottom: 1px solid var(--fz-pista); }}
[class*="st-key-fila_"] button {{ padding: 0.25rem 0.5rem; min-height: 0; }}

/* Botones de navegación de mes: siempre en una fila */
[class*="st-key-navmes"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; align-items: center; }}
[class*="st-key-navmes"] [data-testid="stColumn"] {{ min-width: 0 !important; }}

/* Acciones rápidas (gasto / ingreso): siempre en una fila */
[class*="st-key-acciones"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; }}
[class*="st-key-acciones"] [data-testid="stColumn"] {{ min-width: 0 !important; }}

/* ---------- Tarjeta principal de saldo (estilo Wallet) ---------- */
.fz-hero {{
  background: linear-gradient(135deg, #0E9F6E 0%, #0B7A63 55%, #0A5F6B 100%);
  color: #fff; border-radius: 1.1rem; padding: 1.4rem 1.5rem; margin-bottom: 0.5rem;
  box-shadow: 0 6px 20px rgba(14, 159, 110, 0.25);
}}
.fz-hero .etq {{ font-size: 0.85rem; opacity: 0.85; }}
.fz-hero .saldo {{ font-size: 2.3rem; font-weight: 700; letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums; line-height: 1.15; margin: 0.15rem 0 0.9rem; }}
.fz-hero .fila {{ display: flex; gap: 0.75rem; flex-wrap: wrap; }}
.fz-hero .kpi {{ background: rgba(255, 255, 255, 0.14); border-radius: 0.8rem;
  padding: 0.55rem 0.8rem; flex: 1 1 140px; }}
.fz-hero .kpi b {{ display: block; font-size: 1.1rem; font-variant-numeric: tabular-nums; }}
.fz-hero .kpi span {{ font-size: 0.78rem; opacity: 0.85; }}
.fz-hero .kpi small {{ display: block; font-size: 0.72rem; opacity: 0.8; margin-top: 0.1rem; }}
.fz-hero .neg {{ color: #FFD1D3; }}

/* ---------- Textos y montos ---------- */
.fz-titulo {{ font-weight: 650; font-size: 1.02rem; margin: 0 0 0.6rem; }}
.fz-muted {{ opacity: 0.65; font-size: 0.85rem; }}
.fz-monto {{ font-variant-numeric: tabular-nums; font-weight: 650; white-space: nowrap; }}
.fz-gasto {{ color: var(--fz-rojo); }}
.fz-ingreso {{ color: var(--fz-verde); }}
.fz-grande {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }}

/* Menú en pantallas angostas: hamburguesa (☰) para abrir y X para cerrar,
   en lugar de las flechas » y « de Streamlit. El icono es una fuente de
   símbolos: se oculta el nombre original y se muestra otro con ::before. */
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {{ font-size: 0 !important; }}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::before {{
  content: "menu"; font-size: 1.75rem; color: var(--fz-primario); }}
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before {{
  content: "close"; font-size: 1.5rem; }}

/* Contenedor invisible del script de formateo */
.st-key-fz_js {{ display: none; }}

/* Campos de pesos: números alineados y un poco más grandes */
[class*="st-key-pesos_"] input {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
[class*="st-key-pesos_"] [data-testid="InputInstructions"] {{ display: none; }}

/* ---------- Barras de presupuesto ---------- */
.fz-barra {{ margin: 0 0 0.9rem; }}
.fz-barra .cab {{ display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.9rem; }}
.fz-barra .cab .nom {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.fz-pista {{ background: var(--fz-pista); border-radius: 99px; height: 8px; margin: 0.3rem 0 0.25rem; overflow: hidden; }}
.fz-relleno {{ height: 100%; border-radius: 99px; }}
.fz-barra .pie {{ font-size: 0.78rem; opacity: 0.7; display: flex; justify-content: space-between; gap: 0.5rem; }}

/* ---------- Chips de categoría ---------- */
.fz-chip {{ display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.75rem;
  border-radius: 99px; font-weight: 600; font-size: 0.95rem; border: 1px solid; }}

/* ---------- Icono redondo de categoría ---------- */
.fz-ico {{ width: 2.2rem; height: 2.2rem; border-radius: 50%; display: inline-flex;
  align-items: center; justify-content: center; font-size: 1.05rem; flex: none; }}

/* ---------- Fila de movimiento ---------- */
.fz-mov {{ display: flex; align-items: center; gap: 0.7rem; min-width: 0; }}
.fz-mov .txt {{ min-width: 0; }}
.fz-mov .desc {{ font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.fz-mov .meta {{ font-size: 0.78rem; opacity: 0.65; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.fz-dia {{ display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;
  opacity: 0.7; margin: 1rem 0 0.2rem; }}

/* ---------- Leyenda del gráfico ---------- */
.fz-leyenda {{ display: grid; gap: 0.35rem; font-size: 0.88rem; }}
.fz-leyenda .it {{ display: flex; align-items: center; gap: 0.5rem; }}
.fz-leyenda .pt {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
.fz-leyenda .val {{ margin-left: auto; font-variant-numeric: tabular-nums; }}

/* ---------- Pasos del asistente ---------- */
.fz-pasos {{ display: flex; gap: 0.4rem; margin: 0.2rem 0 1rem; }}
.fz-pasos div {{ flex: 1; height: 5px; border-radius: 99px; background: var(--fz-pista); }}
.fz-pasos div.on {{ background: var(--fz-primario); }}

/* ---------- Estado vacío ---------- */
.fz-vacio {{ text-align: center; padding: 1.5rem 1rem; }}
.fz-vacio .em {{ font-size: 2.4rem; }}

/* ---------- Mes actual en la navegación ---------- */
.fz-mes {{ text-align: center; font-weight: 650; font-size: 1.05rem; white-space: nowrap; }}

@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 4.2rem !important; }}
  h1 {{ font-size: 2rem !important; }}
  .fz-hero .saldo {{ font-size: 1.9rem; }}
}}
</style>
"""


# Formatea en vivo los campos de pesos (clave "pesos_..."): 1250000 -> 1.250.000.
# Escucha en fase de captura sobre el documento, antes que React, así Streamlit
# recibe ya el texto con puntos. Mantiene el cursor en el mismo dígito.
_JS_PESOS = """
<script>
(function () {
  if (window.__fzPesos) return;
  window.__fzPesos = true;
  var SEL = '[class*="st-key-pesos_"] input';
  var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;

  function formatear(texto) {
    var digitos = texto.split(',')[0].replace(/\\D/g, '').replace(/^0+(?=\\d)/, '');
    return digitos.replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
  }

  document.addEventListener('input', function (e) {
    var el = e.target;
    if (!el.matches || !el.matches(SEL)) return;
    var pos = el.selectionStart || 0;
    var antes = el.value.slice(0, pos).replace(/\\D/g, '').length;
    var nuevo = formatear(el.value);
    if (nuevo === el.value) return;
    setter.call(el, nuevo);
    var i = 0, n = 0;
    while (i < nuevo.length && n < antes) { if (/\\d/.test(nuevo[i])) n++; i++; }
    el.setSelectionRange(i, i);
  }, true);

  // Teclado numérico en el celular
  function marcar() {
    document.querySelectorAll(SEL).forEach(function (el) {
      if (el.getAttribute('inputmode') !== 'numeric') el.setAttribute('inputmode', 'numeric');
    });
  }
  marcar();
  new MutationObserver(marcar).observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


def aplicar_estilos():
    st.html(_CSS)
    with st.container(key="fz_js"):
        st.html(_JS_PESOS, unsafe_allow_javascript=True)

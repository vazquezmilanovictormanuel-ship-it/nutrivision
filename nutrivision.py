"""
NutriVision — Analizador de Comida y Composición Corporal con IA
Ejecutar: streamlit run nutrivision.py
Requiere: pip install streamlit anthropic Pillow
"""

import base64
import json
import math
import streamlit as st
from anthropic import Anthropic

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="NutriVision AI",
    page_icon="🧬",
    layout="centered",
)

# ── Estilos personalizados ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;600&family=Space+Mono&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Fondo oscuro */
.stApp { background: #0a0a0f; color: #e8e8f0; }
section[data-testid="stSidebar"] { background: #12121a; }

/* Títulos grandes */
.big-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.5rem;
    letter-spacing: 3px;
    background: linear-gradient(90deg, #00ff88, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}

/* Tarjeta de resultado */
.result-card {
    background: #1a1a26;
    border: 1px solid #2a2a3d;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 16px;
    border-top: 2px solid #7c3aed;
}

/* Número grande de calorías */
.cal-big {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.5rem;
    background: linear-gradient(135deg, #00ff88, #00c0ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
}

/* Macros en fila */
.macro-row { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.macro-box {
    flex: 1; min-width: 80px;
    background: #12121a;
    border: 1px solid #2a2a3d;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
}
.macro-val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    line-height: 1;
}
.macro-label { font-size: 11px; color: #6b6b8a; margin-top: 3px; font-weight: 600; }
.m-protein { color: #ff6b6b; }
.m-carbs   { color: #ffd93d; }
.m-fat     { color: #6bcbff; }

/* Badge */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    margin: 3px;
}
.badge-green  { background: rgba(0,255,136,.12); color: #00ff88; border: 1px solid rgba(0,255,136,.25); }
.badge-orange { background: rgba(255,107,53,.12); color: #ff6b35; border: 1px solid rgba(255,107,53,.25); }
.badge-purple { background: rgba(124,58,237,.12); color: #a78bfa; border: 1px solid rgba(124,58,237,.25); }

/* Tip box */
.tip-box {
    background: rgba(124,58,237,.08);
    border: 1px solid rgba(124,58,237,.2);
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 14px;
    color: #9b9bb8;
    display: flex; gap: 10px;
    margin-top: 12px;
}

/* Score */
.score-block { display: flex; align-items: center; gap: 20px; margin-bottom: 12px; }
.score-circle-text {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: #00ff88;
    line-height: 1;
    min-width: 80px;
    text-align: center;
}
.score-sub { font-size: 11px; color: #6b6b8a; }

/* Alimentos lista */
.food-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 14px;
    background: #12121a;
    border: 1px solid #2a2a3d;
    border-radius: 10px;
    font-size: 14px;
    margin-bottom: 6px;
}
.food-cal { font-family: 'Space Mono'; color: #00ff88; }

/* Insights */
.insight-item {
    display: flex; gap: 10px;
    font-size: 14px; line-height: 1.5; color: #e8e8f0;
    margin-bottom: 8px;
}
.insight-arrow { color: #00ff88; font-size: 16px; flex-shrink: 0; }

/* Calorias highlight */
.cal-highlight {
    background: linear-gradient(135deg, rgba(0,255,136,.08), rgba(124,58,237,.1));
    border: 1px solid rgba(0,255,136,.25);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    margin: 12px 0;
}

/* Tabs estilo */
div[data-baseweb="tab-list"] { background: #12121a; border-radius: 12px; padding: 4px; gap: 4px; }
button[data-baseweb="tab"] { border-radius: 8px; color: #6b6b8a; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg,#7c3aed,rgba(0,255,136,.3)) !important;
    color: white !important;
}

/* Ocultar marca de agua */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constantes ────────────────────────────────────────────────────────────────
GOAL_PLANS = {
    "💪 Volumen":             dict(calories=+300, protein_mult=2.2),
    "⚖️ Mantenimiento":       dict(calories=0,    protein_mult=1.8),
    "🔥 Déficit / Cutting":   dict(calories=-400,  protein_mult=2.4),
    "⚡ Déficit Agresivo":    dict(calories=-700,  protein_mult=2.6),
}

ACTIVITY_MULT = {
    "Sedentario (sin ejercicio)":          1.2,
    "Ligero (1-2 días/semana)":            1.375,
    "Moderado (3-4 días/semana)":          1.55,
    "Activo (5-6 días/semana)":            1.725,
    "Muy activo (2x día o trabajo físico)":1.9,
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def calc_bmr(weight: float, height: float, age: int, sex: str) -> float:
    if sex == "Hombre":
        return 88.36 + 13.4 * weight + 4.8 * height - 5.7 * age
    return 447.6 + 9.2 * weight + 3.1 * height - 4.3 * age

def calc_tdee(bmr: float, activity: str) -> int:
    return math.ceil(bmr * ACTIVITY_MULT[activity])

def img_to_b64(uploaded_file) -> tuple[str, str]:
    data = uploaded_file.read()
    b64  = base64.b64encode(data).decode()
    mt   = uploaded_file.type or "image/jpeg"
    return b64, mt

def call_claude(messages: list) -> str:
    client = Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=messages,
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text"))

def parse_json(raw: str) -> dict | None:
    clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except Exception:
        return None

# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("## 🧬")
with col_title:
    st.markdown('<p class="big-title">NUTRIVISION</p>', unsafe_allow_html=True)
    st.markdown('<span style="font-size:11px;color:#6b6b8a;letter-spacing:2px;font-family:\'Space Mono\'">AI · NUTRICIÓN · CUERPO</span>', unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_food, tab_body = st.tabs(["🍽️ Analizar Comida", "💪 Analizar Cuerpo"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FOOD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_food:
    st.markdown('<p class="big-title">ESCÁNER DE COMIDA</p>', unsafe_allow_html=True)
    st.markdown(
        "Sube una foto de tu plato y la IA detectará automáticamente calorías, "
        "proteínas, carbohidratos y grasas de cada alimento.",
        unsafe_allow_html=False,
    )

    food_file = st.file_uploader(
        "📸 Sube una foto de tu comida",
        type=["jpg", "jpeg", "png", "heic", "webp"],
        key="food_uploader",
    )

    if food_file:
        st.image(food_file, use_container_width=True)

        if st.button("🔍 Analizar Nutrición", type="primary", use_container_width=True):
            with st.spinner("Identificando alimentos y calculando macros…"):
                try:
                    b64, mt = img_to_b64(food_file)
                    raw = call_claude([{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                            {"type": "text", "text": (
                                "Eres un nutricionista experto. Analiza esta imagen de comida y responde "
                                "SOLO en JSON válido sin texto adicional ni backticks:\n"
                                "{\n"
                                '  "foods": [{"name": "nombre del alimento", "grams": número, "calories": calorías}],\n'
                                '  "total_calories": número,\n'
                                '  "protein_g": número,\n'
                                '  "carbs_g": número,\n'
                                '  "fat_g": número,\n'
                                '  "fiber_g": número,\n'
                                '  "meal_quality": "excelente|bueno|regular|mejorable",\n'
                                '  "quality_score": número del 1 al 10,\n'
                                '  "tip": "consejo nutricional breve en español"\n'
                                "}\n"
                                "Sé preciso estimando porciones. Si no hay comida, arrays vacíos y ceros."
                            )}
                        ],
                    }])
                    result = parse_json(raw)
                    if not result:
                        st.error("No se pudo interpretar la respuesta de la IA. Intenta con otra foto.")
                    else:
                        # ── Calorías totales ──────────────────────────────────
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="cal-big">{result["total_calories"]}</div>'
                            f'<div style="color:#6b6b8a;font-size:14px;margin-top:4px">'
                            f'kcal · Calidad: <strong style="color:#e8e8f0">{result["meal_quality"]}</strong>'
                            f' {result["quality_score"]}/10</div>'
                            f'<div class="macro-row">'
                            f'<div class="macro-box"><div class="macro-val m-protein">{result["protein_g"]}g</div>'
                            f'<div class="macro-label">Proteína</div></div>'
                            f'<div class="macro-box"><div class="macro-val m-carbs">{result["carbs_g"]}g</div>'
                            f'<div class="macro-label">Carbos</div></div>'
                            f'<div class="macro-box"><div class="macro-val m-fat">{result["fat_g"]}g</div>'
                            f'<div class="macro-label">Grasas</div></div>'
                            f'</div>'
                            f'<div style="margin-top:10px"><span class="badge badge-green">🌾 Fibra: {result["fiber_g"]}g</span></div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("</div>", unsafe_allow_html=True)

                        # ── Alimentos detectados ──────────────────────────────
                        if result.get("foods"):
                            st.markdown('<div class="result-card">', unsafe_allow_html=True)
                            st.markdown('<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">ALIMENTOS DETECTADOS</div>', unsafe_allow_html=True)
                            for f in result["foods"]:
                                st.markdown(
                                    f'<div class="food-item">'
                                    f'<span>🍽️ {f["name"]} <span style="color:#6b6b8a;font-weight:400">~{f["grams"]}g</span></span>'
                                    f'<span class="food-cal">{f["calories"]} kcal</span>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown("</div>", unsafe_allow_html=True)

                        # ── Consejo ───────────────────────────────────────────
                        if result.get("tip"):
                            st.markdown(
                                f'<div class="tip-box"><span>💡</span><span>{result["tip"]}</span></div>',
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    st.error(f"No se pudo analizar la imagen. Verifica que sea una foto clara de comida. ({e})")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BODY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_body:
    st.markdown('<p class="big-title">ANÁLISIS CORPORAL</p>', unsafe_allow_html=True)
    st.markdown(
        "Sube una foto de cuerpo completo junto con tus datos para obtener un análisis "
        "detallado de tu composición corporal y plan nutricional personalizado."
    )

    # ── Datos personales ──────────────────────────────────────────────────────
    with st.expander("📋 Tus Datos Personales", expanded=True):
        c1, c2 = st.columns(2)
        weight = c1.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=70.0, step=0.5)
        height = c2.number_input("Altura (cm)", min_value=120.0, max_value=230.0, value=175.0, step=0.5)
        c3, c4 = st.columns(2)
        age    = c3.number_input("Edad", min_value=12, max_value=100, value=25, step=1)
        sex    = c4.selectbox("Sexo", ["Hombre", "Mujer"])
        activity = st.selectbox("Nivel de Actividad", list(ACTIVITY_MULT.keys()), index=2)

        bmr  = calc_bmr(weight, height, age, sex)
        tdee = calc_tdee(bmr, activity)
        st.markdown(
            f'<span class="badge badge-green">🔥 TDEE: {tdee} kcal/día</span>'
            f'<span style="font-size:12px;color:#6b6b8a;margin-left:8px">metabolismo base calculado</span>',
            unsafe_allow_html=True,
        )

    # ── Objetivo ──────────────────────────────────────────────────────────────
    goal_name = st.radio(
        "🎯 Tu Objetivo",
        list(GOAL_PLANS.keys()),
        index=1,
        horizontal=True,
    )
    plan = GOAL_PLANS[goal_name]
    target_cals    = tdee + plan["calories"]
    target_protein = round(weight * plan["protein_mult"])
    target_carbs   = round((target_cals * 0.40) / 4)
    target_fat     = round((target_cals * 0.25) / 9)

    st.markdown(
        f'<div class="cal-highlight">'
        f'<div class="cal-big">{target_cals}</div>'
        f'<div style="color:#6b6b8a;font-size:13px;margin-top:4px">calorías diarias recomendadas para {goal_name}</div>'
        f'<div style="margin-top:10px">'
        f'<span class="badge badge-orange">🥩 Proteína: ~{target_protein}g</span>'
        f'<span class="badge badge-green">⚡ Carbos: ~{target_carbs}g</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Imagen ────────────────────────────────────────────────────────────────
    body_file = st.file_uploader(
        "🧍 Sube una foto de cuerpo completo (frente, buena iluminación)",
        type=["jpg", "jpeg", "png", "webp"],
        key="body_uploader",
    )

    if body_file:
        st.image(body_file, use_container_width=True)

        if st.button("🧬 Analizar Composición Corporal", type="primary", use_container_width=True):
            with st.spinner("Evaluando composición corporal con IA…"):
                try:
                    b64, mt = img_to_b64(body_file)
                    prompt_text = (
                        f"Eres un entrenador personal y nutricionista experto. "
                        f"La persona tiene: {weight}kg, {height}cm, {age} años, sexo: {sex}, actividad: {activity}.\n"
                        "Analiza visualmente su composición corporal y responde SOLO en JSON válido sin texto adicional ni backticks:\n"
                        "{\n"
                        '  "body_fat_pct": número estimado de % grasa corporal,\n'
                        '  "muscle_mass": "baja|media|buena|alta",\n'
                        '  "body_type": "ectomorfo|mesomorfo|endomorfo",\n'
                        '  "health_score": número del 1 al 10,\n'
                        '  "fitness_level": "principiante|intermedio|avanzado",\n'
                        '  "strengths": ["fortaleza 1", "fortaleza 2"],\n'
                        '  "areas_to_improve": ["área 1", "área 2"],\n'
                        '  "insights": ["insight 1", "insight 2", "insight 3"],\n'
                        f'  "target_calories": {target_cals},\n'
                        f'  "target_protein_g": {target_protein},\n'
                        f'  "target_carbs_g": {target_carbs},\n'
                        f'  "target_fat_g": {target_fat},\n'
                        '  "meal_plan_hints": ["sugerencia 1", "sugerencia 2", "sugerencia 3"],\n'
                        f'  "training_tip": "consejo de entrenamiento para el objetivo de {goal_name}"\n'
                        "}"
                    )
                    raw    = call_claude([{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
                            {"type": "text", "text": prompt_text},
                        ],
                    }])
                    result = parse_json(raw)
                    if not result:
                        st.error("No se pudo interpretar la respuesta. Intenta con otra foto.")
                    else:
                        # ── Score + tipo ──────────────────────────────────────
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="score-block">'
                            f'<div style="text-align:center">'
                            f'<div class="score-circle-text">{result["health_score"]}</div>'
                            f'<div class="score-sub">SCORE /10</div></div>'
                            f'<div>'
                            f'<span class="badge badge-green">🏋️ {result["fitness_level"]}</span>'
                            f'<span class="badge badge-orange">🧬 {result["body_type"]}</span><br>'
                            f'<span style="font-size:14px;color:#6b6b8a">Masa muscular: '
                            f'<strong style="color:#e8e8f0">{result["muscle_mass"]}</strong></span><br>'
                            f'<span style="font-size:14px;color:#6b6b8a">% Grasa estimada: '
                            f'<strong style="color:#ff6b35">{result["body_fat_pct"]}%</strong></span>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("</div>", unsafe_allow_html=True)

                        # ── Plan nutricional ──────────────────────────────────
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown(
                            f'<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">'
                            f'PLAN NUTRICIONAL — {goal_name}</div>'
                            f'<div class="cal-highlight">'
                            f'<div class="cal-big">{result["target_calories"]}</div>'
                            f'<div style="color:#6b6b8a;font-size:13px">kcal diarias objetivo</div></div>'
                            f'<div class="macro-row">'
                            f'<div class="macro-box"><div class="macro-val m-protein">{result["target_protein_g"]}g</div>'
                            f'<div class="macro-label">Proteína</div></div>'
                            f'<div class="macro-box"><div class="macro-val m-carbs">{result["target_carbs_g"]}g</div>'
                            f'<div class="macro-label">Carbos</div></div>'
                            f'<div class="macro-box"><div class="macro-val m-fat">{result["target_fat_g"]}g</div>'
                            f'<div class="macro-label">Grasas</div></div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("</div>", unsafe_allow_html=True)

                        # ── Insights ──────────────────────────────────────────
                        if result.get("insights"):
                            st.markdown('<div class="result-card">', unsafe_allow_html=True)
                            st.markdown('<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">INSIGHTS CORPORALES</div>', unsafe_allow_html=True)
                            for ins in result["insights"]:
                                st.markdown(
                                    f'<div class="insight-item"><span class="insight-arrow">→</span><span>{ins}</span></div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown("</div>", unsafe_allow_html=True)

                        # ── Fortalezas / A mejorar ────────────────────────────
                        col_s, col_m = st.columns(2)
                        if result.get("strengths"):
                            with col_s:
                                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                                st.markdown('<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">✅ FORTALEZAS</div>', unsafe_allow_html=True)
                                for s in result["strengths"]:
                                    st.markdown(f'<div class="insight-item"><span style="color:#00ff88">✓</span><span>{s}</span></div>', unsafe_allow_html=True)
                                st.markdown("</div>", unsafe_allow_html=True)
                        if result.get("areas_to_improve"):
                            with col_m:
                                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                                st.markdown('<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">🎯 A MEJORAR</div>', unsafe_allow_html=True)
                                for a in result["areas_to_improve"]:
                                    st.markdown(f'<div class="insight-item"><span style="color:#ff6b35">→</span><span>{a}</span></div>', unsafe_allow_html=True)
                                st.markdown("</div>", unsafe_allow_html=True)

                        # ── Sugerencias alimentarias ──────────────────────────
                        if result.get("meal_plan_hints"):
                            st.markdown('<div class="result-card">', unsafe_allow_html=True)
                            st.markdown('<div style="font-size:11px;letter-spacing:2px;color:#6b6b8a;font-weight:700;margin-bottom:10px">🥗 SUGERENCIAS ALIMENTARIAS</div>', unsafe_allow_html=True)
                            for h in result["meal_plan_hints"]:
                                st.markdown(f'<div class="food-item"><span>{h}</span></div>', unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)

                        # ── Training tip ──────────────────────────────────────
                        if result.get("training_tip"):
                            st.markdown(
                                f'<div class="tip-box"><span>🏋️</span><span>{result["training_tip"]}</span></div>',
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    st.error(f"Error al analizar. Verifica que la foto sea clara y de cuerpo completo. ({e})")

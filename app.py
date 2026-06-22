"""
Microgrid Scenario Simulator v2.0
Dashboard profesional reactivo - la simulación se ejecuta automáticamente
al modificar cualquier parámetro (sin necesidad de botón Run).
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path

from src.model import run_simulation, run_stochastic_simulation
from src.metrics import calculate_kpis, get_kpi_descriptions
from src.scenarios import (
    save_scenario, get_comparison_table,
    export_scenarios_csv, export_results_csv
)
from src.plots import (
    plot_generation_vs_demand, plot_energy_balance,
    plot_soc, plot_grid_exchange, plot_emissions,
    plot_thd, plot_voltage, plot_costs,
    plot_curtailment, plot_radar_performance,
    plot_bess_power, plot_frequency_deviation
)

# --- Configuración de página ---
st.set_page_config(
    page_title="Microgrid Scenario Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS PROFESIONAL
# =============================================================================
st.markdown("""
<style>
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(100, 200, 255, 0.15);
    }
    .main-header h1 {
        color: #e0e0e0;
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #a0a0a0;
        font-size: 0.95rem;
        margin: 0.3rem 0 0 0;
    }

    /* KPI card styling */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(100, 200, 255, 0.12);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #60a5fa;
        margin: 0.3rem 0;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    .kpi-good { color: #34d399; }
    .kpi-warn { color: #fbbf24; }
    .kpi-bad { color: #f87171; }

    /* Section headers */
    .section-header {
        color: #e2e8f0;
        font-size: 1.2rem;
        font-weight: 600;
        padding: 0.5rem 0;
        border-bottom: 2px solid rgba(96, 165, 250, 0.3);
        margin: 1.5rem 0 1rem 0;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
    }

    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Plotly chart containers */
    .plot-container {
        border: 1px solid rgba(100, 200, 255, 0.08);
        border-radius: 10px;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HEADER
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>⚡ Microgrid Scenario Simulator</h1>
    <p>Simulador What-If para microrredes multinodales · Generación renovable · BESS · EVs · Calidad de energía · Optimización multi-objetivo</p>
</div>
""", unsafe_allow_html=True)

# --- Session state ---
if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## 🎛️ Parámetros")
    st.caption("La simulación se actualiza automáticamente al modificar cualquier valor.")
    st.divider()

    # --- 1. Escenario General ---
    with st.expander("📋 Escenario General", expanded=True):
        scenario_name = st.text_input("Nombre del escenario", value="Base Scenario")
        horizon_hours = 24
        num_nodes = st.slider("Número de nodos", 1, 20, 5)
        num_stochastic = st.slider("Escenarios estocásticos", 1, 10, 3)

    # --- 2. Generación Renovable ---
    with st.expander("☀️ Generación Renovable", expanded=False):
        pv_capacity = st.slider("Solar PV (kW)", 0, 2000, 500, 50)
        wind_capacity = st.slider("Eólica (kW)", 0, 2000, 300, 50)
        solar_factor = st.slider("Factor irradiancia", 0.0, 1.0, 0.75, 0.05)
        wind_factor = st.slider("Factor viento", 0.0, 1.0, 0.60, 0.05)
        renewable_variability = st.slider("Variabilidad", 0.0, 0.50, 0.15, 0.05)

    # --- 3. BESS ---
    with st.expander("🔋 BESS", expanded=False):
        bess_capacity = st.slider("Capacidad (kWh)", 0, 5000, 1000, 100)
        bess_max_charge = st.slider("Carga máx (kW)", 0, 2000, 250, 50)
        bess_max_discharge = st.slider("Descarga máx (kW)", 0, 2000, 250, 50)
        bess_initial_soc = st.slider("SoC inicial (%)", 0, 100, 50) / 100.0
        bess_min_soc = st.slider("SoC mínimo (%)", 0, 50, 20) / 100.0
        bess_max_soc = st.slider("SoC máximo (%)", 50, 100, 90) / 100.0
        bess_charge_eff = st.slider("η carga (%)", 80, 100, 95) / 100.0
        bess_discharge_eff = st.slider("η descarga (%)", 80, 100, 95) / 100.0
        bess_initial_soh = st.slider("SoH inicial (%)", 50, 100, 100) / 100.0

    # --- 4. Demanda y EVs ---
    with st.expander("🚗 Demanda y EVs", expanded=False):
        base_demand = st.slider("Demanda base (kW)", 100, 2000, 600, 50)
        demand_variability = st.slider("Variabilidad demanda (%)", 0, 50, 20) / 100.0
        num_evs = st.slider("Número de EVs", 0, 200, 40, 5)
        ev_charger_power = st.number_input("Potencia cargador (kW)", value=7.4, step=0.1)
        ev_simultaneity = st.slider("Simultaneidad EV", 0.0, 1.0, 0.35, 0.05)

    # --- 5. Red Principal ---
    with st.expander("🔌 Red Principal", expanded=False):
        buy_price = st.number_input("Precio compra (USD/kWh)", value=0.20, step=0.01, format="%.3f")
        sell_price = st.number_input("Precio venta (USD/kWh)", value=0.10, step=0.01, format="%.3f")
        max_buy = st.slider("Máx compra (kW)", 0, 3000, 1000, 100)
        max_sell = st.slider("Máx venta (kW)", 0, 3000, 1000, 100)

    # --- 6. No Renovables ---
    with st.expander("🏭 No Renovables", expanded=False):
        diesel_available = st.checkbox("Diésel disponible", False)
        gas_available = st.checkbox("Gas natural disponible", False)
        diesel_max = st.slider("Máx diésel (kW)", 0, 2000, 500, 50)
        gas_max = st.slider("Máx gas (kW)", 0, 2000, 500, 50)
        diesel_ef = st.number_input("Emisión diésel (kg/kWh)", value=0.75, step=0.05)
        gasoline_ef = st.number_input("Emisión gasolina (kg/kWh)", value=0.65, step=0.05)
        gas_ef = st.number_input("Emisión gas (kg/kWh)", value=0.45, step=0.05)
        solar_ef = st.number_input("Emisión solar (kg/kWh)", value=0.05, step=0.005, format="%.3f")
        wind_ef = st.number_input("Emisión eólica (kg/kWh)", value=0.015, step=0.005, format="%.3f")

    # --- 7. Calidad de Energía ---
    with st.expander("📊 Calidad de Energía", expanded=False):
        thd_limit = st.number_input("THD límite (%)", value=5.0, step=0.5)
        thd_base_ev = st.number_input("THD base EV (%)", value=3.0, step=0.5)
        ev_harmonic = st.number_input("Armónico EV (%)", value=8.0, step=0.5)
        v_min = st.number_input("V mínimo (p.u.)", value=0.95, step=0.01, format="%.3f")
        v_max = st.number_input("V máximo (p.u.)", value=1.05, step=0.01, format="%.3f")
        freq_nominal = st.number_input("Frecuencia (Hz)", value=60.0, step=1.0)
        freq_max_dev = st.number_input("Δf máx (Hz)", value=0.5, step=0.1)

    # --- 8. Costos ---
    with st.expander("💰 Inversión", expanded=False):
        pv_cost = st.number_input("Costo PV (USD/kW)", value=900, step=50)
        wind_cost = st.number_input("Costo eólico (USD/kW)", value=1300, step=50)
        bess_cost = st.number_input("Costo BESS (USD/kWh)", value=400, step=50)
        diesel_cost = st.number_input("Costo diésel (USD/kW)", value=500, step=50)
        gas_cost = st.number_input("Costo gas (USD/kW)", value=800, step=50)
        discount_rate = st.slider("Tasa descuento (%)", 1, 20, 8) / 100.0
        project_lifetime = st.slider("Vida útil (años)", 5, 40, 20)

    # --- 9. Pesos ---
    with st.expander("⚖️ Pesos Optimización", expanded=False):
        w_economic = st.slider("Económico", 0.0, 1.0, 0.35, 0.05)
        w_technical = st.slider("Técnico", 0.0, 1.0, 0.25, 0.05)
        w_environmental = st.slider("Ambiental", 0.0, 1.0, 0.25, 0.05)
        w_renewable = st.slider("Renovable", 0.0, 1.0, 0.15, 0.05)
        total_w = w_economic + w_technical + w_environmental + w_renewable
        if abs(total_w - 1.0) > 0.01:
            st.warning(f"Suma: {total_w:.2f} ≠ 1.0")
        else:
            st.success(f"✓ Suma: {total_w:.2f}")

# =============================================================================
# CONSTRUIR PARÁMETROS Y EJECUTAR SIMULACIÓN REACTIVA
# =============================================================================
params = {
    "scenario": {
        "name": scenario_name,
        "horizon_hours": horizon_hours,
        "time_step_hours": 1,
        "num_nodes": num_nodes,
        "num_stochastic_scenarios": num_stochastic,
    },
    "renewable": {
        "pv_capacity_kw": pv_capacity,
        "wind_capacity_kw": wind_capacity,
        "solar_irradiance_factor": solar_factor,
        "wind_factor": wind_factor,
        "renewable_variability": renewable_variability,
    },
    "bess": {
        "energy_capacity_kwh": bess_capacity,
        "max_charge_power_kw": bess_max_charge,
        "max_discharge_power_kw": bess_max_discharge,
        "initial_soc": bess_initial_soc,
        "min_soc": bess_min_soc,
        "max_soc": bess_max_soc,
        "charge_efficiency": bess_charge_eff,
        "discharge_efficiency": bess_discharge_eff,
        "initial_soh": bess_initial_soh,
    },
    "demand": {
        "base_demand_kw": base_demand,
        "demand_variability": demand_variability,
        "num_evs": num_evs,
        "ev_charger_power_kw": ev_charger_power,
        "ev_simultaneity_factor": ev_simultaneity,
    },
    "grid": {
        "buy_price_usd_kwh": buy_price,
        "sell_price_usd_kwh": sell_price,
        "max_buy_kw": max_buy,
        "max_sell_kw": max_sell,
    },
    "non_renewable": {
        "diesel_available": diesel_available,
        "gas_available": gas_available,
        "diesel_max_kw": diesel_max,
        "gas_max_kw": gas_max,
        "diesel_emission_factor": diesel_ef,
        "gasoline_emission_factor": gasoline_ef,
        "gas_emission_factor": gas_ef,
        "solar_emission_factor": solar_ef,
        "wind_emission_factor": wind_ef,
    },
    "power_quality": {
        "thd_limit_pct": thd_limit,
        "thd_base_ev_pct": thd_base_ev,
        "ev_harmonic_content_pct": ev_harmonic,
        "voltage_min_pu": v_min,
        "voltage_max_pu": v_max,
        "nominal_frequency_hz": freq_nominal,
        "max_frequency_deviation_hz": freq_max_dev,
    },
    "investment": {
        "pv_cost_usd_kw": pv_cost,
        "wind_cost_usd_kw": wind_cost,
        "bess_cost_usd_kwh": bess_cost,
        "diesel_cost_usd_kw": diesel_cost,
        "gas_cost_usd_kw": gas_cost,
        "discount_rate": discount_rate,
        "project_lifetime_years": project_lifetime,
    },
    "optimization_weights": {
        "economic": w_economic,
        "technical": w_technical,
        "environmental": w_environmental,
        "renewable": w_renewable,
    },
}

# --- Ejecutar simulación automáticamente (reactivo) ---
@st.cache_data(show_spinner=False)
def run_cached_simulation(params_json: str):
    """Ejecuta simulación con cache para evitar recálculos innecesarios."""
    p = json.loads(params_json)
    avg_results, all_results = run_stochastic_simulation(p)
    kpis = calculate_kpis(avg_results, p)
    return avg_results, kpis

# Validar parámetros
valid = True
if bess_min_soc >= bess_max_soc:
    valid = False
if abs(total_w - 1.0) > 0.01:
    valid = False

if valid:
    params_json = json.dumps(params, sort_keys=True)
    results, kpis = run_cached_simulation(params_json)
else:
    st.error("⚠️ Parámetros inválidos. Revise SoC min < SoC max y que los pesos sumen 1.0")
    st.stop()

# =============================================================================
# HELPER: KPI Card HTML
# =============================================================================
def kpi_card(label: str, value: str, color_class: str = "") -> str:
    """Genera HTML para una tarjeta KPI."""
    color = f"kpi-{color_class}" if color_class else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color}">{value}</div>
    </div>
    """


def render_kpi_row(kpi_data: list):
    """Renderiza una fila de KPIs."""
    cols = st.columns(len(kpi_data))
    for col, (label, value, color) in zip(cols, kpi_data):
        with col:
            st.markdown(kpi_card(label, value, color), unsafe_allow_html=True)

# =============================================================================
# TABS PRINCIPALES
# =============================================================================
tab_overview, tab_energy, tab_battery, tab_pq, tab_economics, tab_compare = st.tabs([
    "📊 Overview",
    "⚡ Energy Balance",
    "🔋 Battery",
    "📈 Power Quality",
    "💰 Economics",
    "🔄 Scenarios"
])

# =============================================================================
# TAB: OVERVIEW
# =============================================================================
with tab_overview:
    st.markdown(f'<div class="section-header">Escenario: {scenario_name}</div>',
                unsafe_allow_html=True)

    # Fila 1 - KPIs principales
    ren_color = "good" if kpis["renewable_pct"] > 0.7 else ("warn" if kpis["renewable_pct"] > 0.4 else "bad")
    thd_color = "good" if kpis["thd_max_pct"] <= thd_limit else "bad"
    perf_color = "good" if kpis["performance_index"] > 65 else ("warn" if kpis["performance_index"] > 40 else "bad")

    render_kpi_row([
        ("Índice Global", f"{kpis['performance_index']:.1f}", perf_color),
        ("% Renovable", f"{kpis['renewable_pct']*100:.1f}%", ren_color),
        ("Costo Diario", f"${kpis['daily_cost_usd']:.2f}", ""),
        ("Emisiones CO₂", f"{kpis['total_emissions_kg']:.1f} kg", ""),
        ("THD Máximo", f"{kpis['thd_max_pct']:.2f}%", thd_color),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # Fila 2
    soc_color = "good" if kpis["soc_min"] > 0.3 else ("warn" if kpis["soc_min"] > 0.2 else "bad")
    render_kpi_row([
        ("E. Comprada", f"{kpis['energy_bought_kwh']:.0f} kWh", ""),
        ("E. Vendida", f"{kpis['energy_sold_kwh']:.0f} kWh", ""),
        ("Curtailment", f"{kpis['renewable_curtailed_kwh']:.0f} kWh", ""),
        ("SoC Mínimo", f"{kpis['soc_min']*100:.1f}%", soc_color),
        ("Eficiencia", f"{kpis['global_efficiency']*100:.1f}%", ""),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # Radar + Generación vs Demanda
    col_left, col_right = st.columns([1, 1])
    with col_left:
        fig_radar = plot_radar_performance(kpis, params)
        fig_radar.update_layout(height=380, margin=dict(t=40, b=40, l=60, r=60))
        st.plotly_chart(fig_radar, use_container_width=True)
    with col_right:
        fig_gen = plot_generation_vs_demand(results)
        fig_gen.update_layout(height=380, margin=dict(t=50, b=40))
        st.plotly_chart(fig_gen, use_container_width=True)

# =============================================================================
# TAB: ENERGY BALANCE
# =============================================================================
with tab_energy:
    st.markdown('<div class="section-header">Balance Energético Horario</div>',
                unsafe_allow_html=True)

    fig_balance = plot_energy_balance(results)
    fig_balance.update_layout(height=420, margin=dict(t=50, b=40))
    st.plotly_chart(fig_balance, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_grid = plot_grid_exchange(results)
        fig_grid.update_layout(height=350, margin=dict(t=50, b=40))
        st.plotly_chart(fig_grid, use_container_width=True)
    with col2:
        fig_curt = plot_curtailment(results)
        fig_curt.update_layout(height=350, margin=dict(t=50, b=40))
        st.plotly_chart(fig_curt, use_container_width=True)

    with st.expander("📋 Datos horarios detallados"):
        display_cols = [
            "hour", "pv_generation_kw", "wind_generation_kw", "total_demand_kw",
            "bess_charge_kw", "bess_discharge_kw", "grid_buy_kw", "grid_sell_kw",
            "curtailment_kw", "emissions_total_kg", "net_cost_usd"
        ]
        st.dataframe(
            results[display_cols].round(2),
            use_container_width=True, height=350,
            column_config={
                "hour": st.column_config.NumberColumn("Hora"),
                "pv_generation_kw": st.column_config.NumberColumn("PV (kW)", format="%.1f"),
                "wind_generation_kw": st.column_config.NumberColumn("Eólica (kW)", format="%.1f"),
                "total_demand_kw": st.column_config.NumberColumn("Demanda (kW)", format="%.1f"),
                "bess_charge_kw": st.column_config.NumberColumn("BESS+ (kW)", format="%.1f"),
                "bess_discharge_kw": st.column_config.NumberColumn("BESS- (kW)", format="%.1f"),
                "grid_buy_kw": st.column_config.NumberColumn("Compra (kW)", format="%.1f"),
                "grid_sell_kw": st.column_config.NumberColumn("Venta (kW)", format="%.1f"),
                "curtailment_kw": st.column_config.NumberColumn("Curtail (kW)", format="%.1f"),
                "emissions_total_kg": st.column_config.NumberColumn("CO₂ (kg)", format="%.2f"),
                "net_cost_usd": st.column_config.NumberColumn("Costo ($)", format="%.2f"),
            }
        )

# =============================================================================
# TAB: BATTERY
# =============================================================================
with tab_battery:
    st.markdown('<div class="section-header">Sistema de Almacenamiento BESS</div>',
                unsafe_allow_html=True)

    render_kpi_row([
        ("Capacidad", f"{bess_capacity} kWh", ""),
        ("SoC Mínimo", f"{kpis['soc_min']*100:.1f}%", soc_color),
        ("SoH Final", f"{kpis['soh_final']*100:.3f}%", "good"),
        ("Degradación", f"{(bess_initial_soh - kpis['soh_final'])*100:.4f}%", ""),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    fig_soc = plot_soc(results, params)
    fig_soc.update_layout(height=380, margin=dict(t=50, b=40))
    st.plotly_chart(fig_soc, use_container_width=True)

    fig_bess = plot_bess_power(results)
    fig_bess.update_layout(height=350, margin=dict(t=50, b=40))
    st.plotly_chart(fig_bess, use_container_width=True)

# =============================================================================
# TAB: POWER QUALITY
# =============================================================================
with tab_pq:
    st.markdown('<div class="section-header">Calidad de Energía</div>',
                unsafe_allow_html=True)

    thd_ok = kpis["thd_max_pct"] <= thd_limit
    render_kpi_row([
        ("THD Máximo", f"{kpis['thd_max_pct']:.2f}%", "good" if thd_ok else "bad"),
        ("THD Promedio", f"{kpis['thd_avg_pct']:.2f}%", ""),
        ("Límite IEEE 519", f"{thd_limit}%", ""),
        ("Estado", "✅ Cumple" if thd_ok else "⚠️ Excede", "good" if thd_ok else "bad"),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_thd = plot_thd(results, params)
        fig_thd.update_layout(height=350, margin=dict(t=50, b=40))
        st.plotly_chart(fig_thd, use_container_width=True)
    with col2:
        fig_v = plot_voltage(results, params)
        fig_v.update_layout(height=350, margin=dict(t=50, b=40))
        st.plotly_chart(fig_v, use_container_width=True)

    fig_freq = plot_frequency_deviation(results, params)
    fig_freq.update_layout(height=300, margin=dict(t=50, b=40))
    st.plotly_chart(fig_freq, use_container_width=True)

# =============================================================================
# TAB: ECONOMICS
# =============================================================================
with tab_economics:
    st.markdown('<div class="section-header">Análisis Económico</div>',
                unsafe_allow_html=True)

    render_kpi_row([
        ("CAPEX", f"${kpis['capex_usd']:,.0f}", ""),
        ("CAE", f"${kpis['annual_equivalent_cost_usd']:,.0f}/año", ""),
        ("Costo Op. Diario", f"${kpis['daily_cost_usd']:.2f}", ""),
        ("Costo Total Diario", f"${kpis['total_daily_cost_usd']:.2f}", ""),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_cost = plot_costs(results)
        fig_cost.update_layout(height=380, margin=dict(t=50, b=40))
        st.plotly_chart(fig_cost, use_container_width=True)
    with col2:
        fig_em = plot_emissions(results)
        fig_em.update_layout(height=380, margin=dict(t=50, b=40))
        st.plotly_chart(fig_em, use_container_width=True)

    # Desglose de costos
    with st.expander("📖 Desglose Económico"):
        st.markdown(f"""
        | Concepto | Valor |
        |----------|-------|
        | CAPEX Total | ${kpis['capex_usd']:,.0f} |
        | → Solar PV ({pv_capacity} kW × ${pv_cost}/kW) | ${pv_capacity * pv_cost:,.0f} |
        | → Eólica ({wind_capacity} kW × ${wind_cost}/kW) | ${wind_capacity * wind_cost:,.0f} |
        | → BESS ({bess_capacity} kWh × ${bess_cost}/kWh) | ${bess_capacity * bess_cost:,.0f} |
        | Costo Anual Equivalente (CRF {discount_rate*100:.0f}%, {project_lifetime} años) | ${kpis['annual_equivalent_cost_usd']:,.0f}/año |
        | Costo Operativo Diario (compra - venta) | ${kpis['daily_cost_usd']:.2f}/día |
        | Energía comprada ({kpis['energy_bought_kwh']:.0f} kWh × ${buy_price}/kWh) | ${kpis['energy_bought_kwh'] * buy_price:.2f} |
        | Ingreso venta ({kpis['energy_sold_kwh']:.0f} kWh × ${sell_price}/kWh) | ${kpis['energy_sold_kwh'] * sell_price:.2f} |
        """)

# =============================================================================
# TAB: SCENARIO COMPARISON
# =============================================================================
with tab_compare:
    st.markdown('<div class="section-header">Comparación de Escenarios</div>',
                unsafe_allow_html=True)

    col_save, col_clear, col_spacer = st.columns([1, 1, 2])
    with col_save:
        if st.button("💾 Guardar Escenario", type="primary", use_container_width=True):
            st.session_state.saved_scenarios = save_scenario(
                scenario_name, kpis, params,
                st.session_state.saved_scenarios
            )
            st.toast(f"✅ '{scenario_name}' guardado", icon="💾")
    with col_clear:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.saved_scenarios = []
            st.toast("Escenarios eliminados", icon="🗑️")

    if st.session_state.saved_scenarios:
        st.markdown("<br>", unsafe_allow_html=True)
        comparison_df = get_comparison_table(st.session_state.saved_scenarios)

        st.dataframe(
            comparison_df,
            use_container_width=True,
            height=min(400, 60 + len(st.session_state.saved_scenarios) * 40),
            column_config={
                "% Renovable": st.column_config.NumberColumn(format="%.3f"),
                "SoC Mín": st.column_config.NumberColumn(format="%.3f"),
                "SoH Final": st.column_config.NumberColumn(format="%.4f"),
                "Índice Global": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.1f"
                ),
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "📥 Comparación CSV",
                export_scenarios_csv(st.session_state.saved_scenarios),
                file_name="scenario_comparison.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            st.download_button(
                "📥 Resultados Horarios CSV",
                export_results_csv(results),
                file_name="hourly_results.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info(
            "Modifique parámetros en la barra lateral, nombre el escenario y "
            "presione **Guardar Escenario** para comenzar a comparar."
        )

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#64748b; font-size:0.8rem;">'
    'Microgrid Scenario Simulator v2.0 · Modelo simplificado para análisis What-If · '
    'Generación renovable · BESS · EVs · Optimización multi-objetivo'
    '</p>',
    unsafe_allow_html=True
)

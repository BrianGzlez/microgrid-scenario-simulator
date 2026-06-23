"""
Simulador de Escenarios de Microrred v3.1
Dashboard profesional · Fondo blanco · Español · Moneda: Pesos Dominicanos (RD$)
"""

import streamlit as st
import pandas as pd
import numpy as np
import json

from src.model import run_stochastic_simulation
from src.metrics import calculate_kpis
from src.scenarios import (
    save_scenario, get_comparison_table,
    export_scenarios_csv, export_results_csv
)
from src.plots import (
    plot_generation_vs_demand, plot_energy_balance,
    plot_soc, plot_grid_exchange, plot_emissions,
    plot_thd, plot_voltage, plot_costs,
    plot_curtailment, plot_radar_performance,
    plot_bess_power, plot_frequency_deviation,
    plot_energy_mix_donut, plot_hourly_cost_line,
    plot_bess_energy_stored, plot_bess_cycles, plot_soh_evolution,
    plot_capex_breakdown, plot_daily_revenue_cost, plot_cost_by_period
)

st.set_page_config(
    page_title="Simulador de Microrred",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# CSS
# =============================================================================
st.markdown("""
<style>
    .kpi-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e40af;
        margin: 0.3rem 0;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .kpi-good { color: #16a34a; }
    .kpi-warn { color: #d97706; }
    .kpi-bad { color: #dc2626; }
    .section-header {
        color: #1e293b;
        font-size: 1.15rem;
        font-weight: 600;
        padding: 0.4rem 0;
        border-bottom: 2px solid #2563eb;
        margin: 1rem 0 1rem 0;
    }
    .param-group-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #334155;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 1.2rem 0 0.6rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #e2e8f0;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ENCABEZADO
# =============================================================================
st.markdown("# Simulador de Escenarios de Microrred Multinodal")
st.caption(
    "Plataforma de simulación y análisis What-If para el diseño óptimo de microrredes con "
    "generación solar y eólica, almacenamiento en baterías (BESS), carga de vehículos eléctricos, "
    "interconexión con la red principal y evaluación técnico-económica-ambiental."
)
st.divider()

if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []

# =============================================================================
# PESTAÑAS
# =============================================================================
tab_params, tab_overview, tab_energy, tab_battery, tab_pq, tab_economics, tab_compare = st.tabs([
    "Parámetros",
    "Resumen",
    "Balance Energético",
    "Batería",
    "Calidad de Energía",
    "Economía",
    "Comparar Escenarios"
])

# =============================================================================
# PESTAÑA: PARÁMETROS
# =============================================================================
with tab_params:
    st.markdown('<div class="section-header">Configuración del Escenario</div>',
                unsafe_allow_html=True)
    st.caption("Los resultados se actualizan automáticamente al modificar cualquier valor.")

    # ─── FILA 1: Escenario + Generación | Almacenamiento | Demanda + Red ───
    col_a, col_b, col_c = st.columns(3, gap="large")

    with col_a:
        st.markdown('<div class="param-group-title">Escenario General</div>', unsafe_allow_html=True)
        scenario_name = st.text_input("Nombre del escenario", value="Escenario Base")
        num_nodes = st.slider("Número de nodos", 1, 20, 5)
        num_stochastic = st.slider("Escenarios estocásticos", 1, 10, 3)
        horizon_hours = 24

        st.markdown('<div class="param-group-title">Generación Renovable</div>', unsafe_allow_html=True)
        pv_capacity = st.slider("Capacidad solar PV (kW)", 0, 2000, 500, 50)
        wind_capacity = st.slider("Capacidad eólica (kW)", 0, 2000, 300, 50)
        solar_factor = st.slider("Factor de irradiancia solar", 0.0, 1.0, 0.75, 0.05)
        wind_factor = st.slider("Factor de viento", 0.0, 1.0, 0.60, 0.05)
        renewable_variability = st.slider("Variabilidad renovable", 0.0, 0.50, 0.15, 0.05)

    with col_b:
        st.markdown('<div class="param-group-title">Almacenamiento BESS</div>', unsafe_allow_html=True)
        bess_capacity = st.slider("Capacidad energética (kWh)", 0, 5000, 1000, 100)
        bess_max_charge = st.slider("Potencia máx. carga (kW)", 0, 2000, 250, 50)
        bess_max_discharge = st.slider("Potencia máx. descarga (kW)", 0, 2000, 250, 50)
        bess_initial_soc = st.slider("Estado de carga inicial (%)", 0, 100, 50) / 100.0
        bess_min_soc = st.slider("SoC mínimo operativo (%)", 0, 50, 20) / 100.0
        bess_max_soc = st.slider("SoC máximo operativo (%)", 50, 100, 90) / 100.0
        bess_charge_eff = st.slider("Eficiencia de carga (%)", 80, 100, 95) / 100.0
        bess_discharge_eff = st.slider("Eficiencia de descarga (%)", 80, 100, 95) / 100.0
        bess_initial_soh = st.slider("Estado de salud inicial (%)", 50, 100, 100) / 100.0

    with col_c:
        st.markdown('<div class="param-group-title">Demanda</div>', unsafe_allow_html=True)
        base_demand = st.slider("Demanda base promedio (kW)", 100, 2000, 600, 50)
        demand_variability = st.slider("Variabilidad de demanda (%)", 0, 50, 20) / 100.0
        num_evs = st.slider("Vehículos eléctricos conectados", 0, 200, 40, 5)
        ev_charger_power = st.number_input("Potencia por cargador EV (kW)", value=7.4, step=0.1)
        ev_simultaneity = st.slider("Factor de simultaneidad EV", 0.0, 1.0, 0.35, 0.05)

        st.markdown('<div class="param-group-title">Red Principal</div>', unsafe_allow_html=True)
        buy_price = st.number_input("Tarifa de compra (RD$/kWh)", value=12.0, step=0.5, format="%.2f")
        sell_price = st.number_input("Tarifa de venta (RD$/kWh)", value=6.0, step=0.5, format="%.2f")
        max_buy = st.slider("Potencia máx. importación (kW)", 0, 3000, 1000, 100)
        max_sell = st.slider("Potencia máx. exportación (kW)", 0, 3000, 1000, 100)

    st.divider()

    # ─── FILA 2: No Renovables | Calidad + Pesos | Inversión ───
    col_d, col_e, col_f = st.columns(3, gap="large")

    with col_d:
        st.markdown('<div class="param-group-title">Generación Convencional</div>', unsafe_allow_html=True)
        diesel_available = st.checkbox("Diésel disponible", False)
        gas_available = st.checkbox("Gas natural disponible", False)
        diesel_max = st.slider("Potencia máx. diésel (kW)", 0, 2000, 500, 50)
        gas_max = st.slider("Potencia máx. gas natural (kW)", 0, 2000, 500, 50)

        st.markdown('<div class="param-group-title">Factores de Emisión</div>', unsafe_allow_html=True)
        diesel_ef = st.number_input("Diésel (kg CO₂/kWh)", value=0.75, step=0.05)
        gasoline_ef = st.number_input("Gasolina (kg CO₂/kWh)", value=0.65, step=0.05)
        gas_ef = st.number_input("Gas natural (kg CO₂/kWh)", value=0.45, step=0.05)
        solar_ef = st.number_input("Solar (kg CO₂/kWh)", value=0.050, step=0.005, format="%.3f")
        wind_ef = st.number_input("Eólica (kg CO₂/kWh)", value=0.015, step=0.005, format="%.3f")

    with col_e:
        st.markdown('<div class="param-group-title">Calidad de Energía</div>', unsafe_allow_html=True)
        thd_limit = st.number_input("THD límite máximo (%)", value=5.0, step=0.5)
        thd_base_ev = st.number_input("THD base por cargadores EV (%)", value=3.0, step=0.5)
        ev_harmonic = st.number_input("Contenido armónico EV (%)", value=8.0, step=0.5)
        v_min = st.number_input("Voltaje mínimo permitido (p.u.)", value=0.95, step=0.01, format="%.3f")
        v_max = st.number_input("Voltaje máximo permitido (p.u.)", value=1.05, step=0.01, format="%.3f")
        freq_nominal = st.number_input("Frecuencia nominal (Hz)", value=60.0, step=1.0)
        freq_max_dev = st.number_input("Desviación máx. frecuencia (Hz)", value=0.5, step=0.1)

        st.markdown('<div class="param-group-title">Pesos de Optimización</div>', unsafe_allow_html=True)
        w_economic = st.slider("Peso económico", 0.0, 1.0, 0.35, 0.05)
        w_technical = st.slider("Peso técnico", 0.0, 1.0, 0.25, 0.05)
        w_environmental = st.slider("Peso ambiental", 0.0, 1.0, 0.25, 0.05)
        w_renewable = st.slider("Peso renovable", 0.0, 1.0, 0.15, 0.05)
        total_w = w_economic + w_technical + w_environmental + w_renewable
        if abs(total_w - 1.0) > 0.01:
            st.caption(f"Suma: {total_w:.2f} — se normalizará automáticamente")
        else:
            st.caption(f"Suma de pesos: {total_w:.2f}")

    with col_f:
        st.markdown('<div class="param-group-title">Inversión de Capital (RD$)</div>', unsafe_allow_html=True)
        pv_cost = st.number_input("Costo solar PV (RD$/kW)", value=54000, step=1000)
        wind_cost = st.number_input("Costo eólico (RD$/kW)", value=78000, step=1000)
        bess_cost = st.number_input("Costo BESS (RD$/kWh)", value=24000, step=1000)
        diesel_cost = st.number_input("Costo diésel (RD$/kW)", value=30000, step=1000)
        gas_cost = st.number_input("Costo gas natural (RD$/kW)", value=48000, step=1000)

        st.markdown('<div class="param-group-title">Parámetros Financieros</div>', unsafe_allow_html=True)
        discount_rate = st.slider("Tasa de descuento (%)", 1, 20, 8) / 100.0
        project_lifetime = st.slider("Vida útil del proyecto (años)", 5, 40, 20)

# =============================================================================
# CONSTRUIR PARÁMETROS Y SIMULACIÓN
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

@st.cache_data(show_spinner=False)
def run_cached_simulation(params_json: str):
    p = json.loads(params_json)
    avg_results, _ = run_stochastic_simulation(p)
    kpis = calculate_kpis(avg_results, p)
    return avg_results, kpis

# Validar
valid = True
if bess_min_soc >= bess_max_soc:
    valid = False

# Auto-normalizar pesos si no suman 1.0
if total_w > 0 and abs(total_w - 1.0) > 0.01:
    params["optimization_weights"]["economic"] = w_economic / total_w
    params["optimization_weights"]["technical"] = w_technical / total_w
    params["optimization_weights"]["environmental"] = w_environmental / total_w
    params["optimization_weights"]["renewable"] = w_renewable / total_w

if valid:
    params_json = json.dumps(params, sort_keys=True)
    results, kpis = run_cached_simulation(params_json)
else:
    st.error("Parámetros inválidos. Verifique que SoC mínimo sea menor que SoC máximo.")
    st.stop()

# =============================================================================
# HELPERS
# =============================================================================
def kpi_card(label: str, value: str, color_class: str = "") -> str:
    color = f"kpi-{color_class}" if color_class else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color}">{value}</div>
    </div>
    """

def render_kpi_row(kpi_data: list):
    cols = st.columns(len(kpi_data))
    for col, (label, value, color) in zip(cols, kpi_data):
        with col:
            st.markdown(kpi_card(label, value, color), unsafe_allow_html=True)

# =============================================================================
# PESTAÑA: RESUMEN
# =============================================================================
with tab_overview:
    st.markdown(f'<div class="section-header">Resumen — {scenario_name}</div>',
                unsafe_allow_html=True)

    ren_color = "good" if kpis["renewable_pct"] > 0.7 else ("warn" if kpis["renewable_pct"] > 0.4 else "bad")
    thd_color = "good" if kpis["thd_max_pct"] <= thd_limit else "bad"
    perf_color = "good" if kpis["performance_index"] > 65 else ("warn" if kpis["performance_index"] > 40 else "bad")
    soc_color = "good" if kpis["soc_min"] > 0.3 else ("warn" if kpis["soc_min"] > 0.2 else "bad")

    render_kpi_row([
        ("Índice Global", f"{kpis['performance_index']:.1f}/100", perf_color),
        ("Penetración Renovable", f"{kpis['renewable_pct']*100:.1f}%", ren_color),
        ("Costo Operativo Diario", f"RD${kpis['daily_cost_usd']:,.2f}", ""),
        ("Emisiones CO₂", f"{kpis['total_emissions_kg']:.1f} kg", ""),
        ("THD Máximo", f"{kpis['thd_max_pct']:.2f}%", thd_color),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    render_kpi_row([
        ("Energía Comprada", f"{kpis['energy_bought_kwh']:.0f} kWh", ""),
        ("Energía Vendida", f"{kpis['energy_sold_kwh']:.0f} kWh", ""),
        ("Curtailment", f"{kpis['renewable_curtailed_kwh']:.0f} kWh", ""),
        ("SoC Mínimo", f"{kpis['soc_min']*100:.1f}%", soc_color),
        ("Eficiencia Global", f"{kpis['global_efficiency']*100:.1f}%", ""),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── Indicadores de desempeño ──────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        fig_radar = plot_radar_performance(kpis, params)
        st.plotly_chart(fig_radar, use_container_width=True)
        st.caption("Evaluación normalizada (0–100) en cinco dimensiones clave del sistema.")
    with col2:
        fig_donut = plot_energy_mix_donut(results)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.caption("Proporción de cada fuente en la energía total entregada durante el día.")
    with col3:
        fig_cum_cost = plot_hourly_cost_line(results)
        st.plotly_chart(fig_cum_cost, use_container_width=True)
        st.caption("Acumulación del costo operativo neto (compra − venta) hora a hora.")

    st.divider()

    # ─── Balance generación / demanda ──────────────────────────────────
    st.markdown('<div class="section-header">Generación vs Demanda</div>', unsafe_allow_html=True)
    st.caption(
        "Comparación horaria entre la generación renovable disponible y la demanda total. "
        "Las áreas sombreadas muestran la contribución solar y eólica; las líneas, la demanda."
    )
    fig_gen = plot_generation_vs_demand(results)
    fig_gen.update_layout(height=380)
    st.plotly_chart(fig_gen, use_container_width=True)

    st.divider()

    # ─── Almacenamiento y red ──────────────────────────────────────────
    st.markdown('<div class="section-header">Almacenamiento e Intercambio con Red</div>', unsafe_allow_html=True)
    col_left, col_right = st.columns(2)
    with col_left:
        fig_soc = plot_soc(results, params)
        fig_soc.update_layout(height=340)
        st.plotly_chart(fig_soc, use_container_width=True)
        st.caption("Estado de carga del BESS. Debe mantenerse dentro del rango operativo definido.")
    with col_right:
        fig_grid = plot_grid_exchange(results)
        fig_grid.update_layout(height=340)
        st.plotly_chart(fig_grid, use_container_width=True)
        st.caption("Flujo con la red principal. Valores positivos = importación, negativos = exportación.")

# =============================================================================
# PESTAÑA: BALANCE ENERGÉTICO
# =============================================================================
with tab_energy:
    st.markdown('<div class="section-header">Balance Energético Horario</div>',
                unsafe_allow_html=True)
    st.caption(
        "Desglose completo de la generación por fuente vs la demanda total. "
        "Las barras apiladas muestran cada fuente; la línea roja, la demanda a cubrir."
    )

    fig_balance = plot_energy_balance(results)
    fig_balance.update_layout(height=440)
    st.plotly_chart(fig_balance, use_container_width=True)

    st.divider()

    # ─── Intercambio con Red + Generación Renovable vs Demanda ─────────
    st.markdown('<div class="section-header">Intercambio con Red y Excedentes</div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_grid = plot_grid_exchange(results)
        fig_grid.update_layout(height=380)
        st.plotly_chart(fig_grid, use_container_width=True)
        st.caption(
            "Flujo de potencia con la red principal. "
            "Área superior = importación (compra), área inferior = exportación (venta)."
        )
    with col2:
        fig_curt = plot_curtailment(results)
        fig_curt.update_layout(height=380)
        st.plotly_chart(fig_curt, use_container_width=True)
        curtailment_total = results["curtailment_kw"].sum()
        if curtailment_total < 1:
            st.caption(
                "No hay curtailment en este escenario. La generación renovable se absorbe "
                "completamente entre demanda, BESS y venta a la red. "
                "Aumente la capacidad renovable o reduzca la demanda para observar recortes."
            )
        else:
            st.caption(
                f"Energía renovable recortada: {curtailment_total:.0f} kWh. "
                "Ocurre cuando la generación excede demanda + BESS + límite de exportación."
            )

    st.divider()

    # ─── KPIs de balance ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Resumen de Flujos de Energía</div>',
                unsafe_allow_html=True)
    total_gen_ren = results["renewable_total_kw"].sum()
    total_demand = results["total_demand_kw"].sum()
    total_grid_buy = results["grid_buy_kw"].sum()
    total_grid_sell = results["grid_sell_kw"].sum()
    total_bess_charge = results["bess_charge_kw"].sum()
    total_bess_discharge = results["bess_discharge_kw"].sum()

    render_kpi_row([
        ("Generación Renovable", f"{total_gen_ren:,.0f} kWh", ""),
        ("Demanda Total", f"{total_demand:,.0f} kWh", ""),
        ("Compra de Red", f"{total_grid_buy:,.0f} kWh", ""),
        ("Venta a Red", f"{total_grid_sell:,.0f} kWh", ""),
        ("Carga BESS", f"{total_bess_charge:,.0f} kWh", ""),
        ("Descarga BESS", f"{total_bess_discharge:,.0f} kWh", ""),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("Datos horarios detallados"):
        display_cols = [
            "hour", "pv_generation_kw", "wind_generation_kw", "total_demand_kw",
            "bess_charge_kw", "bess_discharge_kw", "grid_buy_kw", "grid_sell_kw",
            "curtailment_kw", "emissions_total_kg", "net_cost_usd"
        ]
        st.dataframe(results[display_cols].round(2), use_container_width=True, height=350)

# =============================================================================
# PESTAÑA: BATERÍA
# =============================================================================
with tab_battery:
    st.markdown('<div class="section-header">Sistema de Almacenamiento BESS</div>',
                unsafe_allow_html=True)

    render_kpi_row([
        ("Capacidad Instalada", f"{bess_capacity} kWh", ""),
        ("SoC Mínimo Alcanzado", f"{kpis['soc_min']*100:.1f}%", soc_color),
        ("SoH al Final del Día", f"{kpis['soh_final']*100:.3f}%", "good"),
        ("Degradación Diaria", f"{(bess_initial_soh - kpis['soh_final'])*100:.4f}%", ""),
    ])

    st.divider()

    # ─── Estado de carga ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Estado de Carga</div>', unsafe_allow_html=True)
    st.caption(
        "Evolución del SoC durante las 24 horas. Las líneas punteadas marcan los límites "
        "operativos configurados. El BESS no debe operar fuera de estos rangos."
    )
    fig_soc = plot_soc(results, params)
    fig_soc.update_layout(height=380)
    st.plotly_chart(fig_soc, use_container_width=True)

    st.divider()

    # ─── Potencia y energía ────────────────────────────────────────────
    st.markdown('<div class="section-header">Potencia y Energía</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_bess = plot_bess_power(results)
        fig_bess.update_layout(height=380)
        st.plotly_chart(fig_bess, use_container_width=True)
        st.caption("Potencia instantánea. Barras arriba = carga, abajo = descarga.")
    with col2:
        fig_energy = plot_bess_energy_stored(results, params)
        st.plotly_chart(fig_energy, use_container_width=True)
        st.caption("Energía total almacenada en kWh absolutos (SoC x Capacidad).")

    st.divider()

    # ─── Degradación y ciclos ──────────────────────────────────────────
    st.markdown('<div class="section-header">Degradación y Vida Útil</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_cycles = plot_bess_cycles(results, params)
        st.plotly_chart(fig_cycles, use_container_width=True)
        st.caption(
            "Ciclos equivalentes acumulados durante el día. "
            "Un ciclo = carga completa + descarga completa (capacidad nominal)."
        )
    with col2:
        fig_soh = plot_soh_evolution(results)
        st.plotly_chart(fig_soh, use_container_width=True)
        st.caption(
            "Degradación del SoH hora a hora. Modelo simplificado lineal "
            "proporcional a la profundidad de ciclado."
        )

# =============================================================================
# PESTAÑA: CALIDAD DE ENERGÍA
# =============================================================================
with tab_pq:
    st.markdown('<div class="section-header">Calidad de Energía</div>',
                unsafe_allow_html=True)

    thd_ok = kpis["thd_max_pct"] <= thd_limit
    v_min_val = results["voltage_pu"].min()
    v_max_val = results["voltage_pu"].max()
    v_ok = v_min_val >= v_min and v_max_val <= v_max
    freq_max_val = results["frequency_deviation_hz"].abs().max()
    freq_ok = freq_max_val <= freq_max_dev

    render_kpi_row([
        ("THD Máximo", f"{kpis['thd_max_pct']:.2f}%", "good" if thd_ok else "bad"),
        ("THD Promedio", f"{kpis['thd_avg_pct']:.2f}%", ""),
        ("Voltaje Mín/Máx", f"{v_min_val:.3f} / {v_max_val:.3f} p.u.", "good" if v_ok else "warn"),
        ("Δf Máxima", f"{freq_max_val:.3f} Hz", "good" if freq_ok else "warn"),
        ("Cumplimiento THD", "Cumple" if thd_ok else "Excede", "good" if thd_ok else "bad"),
    ])

    st.divider()

    # ─── Distorsión Armónica ───────────────────────────────────────────
    st.markdown('<div class="section-header">Distorsión Armónica Total (THD)</div>',
                unsafe_allow_html=True)
    st.caption(
        "El THD aumenta con mayor proporción de carga EV y actividad de convertidores del BESS. "
        f"Límite normativo IEEE 519: {thd_limit}%. "
        + ("El sistema cumple con el estándar." if thd_ok else "Se supera el límite en algunas horas.")
    )
    fig_thd = plot_thd(results, params)
    fig_thd.update_layout(height=360)
    st.plotly_chart(fig_thd, use_container_width=True)

    st.divider()

    # ─── Voltaje y Frecuencia ──────────────────────────────────────────
    st.markdown('<div class="section-header">Regulación de Voltaje y Frecuencia</div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_v = plot_voltage(results, params)
        fig_v.update_layout(height=360)
        st.plotly_chart(fig_v, use_container_width=True)
        st.caption(
            f"Voltaje nodal promedio. Rango permitido: {v_min}–{v_max} p.u. "
            "La inyección renovable puede causar sobrevoltaje; alta demanda, subvoltaje."
        )
    with col2:
        fig_freq = plot_frequency_deviation(results, params)
        fig_freq.update_layout(height=360)
        st.plotly_chart(fig_freq, use_container_width=True)
        st.caption(
            f"Desviación respecto a {freq_nominal} Hz. "
            f"Rango aceptable: ±{freq_max_dev} Hz. "
            "Refleja desbalances instantáneos entre generación y demanda."
        )

# =============================================================================
# PESTAÑA: ECONOMÍA
# =============================================================================
with tab_economics:
    st.markdown('<div class="section-header">Análisis Económico</div>',
                unsafe_allow_html=True)

    render_kpi_row([
        ("CAPEX Total", f"RD${kpis['capex_usd']:,.0f}", ""),
        ("Costo Anual Equivalente", f"RD${kpis['annual_equivalent_cost_usd']:,.0f}/año", ""),
        ("Costo Operativo Diario", f"RD${kpis['daily_cost_usd']:,.2f}", ""),
        ("Costo Total Diario", f"RD${kpis['total_daily_cost_usd']:,.2f}", ""),
    ])

    st.divider()

    # ─── Costos horarios ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Costos Operativos Horarios</div>',
                unsafe_allow_html=True)
    st.caption(
        "Desglose del costo neto por hora: costo de compra menos ingreso por venta de excedentes."
    )
    col1, col2 = st.columns(2)
    with col1:
        fig_cost = plot_costs(results)
        fig_cost.update_layout(height=380)
        st.plotly_chart(fig_cost, use_container_width=True)
        st.caption("Barras: compra (+) e ingreso venta (-). Línea: costo neto horario.")
    with col2:
        fig_rev = plot_daily_revenue_cost(results)
        st.plotly_chart(fig_rev, use_container_width=True)
        st.caption("Comparación directa entre lo pagado por comprar y lo recibido por vender.")

    st.divider()

    # ─── Costo por periodo + Acumulado ─────────────────────────────────
    st.markdown('<div class="section-header">Distribución de Costos</div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_period = plot_cost_by_period(results)
        st.plotly_chart(fig_period, use_container_width=True)
        st.caption(
            "Proporción del costo diario distribuida por periodo. "
            "Muestra en qué horas se concentra el gasto operativo."
        )
    with col2:
        fig_cum = plot_hourly_cost_line(results)
        st.plotly_chart(fig_cum, use_container_width=True, key="econ_cost_accum")
        st.caption("Acumulación progresiva del costo operativo a lo largo del día.")

    st.divider()

    # ─── Inversión y emisiones ─────────────────────────────────────────
    st.markdown('<div class="section-header">Inversión y Emisiones</div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig_capex = plot_capex_breakdown(params)
        st.plotly_chart(fig_capex, use_container_width=True)
        st.caption("Distribución de la inversión de capital por componente tecnológico.")
    with col2:
        fig_em = plot_emissions(results)
        fig_em.update_layout(height=320)
        st.plotly_chart(fig_em, use_container_width=True)
        st.caption("Emisiones de CO₂ por fuente y hora. Renovables tienen emisiones de ciclo de vida mínimas.")

    st.divider()

    # ─── Desglose tabla ────────────────────────────────────────────────
    with st.expander("Desglose detallado de inversión"):
        st.markdown(f"""
        | Concepto | Valor |
        |----------|-------|
        | CAPEX Total | RD${kpis['capex_usd']:,.0f} |
        | Solar PV ({pv_capacity} kW x RD${pv_cost:,}/kW) | RD${pv_capacity * pv_cost:,.0f} |
        | Eólica ({wind_capacity} kW x RD${wind_cost:,}/kW) | RD${wind_capacity * wind_cost:,.0f} |
        | BESS ({bess_capacity} kWh x RD${bess_cost:,}/kWh) | RD${bess_capacity * bess_cost:,.0f} |
        | Costo Anual Equivalente (tasa {discount_rate*100:.0f}%, {project_lifetime} años) | RD${kpis['annual_equivalent_cost_usd']:,.0f}/año |
        | Costo operativo diario (compra - venta) | RD${kpis['daily_cost_usd']:,.2f}/día |
        """)

# =============================================================================
# PESTAÑA: COMPARAR ESCENARIOS
# =============================================================================
with tab_compare:
    st.markdown('<div class="section-header">Comparación de Escenarios</div>',
                unsafe_allow_html=True)

    col_save, col_clear, _ = st.columns([1, 1, 2])
    with col_save:
        if st.button("Guardar Escenario", type="primary", use_container_width=True):
            st.session_state.saved_scenarios = save_scenario(
                scenario_name, kpis, params,
                st.session_state.saved_scenarios
            )
            st.toast(f"'{scenario_name}' guardado")
    with col_clear:
        if st.button("Limpiar Todo", use_container_width=True):
            st.session_state.saved_scenarios = []
            st.toast("Escenarios eliminados")

    if st.session_state.saved_scenarios:
        st.markdown("<br>", unsafe_allow_html=True)
        comparison_df = get_comparison_table(st.session_state.saved_scenarios)
        st.dataframe(
            comparison_df,
            use_container_width=True,
            height=min(400, 60 + len(st.session_state.saved_scenarios) * 40),
            column_config={
                "Índice Global": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.1f"
                ),
            }
        )

        # ─── Gráficas comparativas (solo si hay 2+ escenarios) ────────
        if len(st.session_state.saved_scenarios) >= 2:
            st.divider()
            st.markdown('<div class="section-header">Comparación Visual</div>',
                        unsafe_allow_html=True)

            import plotly.graph_objects as go

            sc_data = st.session_state.saved_scenarios
            sc_names = [s["name"] for s in sc_data]

            # Normalizar métricas a 0–100 (mejor = mayor)
            max_cost = max(abs(s["daily_cost_usd"]) for s in sc_data) or 1
            max_em = max(s["total_emissions_kg"] for s in sc_data) or 1

            categories = ["Económico", "Ambiental", "Renovable", "Calidad (THD)", "Desempeño"]
            radar_colors = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]

            fig_radar_comp = go.Figure()

            for i, s in enumerate(sc_data):
                cost_score = max(0, min(100, 100 * (1 - abs(s["daily_cost_usd"]) / max_cost)))
                em_score = max(0, min(100, 100 * (1 - s["total_emissions_kg"] / max_em)))
                ren_score = s["renewable_pct"] * 100
                thd_score = max(0, min(100, 100 * (1 - s["thd_max_pct"] / 10)))
                idx_score = s["performance_index"]

                values = [cost_score, em_score, ren_score, thd_score, idx_score]
                color = radar_colors[i % len(radar_colors)]
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

                fig_radar_comp.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill="toself",
                    fillcolor=f"rgba({r},{g},{b},0.08)",
                    line=dict(color=color, width=3),
                    name=s["name"],
                    marker=dict(size=8, color=color, symbol="circle"),
                ))

            fig_radar_comp.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True, range=[0, 100],
                        tickvals=[20, 40, 60, 80, 100],
                        ticktext=["20", "40", "60", "80", "100"],
                        gridcolor="rgba(0,0,0,0.05)",
                        linecolor="rgba(0,0,0,0.08)",
                        tickfont=dict(size=10, color="#94a3b8"),
                    ),
                    angularaxis=dict(
                        gridcolor="rgba(0,0,0,0.08)",
                        linecolor="rgba(0,0,0,0.08)",
                        tickfont=dict(size=13, color="#1e293b"),
                    ),
                    bgcolor="rgba(0,0,0,0)",
                ),
                title=dict(
                    text="Comparación Multidimensional de Escenarios",
                    x=0.5, xanchor="center",
                    font=dict(size=15, color="#1e293b"),
                ),
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="top", y=-0.05,
                    xanchor="center", x=0.5,
                    font=dict(size=12),
                    bgcolor="rgba(0,0,0,0)",
                ),
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1e293b"),
                margin=dict(t=70, b=70, l=80, r=80),
            )

            st.plotly_chart(fig_radar_comp, use_container_width=True)
            st.caption(
                "Cada eje normalizado de 0 a 100 (mayor = mejor). "
                "El escenario con mayor área tiene mejor desempeño integral."
            )

        st.divider()

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "Descargar Comparación (CSV)",
                export_scenarios_csv(st.session_state.saved_scenarios),
                file_name="comparacion_escenarios.csv",
                mime="text/csv", use_container_width=True
            )
        with col_dl2:
            st.download_button(
                "Descargar Resultados Horarios (CSV)",
                export_results_csv(results),
                file_name="resultados_horarios.csv",
                mime="text/csv", use_container_width=True
            )
    else:
        st.info(
            "Modifique parámetros en la pestaña Parámetros, nombre el escenario y "
            "presione Guardar Escenario para comenzar a comparar."
        )

# =============================================================================
# PIE DE PÁGINA
# =============================================================================

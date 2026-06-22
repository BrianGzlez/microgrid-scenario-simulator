"""
Microgrid Scenario Simulator
Dashboard interactivo para simulación de escenarios de microrredes multinodales
con generación renovable, BESS, vehículos eléctricos, red principal,
costos, emisiones y calidad de energía.

Autor: Simulador de Microrredes
Versión: 1.0.0
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

# --- Inicializar session state ---
if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []
if "results" not in st.session_state:
    st.session_state.results = None
if "kpis" not in st.session_state:
    st.session_state.kpis = None
if "params" not in st.session_state:
    st.session_state.params = None

# --- Título principal ---
st.title("⚡ Microgrid Scenario Simulator")
st.markdown(
    "Simulador de escenarios *What-If* para microrredes multinodales con "
    "generación renovable, almacenamiento BESS, vehículos eléctricos, "
    "interacción con red principal, análisis económico, ambiental y de calidad de energía."
)
st.divider()

# =============================================================================
# SIDEBAR - Parámetros de entrada
# =============================================================================
with st.sidebar:
    st.header("🎛️ Parámetros de Simulación")

    # --- 1. Escenario General ---
    with st.expander("📋 Escenario General", expanded=True):
        scenario_name = st.text_input("Nombre del escenario", value="Base Scenario")
        horizon_hours = st.number_input("Horizonte (horas)", value=24, min_value=1, max_value=168)
        num_nodes = st.slider("Número de nodos", min_value=1, max_value=20, value=5)
        num_stochastic = st.slider("Escenarios estocásticos", min_value=1, max_value=10, value=3)

    # --- 2. Generación Renovable ---
    with st.expander("☀️ Generación Renovable"):
        pv_capacity = st.slider("Potencia Solar PV (kW)", 0, 2000, 500, step=50)
        wind_capacity = st.slider("Potencia Eólica (kW)", 0, 2000, 300, step=50)
        solar_factor = st.slider("Factor de irradiancia", 0.0, 1.0, 0.75, step=0.05)
        wind_factor = st.slider("Factor de viento", 0.0, 1.0, 0.60, step=0.05)
        renewable_variability = st.slider("Variabilidad renovable", 0.0, 0.50, 0.15, step=0.05)

    # --- 3. Batería BESS ---
    with st.expander("🔋 Batería BESS"):
        bess_capacity = st.slider("Capacidad BESS (kWh)", 0, 5000, 1000, step=100)
        bess_max_charge = st.slider("Potencia máx. carga (kW)", 0, 2000, 250, step=50)
        bess_max_discharge = st.slider("Potencia máx. descarga (kW)", 0, 2000, 250, step=50)
        bess_initial_soc = st.slider("SoC inicial (%)", 0, 100, 50) / 100.0
        bess_min_soc = st.slider("SoC mínimo (%)", 0, 50, 20) / 100.0
        bess_max_soc = st.slider("SoC máximo (%)", 50, 100, 90) / 100.0
        bess_charge_eff = st.slider("Eficiencia carga (%)", 80, 100, 95) / 100.0
        bess_discharge_eff = st.slider("Eficiencia descarga (%)", 80, 100, 95) / 100.0
        bess_initial_soh = st.slider("SoH inicial (%)", 50, 100, 100) / 100.0

    # --- 4. Demanda y Vehículos Eléctricos ---
    with st.expander("🚗 Demanda y EVs"):
        base_demand = st.slider("Demanda base promedio (kW)", 100, 2000, 600, step=50)
        demand_variability = st.slider("Variabilidad demanda (%)", 0, 50, 20) / 100.0
        num_evs = st.slider("Número de EVs", 0, 200, 40, step=5)
        ev_charger_power = st.number_input("Potencia cargador EV (kW)", value=7.4, step=0.1)
        ev_simultaneity = st.slider("Factor simultaneidad EV", 0.0, 1.0, 0.35, step=0.05)

    # --- 5. Red Principal ---
    with st.expander("🔌 Red Principal"):
        buy_price = st.number_input("Precio compra (USD/kWh)", value=0.20, step=0.01, format="%.3f")
        sell_price = st.number_input("Precio venta (USD/kWh)", value=0.10, step=0.01, format="%.3f")
        max_buy = st.slider("Máx. compra red (kW)", 0, 3000, 1000, step=100)
        max_sell = st.slider("Máx. venta red (kW)", 0, 3000, 1000, step=100)

    # --- 6. Tecnologías No Renovables ---
    with st.expander("🏭 No Renovables"):
        diesel_available = st.checkbox("Diésel disponible", value=False)
        gas_available = st.checkbox("Gas natural disponible", value=False)
        diesel_max = st.slider("Potencia máx. diésel (kW)", 0, 2000, 500, step=50)
        gas_max = st.slider("Potencia máx. gas natural (kW)", 0, 2000, 500, step=50)
        diesel_ef = st.number_input("Factor emisión diésel (kg CO₂/kWh)", value=0.75, step=0.05)
        gasoline_ef = st.number_input("Factor emisión gasolina (kg CO₂/kWh)", value=0.65, step=0.05)
        gas_ef = st.number_input("Factor emisión gas natural (kg CO₂/kWh)", value=0.45, step=0.05)
        solar_ef = st.number_input("Factor emisión solar (kg CO₂/kWh)", value=0.05, step=0.005, format="%.3f")
        wind_ef = st.number_input("Factor emisión eólica (kg CO₂/kWh)", value=0.015, step=0.005, format="%.3f")

    # --- 7. Calidad de Energía ---
    with st.expander("📊 Calidad de Energía"):
        thd_limit = st.number_input("THD límite máximo (%)", value=5.0, step=0.5)
        thd_base_ev = st.number_input("THD base EV (%)", value=3.0, step=0.5)
        ev_harmonic = st.number_input("Contenido armónico EV (%)", value=8.0, step=0.5)
        v_min = st.number_input("Voltaje mínimo (p.u.)", value=0.95, step=0.01, format="%.3f")
        v_max = st.number_input("Voltaje máximo (p.u.)", value=1.05, step=0.01, format="%.3f")
        freq_nominal = st.number_input("Frecuencia nominal (Hz)", value=60.0, step=1.0)
        freq_max_dev = st.number_input("Desviación máx. frecuencia (Hz)", value=0.5, step=0.1)

    # --- 8. Costos de Inversión ---
    with st.expander("💰 Costos de Inversión"):
        pv_cost = st.number_input("Costo PV (USD/kW)", value=900, step=50)
        wind_cost = st.number_input("Costo eólico (USD/kW)", value=1300, step=50)
        bess_cost = st.number_input("Costo BESS (USD/kWh)", value=400, step=50)
        diesel_cost = st.number_input("Costo diésel (USD/kW)", value=500, step=50)
        gas_cost = st.number_input("Costo gas natural (USD/kW)", value=800, step=50)
        discount_rate = st.slider("Tasa de descuento (%)", 1, 20, 8) / 100.0
        project_lifetime = st.slider("Vida útil proyecto (años)", 5, 40, 20)

    # --- 9. Pesos de Optimización ---
    with st.expander("⚖️ Pesos de Optimización"):
        st.caption("Los pesos deben sumar 1.0")
        w_economic = st.slider("Peso económico", 0.0, 1.0, 0.35, step=0.05)
        w_technical = st.slider("Peso técnico", 0.0, 1.0, 0.25, step=0.05)
        w_environmental = st.slider("Peso ambiental", 0.0, 1.0, 0.25, step=0.05)
        w_renewable = st.slider("Peso renovable", 0.0, 1.0, 0.15, step=0.05)
        total_weights = w_economic + w_technical + w_environmental + w_renewable
        if abs(total_weights - 1.0) > 0.01:
            st.warning(f"⚠️ Suma actual: {total_weights:.2f} (debe ser 1.0)")
        else:
            st.success(f"✅ Suma: {total_weights:.2f}")

    st.divider()

    # --- Botón de ejecución ---
    run_button = st.button("🚀 Run Scenario", type="primary", use_container_width=True)

# =============================================================================
# Construir diccionario de parámetros
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

# =============================================================================
# Ejecución de simulación
# =============================================================================
if run_button:
    total_weights = (params["optimization_weights"]["economic"] +
                     params["optimization_weights"]["technical"] +
                     params["optimization_weights"]["environmental"] +
                     params["optimization_weights"]["renewable"])
    if abs(total_weights - 1.0) > 0.01:
        st.error("❌ Los pesos de optimización deben sumar 1.0. Ajuste los valores.")
    elif params["bess"]["min_soc"] >= params["bess"]["max_soc"]:
        st.error("❌ El SoC mínimo debe ser menor que el SoC máximo.")
    else:
        with st.spinner("🔄 Ejecutando simulación estocástica..."):
            try:
                avg_results, all_results = run_stochastic_simulation(params)
                kpis = calculate_kpis(avg_results, params)
                st.session_state.results = avg_results
                st.session_state.kpis = kpis
                st.session_state.params = params
                st.success("✅ Simulación completada exitosamente.")
            except Exception as e:
                st.error(f"❌ Error en simulación: {str(e)}")

# =============================================================================
# Mostrar resultados
# =============================================================================
if st.session_state.results is not None:
    results = st.session_state.results
    kpis = st.session_state.kpis
    current_params = st.session_state.params

    # --- Tabs principales ---
    tab_overview, tab_energy, tab_battery, tab_pq, tab_economics, tab_compare = st.tabs([
        "📊 Overview",
        "⚡ Energy Balance",
        "🔋 Battery",
        "📈 Power Quality",
        "💰 Economics",
        "🔄 Scenario Comparison"
    ])

    # =================================================================
    # TAB: OVERVIEW
    # =================================================================
    with tab_overview:
        st.subheader(f"📊 Resumen del Escenario: {current_params['scenario']['name']}")

        # KPI Cards - Fila 1
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Costo Diario Operativo", f"${kpis['daily_cost_usd']:.2f}")
        with col2:
            st.metric("Energía Comprada", f"{kpis['energy_bought_kwh']:.1f} kWh")
        with col3:
            st.metric("Energía Vendida", f"{kpis['energy_sold_kwh']:.1f} kWh")
        with col4:
            st.metric("% Renovable", f"{kpis['renewable_pct']*100:.1f}%")

        # KPI Cards - Fila 2
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Emisiones CO₂", f"{kpis['total_emissions_kg']:.1f} kg")
        with col2:
            st.metric("Curtailment", f"{kpis['renewable_curtailed_kwh']:.1f} kWh")
        with col3:
            st.metric("THD Máximo", f"{kpis['thd_max_pct']:.2f}%")
        with col4:
            st.metric("Índice Global", f"{kpis['performance_index']:.1f}/100")

        # KPI Cards - Fila 3
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("SoC Mínimo", f"{kpis['soc_min']*100:.1f}%")
        with col2:
            st.metric("SoH Final", f"{kpis['soh_final']*100:.2f}%")
        with col3:
            st.metric("Eficiencia Global", f"{kpis['global_efficiency']*100:.1f}%")
        with col4:
            st.metric("THD Promedio", f"{kpis['thd_avg_pct']:.2f}%")

        st.divider()

        # Radar Chart
        col_radar, col_info = st.columns([2, 1])
        with col_radar:
            fig_radar = plot_radar_performance(kpis, current_params)
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_info:
            st.markdown("### 📖 Interpretación")
            st.markdown("""
            El **Índice Global de Desempeño** combina:
            - **Económico**: Menor costo operativo = mejor.
            - **Técnico**: Menor THD y mayor estabilidad del SoC = mejor.
            - **Ambiental**: Menores emisiones CO₂ = mejor.
            - **Renovable**: Mayor penetración renovable = mejor.
            - **Eficiencia**: Mayor aprovechamiento energético = mejor.

            Cada eje se normaliza de 0 a 100. El área del polígono
            indica el desempeño general del escenario.
            """)

        # Generación vs Demanda
        st.plotly_chart(plot_generation_vs_demand(results), use_container_width=True)
        st.caption(
            "Esta gráfica muestra la generación renovable total (solar + eólica) "
            "comparada con la demanda total (base + EV). Las áreas sombreadas "
            "representan la generación acumulada por fuente."
        )

    # =================================================================
    # TAB: ENERGY BALANCE
    # =================================================================
    with tab_energy:
        st.subheader("⚡ Balance Energético")

        st.plotly_chart(plot_energy_balance(results), use_container_width=True)
        st.caption(
            "Balance energético desglosado por fuente. Las barras apiladas muestran "
            "la contribución de cada fuente (solar, eólica, BESS, red, diésel, gas) "
            "y la línea roja representa la demanda total a cubrir."
        )

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_grid_exchange(results), use_container_width=True)
            st.caption(
                "Intercambio con la red principal. Valores positivos = compra, "
                "negativos = venta. Idealmente, se minimiza la compra y se "
                "maximiza la venta durante horas de excedente renovable."
            )
        with col2:
            st.plotly_chart(plot_curtailment(results), use_container_width=True)
            st.caption(
                "Energía renovable desperdiciada (curtailment) por hora. "
                "Ocurre cuando la generación excede la demanda, la capacidad "
                "del BESS está llena y el límite de venta a la red se alcanza."
            )

        # Tabla de datos horarios
        with st.expander("📋 Datos horarios detallados"):
            st.dataframe(results.round(2), use_container_width=True, height=400)

    # =================================================================
    # TAB: BATTERY
    # =================================================================
    with tab_battery:
        st.subheader("🔋 Sistema de Almacenamiento BESS")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Capacidad", f"{current_params['bess']['energy_capacity_kwh']} kWh")
        with col2:
            st.metric("SoC Mínimo Alcanzado", f"{kpis['soc_min']*100:.1f}%")
        with col3:
            st.metric("SoH Final", f"{kpis['soh_final']*100:.3f}%")

        st.plotly_chart(plot_soc(results, current_params), use_container_width=True)
        st.caption(
            "Estado de carga (SoC) del BESS durante las 24 horas. Las líneas "
            "punteadas indican los límites operativos configurados. El SoC no "
            "debe caer por debajo del mínimo para preservar la vida útil."
        )

        st.plotly_chart(plot_bess_power(results), use_container_width=True)
        st.caption(
            "Potencia de carga (positiva) y descarga (negativa) del BESS. "
            "La batería se carga durante excedente renovable y se descarga "
            "durante el déficit, optimizando el autoconsumo."
        )

        # SoH evolution
        st.markdown("### Degradación de Batería")
        st.markdown(
            f"La batería inició con SoH = {current_params['bess']['initial_soh']*100:.1f}% "
            f"y terminó con SoH = {kpis['soh_final']*100:.3f}%. "
            f"La degradación diaria aproximada es de "
            f"{(current_params['bess']['initial_soh'] - kpis['soh_final'])*100:.4f}%."
        )

    # =================================================================
    # TAB: POWER QUALITY
    # =================================================================
    with tab_pq:
        st.subheader("📈 Calidad de Energía")

        col1, col2, col3 = st.columns(3)
        with col1:
            thd_status = "✅" if kpis["thd_max_pct"] <= current_params["power_quality"]["thd_limit_pct"] else "⚠️"
            st.metric(f"THD Máximo {thd_status}", f"{kpis['thd_max_pct']:.2f}%")
        with col2:
            st.metric("THD Promedio", f"{kpis['thd_avg_pct']:.2f}%")
        with col3:
            st.metric("Límite THD", f"{current_params['power_quality']['thd_limit_pct']}%")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_thd(results, current_params), use_container_width=True)
            st.caption(
                "THD por hora. Aumenta con mayor proporción de carga EV "
                "y actividad de convertidores del BESS. Debe mantenerse "
                "por debajo del límite regulatorio."
            )
        with col2:
            st.plotly_chart(plot_voltage(results, current_params), use_container_width=True)
            st.caption(
                "Voltaje nodal promedio. Debe mantenerse entre los límites "
                "regulatorios (típicamente ±5% de nominal). La inyección "
                "renovable puede causar sobrevoltaje en horas de alta generación."
            )

        st.plotly_chart(plot_frequency_deviation(results, current_params), use_container_width=True)
        st.caption(
            "Desviación de frecuencia respecto al nominal. Refleja desbalances "
            "entre generación y demanda. La banda sombreada indica el rango "
            "aceptable de operación."
        )

        st.markdown("### 📖 Nota sobre Calidad de Energía")
        st.markdown("""
        Los valores de THD, voltaje y frecuencia son **aproximaciones simplificadas**
        basadas en modelos empíricos. En un análisis real se requeriría:
        - Flujo de potencia detallado (Newton-Raphson o similar).
        - Análisis armónico con modelos de convertidores.
        - Simulación dinámica para respuesta de frecuencia.
        """)

    # =================================================================
    # TAB: ECONOMICS
    # =================================================================
    with tab_economics:
        st.subheader("💰 Análisis Económico")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("CAPEX Total", f"${kpis['capex_usd']:,.0f}")
        with col2:
            st.metric("CAE (USD/año)", f"${kpis['annual_equivalent_cost_usd']:,.0f}")
        with col3:
            st.metric("Costo Diario Op.", f"${kpis['daily_cost_usd']:.2f}")
        with col4:
            st.metric("Costo Total Diario", f"${kpis['total_daily_cost_usd']:.2f}")

        st.plotly_chart(plot_costs(results), use_container_width=True)
        st.caption(
            "Costos horarios de energía. Las barras muestran el costo de compra "
            "y el ingreso por venta. La línea negra es el costo neto por hora."
        )

        st.plotly_chart(plot_emissions(results), use_container_width=True)
        st.caption(
            "Emisiones de CO₂ por fuente y hora. Las fuentes renovables tienen "
            "emisiones muy bajas (solo del ciclo de vida del equipo). "
            "Diésel y gas natural son los principales contribuyentes."
        )

        st.markdown("### 📖 Fórmulas Económicas")
        st.markdown(f"""
        | Concepto | Fórmula | Valor |
        |----------|---------|-------|
        | CAPEX | PV×CostPV + Wind×CostWind + BESS×CostBESS + ... | ${kpis['capex_usd']:,.0f} |
        | CAE | CAPEX × CRF(i, n) | ${kpis['annual_equivalent_cost_usd']:,.0f}/año |
        | CRF | i(1+i)ⁿ / ((1+i)ⁿ - 1) | {current_params['investment']['discount_rate']*100:.0f}%, {current_params['investment']['project_lifetime_years']} años |
        | Costo diario | E_comprada×P_compra - E_vendida×P_venta | ${kpis['daily_cost_usd']:.2f} |
        """)

    # =================================================================
    # TAB: SCENARIO COMPARISON
    # =================================================================
    with tab_compare:
        st.subheader("🔄 Comparación de Escenarios")

        # Botón para guardar escenario actual
        col_save, col_clear = st.columns(2)
        with col_save:
            if st.button("💾 Guardar Escenario Actual", use_container_width=True):
                st.session_state.saved_scenarios = save_scenario(
                    current_params["scenario"]["name"],
                    kpis, current_params,
                    st.session_state.saved_scenarios
                )
                st.success(f"✅ Escenario '{current_params['scenario']['name']}' guardado.")
        with col_clear:
            if st.button("🗑️ Limpiar Escenarios", use_container_width=True):
                st.session_state.saved_scenarios = []
                st.info("Escenarios guardados eliminados.")

        # Tabla comparativa
        if st.session_state.saved_scenarios:
            st.markdown("### Tabla Comparativa")
            comparison_df = get_comparison_table(st.session_state.saved_scenarios)
            st.dataframe(comparison_df, use_container_width=True)

            st.markdown("### Exportación")
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv_scenarios = export_scenarios_csv(st.session_state.saved_scenarios)
                st.download_button(
                    "📥 Descargar Comparación (CSV)",
                    csv_scenarios,
                    file_name="scenario_comparison.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_exp2:
                csv_results = export_results_csv(results)
                st.download_button(
                    "📥 Descargar Resultados Horarios (CSV)",
                    csv_results,
                    file_name="hourly_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info(
                "No hay escenarios guardados. Ejecute una simulación y presione "
                "'Guardar Escenario Actual' para comenzar a comparar."
            )

else:
    # --- Estado inicial sin simulación ---
    st.info(
        "👈 Configure los parámetros en la barra lateral y presione "
        "**'🚀 Run Scenario'** para ejecutar la simulación."
    )

    st.markdown("### 🏗️ Arquitectura del Simulador")
    st.markdown("""
    Este simulador modela una microrred multinodal con los siguientes componentes:

    | Componente | Descripción |
    |------------|-------------|
    | ☀️ Solar PV | Generación fotovoltaica con perfil de irradiancia diaria |
    | 💨 Eólica | Generación eólica con variabilidad estocástica |
    | 🔋 BESS | Sistema de almacenamiento con degradación y límites de SoC |
    | 🚗 EVs | Vehículos eléctricos con patrones de carga característicos |
    | 🔌 Red | Interconexión con red principal (compra/venta) |
    | 🏭 Diésel/Gas | Generación convencional de respaldo |

    **Flujo de despacho** (prioridad):
    1. Generación renovable cubre demanda directamente.
    2. Excedente renovable carga el BESS.
    3. Excedente restante se vende a la red.
    4. Déficit se cubre con BESS → Diésel/Gas → Red.
    5. Energía no utilizable se contabiliza como curtailment.
    """)

# --- Footer ---
st.divider()
st.caption(
    "Microgrid Scenario Simulator v1.0 | "
    "Modelo simplificado para análisis de escenarios What-If | "
    "Desarrollado para investigación en microrredes, BESS, EVs y optimización energética."
)

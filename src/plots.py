"""
Módulo de visualización con Plotly para el simulador de microrredes.
Genera gráficas interactivas profesionales para el dashboard.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any


# Paleta de colores profesional
COLORS = {
    "solar": "#FBBF24",
    "wind": "#34D399",
    "demand": "#F87171",
    "ev_demand": "#A78BFA",
    "bess_charge": "#60A5FA",
    "bess_discharge": "#FB923C",
    "grid_buy": "#A1887F",
    "grid_sell": "#22D3EE",
    "curtailment": "#94A3B8",
    "diesel": "#9CA3AF",
    "gas": "#D4A574",
    "soc": "#818CF8",
    "thd": "#F472B6",
    "voltage": "#2DD4BF",
    "emissions": "#FB7185",
}

# Layout base para todas las gráficas (light/clean theme)
LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter, sans-serif", color="#1e293b"),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11)
    ),
    margin=dict(l=50, r=20, t=50, b=40),
    hovermode="x unified",
)


def plot_generation_vs_demand(results: pd.DataFrame) -> go.Figure:
    """
    Genera gráfica de generación renovable vs demanda total.
    Muestra el balance energético hora a hora.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["pv_generation_kw"],
        name="Solar PV", fill="tozeroy",
        line=dict(color=COLORS["solar"], width=0),
        fillcolor="rgba(251, 191, 36, 0.35)"
    ))
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["pv_generation_kw"] + results["wind_generation_kw"],
        name="Eólica (acumulada)", fill="tonexty",
        line=dict(color=COLORS["wind"], width=0),
        fillcolor="rgba(52, 211, 153, 0.35)"
    ))
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["total_demand_kw"],
        name="Demanda Total", line=dict(color=COLORS["demand"], width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["base_demand_kw"],
        name="Demanda Base", line=dict(color=COLORS["demand"], width=1, dash="dash")
    ))
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["ev_demand_kw"],
        name="Demanda EV", line=dict(color=COLORS["ev_demand"], width=2, dash="dot")
    ))
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Generación Renovable vs Demanda",
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        height=450,
    )
    
    return fig


def plot_energy_balance(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de balance energético completo mostrando todas las fuentes y usos.
    """
    fig = go.Figure()
    
    # Fuentes de energía (positivas)
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["pv_generation_kw"],
        name="Solar PV", marker_color=COLORS["solar"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["wind_generation_kw"],
        name="Eólica", marker_color=COLORS["wind"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["bess_discharge_kw"],
        name="BESS Descarga", marker_color=COLORS["bess_discharge"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["grid_buy_kw"],
        name="Compra Red", marker_color=COLORS["grid_buy"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["diesel_generation_kw"],
        name="Diésel", marker_color=COLORS["diesel"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["gas_generation_kw"],
        name="Gas Natural", marker_color=COLORS["gas"]
    ))
    
    # Demanda (línea)
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["total_demand_kw"],
        name="Demanda Total", line=dict(color=COLORS["demand"], width=3),
        mode="lines+markers"
    ))
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Balance Energético por Fuente",
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        barmode="stack",
        height=450,
    )
    
    return fig


def plot_soc(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica del estado de carga de la batería con límites.
    """
    fig = go.Figure()
    
    min_soc = params["bess"]["min_soc"]
    max_soc = params["bess"]["max_soc"]
    
    # Banda de operación
    fig.add_hrect(
        y0=min_soc, y1=max_soc,
        fillcolor="rgba(76, 175, 80, 0.1)",
        line_width=0,
        annotation_text="Rango operativo",
        annotation_position="top left"
    )
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["soc"],
        name="SoC", line=dict(color=COLORS["soc"], width=3),
        fill="tozeroy", fillcolor="rgba(129, 140, 248, 0.2)"
    ))
    
    fig.add_hline(y=min_soc, line_dash="dash", line_color="red",
                  annotation_text=f"SoC Mín ({min_soc*100:.0f}%)")
    fig.add_hline(y=max_soc, line_dash="dash", line_color="green",
                  annotation_text=f"SoC Máx ({max_soc*100:.0f}%)")
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Estado de Carga de Batería (SoC)",
        xaxis_title="Hora del día",
        yaxis_title="SoC (fracción)",
        yaxis_range=[0, 1],
        height=400,
    )
    
    return fig


def plot_grid_exchange(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de intercambio con la red como área continua (más legible).
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["grid_buy_kw"],
        name="Compra de red",
        line=dict(color=COLORS["grid_buy"], width=2),
        fill="tozeroy",
        fillcolor="rgba(161, 136, 127, 0.3)",
        mode="lines",
        hovertemplate="Hora %{x}<br>Compra: %{y:.1f} kW<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=results["hour"], y=-results["grid_sell_kw"],
        name="Venta a red",
        line=dict(color=COLORS["grid_sell"], width=2),
        fill="tozeroy",
        fillcolor="rgba(34, 211, 238, 0.3)",
        mode="lines",
        hovertemplate="Hora %{x}<br>Venta: %{y:.1f} kW<extra></extra>",
    ))

    fig.add_hline(y=0, line_color="#94a3b8", line_width=1, line_dash="dot")

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Intercambio con la Red Principal",
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        height=400,
    )

    return fig


def plot_emissions(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de emisiones por fuente.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_diesel_kg"],
        name="Diésel", marker_color=COLORS["diesel"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_gas_kg"],
        name="Gas Natural", marker_color=COLORS["gas"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_solar_kg"],
        name="Solar", marker_color=COLORS["solar"]
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_wind_kg"],
        name="Eólica", marker_color=COLORS["wind"]
    ))
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Emisiones de CO₂ por Fuente",
        xaxis_title="Hora del día",
        yaxis_title="Emisiones (kg CO₂)",
        barmode="stack",
        height=400,
    )
    
    return fig


def plot_thd(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de distorsión armónica total (THD) por hora.
    """
    fig = go.Figure()
    
    thd_limit = params["power_quality"]["thd_limit_pct"]
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["thd_pct"],
        name="THD", line=dict(color=COLORS["thd"], width=3),
        fill="tozeroy", fillcolor="rgba(244, 114, 182, 0.15)"
    ))
    
    fig.add_hline(y=thd_limit, line_dash="dash", line_color="red",
                  annotation_text=f"Límite THD ({thd_limit}%)")
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Distorsión Armónica Total (THD)",
        xaxis_title="Hora del día",
        yaxis_title="THD (%)",
        height=400,
    )
    
    return fig


def plot_voltage(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de voltaje nodal promedio.
    """
    fig = go.Figure()
    
    v_min = params["power_quality"]["voltage_min_pu"]
    v_max = params["power_quality"]["voltage_max_pu"]
    
    # Banda permitida
    fig.add_hrect(
        y0=v_min, y1=v_max,
        fillcolor="rgba(0, 150, 136, 0.1)",
        line_width=0,
    )
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["voltage_pu"],
        name="Voltaje", line=dict(color=COLORS["voltage"], width=3),
    ))
    
    fig.add_hline(y=v_min, line_dash="dash", line_color="red",
                  annotation_text=f"V mín ({v_min} p.u.)")
    fig.add_hline(y=v_max, line_dash="dash", line_color="red",
                  annotation_text=f"V máx ({v_max} p.u.)")
    fig.add_hline(y=1.0, line_dash="dot", line_color="gray",
                  annotation_text="Nominal")
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Voltaje Nodal Promedio",
        xaxis_title="Hora del día",
        yaxis_title="Voltaje (p.u.)",
        height=400,
    )
    
    return fig


def plot_costs(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de costos horarios.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["cost_buy_usd"],
        name="Costo Compra", marker_color=COLORS["grid_buy"]
    ))
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=-results["revenue_sell_usd"],
        name="Ingreso Venta", marker_color=COLORS["grid_sell"]
    ))
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["net_cost_usd"],
        name="Costo Neto", line=dict(color="black", width=2),
        mode="lines+markers"
    ))
    
    fig.add_hline(y=0, line_color="gray", line_width=0.5)
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Costos Horarios de Energía",
        xaxis_title="Hora del día",
        yaxis_title="RD$ [+ costo / - ingreso]",
        height=400,
    )
    
    return fig


def plot_curtailment(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de curtailment renovable.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["curtailment_kw"],
        name="Curtailment", marker_color=COLORS["curtailment"]
    ))
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Curtailment de Energía Renovable",
        xaxis_title="Hora del día",
        yaxis_title="Potencia Recortada (kW)",
        height=350,
    )
    
    return fig


def plot_radar_performance(kpis: Dict[str, float], params: Dict[str, Any]) -> go.Figure:
    """
    Radar chart del desempeño del escenario — estilo profesional con relleno degradado.
    """
    max_cost_ref = 90000.0
    idx_economic = max(0, min(100, 100 * (1 - kpis["daily_cost_usd"] / max_cost_ref)))

    pq = params["power_quality"]
    thd_score = max(0, min(100, 100 * (1 - kpis["thd_max_pct"] / (pq["thd_limit_pct"] * 2))))
    soc_score = max(0, min(100, kpis["soc_min"] * 100 / params["bess"]["max_soc"]))
    idx_technical = 0.6 * thd_score + 0.4 * soc_score

    max_emissions_ref = 500.0
    idx_environmental = max(0, min(100, 100 * (1 - kpis["total_emissions_kg"] / max_emissions_ref)))

    idx_renewable = kpis["renewable_pct"] * 100
    idx_efficiency = kpis["global_efficiency"] * 100

    categories = ["Económico", "Técnico", "Ambiental", "Renovable", "Eficiencia"]
    values = [idx_economic, idx_technical, idx_environmental, idx_renewable, idx_efficiency]

    fig = go.Figure()

    # Fondo de referencia (100%)
    fig.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100, 100, 100],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(226, 232, 240, 0.3)",
        line=dict(color="rgba(203, 213, 225, 0.6)", width=1, dash="dot"),
        name="Máximo",
        showlegend=False,
    ))

    # Datos reales
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(37, 99, 235, 0.15)",
        line=dict(color="#2563eb", width=2.5),
        marker=dict(size=7, color="#2563eb", symbol="circle"),
        name="Desempeño",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
                ticktext=["20", "40", "60", "80", "100"],
                gridcolor="rgba(0,0,0,0.06)",
                linecolor="rgba(0,0,0,0.1)",
                tickfont=dict(size=10, color="#64748b"),
            ),
            angularaxis=dict(
                gridcolor="rgba(0,0,0,0.06)",
                linecolor="rgba(0,0,0,0.1)",
                tickfont=dict(size=12, color="#334155", weight="bold" if hasattr(dict, '') else None),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(
            text="Desempeño Multidimensional",
            font=dict(size=14, color="#1e293b"),
            x=0.5,
        ),
        showlegend=False,
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        margin=dict(t=60, b=40, l=60, r=60),
    )

    return fig


def plot_bess_power(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de potencia de carga/descarga del BESS.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["bess_charge_kw"],
        name="Carga BESS", marker_color=COLORS["bess_charge"]
    ))
    
    fig.add_trace(go.Bar(
        x=results["hour"], y=-results["bess_discharge_kw"],
        name="Descarga BESS", marker_color=COLORS["bess_discharge"]
    ))
    
    fig.add_hline(y=0, line_color="black", line_width=1)
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Potencia de Carga/Descarga BESS",
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW) [+ carga / - descarga]",
        height=400,
    )
    
    return fig


def plot_frequency_deviation(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de desviación de frecuencia.
    """
    fig = go.Figure()
    
    max_dev = params["power_quality"]["max_frequency_deviation_hz"]
    
    fig.add_hrect(
        y0=-max_dev, y1=max_dev,
        fillcolor="rgba(255, 152, 0, 0.1)",
        line_width=0,
    )
    
    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["frequency_deviation_hz"],
        name="Desviación de Frecuencia",
        line=dict(color="#FF9800", width=2),
        fill="tozeroy", fillcolor="rgba(255, 152, 0, 0.2)"
    ))
    
    fig.add_hline(y=max_dev, line_dash="dash", line_color="red",
                  annotation_text=f"+{max_dev} Hz")
    fig.add_hline(y=-max_dev, line_dash="dash", line_color="red",
                  annotation_text=f"-{max_dev} Hz")
    
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Desviación de Frecuencia",
        xaxis_title="Hora del día",
        yaxis_title="Δf (Hz)",
        height=350,
    )
    
    return fig


def plot_energy_mix_donut(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de composición del suministro — barras horizontales limpias
    mostrando la proporción de cada fuente. Más legible que una dona.
    """
    solar = results["pv_generation_kw"].sum()
    wind = results["wind_generation_kw"].sum()
    bess_net = results["bess_discharge_kw"].sum()
    grid = results["grid_buy_kw"].sum()
    diesel = results["diesel_generation_kw"].sum()
    gas = results["gas_generation_kw"].sum()

    sources = []
    values = []
    colors = []

    # Orden de mayor a menor
    raw = [
        ("Solar PV", solar, COLORS["solar"]),
        ("Eólica", wind, COLORS["wind"]),
        ("BESS", bess_net, COLORS["bess_discharge"]),
        ("Red", grid, COLORS["grid_buy"]),
        ("Diésel", diesel, COLORS["diesel"]),
        ("Gas Natural", gas, COLORS["gas"]),
    ]

    for name, val, color in raw:
        if val > 0:
            sources.append(name)
            values.append(val)
            colors.append(color)

    total = sum(values)
    percentages = [(v / total) * 100 for v in values]

    # Ordenar de mayor a menor
    combined = sorted(zip(percentages, sources, values, colors), reverse=True)
    percentages = [c[0] for c in combined]
    sources = [c[1] for c in combined]
    values = [c[2] for c in combined]
    colors = [c[3] for c in combined]

    # Invertir para que el mayor quede arriba en barras horizontales
    sources.reverse()
    percentages.reverse()
    values.reverse()
    colors.reverse()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=sources,
        x=percentages,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="#ffffff", width=1),
        ),
        text=[f"{p:.1f}% ({v:.0f} kWh)" for p, v in zip(percentages, values)],
        textposition="auto",
        textfont=dict(size=11, color="#1e293b"),
        hovertemplate="%{y}: %{x:.1f}%<br>%{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=f"Composición del Suministro — {total:.0f} kWh total",
            font=dict(size=14, color="#1e293b"),
        ),
        xaxis=dict(
            title="Participación (%)",
            range=[0, 100],
            gridcolor="rgba(0,0,0,0.05)",
        ),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        height=350,
        margin=dict(t=50, b=40, l=90, r=20),
        showlegend=False,
    )

    return fig


def plot_hourly_cost_line(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de línea del costo neto acumulado a lo largo del día.
    """
    cumulative_cost = results["net_cost_usd"].cumsum()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"],
        y=cumulative_cost,
        fill="tozeroy",
        fillcolor="rgba(37, 99, 235, 0.08)",
        line=dict(color="#2563eb", width=2.5),
        mode="lines",
        name="Costo acumulado",
        hovertemplate="Hora %{x}<br>RD$%{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(text="Costo Operativo Acumulado", font=dict(size=14, color="#1e293b")),
        xaxis_title="Hora del día",
        yaxis_title="RD$ acumulados",
        height=350,
    )

    return fig

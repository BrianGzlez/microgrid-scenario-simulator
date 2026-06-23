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
        yanchor="bottom", y=1.08,
        xanchor="center", x=0.5,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11)
    ),
    margin=dict(l=50, r=20, t=70, b=40),
    hovermode="x unified",
)


def _title(text: str) -> dict:
    """Helper para crear título centrado uniforme."""
    return dict(text=text, x=0.5, xanchor="center", font=dict(size=14, color="#1e293b"))


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
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k not in ("margin", "legend")},
        title=_title("Generación Renovable vs Demanda"),
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        height=450,
        margin=dict(l=50, r=20, t=90, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.06,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
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
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k not in ("margin", "legend")},
        title=_title("Balance Energético por Fuente"),
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        barmode="stack",
        height=450,
        margin=dict(l=50, r=20, t=90, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.06,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
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
        title=_title("Estado de Carga de Batería (SoC)"),
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
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"},
        title=_title("Intercambio con la Red Principal"),
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        height=400,
        margin=dict(l=50, r=20, t=85, b=40),
    )

    return fig


def plot_emissions(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de emisiones por fuente — colores más vivos y espaciado correcto.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_solar_kg"],
        name="Solar", marker_color="#f59e0b",
        hovertemplate="Hora %{x}<br>Solar: %{y:.2f} kg<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_wind_kg"],
        name="Eólica", marker_color="#10b981",
        hovertemplate="Hora %{x}<br>Eólica: %{y:.2f} kg<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_gas_kg"],
        name="Gas Natural", marker_color="#6366f1",
        hovertemplate="Hora %{x}<br>Gas: %{y:.2f} kg<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=results["hour"], y=results["emissions_diesel_kg"],
        name="Diésel", marker_color="#64748b",
        hovertemplate="Hora %{x}<br>Diésel: %{y:.2f} kg<extra></extra>",
    ))

    fig.update_layout(
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k not in ("margin", "legend")},
        title=_title("Emisiones de CO₂ por Fuente"),
        xaxis_title="Hora del día",
        yaxis_title="Emisiones (kg CO₂)",
        barmode="stack",
        height=400,
        margin=dict(l=50, r=20, t=85, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.06,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
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
        title=_title("Distorsión Armónica Total (THD)"),
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
        title=_title("Voltaje Nodal Promedio"),
        xaxis_title="Hora del día",
        yaxis_title="Voltaje (p.u.)",
        height=400,
    )
    
    return fig


def plot_costs(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de costos horarios — áreas para compra/venta + línea neta.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["cost_buy_usd"],
        name="Costo compra",
        line=dict(color="#ef4444", width=2),
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.15)",
        hovertemplate="Hora %{x}<br>Compra: RD$%{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=results["hour"], y=-results["revenue_sell_usd"],
        name="Ingreso venta",
        line=dict(color="#22c55e", width=2),
        fill="tozeroy",
        fillcolor="rgba(34, 197, 94, 0.15)",
        hovertemplate="Hora %{x}<br>Venta: RD$%{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["net_cost_usd"],
        name="Costo neto",
        line=dict(color="#1e293b", width=2.5),
        mode="lines+markers",
        marker=dict(size=4),
        hovertemplate="Hora %{x}<br>Neto: RD$%{y:,.0f}<extra></extra>",
    ))

    fig.add_hline(y=0, line_color="#94a3b8", line_width=1, line_dash="dot")

    fig.update_layout(
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"},
        title=_title("Costos Horarios de Energía"),
        xaxis_title="Hora del día",
        yaxis_title="RD$",
        height=400,
        margin=dict(l=50, r=20, t=85, b=40),
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
        title=_title("Curtailment de Energía Renovable"),
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
            x=0.5, xanchor="center",
        ),
        showlegend=False,
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        margin=dict(t=50, b=40, l=60, r=60),
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
    
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1, line_dash="dot")
    
    fig.update_layout(
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"},
        title=_title("Potencia de Carga / Descarga BESS"),
        xaxis_title="Hora del día",
        yaxis_title="Potencia (kW)",
        height=400,
        margin=dict(l=50, r=20, t=85, b=40),
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
        title=_title("Desviación de Frecuencia"),
        xaxis_title="Hora del día",
        yaxis_title="Δf (Hz)",
        height=350,
    )
    
    return fig


def plot_energy_mix_donut(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de dona con leyenda lateral limpia y título centrado.
    """
    solar = results["pv_generation_kw"].sum()
    wind = results["wind_generation_kw"].sum()
    bess_net = results["bess_discharge_kw"].sum()
    grid = results["grid_buy_kw"].sum()
    diesel = results["diesel_generation_kw"].sum()
    gas = results["gas_generation_kw"].sum()

    raw = [
        ("Solar PV", solar, COLORS["solar"]),
        ("Eólica", wind, COLORS["wind"]),
        ("BESS", bess_net, COLORS["bess_discharge"]),
        ("Red", grid, COLORS["grid_buy"]),
        ("Diésel", diesel, COLORS["diesel"]),
        ("Gas Natural", gas, COLORS["gas"]),
    ]

    labels = []
    values = []
    colors = []
    for name, val, color in raw:
        if val > 0:
            labels.append(name)
            values.append(val)
            colors.append(color)

    total = sum(values)

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors, line=dict(color="#ffffff", width=2.5)),
        textinfo="percent",
        textfont=dict(size=12, color="#1e293b"),
        textposition="outside",
        hovertemplate="%{label}<br>%{value:.0f} kWh (%{percent})<extra></extra>",
        sort=False,
    )])

    fig.update_layout(
        title=dict(
            text="Composición del Suministro",
            font=dict(size=14, color="#1e293b"),
            x=0.5, xanchor="center",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.05,
            xanchor="center", x=0.5,
            font=dict(size=11),
        ),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        margin=dict(t=50, b=60, l=20, r=20),
        annotations=[dict(
            text=f"<b>{total:,.0f}</b><br>kWh",
            x=0.5, y=0.5, font_size=15, font_color="#1e293b",
            showarrow=False,
        )]
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
        title=_title("Costo Operativo Acumulado"),
        xaxis_title="Hora del día",
        yaxis_title="RD$ acumulados",
        height=380,
    )

    return fig


def plot_bess_energy_stored(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de energía almacenada en el BESS (kWh) a lo largo del día.
    """
    capacity = params["bess"]["energy_capacity_kwh"]
    energy_stored = results["soc"] * capacity

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=energy_stored,
        name="Energía almacenada",
        line=dict(color="#2563eb", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(37, 99, 235, 0.1)",
        hovertemplate="Hora %{x}<br>%{y:.1f} kWh<extra></extra>",
    ))

    # Líneas de referencia
    fig.add_hline(
        y=params["bess"]["min_soc"] * capacity,
        line_dash="dash", line_color="#dc2626", line_width=1,
        annotation_text=f"Mín: {params['bess']['min_soc'] * capacity:.0f} kWh",
    )
    fig.add_hline(
        y=params["bess"]["max_soc"] * capacity,
        line_dash="dash", line_color="#16a34a", line_width=1,
        annotation_text=f"Máx: {params['bess']['max_soc'] * capacity:.0f} kWh",
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=_title("Energía Almacenada en BESS"),
        xaxis_title="Hora del día",
        yaxis_title="Energía (kWh)",
        yaxis_range=[0, capacity],
        height=380,
    )

    return fig


def plot_bess_cycles(results: pd.DataFrame, params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de ciclos acumulados y throughput del BESS.
    """
    capacity = params["bess"]["energy_capacity_kwh"]
    charge_energy = results["bess_charge_kw"].values  # kWh (paso = 1h)
    discharge_energy = results["bess_discharge_kw"].values

    throughput = (charge_energy + discharge_energy) / 2  # medio ciclo
    cumulative_throughput = np.cumsum(throughput)
    equivalent_cycles = cumulative_throughput / capacity if capacity > 0 else cumulative_throughput * 0

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=equivalent_cycles,
        name="Ciclos equivalentes",
        line=dict(color="#7c3aed", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(124, 58, 237, 0.08)",
        hovertemplate="Hora %{x}<br>%{y:.3f} ciclos<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=_title("Ciclos Equivalentes Acumulados"),
        xaxis_title="Hora del día",
        yaxis_title="Ciclos equivalentes",
        height=380,
    )

    return fig


def plot_soh_evolution(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de evolución del estado de salud (SoH) durante el día.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["soh"] * 100,
        name="SoH",
        line=dict(color="#059669", width=2.5),
        mode="lines+markers",
        marker=dict(size=4),
        hovertemplate="Hora %{x}<br>SoH: %{y:.4f}%<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=_title("Evolución del Estado de Salud (SoH)"),
        xaxis_title="Hora del día",
        yaxis_title="SoH (%)",
        height=340,
    )

    return fig


def plot_capex_breakdown(params: Dict[str, Any]) -> go.Figure:
    """
    Gráfica de barras horizontales con el desglose del CAPEX por componente.
    """
    components = []
    values = []
    colors_list = []

    pv_val = params["renewable"]["pv_capacity_kw"] * params["investment"]["pv_cost_usd_kw"]
    wind_val = params["renewable"]["wind_capacity_kw"] * params["investment"]["wind_cost_usd_kw"]
    bess_val = params["bess"]["energy_capacity_kwh"] * params["investment"]["bess_cost_usd_kwh"]

    if pv_val > 0:
        components.append("Solar PV")
        values.append(pv_val)
        colors_list.append("#f59e0b")
    if wind_val > 0:
        components.append("Eólica")
        values.append(wind_val)
        colors_list.append("#10b981")
    if bess_val > 0:
        components.append("BESS")
        values.append(bess_val)
        colors_list.append("#3b82f6")

    if params["non_renewable"]["diesel_available"]:
        d_val = params["non_renewable"]["diesel_max_kw"] * params["investment"]["diesel_cost_usd_kw"]
        components.append("Diésel")
        values.append(d_val)
        colors_list.append("#64748b")
    if params["non_renewable"]["gas_available"]:
        g_val = params["non_renewable"]["gas_max_kw"] * params["investment"]["gas_cost_usd_kw"]
        components.append("Gas Natural")
        values.append(g_val)
        colors_list.append("#6366f1")

    total = sum(values)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=components,
        x=values,
        orientation="h",
        marker=dict(
            color=colors_list,
            line=dict(color="#ffffff", width=1.5),
        ),
        text=[f"RD${v:,.0f} ({v/total*100:.0f}%)" for v in values],
        textposition="inside",
        textfont=dict(size=11, color="#ffffff"),
        insidetextanchor="middle",
        hovertemplate="%{y}: RD$%{x:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=_title(f"Desglose del CAPEX — RD${total:,.0f}"),
        xaxis=dict(title="", showticklabels=False, showgrid=False),
        yaxis=dict(title="", tickfont=dict(size=12)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        height=300,
        margin=dict(t=60, b=20, l=80, r=20),
        showlegend=False,
    )

    return fig


def plot_daily_revenue_cost(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de barras comparando ingresos vs costos por hora.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["cost_buy_usd"],
        name="Costo compra",
        line=dict(color="#dc2626", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(220, 38, 38, 0.1)",
        hovertemplate="Hora %{x}<br>Compra: RD$%{y:,.2f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=results["hour"], y=results["revenue_sell_usd"],
        name="Ingreso venta",
        line=dict(color="#16a34a", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(22, 163, 74, 0.1)",
        hovertemplate="Hora %{x}<br>Venta: RD$%{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        **{k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"},
        title=_title("Costo de Compra vs Ingreso por Venta"),
        xaxis_title="Hora del día",
        yaxis_title="RD$",
        height=380,
        margin=dict(l=50, r=20, t=85, b=40),
    )

    return fig


def plot_cost_by_period(results: pd.DataFrame) -> go.Figure:
    """
    Gráfica de costo neto por periodo del día — dona para mostrar distribución.
    """
    periods = {
        "Madrugada (0–6h)": results[(results["hour"] >= 0) & (results["hour"] < 6)]["net_cost_usd"].sum(),
        "Mañana (6–12h)": results[(results["hour"] >= 6) & (results["hour"] < 12)]["net_cost_usd"].sum(),
        "Tarde (12–18h)": results[(results["hour"] >= 12) & (results["hour"] < 18)]["net_cost_usd"].sum(),
        "Noche (18–24h)": results[(results["hour"] >= 18) & (results["hour"] < 24)]["net_cost_usd"].sum(),
    }

    names = list(periods.keys())
    vals = list(periods.values())
    total = sum(vals)

    # Para la dona usamos valores absolutos (proporciones)
    abs_vals = [abs(v) for v in vals]
    period_colors = ["#1e3a5f", "#2563eb", "#60a5fa", "#93c5fd"]

    fig = go.Figure(data=[go.Pie(
        labels=names,
        values=abs_vals,
        hole=0.5,
        marker=dict(colors=period_colors, line=dict(color="#ffffff", width=2)),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11),
        hovertemplate="%{label}<br>RD$%{value:,.0f}<extra></extra>",
        sort=False,
    )])

    fig.update_layout(
        title=_title("Distribución de Costos por Periodo"),
        showlegend=False,
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#1e293b"),
        margin=dict(t=60, b=40, l=20, r=20),
        annotations=[dict(
            text=f"<b>RD${total:,.0f}</b><br>diario",
            x=0.5, y=0.5, font_size=13, font_color="#1e293b",
            showarrow=False,
        )]
    )

    return fig

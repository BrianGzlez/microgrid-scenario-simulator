"""
Módulo de cálculo de métricas e indicadores KPI para la microrred.
Incluye métricas económicas, técnicas, ambientales y de calidad de energía.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any

from src.utils import annualized_cost, calculate_capex


def calculate_kpis(results: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
    """
    Calcula todos los KPIs a partir de los resultados de simulación.
    
    Args:
        results: DataFrame con resultados horarios de la simulación.
        params: Diccionario completo de parámetros.
    
    Returns:
        Diccionario con todos los KPIs calculados.
    """
    # --- Energía (integrar potencia * 1 hora = energía en kWh) ---
    energy_bought = results["grid_buy_kw"].sum()  # kWh (paso = 1h)
    energy_sold = results["grid_sell_kw"].sum()
    renewable_used = (results["renewable_total_kw"].sum() -
                      results["curtailment_kw"].sum())
    renewable_curtailed = results["curtailment_kw"].sum()
    total_renewable_gen = results["renewable_total_kw"].sum()
    total_demand = results["total_demand_kw"].sum()
    diesel_energy = results["diesel_generation_kw"].sum()
    gas_energy = results["gas_generation_kw"].sum()
    
    # --- Costos ---
    grid = params["grid"]
    daily_cost = (energy_bought * grid["buy_price_usd_kwh"] -
                  energy_sold * grid["sell_price_usd_kwh"])
    
    capex = calculate_capex(params)
    inv = params["investment"]
    annual_equivalent_cost = annualized_cost(
        capex, inv["discount_rate"], inv["project_lifetime_years"]
    )
    
    # Costo diario equivalente incluyendo CAPEX anualizado
    daily_capex_equivalent = annual_equivalent_cost / 365.0
    total_daily_cost = daily_cost + daily_capex_equivalent
    
    # --- Emisiones ---
    total_emissions = results["emissions_total_kg"].sum()
    
    # --- Porcentaje renovable ---
    total_generation = (renewable_used + diesel_energy + gas_energy + energy_bought)
    if total_generation > 0:
        renewable_pct = renewable_used / total_generation
    else:
        renewable_pct = 0
    
    # --- Eficiencia global ---
    total_supply = (results["renewable_total_kw"].sum() + diesel_energy +
                    gas_energy + energy_bought)
    if total_supply > 0:
        global_efficiency = total_demand / total_supply
    else:
        global_efficiency = 0
    
    # --- Calidad de energía ---
    thd_avg = results["thd_pct"].mean()
    thd_max = results["thd_pct"].max()
    
    # --- Batería ---
    soc_min = results["soc"].min()
    soh_final = results["soh"].iloc[-1]
    
    # --- Índice global de desempeño ---
    performance_index = _calculate_performance_index(
        daily_cost=daily_cost,
        total_emissions=total_emissions,
        renewable_pct=renewable_pct,
        thd_max=thd_max,
        soc_min=soc_min,
        params=params
    )
    
    kpis = {
        "daily_cost_usd": daily_cost,
        "total_daily_cost_usd": total_daily_cost,
        "annual_equivalent_cost_usd": annual_equivalent_cost,
        "capex_usd": capex,
        "energy_bought_kwh": energy_bought,
        "energy_sold_kwh": energy_sold,
        "renewable_used_kwh": renewable_used,
        "renewable_curtailed_kwh": renewable_curtailed,
        "total_emissions_kg": total_emissions,
        "renewable_pct": renewable_pct,
        "global_efficiency": global_efficiency,
        "thd_avg_pct": thd_avg,
        "thd_max_pct": thd_max,
        "soc_min": soc_min,
        "soh_final": soh_final,
        "performance_index": performance_index,
        "diesel_energy_kwh": diesel_energy,
        "gas_energy_kwh": gas_energy,
        "unserved_energy_kwh": results["unserved_demand_kw"].sum(),
    }
    
    return kpis


def _calculate_performance_index(daily_cost: float, total_emissions: float,
                                  renewable_pct: float, thd_max: float,
                                  soc_min: float, params: Dict[str, Any]) -> float:
    """
    Calcula el índice global de desempeño normalizado [0-100].
    
    Índice = w_eco * I_eco + w_tec * I_tec + w_amb * I_amb + w_ren * I_ren
    
    Donde cada sub-índice se normaliza de 0 a 100:
    - I_eco: Menor costo es mejor (normalizado inversamente).
    - I_tec: THD bajo y SoC alto es mejor.
    - I_amb: Menores emisiones es mejor.
    - I_ren: Mayor % renovable es mejor.
    
    Args:
        daily_cost: Costo diario operativo.
        total_emissions: Emisiones totales diarias en kg CO2.
        renewable_pct: Porcentaje renovable (0-1).
        thd_max: THD máximo (%).
        soc_min: SoC mínimo alcanzado.
        params: Parámetros con pesos de optimización.
    
    Returns:
        Índice de desempeño [0-100].
    """
    weights = params["optimization_weights"]
    
    # Índice económico: menor costo mejor (referencia: 90000 RD$/día como peor caso)
    max_cost_ref = 90000.0
    idx_economic = max(0, min(100, 100 * (1 - daily_cost / max_cost_ref)))
    
    # Índice técnico: combinación de THD y SoC
    pq = params["power_quality"]
    thd_score = max(0, min(100, 100 * (1 - thd_max / (pq["thd_limit_pct"] * 2))))
    soc_score = max(0, min(100, soc_min * 100 / params["bess"]["max_soc"]))
    idx_technical = 0.6 * thd_score + 0.4 * soc_score
    
    # Índice ambiental: menores emisiones mejor (referencia: 1000 kg/día como peor caso)
    max_emissions_ref = 1000.0
    idx_environmental = max(0, min(100, 100 * (1 - total_emissions / max_emissions_ref)))
    
    # Índice renovable: mayor penetración mejor
    idx_renewable = renewable_pct * 100
    
    # Índice global ponderado
    performance = (weights["economic"] * idx_economic +
                   weights["technical"] * idx_technical +
                   weights["environmental"] * idx_environmental +
                   weights["renewable"] * idx_renewable)
    
    return max(0, min(100, performance))


def get_kpi_descriptions() -> Dict[str, str]:
    """
    Retorna descripciones de cada KPI para mostrar en el dashboard.
    
    Returns:
        Diccionario con nombre del KPI y su descripción.
    """
    return {
        "daily_cost_usd": "Costo operativo diario neto (compra - venta de energía)",
        "total_daily_cost_usd": "Costo diario total incluyendo CAPEX anualizado",
        "annual_equivalent_cost_usd": "Costo anualizado equivalente del CAPEX total",
        "capex_usd": "Inversión de capital total del proyecto",
        "energy_bought_kwh": "Energía total comprada de la red principal en el día",
        "energy_sold_kwh": "Energía total vendida a la red principal en el día",
        "renewable_used_kwh": "Energía renovable efectivamente utilizada",
        "renewable_curtailed_kwh": "Energía renovable desperdiciada (curtailment)",
        "total_emissions_kg": "Emisiones totales de CO₂ en el día",
        "renewable_pct": "Porcentaje de la demanda cubierta con renovables",
        "global_efficiency": "Relación demanda servida / energía total generada",
        "thd_avg_pct": "Distorsión armónica total promedio",
        "thd_max_pct": "Distorsión armónica total máxima",
        "soc_min": "Estado de carga mínimo alcanzado por la batería",
        "soh_final": "Estado de salud de la batería al final del día",
        "performance_index": "Índice global de desempeño ponderado (0-100)",
    }

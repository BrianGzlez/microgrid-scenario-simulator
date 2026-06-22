"""
Módulo de gestión de escenarios.
Permite guardar, comparar y exportar múltiples escenarios de simulación.
"""

import pandas as pd
from typing import Dict, Any, List


def save_scenario(scenario_name: str, kpis: Dict[str, float],
                  params: Dict[str, Any], saved_scenarios: List[Dict]) -> List[Dict]:
    """
    Guarda un escenario en la lista de escenarios guardados.
    
    Args:
        scenario_name: Nombre del escenario.
        kpis: KPIs calculados del escenario.
        params: Parámetros del escenario.
        saved_scenarios: Lista existente de escenarios guardados.
    
    Returns:
        Lista actualizada de escenarios guardados.
    """
    scenario_data = {
        "name": scenario_name,
        "daily_cost_usd": kpis["daily_cost_usd"],
        "total_daily_cost_usd": kpis["total_daily_cost_usd"],
        "annual_equivalent_cost_usd": kpis["annual_equivalent_cost_usd"],
        "capex_usd": kpis["capex_usd"],
        "energy_bought_kwh": kpis["energy_bought_kwh"],
        "energy_sold_kwh": kpis["energy_sold_kwh"],
        "renewable_pct": kpis["renewable_pct"],
        "total_emissions_kg": kpis["total_emissions_kg"],
        "thd_max_pct": kpis["thd_max_pct"],
        "soc_min": kpis["soc_min"],
        "soh_final": kpis["soh_final"],
        "performance_index": kpis["performance_index"],
        "pv_kw": params["renewable"]["pv_capacity_kw"],
        "wind_kw": params["renewable"]["wind_capacity_kw"],
        "bess_kwh": params["bess"]["energy_capacity_kwh"],
        "num_evs": params["demand"]["num_evs"],
    }
    
    saved_scenarios.append(scenario_data)
    return saved_scenarios


def get_comparison_table(saved_scenarios: List[Dict]) -> pd.DataFrame:
    """
    Genera una tabla comparativa de escenarios guardados.
    
    Args:
        saved_scenarios: Lista de escenarios guardados.
    
    Returns:
        DataFrame con la comparación de escenarios.
    """
    if not saved_scenarios:
        return pd.DataFrame()
    
    df = pd.DataFrame(saved_scenarios)
    
    # Renombrar columnas para presentación
    column_names = {
        "name": "Escenario",
        "daily_cost_usd": "Costo Diario (USD)",
        "total_daily_cost_usd": "Costo Total Diario (USD)",
        "annual_equivalent_cost_usd": "CAE (USD/año)",
        "capex_usd": "CAPEX (USD)",
        "energy_bought_kwh": "E. Comprada (kWh)",
        "energy_sold_kwh": "E. Vendida (kWh)",
        "renewable_pct": "% Renovable",
        "total_emissions_kg": "Emisiones (kg CO₂)",
        "thd_max_pct": "THD Máx (%)",
        "soc_min": "SoC Mín",
        "soh_final": "SoH Final",
        "performance_index": "Índice Global",
        "pv_kw": "PV (kW)",
        "wind_kw": "Eólica (kW)",
        "bess_kwh": "BESS (kWh)",
        "num_evs": "# EVs",
    }
    
    df = df.rename(columns=column_names)
    return df


def export_scenarios_csv(saved_scenarios: List[Dict]) -> str:
    """
    Exporta los escenarios guardados como CSV string.
    
    Args:
        saved_scenarios: Lista de escenarios guardados.
    
    Returns:
        String con contenido CSV.
    """
    df = get_comparison_table(saved_scenarios)
    return df.to_csv(index=False)


def export_results_csv(results: pd.DataFrame) -> str:
    """
    Exporta los resultados horarios como CSV string.
    
    Args:
        results: DataFrame con resultados horarios.
    
    Returns:
        String con contenido CSV.
    """
    return results.to_csv(index=False)

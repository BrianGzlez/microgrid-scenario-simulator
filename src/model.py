"""
Modelo de simulación de microrred multinodal.
Ejecuta la simulación hora a hora durante 24 horas, calculando flujos de energía,
estado de batería, interacción con red, emisiones y calidad de energía.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from src.utils import (
    solar_generation_profile,
    wind_generation_profile,
    demand_profile,
    ev_demand_profile,
)


def run_simulation(params: Dict[str, Any], scenario_seed: int = 42) -> pd.DataFrame:
    """
    Ejecuta la simulación completa de la microrred para 24 horas.
    
    Lógica de despacho (por hora):
    1. Calcular generación renovable (solar + eólica).
    2. Calcular demanda total (base + EV).
    3. Calcular balance neto = generación - demanda.
    4. Si hay excedente:
       a. Cargar BESS hasta capacidad disponible.
       b. Vender a la red hasta límite.
       c. Curtailment del resto.
    5. Si hay déficit:
       a. Descargar BESS.
       b. Usar generadores no renovables si disponibles.
       c. Comprar de la red.
       d. Si aún hay déficit, es demanda no servida.
    6. Calcular emisiones, costos, THD, voltaje y frecuencia.
    
    Args:
        params: Diccionario completo de parámetros.
        scenario_seed: Semilla para generación estocástica.
    
    Returns:
        DataFrame con resultados horarios detallados.
    """
    hours = params["scenario"]["horizon_hours"]
    ren = params["renewable"]
    bess_params = params["bess"]
    dem = params["demand"]
    grid = params["grid"]
    nr = params["non_renewable"]
    pq = params["power_quality"]
    
    # --- Generar perfiles ---
    solar_profile = solar_generation_profile(hours)
    wind_prof = wind_generation_profile(
        hours, ren["wind_factor"], ren["renewable_variability"], seed=scenario_seed
    )
    base_dem = demand_profile(
        hours, dem["base_demand_kw"], dem["demand_variability"], seed=scenario_seed + 1
    )
    ev_dem = ev_demand_profile(
        hours, dem["num_evs"], dem["ev_charger_power_kw"],
        dem["ev_simultaneity_factor"], seed=scenario_seed + 2
    )
    
    # Generación renovable en kW
    pv_gen = ren["pv_capacity_kw"] * solar_profile * ren["solar_irradiance_factor"]
    wind_gen = ren["wind_capacity_kw"] * wind_prof
    
    # Demanda total
    total_demand = base_dem + ev_dem
    
    # --- Inicializar arrays de resultados ---
    soc = np.zeros(hours + 1)
    soc[0] = bess_params["initial_soc"]
    soh = np.zeros(hours + 1)
    soh[0] = bess_params["initial_soh"]
    
    bess_charge = np.zeros(hours)
    bess_discharge = np.zeros(hours)
    grid_buy = np.zeros(hours)
    grid_sell = np.zeros(hours)
    curtailment = np.zeros(hours)
    diesel_gen = np.zeros(hours)
    gas_gen = np.zeros(hours)
    unserved = np.zeros(hours)
    
    bess_capacity = bess_params["energy_capacity_kwh"]
    max_charge = bess_params["max_charge_power_kw"]
    max_discharge = bess_params["max_discharge_power_kw"]
    min_soc = bess_params["min_soc"]
    max_soc = bess_params["max_soc"]
    eta_charge = bess_params["charge_efficiency"]
    eta_discharge = bess_params["discharge_efficiency"]
    
    # --- Simulación hora a hora ---
    for t in range(hours):
        renewable_total = pv_gen[t] + wind_gen[t]
        net_balance = renewable_total - total_demand[t]
        
        if net_balance >= 0:
            # Excedente renovable
            surplus = net_balance
            
            # 1. Cargar BESS
            available_capacity = (max_soc - soc[t]) * bess_capacity
            charge_possible = min(surplus, max_charge, available_capacity / eta_charge)
            if bess_capacity > 0:
                bess_charge[t] = charge_possible
                soc[t + 1] = soc[t] + (charge_possible * eta_charge) / bess_capacity
            else:
                bess_charge[t] = 0
                soc[t + 1] = soc[t]
            surplus -= charge_possible
            
            # 2. Vender a la red
            sell_possible = min(surplus, grid["max_sell_kw"])
            grid_sell[t] = sell_possible
            surplus -= sell_possible
            
            # 3. Curtailment
            curtailment[t] = surplus
            
        else:
            # Déficit
            deficit = -net_balance
            
            # 1. Descargar BESS
            available_energy = (soc[t] - min_soc) * bess_capacity
            discharge_possible = min(deficit, max_discharge, available_energy * eta_discharge)
            if bess_capacity > 0:
                bess_discharge[t] = discharge_possible
                soc[t + 1] = soc[t] - (discharge_possible / eta_discharge) / bess_capacity
            else:
                bess_discharge[t] = 0
                soc[t + 1] = soc[t]
            deficit -= discharge_possible
            
            # 2. Generadores no renovables
            if nr["diesel_available"] and deficit > 0:
                diesel_possible = min(deficit, nr["diesel_max_kw"])
                diesel_gen[t] = diesel_possible
                deficit -= diesel_possible
            
            if nr["gas_available"] and deficit > 0:
                gas_possible = min(deficit, nr["gas_max_kw"])
                gas_gen[t] = gas_possible
                deficit -= gas_possible
            
            # 3. Comprar de la red
            buy_possible = min(deficit, grid["max_buy_kw"])
            grid_buy[t] = buy_possible
            deficit -= buy_possible
            
            # 4. Demanda no servida
            unserved[t] = deficit
        
        # Si no hubo cambio de SoC por excedente/déficit (edge case)
        if net_balance >= 0:
            pass  # ya se actualizó arriba
        
        # Degradación de SoH (simplificada)
        # Cada ciclo completo degrada ~0.02% del SoH
        cycle_depth = abs(soc[t + 1] - soc[t])
        soh[t + 1] = soh[t] - cycle_depth * 0.0002  # degradación simplificada
    
    # --- Calcular métricas de calidad de energía ---
    thd = _calculate_thd(hours, ev_dem, bess_charge, bess_discharge, total_demand, pq)
    voltage = _calculate_voltage(hours, net_balance_arr=(pv_gen + wind_gen - total_demand),
                                  grid_buy=grid_buy, grid_sell=grid_sell, pq=pq,
                                  num_nodes=params["scenario"]["num_nodes"],
                                  seed=scenario_seed + 3)
    frequency_dev = _calculate_frequency_deviation(
        hours, grid_buy, grid_sell, total_demand, pq, seed=scenario_seed + 4
    )
    
    # --- Calcular emisiones ---
    emissions_diesel = diesel_gen * nr["diesel_emission_factor"]
    emissions_gas = gas_gen * nr["gas_emission_factor"]
    emissions_solar = pv_gen * nr["solar_emission_factor"]
    emissions_wind = wind_gen * nr["wind_emission_factor"]
    emissions_total = emissions_diesel + emissions_gas + emissions_solar + emissions_wind
    
    # --- Calcular costos horarios ---
    cost_buy = grid_buy * grid["buy_price_usd_kwh"]
    revenue_sell = grid_sell * grid["sell_price_usd_kwh"]
    net_cost = cost_buy - revenue_sell
    
    # --- Construir DataFrame ---
    results = pd.DataFrame({
        "hour": np.arange(hours),
        "pv_generation_kw": pv_gen,
        "wind_generation_kw": wind_gen,
        "renewable_total_kw": pv_gen + wind_gen,
        "base_demand_kw": base_dem,
        "ev_demand_kw": ev_dem,
        "total_demand_kw": total_demand,
        "bess_charge_kw": bess_charge,
        "bess_discharge_kw": bess_discharge,
        "soc": soc[1:],
        "soh": soh[1:],
        "grid_buy_kw": grid_buy,
        "grid_sell_kw": grid_sell,
        "diesel_generation_kw": diesel_gen,
        "gas_generation_kw": gas_gen,
        "curtailment_kw": curtailment,
        "unserved_demand_kw": unserved,
        "thd_pct": thd,
        "voltage_pu": voltage,
        "frequency_deviation_hz": frequency_dev,
        "emissions_diesel_kg": emissions_diesel,
        "emissions_gas_kg": emissions_gas,
        "emissions_solar_kg": emissions_solar,
        "emissions_wind_kg": emissions_wind,
        "emissions_total_kg": emissions_total,
        "cost_buy_usd": cost_buy,
        "revenue_sell_usd": revenue_sell,
        "net_cost_usd": net_cost,
    })
    
    return results


def run_stochastic_simulation(params: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta múltiples escenarios estocásticos y retorna el promedio y todos los resultados.
    
    Args:
        params: Diccionario completo de parámetros.
    
    Returns:
        Tuple con (DataFrame promedio, DataFrame con todos los escenarios).
    """
    n_scenarios = params["scenario"]["num_stochastic_scenarios"]
    all_results = []
    
    for s in range(n_scenarios):
        result = run_simulation(params, scenario_seed=42 + s * 7)
        result["scenario_id"] = s
        all_results.append(result)
    
    all_df = pd.concat(all_results, ignore_index=True)
    
    # Promediar por hora
    numeric_cols = all_df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ["hour", "scenario_id"]]
    avg_df = all_df.groupby("hour")[numeric_cols].mean().reset_index()
    
    return avg_df, all_df


def _calculate_thd(hours: int, ev_demand: np.ndarray,
                   bess_charge: np.ndarray, bess_discharge: np.ndarray,
                   total_demand: np.ndarray, pq: Dict) -> np.ndarray:
    """
    Calcula THD aproximado hora a hora.
    El THD aumenta con:
    - Mayor proporción de carga EV (armónicos de convertidores).
    - Mayor actividad del BESS (convertidores de potencia).
    - Menor demanda total (menor dilución armónica).
    
    Args:
        hours: Número de horas.
        ev_demand: Demanda EV en kW.
        bess_charge: Carga BESS en kW.
        bess_discharge: Descarga BESS en kW.
        total_demand: Demanda total en kW.
        pq: Parámetros de calidad de energía.
    
    Returns:
        Array con THD (%) por hora.
    """
    thd_base = pq["thd_base_ev_pct"]
    ev_harmonic = pq["ev_harmonic_content_pct"]
    
    thd = np.zeros(hours)
    for t in range(hours):
        if total_demand[t] > 0:
            # Contribución EV al THD
            ev_ratio = ev_demand[t] / total_demand[t]
            # Contribución BESS (convertidores)
            bess_activity = (bess_charge[t] + bess_discharge[t]) / max(total_demand[t], 1)
            # THD total
            thd[t] = thd_base + ev_ratio * ev_harmonic + bess_activity * 2.0
        else:
            thd[t] = thd_base
    
    return np.clip(thd, 0, 20)


def _calculate_voltage(hours: int, net_balance_arr: np.ndarray,
                       grid_buy: np.ndarray, grid_sell: np.ndarray,
                       pq: Dict, num_nodes: int, seed: int) -> np.ndarray:
    """
    Calcula voltaje nodal promedio aproximado.
    El voltaje se desvía de 1.0 p.u. cuando hay:
    - Alta inyección renovable (sobrevoltaje).
    - Alta demanda sin generación (subvoltaje).
    
    Args:
        hours: Número de horas.
        net_balance_arr: Balance neto (generación - demanda).
        grid_buy: Compra de red.
        grid_sell: Venta a red.
        pq: Parámetros de calidad de energía.
        num_nodes: Número de nodos.
        seed: Semilla para ruido.
    
    Returns:
        Array con voltaje promedio (p.u.) por hora.
    """
    rng = np.random.default_rng(seed)
    voltage = np.ones(hours)
    
    # Normalizar el balance neto para estimar desviación de voltaje
    max_abs = max(np.max(np.abs(net_balance_arr)), 1)
    normalized_balance = net_balance_arr / max_abs
    
    for t in range(hours):
        # Sobrevoltaje por excedente, subvoltaje por déficit
        deviation = normalized_balance[t] * 0.03
        # Ruido por variabilidad entre nodos
        node_noise = rng.normal(0, 0.005)
        voltage[t] = 1.0 + deviation + node_noise
    
    return np.clip(voltage, pq["voltage_min_pu"] - 0.02, pq["voltage_max_pu"] + 0.02)


def _calculate_frequency_deviation(hours: int, grid_buy: np.ndarray,
                                    grid_sell: np.ndarray,
                                    total_demand: np.ndarray,
                                    pq: Dict, seed: int) -> np.ndarray:
    """
    Calcula desviación de frecuencia aproximada.
    La frecuencia se desvía más cuando:
    - Hay desbalance potencia generada vs demandada.
    - Hay cambios bruscos en generación/demanda.
    
    Args:
        hours: Número de horas.
        grid_buy: Compra de red.
        grid_sell: Venta a red.
        total_demand: Demanda total.
        pq: Parámetros de calidad de energía.
        seed: Semilla para ruido.
    
    Returns:
        Array con desviación de frecuencia (Hz) por hora.
    """
    rng = np.random.default_rng(seed)
    freq_dev = np.zeros(hours)
    max_dev = pq["max_frequency_deviation_hz"]
    
    for t in range(hours):
        # Desviación proporcional al desbalance relativo
        if total_demand[t] > 0:
            imbalance_ratio = (grid_buy[t] - grid_sell[t]) / total_demand[t]
        else:
            imbalance_ratio = 0
        base_dev = imbalance_ratio * max_dev * 0.5
        noise = rng.normal(0, max_dev * 0.1)
        freq_dev[t] = base_dev + noise
    
    return np.clip(freq_dev, -max_dev, max_dev)

"""
Utilidades generales para el simulador de microrredes.
Funciones auxiliares de formato, validación y cálculos comunes.
"""

import numpy as np
from typing import Dict, Any


def validate_params(params: Dict[str, Any]) -> bool:
    """
    Valida que los parámetros esenciales estén dentro de rangos físicamente coherentes.
    
    Args:
        params: Diccionario con todos los parámetros de simulación.
    
    Returns:
        True si los parámetros son válidos.
    
    Raises:
        ValueError si algún parámetro es inválido.
    """
    if params["renewable"]["pv_capacity_kw"] < 0:
        raise ValueError("La capacidad PV no puede ser negativa.")
    if params["renewable"]["wind_capacity_kw"] < 0:
        raise ValueError("La capacidad eólica no puede ser negativa.")
    if params["bess"]["energy_capacity_kwh"] < 0:
        raise ValueError("La capacidad BESS no puede ser negativa.")
    if params["bess"]["min_soc"] >= params["bess"]["max_soc"]:
        raise ValueError("SoC mínimo debe ser menor que SoC máximo.")
    if params["bess"]["initial_soc"] < params["bess"]["min_soc"]:
        raise ValueError("SoC inicial no puede ser menor que SoC mínimo.")
    if params["bess"]["initial_soc"] > params["bess"]["max_soc"]:
        raise ValueError("SoC inicial no puede ser mayor que SoC máximo.")
    
    weights = params["optimization_weights"]
    total_w = weights["economic"] + weights["technical"] + weights["environmental"] + weights["renewable"]
    if abs(total_w - 1.0) > 0.01:
        raise ValueError(f"Los pesos de optimización deben sumar 1.0 (actual: {total_w:.3f})")
    
    return True


def format_currency(value: float) -> str:
    """Formatea un valor como moneda USD."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Formatea un valor decimal como porcentaje."""
    return f"{value * 100:.1f}%"


def format_energy(value: float) -> str:
    """Formatea un valor de energía en kWh."""
    return f"{value:,.1f} kWh"


def format_power(value: float) -> str:
    """Formatea un valor de potencia en kW."""
    return f"{value:,.1f} kW"


def solar_generation_profile(hours: int = 24) -> np.ndarray:
    """
    Genera un perfil de generación solar tipo campana de Gauss centrado al mediodía.
    
    Args:
        hours: Número de horas en la simulación.
    
    Returns:
        Array normalizado [0, 1] con el perfil solar horario.
    """
    t = np.arange(hours)
    # Campana centrada en hora 12, sigma = 3 horas
    profile = np.exp(-0.5 * ((t - 12) / 3) ** 2)
    # Solo genera durante el día (horas 6-18 aprox.)
    profile[t < 5] = 0.0
    profile[t > 19] = 0.0
    return profile


def wind_generation_profile(hours: int = 24, wind_factor: float = 0.6,
                            variability: float = 0.15, seed: int = None) -> np.ndarray:
    """
    Genera un perfil de generación eólica con variabilidad estocástica.
    El viento tiende a ser más fuerte durante la noche y la madrugada.
    
    Args:
        hours: Número de horas.
        wind_factor: Factor base de capacidad eólica.
        variability: Desviación estándar del ruido.
        seed: Semilla para reproducibilidad.
    
    Returns:
        Array normalizado [0, 1] con el perfil eólico horario.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(hours)
    # Perfil base: mayor viento en noche/madrugada
    base = wind_factor * (1 + 0.2 * np.cos(2 * np.pi * (t - 3) / 24))
    noise = rng.normal(0, variability, hours)
    profile = np.clip(base + noise, 0, 1)
    return profile


def demand_profile(hours: int = 24, base_demand_kw: float = 600,
                   variability: float = 0.2, seed: int = None) -> np.ndarray:
    """
    Genera un perfil de demanda base con variabilidad y patrón diario típico.
    Picos en mañana (8-10) y tarde-noche (18-21).
    
    Args:
        hours: Número de horas.
        base_demand_kw: Demanda base promedio en kW.
        variability: Fracción de variabilidad.
        seed: Semilla para reproducibilidad.
    
    Returns:
        Array con demanda en kW para cada hora.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(hours)
    # Patrón diario: dos picos (mañana y noche)
    pattern = (0.7 + 0.15 * np.sin(2 * np.pi * (t - 6) / 12) +
               0.15 * np.sin(2 * np.pi * (t - 2) / 24))
    noise = rng.normal(0, variability * 0.5, hours)
    profile = base_demand_kw * (pattern + noise)
    return np.clip(profile, base_demand_kw * 0.3, base_demand_kw * 1.8)


def ev_demand_profile(hours: int = 24, num_evs: int = 40,
                      charger_power_kw: float = 7.4,
                      simultaneity: float = 0.35, seed: int = None) -> np.ndarray:
    """
    Genera un perfil de demanda de vehículos eléctricos.
    Mayor carga entre 17:00 y 23:00 (llegada a casa) y algo en la mañana.
    
    Args:
        hours: Número de horas.
        num_evs: Cantidad de vehículos eléctricos.
        charger_power_kw: Potencia promedio por cargador.
        simultaneity: Factor de simultaneidad.
        seed: Semilla para reproducibilidad.
    
    Returns:
        Array con demanda EV en kW para cada hora.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(hours)
    # Perfil de carga EV: pico en la noche
    ev_pattern = np.zeros(hours)
    ev_pattern[6:9] = 0.15  # Carga matutina ligera
    ev_pattern[9:17] = 0.05  # Día laboral bajo
    ev_pattern[17:23] = 0.7 + 0.3 * np.exp(-0.5 * ((t[17:23] - 20) / 1.5) ** 2)
    ev_pattern[23:] = 0.3  # Carga nocturna residual
    ev_pattern[0:6] = 0.2  # Madrugada
    
    noise = rng.normal(0, 0.05, hours)
    max_ev_demand = num_evs * charger_power_kw * simultaneity
    profile = max_ev_demand * np.clip(ev_pattern + noise, 0, 1)
    return profile


def annualized_cost(capex: float, discount_rate: float, lifetime_years: int) -> float:
    """
    Calcula el costo anual equivalente (CRF - Capital Recovery Factor).
    
    CAE = CAPEX * (i * (1+i)^n) / ((1+i)^n - 1)
    
    Args:
        capex: Inversión total de capital.
        discount_rate: Tasa de descuento (fracción).
        lifetime_years: Vida útil del proyecto en años.
    
    Returns:
        Costo anualizado en USD/año.
    """
    i = discount_rate
    n = lifetime_years
    if i == 0:
        return capex / n
    crf = (i * (1 + i) ** n) / ((1 + i) ** n - 1)
    return capex * crf


def calculate_capex(params: Dict[str, Any]) -> float:
    """
    Calcula el CAPEX total de la microrred.
    
    Args:
        params: Diccionario con todos los parámetros.
    
    Returns:
        CAPEX total en USD.
    """
    inv = params["investment"]
    ren = params["renewable"]
    bess = params["bess"]
    nr = params["non_renewable"]
    
    capex = (ren["pv_capacity_kw"] * inv["pv_cost_usd_kw"] +
             ren["wind_capacity_kw"] * inv["wind_cost_usd_kw"] +
             bess["energy_capacity_kwh"] * inv["bess_cost_usd_kwh"])
    
    if nr["diesel_available"]:
        capex += nr["diesel_max_kw"] * inv["diesel_cost_usd_kw"]
    if nr["gas_available"]:
        capex += nr["gas_max_kw"] * inv["gas_cost_usd_kw"]
    
    return capex

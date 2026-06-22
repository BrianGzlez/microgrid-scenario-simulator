"""
Módulo de optimización para la microrred.
Implementa un enfoque heurístico inspirado en GA-PSO para explorar
configuraciones óptimas de la microrred.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

from src.model import run_simulation
from src.metrics import calculate_kpis


def optimize_dispatch(params: Dict[str, Any], n_iterations: int = 10) -> Dict[str, Any]:
    """
    Optimización heurística simplificada del despacho.
    Explora variaciones en los parámetros de operación del BESS
    para encontrar la estrategia de despacho que maximiza el índice de desempeño.
    
    Este es un enfoque simplificado inspirado en PSO (Particle Swarm Optimization):
    - Cada partícula representa una estrategia de despacho (umbrales de SoC).
    - Se evalúa el rendimiento global.
    - Se actualiza hacia la mejor solución encontrada.
    
    Args:
        params: Parámetros base de la simulación.
        n_iterations: Número de iteraciones de búsqueda.
    
    Returns:
        Diccionario con los mejores parámetros encontrados y su rendimiento.
    """
    best_index = -1
    best_params = params.copy()
    
    rng = np.random.default_rng(123)
    
    # Explorar variaciones en umbrales de SoC para despacho
    for i in range(n_iterations):
        trial_params = _deep_copy_params(params)
        
        # Variar umbrales de operación BESS
        trial_params["bess"]["min_soc"] = np.clip(
            params["bess"]["min_soc"] + rng.uniform(-0.1, 0.1), 0.1, 0.4
        )
        trial_params["bess"]["max_soc"] = np.clip(
            params["bess"]["max_soc"] + rng.uniform(-0.1, 0.1), 0.7, 0.95
        )
        
        # Simular y evaluar
        results = run_simulation(trial_params, scenario_seed=42 + i)
        kpis = calculate_kpis(results, trial_params)
        
        if kpis["performance_index"] > best_index:
            best_index = kpis["performance_index"]
            best_params = trial_params
    
    return {
        "best_params": best_params,
        "best_performance_index": best_index,
    }


def sensitivity_analysis(params: Dict[str, Any], 
                         variable: str,
                         values: List[float]) -> pd.DataFrame:
    """
    Realiza un análisis de sensibilidad variando un parámetro específico.
    
    Args:
        params: Parámetros base.
        variable: Nombre del parámetro a variar (formato: "section.key").
        values: Lista de valores a evaluar.
    
    Returns:
        DataFrame con resultados para cada valor del parámetro.
    """
    results_list = []
    section, key = variable.split(".")
    
    for val in values:
        trial_params = _deep_copy_params(params)
        trial_params[section][key] = val
        
        try:
            sim_results = run_simulation(trial_params)
            kpis = calculate_kpis(sim_results, trial_params)
            kpis["parameter_value"] = val
            results_list.append(kpis)
        except Exception:
            continue
    
    return pd.DataFrame(results_list)


def _deep_copy_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Realiza una copia profunda del diccionario de parámetros.
    
    Args:
        params: Diccionario original.
    
    Returns:
        Copia independiente del diccionario.
    """
    import copy
    return copy.deepcopy(params)

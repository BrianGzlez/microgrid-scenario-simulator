# ⚡ Microgrid Scenario Simulator

Simulador interactivo de escenarios What-If para microrredes multinodales con generación renovable, almacenamiento BESS, vehículos eléctricos, interconexión con red principal, análisis económico, ambiental y de calidad de energía.

## 📋 Descripción del Proyecto

Este dashboard permite a investigadores y estudiantes explorar diferentes configuraciones de microrredes y evaluar su desempeño energético, económico, ambiental y técnico. El simulador ejecuta una simulación de despacho horario durante 24 horas, considerando:

- **Generación renovable**: Solar PV (perfil campana) y eólica (con variabilidad estocástica)
- **Almacenamiento BESS**: Carga/descarga con eficiencias, límites de SoC y degradación de SoH
- **Vehículos eléctricos**: Perfiles de carga con patrones temporales realistas
- **Red principal**: Compra y venta de energía con límites de potencia
- **Generación convencional**: Diésel y gas natural como respaldo
- **Calidad de energía**: THD, voltaje nodal y desviación de frecuencia

## 🚀 Instalación

### Requisitos previos
- Python 3.9 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

```bash
# Clonar o descargar el proyecto
cd microgrid-simulator

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## ▶️ Ejecución

```bash
streamlit run app.py
```

El dashboard se abrirá automáticamente en `http://localhost:8501`.

## 🎛️ Parámetros de Entrada

### 1. Escenario General
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Horizonte | 24 h | Periodo de simulación |
| Nodos | 5 | Número de nodos en la microrred |
| Escenarios estocásticos | 3 | Cantidad de realizaciones aleatorias |

### 2. Generación Renovable
| Parámetro | Default | Rango | Descripción |
|-----------|---------|-------|-------------|
| PV (kW) | 500 | 0–2000 | Capacidad solar instalada |
| Eólica (kW) | 300 | 0–2000 | Capacidad eólica instalada |
| Factor solar | 0.75 | 0–1 | Factor de aprovechamiento de irradiancia |
| Factor viento | 0.60 | 0–1 | Factor de capacidad eólico |
| Variabilidad | 0.15 | 0–0.50 | Desviación estándar del ruido renovable |

### 3. BESS
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Capacidad (kWh) | 1000 | Energía almacenable total |
| Potencia carga (kW) | 250 | Máxima potencia de carga |
| Potencia descarga (kW) | 250 | Máxima potencia de descarga |
| SoC inicial | 50% | Estado de carga al inicio |
| SoC mínimo | 20% | Límite inferior de operación |
| SoC máximo | 90% | Límite superior de operación |
| Eficiencia carga | 95% | Rendimiento del proceso de carga |
| Eficiencia descarga | 95% | Rendimiento del proceso de descarga |
| SoH inicial | 100% | Estado de salud al inicio |

### 4. Demanda y EVs
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Demanda base (kW) | 600 | Demanda promedio de la microrred |
| Variabilidad | 20% | Fluctuación de la demanda |
| Número EVs | 40 | Vehículos eléctricos conectados |
| Potencia cargador (kW) | 7.4 | Potencia promedio por punto de carga |
| Simultaneidad | 0.35 | Fracción de EVs cargando simultáneamente |

### 5. Red Principal
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Precio compra (USD/kWh) | 0.20 | Tarifa de compra de energía |
| Precio venta (USD/kWh) | 0.10 | Tarifa de venta de excedentes |
| Máx. compra (kW) | 1000 | Límite de potencia de importación |
| Máx. venta (kW) | 1000 | Límite de potencia de exportación |

### 6. No Renovables
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Diésel disponible | No | Habilitar generador diésel |
| Gas disponible | No | Habilitar generador gas natural |
| Factor emisión diésel | 0.75 kg CO₂/kWh | Emisiones por kWh generado |
| Factor emisión gas | 0.45 kg CO₂/kWh | Emisiones por kWh generado |
| Factor emisión solar | 0.05 kg CO₂/kWh | Emisiones ciclo de vida |
| Factor emisión eólica | 0.015 kg CO₂/kWh | Emisiones ciclo de vida |

### 7. Calidad de Energía
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| THD límite | 5% | Máximo THD permitido (IEEE 519) |
| THD base EV | 3% | THD base por convertidores EV |
| Armónico EV | 8% | Contenido armónico de cargadores |
| Voltaje mínimo | 0.95 p.u. | Límite inferior de voltaje |
| Voltaje máximo | 1.05 p.u. | Límite superior de voltaje |
| Frecuencia | 60 Hz | Frecuencia nominal del sistema |
| Desviación máx. | 0.5 Hz | Máxima desviación permitida |

### 8. Costos de Inversión
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Costo PV | 900 USD/kW | Inversión por kW solar |
| Costo eólico | 1300 USD/kW | Inversión por kW eólico |
| Costo BESS | 400 USD/kWh | Inversión por kWh de batería |
| Tasa descuento | 8% | Para cálculo de anualización |
| Vida útil | 20 años | Horizonte del proyecto |

### 9. Pesos de Optimización
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| Peso económico | 0.35 | Importancia del costo |
| Peso técnico | 0.25 | Importancia de calidad de energía |
| Peso ambiental | 0.25 | Importancia de emisiones |
| Peso renovable | 0.15 | Importancia de penetración renovable |

## 📊 Resultados y Métricas

### KPIs Principales
| KPI | Descripción |
|-----|-------------|
| Costo diario operativo | Costo neto de compra/venta de energía |
| Costo total diario | Incluye CAPEX anualizado |
| Energía comprada/vendida | kWh intercambiados con la red |
| % Renovable | Fracción de demanda cubierta con renovables |
| Emisiones CO₂ | Total de emisiones diarias |
| Curtailment | Energía renovable desperdiciada |
| THD promedio/máximo | Distorsión armónica |
| SoC mínimo | Profundidad de descarga máxima |
| SoH final | Degradación acumulada |
| Índice global | Desempeño ponderado 0-100 |

### Fórmulas Clave

**Costo diario operativo:**
```
Costo = E_comprada × Precio_compra - E_vendida × Precio_venta
```

**CAPEX total:**
```
CAPEX = PV_kW × Costo_PV + Wind_kW × Costo_Wind + BESS_kWh × Costo_BESS + ...
```

**Costo anual equivalente (CRF):**
```
CAE = CAPEX × [i(1+i)^n] / [(1+i)^n - 1]
```

**Emisiones totales:**
```
CO₂ = Σ(E_fuente × Factor_emisión_fuente) para cada fuente
```

**Índice global de desempeño:**
```
I = w_eco × I_eco + w_tec × I_tec + w_amb × I_amb + w_ren × I_ren
```

## 🏗️ Estructura del Proyecto

```
microgrid-simulator/
├── app.py                  # Dashboard principal Streamlit
├── requirements.txt        # Dependencias Python
├── README.md              # Este archivo
├── src/
│   ├── __init__.py        # Paquete fuente
│   ├── model.py           # Modelo de simulación horaria
│   ├── optimizer.py       # Optimización heurística (GA-PSO)
│   ├── scenarios.py       # Gestión de escenarios
│   ├── metrics.py         # Cálculo de KPIs
│   ├── plots.py           # Visualizaciones Plotly
│   └── utils.py           # Funciones auxiliares
└── data/
    ├── default_parameters.json  # Parámetros por defecto
    └── sample_results.csv       # Resultados de ejemplo
```

## ⚠️ Limitaciones del Modelo

1. **Simplificación del despacho**: El algoritmo de despacho es determinístico y secuencial (sin optimización global hora a hora).
2. **Flujo de potencia**: No se resuelve un flujo de potencia real; el voltaje es una aproximación empírica.
3. **THD simplificado**: El cálculo de THD es una estimación basada en proporciones de carga no lineal, no un análisis armónico real.
4. **Frecuencia**: La desviación de frecuencia es un modelo simplificado que no considera inercia del sistema ni respuesta de generadores.
5. **Degradación BESS**: El modelo de degradación es lineal simplificado; no considera temperatura, C-rate ni calendar aging.
6. **Red uniforme**: No modela impedancias de línea ni topología de red específica.
7. **Sin forecast**: No incluye predicción de generación/demanda; usa perfiles determinísticos con ruido.
8. **Paso temporal**: Resolución de 1 hora; no captura transitorios sub-horarios.

## 🔮 Posibles Mejoras Futuras

1. **Optimización GA-PSO completa**: Implementar algoritmo genético + PSO para optimización multi-objetivo del despacho.
2. **Flujo de potencia AC**: Integrar solver Newton-Raphson para cálculo preciso de voltajes y pérdidas.
3. **Modelo BESS avanzado**: Incluir efectos de temperatura, degradación no lineal y calendar aging.
4. **Predicción ML**: Agregar modelos de forecasting para generación renovable y demanda.
5. **Resolución temporal fina**: Simulación a 15 minutos o 5 minutos para capturar variabilidad intra-horaria.
6. **Mercado eléctrico**: Modelar tarifas dinámicas (TOU, RTP) y servicios auxiliares.
7. **Topología de red**: Modelar la red con impedancias, transformadores y configuración radial/anillada.
8. **Control de EV inteligente**: Incluir V2G (Vehicle-to-Grid) y smart charging.
9. **Análisis de confiabilidad**: Calcular SAIDI, SAIFI y otros índices de confiabilidad.
10. **Resiliencia**: Modelar operación en isla ante fallas de la red principal.
11. **Integración con datos reales**: Conectar con APIs meteorológicas y datos de consumo reales.
12. **Dashboard multi-usuario**: Agregar autenticación y persistencia en base de datos.

## 📖 Referencias

- IEEE 519-2022: Standard for Harmonic Control in Electric Power Systems
- IEC 61000: Electromagnetic Compatibility
- Lasseter, R.H. (2011). Smart Distribution: Coupled Microgrids.
- Olivares, D.E. et al. (2014). Trends in Microgrid Control.

## 📄 Licencia

Proyecto académico para investigación en microrredes y optimización energética.

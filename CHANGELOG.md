# Changelog

Todos los cambios notables del proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [2.0.0] — 2026-04-05

### 🚀 Novedades Principales

#### CLI Completo con Typer
- **Nuevo**: `cli.py` con comandos `scan`, `remediate` y `run`
- Visualización enriquecida con tablas `Rich` y paneles de resumen financiero
- Flag `--demo` para ejecución segura sin credenciales GCP
- Flag `--auto-apply` para remediación completamente autónoma
- Opción `--json` para exportar hallazgos como JSON estructurado
- Opciones `--project`, `--zone`, `--region`, `--output-dir`

#### Nuevos Tipos de Recursos Detectados
- **Compute**: VMs en estado TERMINATED (`scan_stopped_instances()`)
- **Compute**: Snapshots obsoletos (`scan_old_snapshots()`)
- **Networking**: Reglas de firewall excesivamente permisivas (`scan_overly_permissive_firewalls()`)
- **Storage**: Buckets vacíos e inactivos — nuevo módulo `StorageScanner`

#### Escaneo Multi-Zona y Multi-Región
- `ComputeScanner` y `NetworkScanner` ahora iteran sobre **todas** las zonas y regiones del proyecto si no se especifica una zona/región concreta
- Eliminando el punto ciego que dejaba recursos sin auditar en zonas secundarias

#### Resiliencia con Tenacity
- Todos los métodos de escaneo tienen `@retry` con backoff exponencial (3 intentos, 2-10s)
- Protección automática ante errores 429 (Rate Limit) de las APIs de GCP

#### Remediación Autónoma Real
- `TerraformGenerator.generate()` ahora acepta `List[IdleResource]` directamente
- Nuevo método `_execute_terraform()` que ejecuta `terraform init` + `terraform apply`
- Soporte para 6 tipos de recursos en los templates Jinja2

### 🏗️ Mejoras Arquitectónicas

#### Foundation

- **`models.py`**: `IdleResource` migrado de `@dataclass` a `pydantic.BaseModel`
  - Nuevos campos: `estimated_monthly_cost_usd`, `age_days`, `labels`
  - Validación automática de tipos, `.model_dump()`, `.model_copy()`
- **`config.py`** (nuevo): `EngineConfig` centralizado via `pydantic-settings`
  - Lee configuración desde variables de entorno o archivo `.env`
  - Elimina los `os.getenv()` dispersos en 3 módulos distintos
- **`analyzer.py`**: Eliminada serialización JSON innecesaria (`json.dumps`/`json.loads`)
  - `generate_report()` retorna `List[IdleResource]` directamente (type-safe)
  - Nuevo `generate_summary()` con estadísticas financieras de alto nivel
  - Enriquecimiento de costos automático por tipo de recurso
- **`logger.py`**: Logging mejorado
  - Colores en terminal via `colorlog`
  - Handler adicional para archivo `finops.log` (DEBUG completo)
- **`exceptions.py`**: Añadidas `RemediationError` y `ConfigurationError`

#### Templates Terraform
- `main.tf.j2`: Añadido bloque `terraform { required_providers }` y `required_version`
- `main.tf.j2`: Soporte para `google_compute_instance`, `google_compute_snapshot`, `google_storage_bucket`, `google_compute_firewall`
- `outputs.tf.j2` (nuevo): Lista todos los recursos detectados con su costo estimado

### 🧪 Tests
- Añadida suite completa con `pytest`:
  - `tests/conftest.py` — Fixtures compartidas para todos los tipos de recursos
  - `tests/test_models.py` — 7 tests para el modelo Pydantic
  - `tests/test_analyzer.py` — 10 tests para lógica de análisis y costos
  - `tests/test_generator.py` — 11 tests para la generación de Terraform

### 📦 Dependencias Nuevas

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `pydantic-settings` | `>=2.0.0` | Configuración centralizada |
| `typer[all]` | `>=0.9.0` | CLI framework |
| `tenacity` | `>=8.2.3` | Retries automáticos en APIs |
| `colorlog` | `>=6.7.0` | Logging colorizado |
| `google-cloud-storage` | `>=2.10.0` | API de Cloud Storage |
| `pytest` | `>=7.4.0` | Framework de testing |
| `pytest-mock` | `>=3.12.0` | Mocking en tests |

---

## [1.0.0] — 2026-03-22

### Lanzamiento inicial — Aleph Hackathon

- Pipeline básico: escaneo de discos desconectados e IPs no utilizadas
- Generación de código Terraform (`main.tf`, `variables.tf`)
- Modo DEMO para presentaciones sin credenciales GCP
- Logging básico con `logging.StreamHandler`

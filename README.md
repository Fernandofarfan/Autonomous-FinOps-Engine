# Autonomous FinOps Engine 🚀

> **Detecta · Analiza · Remedia** el desperdicio de costos en Google Cloud Platform de forma completamente autónoma.

Creado originalmente para el **Aleph Hackathon (Marzo 2026)** y evolucionado a motor production-ready.

---

## 🌟 ¿Qué hace?

Los entornos cloud generan "zombie costs" silenciosamente: discos desconectados, IPs estáticas sin usar, VMs detenidas, snapshots acumulados y buckets olvidados. El **Autonomous FinOps Engine**:

1. 🔍 **Escanea** tu entorno GCP en busca de recursos ociosos (multi-zona y multi-región)
2. 💰 **Analiza** el impacto financiero estimado por recurso y en total
3. 📄 **Genera** código Terraform listo para importar y destruir los recursos detectados
4. ⚡ **Remedia** de forma autónoma ejecutando `terraform apply` si se habilita `AUTO_APPLY`

---

## 🛠️ Tecnologías

| Categoría | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| GCP APIs | `google-cloud-compute`, `google-cloud-storage` |
| Validación | Pydantic v2 + pydantic-settings |
| CLI | Typer + Rich |
| Resiliencia | Tenacity (retries automáticos) |
| Logging | colorlog (colores en terminal) + archivo `finops.log` |
| Templating IaC | Jinja2 (Terraform HCL) |
| Tests | pytest + pytest-mock |

---

## 🚀 Quick Start

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Modo DEMO (sin credenciales GCP)

```bash
# Scan y reporte
python cli.py scan --demo

# Pipeline completo (scan + reporte + generar Terraform)
python cli.py run --demo

# Pipeline con reporte en JSON
python cli.py run --demo --json
```

### 3. Modo Real (con ADC configurado)

```bash
# Autenticarse con Google Cloud
gcloud auth application-default login

# Configurar variables de entorno
cp .env.example .env
# editar .env con tu GCP_PROJECT_ID

# Escanear todo el proyecto (multi-zona, multi-región)
python cli.py scan --project my-gcp-project

# Generar Terraform en directorio personalizado
python cli.py remediate --project my-gcp-project --output-dir ./mi_remediacion

# Pipeline completo + ejecutar Terraform automáticamente ⚠️
python cli.py run --project my-gcp-project --auto-apply
```

---

## 🎮 Comandos CLI

```
finops CLI:

  scan        Escanea el entorno GCP y muestra el reporte de recursos ociosos
  remediate   Genera código Terraform para remediar los recursos detectados
  run         Pipeline completo: Scan + Report + Remediation (+ Apply opcional)
```

### Opciones Globales

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--demo` | Datos ficticios para testing (sin GCP real) | `false` |
| `--project`, `-p` | GCP Project ID a escanear | `$GCP_PROJECT_ID` |
| `--zone`, `-z` | Zona específica (omitir = todas las zonas) | Todas |
| `--region`, `-r` | Región específica (omitir = todas las regiones) | Todas |
| `--output-dir`, `-o` | Directorio para los archivos `.tf` generados | `tf_output/` |
| `--auto-apply` | ⚠️ Ejecutar `terraform apply` automáticamente | `false` |
| `--json` | Exportar hallazgos en formato JSON (solo `run`) | `false` |

---

## ⚙️ Variables de Entorno

Copia `.env.example` a `.env` y configura:

| Variable | Descripción | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | ID del proyecto GCP objetivo | `my-finops-project` |
| `GCP_ZONE` | Zona específica (vacío = todas) | — |
| `GCP_REGION` | Región específica (vacío = todas) | — |
| `DEMO_MODE` | Modo demo sin GCP (`true`/`false`) | `false` |
| `AUTO_APPLY` | Ejecutar Terraform auto (`true`/`false`) | `false` |
| `MAX_DISK_AGE_DAYS` | Días sin uso para marcar disco como ocioso | `30` |
| `MAX_SNAPSHOT_AGE_DAYS` | Antigüedad en días para snapshots obsoletos | `60` |
| `MAX_STOPPED_INSTANCE_DAYS` | Días en TERMINATED para marcar VM | `14` |

---

## 🔍 Recursos Detectados

| Tipo de Recurso | Scanner | Condición de Detección |
|----------------|---------|----------------------|
| Disco Persistente | `ComputeScanner` | Sin VM adjunta |
| VM (Instancia) | `ComputeScanner` | Estado TERMINATED > N días |
| Snapshot | `ComputeScanner` | Antigüedad > N días |
| IP Estática | `NetworkScanner` | Status `RESERVED` (sin asignar) |
| Regla Firewall | `NetworkScanner` | Permite 0.0.0.0/0 a puertos SSH/RDP |
| Cloud Storage Bucket | `StorageScanner` | Vacío o sin actividad en 90 días |

---

## 📦 Estructura del Proyecto

```
finops_engine/
├── cli.py                  # 🎮 CLI principal (Typer)
├── main.py                 # Punto de entrada retrocompatible
├── requirements.txt        # Dependencias Python
├── .env.example            # Plantilla de configuración
│
├── foundation/             # 🧱 Core: modelos, config, logger, analyzer
│   ├── models.py           # IdleResource (Pydantic BaseModel)
│   ├── config.py           # EngineConfig centralizada (pydantic-settings)
│   ├── analyzer.py         # ResourceAnalyzer con enriquecimiento de costos
│   ├── logger.py           # Logger con colores + archivo finops.log
│   └── exceptions.py       # Jerarquía de excepciones del motor
│
├── compute/                # 🖥️ Escaneo de Compute Engine
│   └── scanner.py          # Discos, VMs detenidas, Snapshots (multi-zona)
│
├── networking/             # 🌐 Escaneo de Networking
│   └── scanner.py          # IPs estáticas, Reglas de firewall (multi-región)
│
├── storage/                # 🪣 Escaneo de Cloud Storage
│   └── scanner.py          # Buckets vacíos e inactivos
│
├── remediation/            # 🔧 Generador de IaC (Terraform)
│   ├── generator.py        # TerraformGenerator + ejecución autónoma
│   └── templates/
│       ├── main.tf.j2      # Template Terraform con import blocks
│       ├── variables.tf.j2 # Variables
│       └── outputs.tf.j2   # Outputs con resumen de costos
│
├── tf_output/              # 📁 Archivos .tf generados (auto-creado)
├── finops.log              # 📋 Log completo de ejecuciones (auto-creado)
│
└── tests/                  # 🧪 Suite de tests
    ├── conftest.py
    ├── test_models.py
    ├── test_analyzer.py
    └── test_generator.py
```

---

## 🧪 Tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con cobertura (instalar pytest-cov)
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## ⚠️ Seguridad — AUTO_APPLY

El flag `--auto-apply` ejecutará **`terraform apply -auto-approve`** en modo completamente desatendido:

- ✅ Solo disponible fuera del modo DEMO
- ✅ Requiere confirmación explícita en la terminal
- ✅ Requiere Terraform instalado en el PATH
- ❌ **No es reversible** — los recursos destruidos no se recuperan automáticamente
- 📋 Siempre revisa los archivos en `tf_output/` antes de usar esta opción

---

## 🎯 Checklist Hackathon (deadline: 22 Marzo 09:00 AM)

- [x] Pipeline funcional Scan → Analyze → Remediate
- [x] Modo DEMO seguro para demos
- [x] README completo
- [ ] Push a GitHub público
- [ ] Video demo (3 minutos)
- [ ] Enviar en DoraHacks

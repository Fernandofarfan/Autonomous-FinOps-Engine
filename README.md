# Autonomous FinOps Engine 🚀

Welcome to the **Autonomous FinOps Engine**, a robust backend application designed to optimize cloud costs by automatically scanning, analyzing, and remediating idle or unused resources in your Google Cloud Platform (GCP) environment. 

Created for the **Aleph Hackathon (March 2026)**.

## 🌟 Purpose
Cloud environments run efficiently only when strictly monitored. Left unchecked, abandoned compute instances, unattached disks, and unused IPs generate silent "zombie" costs. The FinOps Engine autonomously:
1. **Scans** your GCP environment for unattached disks and unused static IPs.
2. **Analyzes** the findings into a consolidated financial report.
3. **Remediates** by automatically generating ready-to-use Terraform code (`main.tf`, `variables.tf`) to gracefully import and destroy the idle resources.

## 🛠️ Technologies Used
- Python 3.10+
- GCP Compute Engine API / Application Default Credentials
- Terraform (IaC Generation)
- Jinja2 Templating
- Pydantic

## 🚀 Quick Start / Demo Mode
For the Hackathon showcase, you can run the engine in `DEMO_MODE`. This allows judges and teammates to test the entire pipeline safely without requiring live GCP credentials or risking actual infrastructure.

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Engine in DEMO mode

**Windows (PowerShell):**
```powershell
$env:DEMO_MODE="true"
python main.py
```

**Linux / Mac / Git Bash:**
```bash
DEMO_MODE="true" python main.py
```

### Checking the Results
After successful execution, check the newly created `tf_output/` directory! You will find autonomously generated `main.tf` and `variables.tf` files which contain the infrastructure code necessary to resolve the detected cloud waste.

## 📦 Project Structure
- `compute/`: Logic for scanning unattached disks.
- `networking/`: Logic for scanning unused external IPs.
- `foundation/`: Core object models, robust error handling, and structured logging.
- `remediation/`: Jinja2-based Terraform Infrastructure-as-Code generator.
- `tf_output/`: Your generated Terraform files will appear here.

## 🎯 Hackathon Submission Checklist (Deadline: March 22, 09:00 AM)
- [x] Minimum submission requirements met technically.
- [x] `README.md` created with project details.
- [ ] Push code to a public GitHub repository.
- [ ] Record a **3-minute Demo Video**.
- [ ] Submit everything via DoraHacks before the deadline!

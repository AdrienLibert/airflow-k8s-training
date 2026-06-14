# Airflow on Kubernetes (local)

## First-time setup

```bash
# 0. Generator deps (once, on your machine)
# Debian/Ubuntu blocks system-wide pip (PEP 668); use a venv:
sudo apt install python3-venv   # once, if `python3 -m venv` fails
python3 -m venv .venv
.venv/bin/pip install -r dags/scripts/requirements.txt

# 1. Build the Airflow platform image
./config/build-image.sh

# 2. Install Airflow via Helm
./config/deploy-platform.sh

# 3. Build task images and import them into worker nodes
./dags/load-image.sh

# 4. Generate Python DAGs from YAML and publish to the volume
./dags/scripts/publish-dags.sh
```

## Runtime

```mermaid
sequenceDiagram
    participant UI as Airflow UI
    participant Sched as Scheduler
    participant Worker as Worker
    participant KPO as KubernetesPodOperator
    participant Pod as hello-world-tasks pod

    UI->>Sched: trigger DAG
    Sched->>Worker: queue tasks
    Worker->>KPO: run get_hello / get_world
    KPO->>Pod: start pod with hello-world-tasks:0.1.0
    Pod-->>KPO: stdout → XCom
    KPO->>Pod: start print_message (with XCom args)
    Pod-->>KPO: "Hello World!"
```

## Redeploy task code

```bash
# 1. Edit dags/dags/definitions/images
#    hello_world_k8s_dag = 0.1.1

# 2. Build + load new task image into worker nodes
./dags/load-image.sh

# 3. Regenerate + publish DAGs
./dags/scripts/publish-dags.sh
```

## DAG authoring

- Edit YAML in `dags/dags/definitions/*.yaml`
- Pin task image tags in `dags/dags/definitions/images`
- `dags/scripts/publish-dags.sh` renders `dags/dags/templates/dag.py.j2` into `dags/dags/generated/*.py`, then copies those files to `/opt/airflow/dags/` on the dag-processor pod

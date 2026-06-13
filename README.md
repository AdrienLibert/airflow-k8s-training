# Airflow on Kubernetes (local)

## First-time setup

```bash
# 1. Build the Airflow platform image
./config/build-image.sh

# 2. Install Airflow via Helm
./config/deploy-platform.sh

# 3. Build task images and import them into worker nodes
./dags/load-image.sh

# 4. Copy DAG YAML + loader into the dag-processor pod
./config/deploy-dags.sh
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
# 1. Edit dags/dags/definitions/versions
#    hello_world_k8s_dag = 0.1.1

# 2. Build + load new task image into worker nodes
./dags/load-image.sh

# 3. Redeploy DAG YAML (substitutes new {{ version }})
./config/deploy-dags.sh
```

from datetime import datetime

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.sdk import dag


@dag(
    dag_id="hello_world_k8s_dag",
    start_date=datetime(2026, 6, 10),
    schedule="@daily",
    catchup=False,
    tags=["example", "k8s"],
)
def hello_world_k8s_dag():
    get_hello = KubernetesPodOperator(
        task_id="get_hello",
        namespace="airflow",
        image="host.docker.internal:5000/hello-world-tasks:0.0.1",
        image_pull_policy="IfNotPresent",
        cmds=["python", "-m", "tasks.get_hello"],
        get_logs=True,
        is_delete_operator_pod=True,
        do_xcom_push=True,
        in_cluster=True,
    )
    get_world = KubernetesPodOperator(
        task_id="get_world",
        namespace="airflow",
        image="host.docker.internal:5000/hello-world-tasks:0.0.1",
        image_pull_policy="IfNotPresent",
        cmds=["python", "-m", "tasks.get_world"],
        get_logs=True,
        is_delete_operator_pod=True,
        do_xcom_push=True,
        in_cluster=True,
    )
    print_message = KubernetesPodOperator(
        task_id="print_message",
        namespace="airflow",
        image="host.docker.internal:5000/hello-world-tasks:0.0.1",
        image_pull_policy="IfNotPresent",
        cmds=["python", "-m", "tasks.print_message"],
        arguments=[
            "{{ ti.xcom_pull(task_ids='get_hello') }}",
            "{{ ti.xcom_pull(task_ids='get_world') }}"
        ],
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
    )

    [get_hello, get_world] >> print_message


hello_world_k8s_dag()

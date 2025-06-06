import threading
import hashlib
from utils.log import log
from db.tasks import get_all_tasks
from messaging.producer import send_message
import os

hostname = os.environ.get("HOSTNAME", "scheduler-0")
try:
    SCHEDULER_ID = int(hostname.split('-')[-1])
except Exception:
    SCHEDULER_ID = 0  # fallback

TOTAL_SCHEDULERS = int(os.environ.get("TOTAL_SCHEDULERS", "2"))  # Via env no YAML


def get_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)

def is_task_owned(task_id: str) -> bool:
    return (get_hash(task_id) % TOTAL_SCHEDULERS) == SCHEDULER_ID

def send_task_periodic(task):
    try:
        log(f"[scheduler-{SCHEDULER_ID}] Enviando tarefa: Nome: {task['task_name']}, Tipo: {task['task_type']}, ID (uuid): {task['task_id']} (id (db)={task['id']})")
        send_message({
            'task_name': task['task_name'],
            'task_id': task['task_id'],
            'type': task['task_type'],
            'payload': task['payload'],
        }, queue='tasks')
    except Exception as e:
        log(f"[scheduler-{SCHEDULER_ID}] ERRO ao enviar tarefa: {e}")
    finally:
        # Agenda o próximo disparo mesmo em caso de erro
        interval = task['interval_seconds']
        timer = threading.Timer(interval, send_task_periodic, args=(task,))
        timer.daemon = True
        timer.start()

def start_scheduler():
    tasks = get_all_tasks()
    my_tasks = [t for t in tasks if is_task_owned(t['task_id'])]

    log(f"[scheduler-{SCHEDULER_ID}] Gerenciando {len(my_tasks)} tarefas...")

    # Agenda disparo inicial imediato para cada tarefa
    for task in my_tasks:
        send_task_periodic(task)

if __name__ == "__main__":
    start_scheduler()
    # Mantém o programa vivo para os timers funcionarem
    threading.Event().wait()

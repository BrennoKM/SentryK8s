import json
from db.tasks import insert_task, get_db_id_by_task_uuid
from utils.log import log
from messaging.producer import send_message

def load_tasks_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data.get('tasks', [])

def send_to_schedulers(task):
    message = {
        'task_name': task['task_name'],
        'task_type': task['task_type'],
        'payload': task['payload'],
        'interval_seconds': task['interval_seconds'],
        'task_uuid': task['task_uuid'],
        'id': task['id']
    }
    try:
        send_message(message, exchange='new_task_exchange', routing_key='')
    except Exception as e:
        log(f"❌ Erro ao enviar tarefa '{task['task_name']}' para os schedulers: {str(e)}")
        raise

def insert_tasks(tasks, interval_override=None):
    inserted_ids = []
    for task in tasks:
        try:
            if interval_override is not None:
                task['interval_seconds'] = interval_override

            task_uuid = insert_task(
                task_name=task['task_name'],
                task_type=task['task_type'],
                payload_json=json.dumps(task['payload']),
                interval_seconds=task['interval_seconds']
            )
            task['task_uuid'] = task_uuid  # Adiciona o UUID gerado à tarefa
            try:
                db_id = get_db_id_by_task_uuid(task_uuid)
            except Exception as e:
                log(f"❌ Erro ao recuperar ID do banco para o task_uuid {task_uuid}: {str(e)}")
                db_id = None
            task['id'] = db_id
            try:
                send_to_schedulers(task)
            except Exception as e:
                log(f"❌ Erro ao enviar tarefa '{task['task_name']}' para os schedulers: {str(e)}")
                continue
            inserted_ids.append(task_uuid)
            log(f"✅ Tarefa '{task['task_name']}' inserida com id {task_uuid} (ID banco: {db_id})")
        except Exception as e:
            print(f"❌ Erro ao inserir tarefa '{task['task_name']}': {str(e)}")
    return inserted_ids

if __name__ == "__main__":
    import sys
    json_file = "tasks.json"
    interval_override = None

    if len(sys.argv) > 1:
        try:
            interval_override = int(sys.argv[1])
            print(f"Substituindo todos os intervalos para {interval_override} segundos.")
        except ValueError:
            print("O argumento deve ser um número inteiro representando o intervalo em segundos.")
            sys.exit(1)

    print(f"Carregando tarefas do arquivo {json_file}...")
    tasks = load_tasks_from_file(json_file)

    if not tasks:
        print("Nenhuma tarefa encontrada no arquivo.")
    else:
        print(f"Encontradas {len(tasks)} tarefas. Iniciando inserção...")
        inserted_ids = insert_tasks(tasks, interval_override)
        print(f"\nConcluído! {len(inserted_ids)} tarefas inseridas com sucesso.")
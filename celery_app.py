from celery_app import celery

@celery.task(bind=True)
def long_task(self, input_value):
    """Background task that runs a long computation."""
    total = 100
    for i in range(total):
        # Here you simulate some work being done
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'current': i, 'total': total})
    return {'current': 100, 'total': 100, 'status': 'Task completed!', 'result': 42}  # Example result

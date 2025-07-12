from routes.drive_routes import celery_app


# This ensures worker can discover tasks
celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.worker_main()

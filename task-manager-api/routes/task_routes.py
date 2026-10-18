from flask import Blueprint, jsonify, request


def create_task_blueprint(controller):
    task_bp = Blueprint("tasks", __name__)

    @task_bp.get("/tasks")
    def get_tasks():
        return jsonify(controller.list_tasks()), 200

    @task_bp.get("/tasks/<int:task_id>")
    def get_task(task_id):
        return jsonify(controller.get_task(task_id)), 200

    @task_bp.post("/tasks")
    def create_task():
        return jsonify(controller.create_task(request.get_json(silent=True))), 201

    @task_bp.put("/tasks/<int:task_id>")
    def update_task(task_id):
        return jsonify(controller.update_task(task_id, request.get_json(silent=True))), 200

    @task_bp.delete("/tasks/<int:task_id>")
    def delete_task(task_id):
        controller.delete_task(task_id)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    @task_bp.get("/tasks/search")
    def search_tasks():
        results = controller.search_tasks(
            request.args.get("q", ""),
            request.args.get("status", ""),
            request.args.get("priority", ""),
            request.args.get("user_id", ""),
        )
        return jsonify(results), 200

    @task_bp.get("/tasks/stats")
    def task_stats():
        return jsonify(controller.stats()), 200

    return task_bp

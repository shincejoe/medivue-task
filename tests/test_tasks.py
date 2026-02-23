import pytest
from datetime import date, timedelta


def future_date(days=10):
    return (date.today() + timedelta(days=days)).isoformat()


def past_date(days=1):
    return (date.today() - timedelta(days=days)).isoformat()


# ────────────────────────────────────────────────
#  POST /tasks — Task creation
# ────────────────────────────────────────────────

class TestCreateTask:
    def test_create_minimal_task(self, client):
        resp = client.post("/tasks", json={"title": "Buy milk"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Buy milk"
        assert data["priority"] == 3          # default
        assert data["completed"] is False
        assert data["tags"] == []

    def test_create_full_task(self, client):
        resp = client.post("/tasks", json={
            "title": "Doctor appointment",
            "description": "Annual check-up",
            "priority": 5,
            "due_date": future_date(),
            "tags": ["health", "urgent"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["priority"] == 5
        tag_names = {t["name"] for t in data["tags"]}
        assert tag_names == {"health", "urgent"}

    def test_create_task_missing_title(self, client):
        resp = client.post("/tasks", json={"priority": 3})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "Validation Failed"
        assert "title" in body["details"]

    def test_create_task_empty_title(self, client):
        resp = client.post("/tasks", json={"title": "   "})
        assert resp.status_code == 422

    def test_create_task_title_too_long(self, client):
        resp = client.post("/tasks", json={"title": "x" * 201})
        assert resp.status_code == 422

    def test_create_task_priority_out_of_range(self, client):
        resp = client.post("/tasks", json={"title": "Task", "priority": 6})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "Validation Failed"

    def test_create_task_priority_zero(self, client):
        resp = client.post("/tasks", json={"title": "Task", "priority": 0})
        assert resp.status_code == 422

    def test_create_task_past_due_date(self, client):
        resp = client.post("/tasks", json={"title": "Task", "due_date": past_date()})
        assert resp.status_code == 422
        body = resp.json()
        assert "due_date" in body["details"]

    def test_create_task_tags_normalized(self, client):
        resp = client.post("/tasks", json={"title": "Task", "tags": ["Work", "URGENT"]})
        assert resp.status_code == 201
        tag_names = {t["name"] for t in resp.json()["tags"]}
        assert tag_names == {"work", "urgent"}

    def test_create_task_duplicate_tag_reuses_existing(self, client):
        client.post("/tasks", json={"title": "Task A", "tags": ["shared"]})
        resp = client.post("/tasks", json={"title": "Task B", "tags": ["shared"]})
        data = resp.json()
        assert any(t["name"] == "shared" for t in data["tags"])


# ────────────────────────────────────────────────
#  GET /tasks — Listing and filtering
# ────────────────────────────────────────────────

class TestListTasks:
    def _seed(self, client):
        client.post("/tasks", json={"title": "Low priority", "priority": 1, "tags": ["work"]})
        client.post("/tasks", json={"title": "High priority", "priority": 5, "tags": ["urgent", "work"]})
        client.post("/tasks", json={"title": "Completed", "priority": 3, "tags": ["personal"]})
        # mark third task completed
        tasks = client.get("/tasks").json()["tasks"]
        task_id = next(t["id"] for t in tasks if t["title"] == "Completed")
        client.patch(f"/tasks/{task_id}", json={"completed": True})

    def test_list_all_tasks(self, client):
        self._seed(client)
        resp = client.get("/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["tasks"]) == 3

    def test_filter_by_completed_true(self, client):
        self._seed(client)
        resp = client.get("/tasks?completed=true")
        data = resp.json()
        assert data["total"] == 1
        assert all(t["completed"] for t in data["tasks"])

    def test_filter_by_completed_false(self, client):
        self._seed(client)
        resp = client.get("/tasks?completed=false")
        data = resp.json()
        assert data["total"] == 2
        assert all(not t["completed"] for t in data["tasks"])

    def test_filter_by_priority(self, client):
        self._seed(client)
        resp = client.get("/tasks?priority=5")
        data = resp.json()
        assert data["total"] == 1
        assert data["tasks"][0]["title"] == "High priority"

    def test_filter_by_single_tag(self, client):
        self._seed(client)
        resp = client.get("/tasks?tags=urgent")
        data = resp.json()
        assert data["total"] == 1
        assert data["tasks"][0]["title"] == "High priority"

    def test_filter_by_multiple_tags_any_match(self, client):
        self._seed(client)
        resp = client.get("/tasks?tags=urgent,personal")
        data = resp.json()
        # Should return tasks with "urgent" OR "personal"
        assert data["total"] == 2
        titles = {t["title"] for t in data["tasks"]}
        assert titles == {"High priority", "Completed"}

    def test_filter_by_tag_work_matches_two(self, client):
        self._seed(client)
        resp = client.get("/tasks?tags=work")
        data = resp.json()
        assert data["total"] == 2

    def test_filter_nonexistent_tag(self, client):
        self._seed(client)
        resp = client.get("/tasks?tags=doesnotexist")
        assert resp.json()["total"] == 0

    def test_pagination_limit(self, client):
        self._seed(client)
        resp = client.get("/tasks?limit=2")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["tasks"]) == 2
        assert data["limit"] == 2

    def test_pagination_offset(self, client):
        self._seed(client)
        resp = client.get("/tasks?limit=2&offset=2")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["tasks"]) == 1

    def test_combined_filters(self, client):
        self._seed(client)
        resp = client.get("/tasks?completed=false&priority=5")
        data = resp.json()
        assert data["total"] == 1


# ────────────────────────────────────────────────
#  GET /tasks/{id}
# ────────────────────────────────────────────────

class TestGetTask:
    def test_get_existing_task(self, client):
        created = client.post("/tasks", json={"title": "Test"}).json()
        resp = client.get(f"/tasks/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_task(self, client):
        resp = client.get("/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "Not Found"

    def test_soft_deleted_task_not_found(self, client):
        created = client.post("/tasks", json={"title": "Delete me"}).json()
        client.delete(f"/tasks/{created['id']}")
        resp = client.get(f"/tasks/{created['id']}")
        assert resp.status_code == 404


# ────────────────────────────────────────────────
#  PATCH /tasks/{id} — Partial updates
# ────────────────────────────────────────────────

class TestUpdateTask:
    def test_patch_title_only(self, client):
        created = client.post("/tasks", json={"title": "Old title", "priority": 4}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"title": "New title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        assert data["priority"] == 4  # unchanged

    def test_patch_mark_completed(self, client):
        created = client.post("/tasks", json={"title": "Task"}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"completed": True})
        assert resp.json()["completed"] is True

    def test_patch_priority(self, client):
        created = client.post("/tasks", json={"title": "Task", "priority": 1}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"priority": 5})
        assert resp.json()["priority"] == 5

    def test_patch_tags_replaces_all(self, client):
        created = client.post("/tasks", json={"title": "Task", "tags": ["old"]}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"tags": ["new1", "new2"]})
        tag_names = {t["name"] for t in resp.json()["tags"]}
        assert tag_names == {"new1", "new2"}

    def test_patch_empty_body_changes_nothing(self, client):
        created = client.post("/tasks", json={"title": "Immutable", "priority": 2}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={})
        data = resp.json()
        assert data["title"] == "Immutable"
        assert data["priority"] == 2

    def test_patch_invalid_priority(self, client):
        created = client.post("/tasks", json={"title": "Task"}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"priority": 10})
        assert resp.status_code == 422

    def test_patch_past_due_date(self, client):
        created = client.post("/tasks", json={"title": "Task"}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"due_date": past_date()})
        assert resp.status_code == 422

    def test_patch_nonexistent_task(self, client):
        resp = client.patch("/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_patch_description(self, client):
        created = client.post("/tasks", json={"title": "Task"}).json()
        resp = client.patch(f"/tasks/{created['id']}", json={"description": "Now has a description"})
        assert resp.json()["description"] == "Now has a description"


# ────────────────────────────────────────────────
#  DELETE /tasks/{id}
# ────────────────────────────────────────────────

class TestDeleteTask:
    def test_soft_delete_returns_204(self, client):
        created = client.post("/tasks", json={"title": "To delete"}).json()
        resp = client.delete(f"/tasks/{created['id']}")
        assert resp.status_code == 204

    def test_deleted_task_excluded_from_list(self, client):
        created = client.post("/tasks", json={"title": "Gone"}).json()
        client.delete(f"/tasks/{created['id']}")
        tasks = client.get("/tasks").json()["tasks"]
        assert all(t["id"] != created["id"] for t in tasks)

    def test_delete_nonexistent_task(self, client):
        resp = client.delete("/tasks/99999")
        assert resp.status_code == 404

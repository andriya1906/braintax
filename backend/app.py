from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import math

app = Flask(__name__)
CORS(app)

CO2_PER_MINUTE = 1.5

co2_points = 45
session_active = False
active_task_id = None

user_profile = {
    "name": "User",
    "avatar_type": "calm"
}

group_scores = {
    "Group Math": 140,
    "Group OS": 120,
    "Group DSA": 110
}

user_group_contributions = {
    "Group Math": 0,
    "Group OS": 0,
    "Group DSA": 0
}

assigned_tasks = [
    {
        "id": 1,
        "title": "Math Problem Set",
        "created_by": "Team Leader",
        "category": "Math",
        "group_name": "Group Math",
        "scheduled_start": "2026-03-26T14:00",
        "scheduled_end": "2026-03-26T16:00",
        "status": "Pending",
        "started": False,
        "completed": False,
        "expired": False,
        "study_started_at": None,
        "study_seconds_total": 0,
        "points_earned": 0
    },
    {
        "id": 2,
        "title": "OS Quiz Prep",
        "created_by": "Team Leader",
        "category": "OS",
        "group_name": "Group OS",
        "scheduled_start": "2026-03-26T18:00",
        "scheduled_end": "2026-03-26T19:30",
        "status": "Pending",
        "started": False,
        "completed": False,
        "expired": False,
        "study_started_at": None,
        "study_seconds_total": 0,
        "points_earned": 0
    },
    {
        "id": 3,
        "title": "DSA Practice Sprint",
        "created_by": "Team Leader",
        "category": "DSA",
        "group_name": "Group DSA",
        "scheduled_start": "2026-03-26T20:00",
        "scheduled_end": "2026-03-26T21:00",
        "status": "Pending",
        "started": False,
        "completed": False,
        "expired": False,
        "study_started_at": None,
        "study_seconds_total": 0,
        "points_earned": 0
    }
]

restricted_apps = [
    {
        "id": 1,
        "name": "Instagram",
        "icon": "📷",
        "limit_minutes": 20,
        "used_seconds": 0,
        "is_open": False,
        "opened_at": None
    },
    {
        "id": 2,
        "name": "YouTube",
        "icon": "▶️",
        "limit_minutes": 30,
        "used_seconds": 0,
        "is_open": False,
        "opened_at": None
    },
    {
        "id": 3,
        "name": "Twitter/X",
        "icon": "🐦",
        "limit_minutes": 15,
        "used_seconds": 0,
        "is_open": False,
        "opened_at": None
    }
]

doom_scroll_total_seconds = 0


def now_local():
    return datetime.now()


def parse_dt(dt_str):
    return datetime.fromisoformat(dt_str)


def round_half_up(value):
    return int(math.floor(value + 0.5))


def clamp_non_negative(value):
    return max(0, round_half_up(value))


def round_points(value):
    return round_half_up(value)


def get_avatar_state():
    global co2_points

    if co2_points >= 70:
        return "happy", "bright"
    elif co2_points >= 30:
        return "neutral", "normal"
    return "sad", "dim"


def seconds_to_points(seconds_value):
    if seconds_value <= 0:
        return 0
    minutes = seconds_value / 60
    return round_points(minutes * CO2_PER_MINUTE)


def get_current_window_task():
    current_time = now_local()

    for task in assigned_tasks:
        if task["completed"] or task["expired"]:
            continue

        start_dt = parse_dt(task["scheduled_start"])
        end_dt = parse_dt(task["scheduled_end"])

        if start_dt <= current_time <= end_dt:
            return task

    return None


def sync_task_statuses():
    global co2_points, active_task_id, session_active

    current_time = now_local()

    for task in assigned_tasks:
        if task["completed"]:
            continue

        end_dt = parse_dt(task["scheduled_end"])

        if current_time > end_dt and not task["expired"]:
            if task["started"] and task["study_started_at"] is not None:
                effective_end = end_dt
                elapsed_seconds = int((effective_end - task["study_started_at"]).total_seconds())

                if elapsed_seconds > 0:
                    task["study_seconds_total"] += elapsed_seconds
                    points = seconds_to_points(elapsed_seconds)
                    task["points_earned"] += points

                    co2_points += points

                    group_name = task["group_name"]
                    group_scores[group_name] += points
                    user_group_contributions[group_name] += points

                task["study_started_at"] = None

            if task["started"]:
                active_task_id = None
                session_active = False
                task["started"] = False

            task["expired"] = True
            task["status"] = "Expired"


def get_live_app_used_seconds(app_item):
    used_seconds = app_item["used_seconds"]

    if app_item["is_open"] and app_item["opened_at"] is not None:
        used_seconds += int((now_local() - app_item["opened_at"]).total_seconds())

    limit_seconds = app_item["limit_minutes"] * 60
    return min(used_seconds, limit_seconds)


def serialize_app(app_item):
    used_seconds = get_live_app_used_seconds(app_item)
    limit_seconds = app_item["limit_minutes"] * 60
    remaining_seconds = max(0, limit_seconds - used_seconds)

    return {
        "id": app_item["id"],
        "name": app_item["name"],
        "icon": app_item["icon"],
        "limit_minutes": app_item["limit_minutes"],
        "used_seconds": used_seconds,
        "remaining_seconds": remaining_seconds,
        "is_open": app_item["is_open"]
    }


def serialize_task(task):
    current_time = now_local()
    start_dt = parse_dt(task["scheduled_start"])
    end_dt = parse_dt(task["scheduled_end"])

    live_study_seconds = task["study_seconds_total"]
    live_points = task["points_earned"]

    if task["started"] and task["study_started_at"] is not None:
        effective_end = min(current_time, end_dt)
        elapsed_seconds = int((effective_end - task["study_started_at"]).total_seconds())
        if elapsed_seconds > 0:
            live_study_seconds += elapsed_seconds
            live_points = task["points_earned"] + seconds_to_points(elapsed_seconds)

    return {
        "id": task["id"],
        "title": task["title"],
        "created_by": task["created_by"],
        "category": task["category"],
        "group_name": task["group_name"],
        "scheduled_start": task["scheduled_start"],
        "scheduled_end": task["scheduled_end"],
        "status": task["status"],
        "started": task["started"],
        "completed": task["completed"],
        "expired": task["expired"],
        "study_seconds_total": live_study_seconds,
        "points_earned": live_points,
        "window_active": start_dt <= current_time <= end_dt,
        "user_group_contribution": user_group_contributions[task["group_name"]]
    }


@app.route("/")
def home():
    return "Backend is running!"


@app.route("/avatar-data")
def avatar_data():
    sync_task_statuses()
    mood, room_state = get_avatar_state()

    return jsonify({
        "name": user_profile["name"],
        "avatar_type": user_profile["avatar_type"],
        "co2_points": co2_points,
        "mood": mood,
        "room_state": room_state,
        "session_active": session_active,
        "doom_scroll_total_seconds": doom_scroll_total_seconds
    })


@app.route("/profile")
def profile():
    return jsonify(user_profile)


@app.route("/update-profile", methods=["POST"])
def update_profile():
    data = request.get_json()

    if "name" in data and data["name"].strip():
        user_profile["name"] = data["name"].strip()

    if "avatar_type" in data:
        user_profile["avatar_type"] = data["avatar_type"]

    return jsonify({
        "message": "Profile updated successfully",
        "profile": user_profile
    })


@app.route("/leaderboard")
def leaderboard():
    leaderboard_data = [
        {"name": "Aisha", "points": 120},
        {"name": "Rahul", "points": 95},
        {"name": user_profile["name"], "points": co2_points},
        {"name": "Neha", "points": 60}
    ]

    leaderboard_data.sort(key=lambda x: x["points"], reverse=True)
    return jsonify(leaderboard_data)


@app.route("/group-leaderboard")
def group_leaderboard():
    data = []

    for group_name, score in group_scores.items():
        data.append({
            "group_name": group_name,
            "points": score,
            "your_contribution": user_group_contributions[group_name]
        })

    data.sort(key=lambda x: x["points"], reverse=True)
    return jsonify(data)


@app.route("/assigned-tasks")
def get_assigned_tasks():
    sync_task_statuses()

    return jsonify({
        "tasks": [serialize_task(task) for task in assigned_tasks],
        "active_task_id": active_task_id
    })


@app.route("/update-task-window", methods=["POST"])
def update_task_window():
    data = request.get_json()
    task_id = data.get("task_id")
    scheduled_start = data.get("scheduled_start")
    scheduled_end = data.get("scheduled_end")

    if not scheduled_start or not scheduled_end:
        return jsonify({"message": "Start and end time are required"}), 400

    start_dt = parse_dt(scheduled_start)
    end_dt = parse_dt(scheduled_end)

    if end_dt <= start_dt:
        return jsonify({"message": "End time must be after start time"}), 400

    for task in assigned_tasks:
        if task["id"] == task_id:
            task["scheduled_start"] = scheduled_start
            task["scheduled_end"] = scheduled_end

            if not task["completed"]:
                task["expired"] = False
                task["status"] = "Pending"
                task["started"] = False
                task["study_started_at"] = None

            return jsonify({
                "message": f'{task["title"]} window updated successfully'
            })

    return jsonify({"message": "Task not found"}), 404


@app.route("/start-task", methods=["POST"])
def start_task():
    global active_task_id, session_active

    sync_task_statuses()

    data = request.get_json()
    task_id = data.get("task_id")

    if active_task_id is not None:
        return jsonify({"message": "Another task is already in progress"}), 400

    for app_item in restricted_apps:
        if app_item["is_open"]:
            return jsonify({"message": "Close the restricted app before starting a study session"}), 400

    current_time = now_local()

    for task in assigned_tasks:
        if task["id"] == task_id:
            if task["completed"]:
                return jsonify({"message": "This task is already completed"}), 400

            if task["expired"]:
                return jsonify({"message": "This task window has already expired"}), 400

            start_dt = parse_dt(task["scheduled_start"])
            end_dt = parse_dt(task["scheduled_end"])

            if current_time < start_dt:
                return jsonify({"message": "This task window has not started yet"}), 400

            if current_time > end_dt:
                task["expired"] = True
                task["status"] = "Expired"
                return jsonify({"message": "This task window has already ended"}), 400

            task["started"] = True
            task["study_started_at"] = current_time
            task["status"] = "In Progress"
            active_task_id = task_id
            session_active = True

            return jsonify({
                "message": f'{task["title"]} started successfully'
            })

    return jsonify({"message": "Task not found"}), 404


@app.route("/end-task", methods=["POST"])
def end_task():
    global active_task_id, session_active, co2_points

    sync_task_statuses()

    data = request.get_json()
    task_id = data.get("task_id")

    if active_task_id != task_id:
        return jsonify({"message": "This task is not currently active"}), 400

    current_time = now_local()

    for task in assigned_tasks:
        if task["id"] == task_id:
            if not task["started"] or task["study_started_at"] is None:
                return jsonify({"message": "This task has not started properly"}), 400

            end_dt = parse_dt(task["scheduled_end"])
            effective_end = min(current_time, end_dt)
            elapsed_seconds = int((effective_end - task["study_started_at"]).total_seconds())

            if elapsed_seconds < 0:
                elapsed_seconds = 0

            task["study_seconds_total"] += elapsed_seconds
            earned_points = seconds_to_points(elapsed_seconds)
            task["points_earned"] += earned_points

            co2_points += earned_points
            group_name = task["group_name"]
            group_scores[group_name] += earned_points
            user_group_contributions[group_name] += earned_points

            task["started"] = False
            task["study_started_at"] = None
            active_task_id = None
            session_active = False

            if current_time <= end_dt:
                task["completed"] = True
                task["status"] = "Completed"
                message = f'{task["title"]} completed within the time window'
            else:
                task["expired"] = True
                task["status"] = "Expired"
                message = f'{task["title"]} expired after the time window'

            return jsonify({
                "message": message,
                "earned_points": earned_points,
                "co2_points": co2_points,
                "group_points": group_scores[group_name],
                "your_group_contribution": user_group_contributions[group_name]
            })

    return jsonify({"message": "Task not found"}), 404


@app.route("/start-session", methods=["POST"])
def start_session():
    global session_active

    for app_item in restricted_apps:
        if app_item["is_open"]:
            return jsonify({"message": "Close the restricted app before starting a study session"}), 400

    session_active = True
    return jsonify({"message": "Solo study session started"})


@app.route("/end-session", methods=["POST"])
def end_session():
    global session_active

    if session_active:
        session_active = False
        return jsonify({"message": "Solo study session ended"})

    return jsonify({"message": "No active solo study session"})


@app.route("/restricted-apps")
def get_restricted_apps():
    sync_task_statuses()

    return jsonify({
        "apps": [serialize_app(app_item) for app_item in restricted_apps],
        "session_active": session_active,
        "doom_scroll_total_seconds": doom_scroll_total_seconds
    })


@app.route("/set-app-limit", methods=["POST"])
def set_app_limit():
    data = request.get_json()
    app_id = data.get("app_id")
    limit_minutes = data.get("limit_minutes")

    if limit_minutes is None:
        return jsonify({"message": "Time limit is required"}), 400

    try:
        limit_minutes = int(limit_minutes)
    except ValueError:
        return jsonify({"message": "Time limit must be a number"}), 400

    if limit_minutes < 0:
        return jsonify({"message": "Time limit cannot be negative"}), 400

    for app_item in restricted_apps:
        if app_item["id"] == app_id:
            used_minutes = math.ceil(app_item["used_seconds"] / 60) if app_item["used_seconds"] > 0 else 0
            if limit_minutes < used_minutes:
                return jsonify({"message": "New limit cannot be less than already used time"}), 400

            app_item["limit_minutes"] = limit_minutes
            return jsonify({
                "message": f'{app_item["name"]} limit updated to {limit_minutes} minutes'
            })

    return jsonify({"message": "App not found"}), 404


@app.route("/toggle-restricted-app", methods=["POST"])
def toggle_restricted_app():
    global doom_scroll_total_seconds, co2_points

    sync_task_statuses()

    data = request.get_json()
    app_id = data.get("app_id")

    selected_app = None
    for app_item in restricted_apps:
        if app_item["id"] == app_id:
            selected_app = app_item
            break

    if selected_app is None:
        return jsonify({"message": "App not found"}), 404

    if not selected_app["is_open"]:
        if session_active:
            return jsonify({
                "message": "Restricted apps cannot be opened during an active study session"
            }), 400

        for app_item in restricted_apps:
            if app_item["is_open"]:
                return jsonify({
                    "message": "Close the currently open restricted app first"
                }), 400

        used_seconds = selected_app["used_seconds"]
        limit_seconds = selected_app["limit_minutes"] * 60

        if used_seconds >= limit_seconds:
            return jsonify({
                "message": f'{selected_app["name"]} has no remaining allowed time'
            }), 400

        selected_app["is_open"] = True
        selected_app["opened_at"] = now_local()

        return jsonify({
            "message": f'{selected_app["name"]} opened successfully',
            "app": serialize_app(selected_app)
        })

    elapsed_seconds = 0
    if selected_app["opened_at"] is not None:
        elapsed_seconds = int((now_local() - selected_app["opened_at"]).total_seconds())

    max_remaining = (selected_app["limit_minutes"] * 60) - selected_app["used_seconds"]
    elapsed_seconds = max(0, min(elapsed_seconds, max_remaining))

    selected_app["used_seconds"] += elapsed_seconds
    selected_app["is_open"] = False
    selected_app["opened_at"] = None

    doom_scroll_total_seconds += elapsed_seconds
    penalty_points = seconds_to_points(elapsed_seconds)

    co2_points = clamp_non_negative(co2_points - penalty_points)

    current_task_window = get_current_window_task()
    group_penalty_applied = False
    affected_group = None

    if current_task_window is not None:
        affected_group = current_task_window["group_name"]
        group_scores[affected_group] = clamp_non_negative(group_scores[affected_group] - penalty_points)
        user_group_contributions[affected_group] = clamp_non_negative(
            user_group_contributions[affected_group] - penalty_points
        )
        group_penalty_applied = True

    message = f'{selected_app["name"]} closed. Doom scroll penalty applied: -{penalty_points} CO₂ points.'

    if group_penalty_applied:
        message += f' Group penalty also applied to {affected_group}.'

    return jsonify({
        "message": message,
        "penalty_points": penalty_points,
        "co2_points": co2_points,
        "group_penalty_applied": group_penalty_applied,
        "affected_group": affected_group,
        "app": serialize_app(selected_app)
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
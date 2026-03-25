from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import math

app = Flask(__name__)
CORS(app)

# =========================================================
# DEMO USERS
# =========================================================
users = [
    {"id": 1, "name": "Andriya", "avatar_style": "focused", "co2_points": 120, "study_seconds": 0},
    {"id": 2, "name": "Aisha", "avatar_style": "calm", "co2_points": 90, "study_seconds": 0},
    {"id": 3, "name": "Rohan", "avatar_style": "energetic", "co2_points": 110, "study_seconds": 0},
]

current_user_id = 1

# =========================================================
# SOLO SESSION / RESTRICTED APPS STATE
# =========================================================
solo_session = {
    "active": False,
    "started_at": None
}

restricted_apps = [
    {
        "id": 1,
        "name": "Instagram",
        "icon": "📸",
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

# =========================================================
# GROUPS / CHATS / TASKS / SESSIONS
# =========================================================
groups = []
group_messages = {}
group_tasks = []
task_assignments = []
group_sessions = []
session_proofs = []

group_id_counter = 1
task_id_counter = 1
session_id_counter = 1
proof_id_counter = 1

# =========================================================
# HELPERS
# =========================================================
def now_dt():
    return datetime.now()

def now_str():
    return datetime.now().isoformat()

def find_user(user_id):
    return next((u for u in users if u["id"] == user_id), None)

def get_current_user():
    return find_user(current_user_id)

def find_group(group_id):
    return next((g for g in groups if g["id"] == group_id), None)

def find_task(task_id):
    return next((t for t in group_tasks if t["id"] == task_id), None)

def find_restricted_app(app_id):
    return next((a for a in restricted_apps if a["id"] == app_id), None)

def generate_join_code(group_name, group_id):
    cleaned = "".join(ch for ch in group_name.upper() if ch.isalnum())
    prefix = cleaned[:3] if cleaned else "GRP"
    return f"{prefix}{100 + group_id}"

def user_in_group(user_id, group):
    return any(member["user_id"] == user_id for member in group["members"])

def get_user_groups(user_id):
    return [group for group in groups if user_in_group(user_id, group)]

def round_up_half(value):
    return math.ceil(value)

def study_points_from_minutes(minutes):
    return round_up_half(minutes * 1.5)

def doom_points_from_minutes(minutes):
    return round_up_half(minutes * 1.5)

def get_avatar_mood(points):
    if points >= 70:
        return "happy"
    elif points >= 30:
        return "neutral"
    return "sad"

def get_room_state(points):
    if points >= 70:
        return "bright"
    elif points >= 30:
        return "normal"
    return "dim"

def get_total_doom_scroll_seconds():
    total = 0
    for app_item in restricted_apps:
        total += get_app_used_seconds(app_item)
    return total

def get_app_used_seconds(app_item):
    used = app_item["used_seconds"]
    if app_item["is_open"] and app_item["opened_at"]:
        opened_dt = datetime.fromisoformat(app_item["opened_at"])
        used += int((now_dt() - opened_dt).total_seconds())
    return used

def close_open_apps_and_apply_penalty():
    user = get_current_user()
    total_penalty_points = 0

    for app_item in restricted_apps:
        if app_item["is_open"] and app_item["opened_at"]:
            opened_dt = datetime.fromisoformat(app_item["opened_at"])
            elapsed_seconds = int((now_dt() - opened_dt).total_seconds())
            if elapsed_seconds < 0:
                elapsed_seconds = 0

            app_item["used_seconds"] += elapsed_seconds
            app_item["is_open"] = False
            app_item["opened_at"] = None

            penalty_minutes = elapsed_seconds / 60.0
            penalty_points = doom_points_from_minutes(penalty_minutes)
            total_penalty_points += penalty_points

    if total_penalty_points > 0 and user:
        user["co2_points"] -= total_penalty_points
        apply_group_penalty_if_active_window(user["id"], total_penalty_points)

    return total_penalty_points

def apply_group_penalty_if_active_window(user_id, penalty_points):
    user_groups = get_user_groups(user_id)

    for group in user_groups:
        has_active_task = False
        for task in group_tasks:
            if task["group_id"] == group["id"] and task_window_status(task) == "Active":
                has_active_task = True
                break

        if has_active_task:
            group["total_points"] = max(0, group["total_points"] - penalty_points)

def task_window_status(task):
    now = datetime.now()
    start = datetime.fromisoformat(task["scheduled_start"])
    end = datetime.fromisoformat(task["scheduled_end"])

    if now < start:
        return "Pending"
    elif start <= now <= end:
        return "Active"
    else:
        return "Expired"

def get_active_group_session(group_id, task_id=None):
    for session in group_sessions:
        if session["group_id"] == group_id and session["status"] == "active":
            if task_id is None or session["task_id"] == task_id:
                return session
    return None

def get_user_group_contribution(group_id, user_id):
    total = 0
    for assignment in task_assignments:
        task = find_task(assignment["task_id"])
        if task and task["group_id"] == group_id and assignment["user_id"] == user_id:
            total += assignment.get("points_earned", 0)
    return total

def get_group_member_leaderboard(group_id):
    group = find_group(group_id)
    if not group:
        return []

    result = []
    for member in group["members"]:
        contribution = get_user_group_contribution(group_id, member["user_id"])
        result.append({
            "user_id": member["user_id"],
            "name": member["name"],
            "role": member["role"],
            "points": contribution
        })

    result.sort(key=lambda x: x["points"], reverse=True)
    return result

def ensure_user_has_study_seconds(user):
    if "study_seconds" not in user:
        user["study_seconds"] = 0

# =========================================================
# CURRENT USER SUPPORT
# =========================================================
@app.route("/current-user", methods=["GET"])
def get_current_user_route():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404
    ensure_user_has_study_seconds(user)
    return jsonify(user)

@app.route("/set-current-user", methods=["POST"])
def set_current_user():
    global current_user_id

    data = request.json
    user_id = data.get("user_id")

    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    ensure_user_has_study_seconds(user)
    current_user_id = user_id
    return jsonify({"message": f"Current user set to {user['name']}", "user": user})

# =========================================================
# AVATAR / PROFILE / SOLO SESSION
# =========================================================
@app.route("/avatar-data", methods=["GET"])
def avatar_data():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_has_study_seconds(user)

    return jsonify({
        "name": user["name"],
        "co2_points": user["co2_points"],
        "mood": get_avatar_mood(user["co2_points"]),
        "room_state": get_room_state(user["co2_points"]),
        "avatar_type": user["avatar_style"],
        "session_active": solo_session["active"],
        "doom_scroll_total_seconds": get_total_doom_scroll_seconds(),
        "study_total_seconds": user["study_seconds"]
    })

@app.route("/profile", methods=["GET"])
def profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_has_study_seconds(user)

    return jsonify({
        "name": user["name"],
        "avatar_type": user["avatar_style"]
    })

@app.route("/update-profile", methods=["POST"])
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    data = request.json
    name = data.get("name", "").strip()
    avatar_type = data.get("avatar_type", "").strip().lower()

    if not name:
        return jsonify({"message": "Name cannot be empty"}), 400

    if avatar_type not in ["calm", "energetic", "focused"]:
        return jsonify({"message": "Invalid avatar style"}), 400

    user["name"] = name
    user["avatar_style"] = avatar_type

    for group in groups:
        for member in group["members"]:
            if member["user_id"] == user["id"]:
                member["name"] = user["name"]

    return jsonify({"message": "Profile updated successfully"})

@app.route("/start-session", methods=["POST"])
def start_session():
    if solo_session["active"]:
        return jsonify({"message": "A solo session is already active"}), 400

    close_open_apps_and_apply_penalty()

    solo_session["active"] = True
    solo_session["started_at"] = now_str()

    return jsonify({"message": "Solo study session started"})

@app.route("/end-session", methods=["POST"])
def end_session():
    user = get_current_user()
    if not user:
        return jsonify({"message": "Current user not found"}), 404

    ensure_user_has_study_seconds(user)

    if not solo_session["active"] or not solo_session["started_at"]:
        return jsonify({"message": "No solo session is active"}), 400

    started_at = datetime.fromisoformat(solo_session["started_at"])
    elapsed_seconds = int((now_dt() - started_at).total_seconds())
    if elapsed_seconds < 0:
        elapsed_seconds = 0

    elapsed_minutes = elapsed_seconds / 60.0
    earned_points = study_points_from_minutes(elapsed_minutes)

    user["co2_points"] += earned_points
    user["study_seconds"] += elapsed_seconds

    solo_session["active"] = False
    solo_session["started_at"] = None

    return jsonify({
        "message": "Solo study session ended",
        "earned_points": earned_points,
        "study_seconds_added": elapsed_seconds
    })

# =========================================================
# RESTRICTED APPS
# =========================================================
@app.route("/restricted-apps", methods=["GET"])
def get_restricted_apps():
    apps_payload = []

    for app_item in restricted_apps:
        used_seconds = get_app_used_seconds(app_item)
        limit_seconds = app_item["limit_minutes"] * 60
        remaining_seconds = max(0, limit_seconds - used_seconds)

        if used_seconds >= limit_seconds and app_item["is_open"]:
            app_item["is_open"] = False
            app_item["opened_at"] = None

        apps_payload.append({
            "id": app_item["id"],
            "name": app_item["name"],
            "icon": app_item["icon"],
            "limit_minutes": app_item["limit_minutes"],
            "used_seconds": min(used_seconds, limit_seconds),
            "remaining_seconds": remaining_seconds,
            "is_open": app_item["is_open"]
        })

    return jsonify({
        "session_active": solo_session["active"],
        "doom_scroll_total_seconds": get_total_doom_scroll_seconds(),
        "apps": apps_payload
    })

@app.route("/set-app-limit", methods=["POST"])
def set_app_limit():
    data = request.json
    app_id = data.get("app_id")
    limit_minutes = data.get("limit_minutes")

    app_item = find_restricted_app(app_id)
    if not app_item:
        return jsonify({"message": "App not found"}), 404

    try:
        limit_minutes = int(limit_minutes)
    except:
        return jsonify({"message": "Limit must be a number"}), 400

    if limit_minutes < 0:
        return jsonify({"message": "Limit cannot be negative"}), 400

    app_item["limit_minutes"] = limit_minutes
    return jsonify({"message": f"{app_item['name']} limit updated successfully"})

@app.route("/toggle-restricted-app", methods=["POST"])
def toggle_restricted_app():
    user = get_current_user()
    if not user:
        return jsonify({"message": "Current user not found"}), 404

    ensure_user_has_study_seconds(user)

    data = request.json
    app_id = data.get("app_id")

    app_item = find_restricted_app(app_id)
    if not app_item:
        return jsonify({"message": "App not found"}), 404

    if app_item["is_open"]:
        opened_dt = datetime.fromisoformat(app_item["opened_at"])
        elapsed_seconds = int((now_dt() - opened_dt).total_seconds())
        if elapsed_seconds < 0:
            elapsed_seconds = 0

        app_item["used_seconds"] += elapsed_seconds
        app_item["is_open"] = False
        app_item["opened_at"] = None

        penalty_minutes = elapsed_seconds / 60.0
        penalty_points = doom_points_from_minutes(penalty_minutes)
        user["co2_points"] -= penalty_points
        apply_group_penalty_if_active_window(user["id"], penalty_points)

        return jsonify({
            "message": f"{app_item['name']} closed. Penalty applied.",
            "penalty_points": penalty_points
        })

    if solo_session["active"]:
        return jsonify({"message": "Cannot open restricted apps during an active study session"}), 400

    used_seconds = get_app_used_seconds(app_item)
    limit_seconds = app_item["limit_minutes"] * 60
    if used_seconds >= limit_seconds:
        return jsonify({"message": f"{app_item['name']} limit exhausted"}), 400

    app_item["is_open"] = True
    app_item["opened_at"] = now_str()

    return jsonify({
        "message": f"{app_item['name']} opened successfully",
        "penalty_points": 0
    })

# =========================================================
# BASIC USER ROUTES
# =========================================================
@app.route("/users", methods=["GET"])
def get_users():
    for user in users:
        ensure_user_has_study_seconds(user)
    return jsonify(users)

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    ensure_user_has_study_seconds(user)
    return jsonify(user)

# =========================================================
# GROUP ROUTES
# =========================================================
@app.route("/groups", methods=["GET"])
def get_groups():
    return jsonify(groups)

@app.route("/groups/my/<int:user_id>", methods=["GET"])
def get_my_groups(user_id):
    my_groups = get_user_groups(user_id)
    result = []

    for group in my_groups:
        result.append({
            **group,
            "your_contribution": get_user_group_contribution(group["id"], user_id),
            "member_count": len(group["members"])
        })

    return jsonify(result)

@app.route("/groups/create", methods=["POST"])
def create_group():
    global group_id_counter

    data = request.json
    name = data.get("name", "").strip()
    leader_id = data.get("leader_id")

    if not name:
        return jsonify({"error": "Group name is required"}), 400

    leader = find_user(leader_id)
    if not leader:
        return jsonify({"error": "Leader user not found"}), 404

    ensure_user_has_study_seconds(leader)

    new_group = {
        "id": group_id_counter,
        "name": name,
        "leader_id": leader_id,
        "join_code": generate_join_code(name, group_id_counter),
        "members": [
            {
                "user_id": leader_id,
                "name": leader["name"],
                "role": "leader"
            }
        ],
        "total_points": 0,
        "created_at": now_str()
    }

    groups.append(new_group)
    group_messages[group_id_counter] = []

    group_id_counter += 1
    return jsonify({
        "message": "Group created successfully",
        "group": new_group
    })

@app.route("/groups/join", methods=["POST"])
def join_group():
    data = request.json
    join_code = data.get("join_code", "").strip().upper()
    user_id = data.get("user_id")

    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    ensure_user_has_study_seconds(user)

    group = next((g for g in groups if g["join_code"] == join_code), None)
    if not group:
        return jsonify({"error": "Invalid join code"}), 404

    if user_in_group(user_id, group):
        return jsonify({"error": "User already in this group"}), 400

    group["members"].append({
        "user_id": user_id,
        "name": user["name"],
        "role": "member"
    })

    return jsonify({
        "message": f"{user['name']} joined {group['name']}",
        "group": group
    })

@app.route("/groups/<int:group_id>", methods=["GET"])
def get_group(group_id):
    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    current_contribution = get_user_group_contribution(group_id, current_user_id)

    return jsonify({
        **group,
        "your_contribution": current_contribution,
        "member_count": len(group["members"])
    })

@app.route("/groups/<int:group_id>/leave", methods=["POST"])
def leave_group(group_id):
    data = request.json
    user_id = data.get("user_id")

    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if not user_in_group(user_id, group):
        return jsonify({"error": "User is not a member of this group"}), 400

    if group["leader_id"] == user_id:
        if len(group["members"]) > 1:
            return jsonify({
                "error": "Leader cannot leave while other members exist"
            }), 400
        else:
            groups.remove(group)
            group_messages.pop(group_id, None)
            return jsonify({"message": "Group deleted because leader left"})

    group["members"] = [m for m in group["members"] if m["user_id"] != user_id]

    return jsonify({"message": "Left group successfully", "group": group})

@app.route("/groups/<int:group_id>/members", methods=["GET"])
def get_group_members(group_id):
    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(group["members"])

# =========================================================
# GROUP CHAT
# =========================================================
@app.route("/groups/<int:group_id>/messages", methods=["GET"])
def get_group_messages(group_id):
    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(group_messages.get(group_id, []))

@app.route("/groups/<int:group_id>/messages", methods=["POST"])
def send_group_message(group_id):
    data = request.json
    user_id = data.get("user_id")
    text = data.get("text", "").strip()

    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400

    if not user_in_group(user_id, group):
        return jsonify({"error": "Only group members can send messages"}), 403

    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    msg = {
        "sender_id": user_id,
        "sender_name": user["name"],
        "text": text,
        "timestamp": now_str()
    }

    group_messages[group_id].append(msg)
    return jsonify({"message": "Message sent", "chat_message": msg})

# =========================================================
# GROUP TASKS
# =========================================================
@app.route("/groups/<int:group_id>/tasks", methods=["GET"])
def get_group_tasks(group_id):
    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    tasks = [t for t in group_tasks if t["group_id"] == group_id]
    result = []

    for task in tasks:
        active_session = get_active_group_session(group_id, task["id"])
        result.append({
            **task,
            "window_status": task_window_status(task),
            "has_active_session": active_session is not None,
            "active_session_id": active_session["id"] if active_session else None
        })

    return jsonify(result)

@app.route("/groups/<int:group_id>/tasks/create", methods=["POST"])
def create_group_task(group_id):
    global task_id_counter

    data = request.json

    creator_id = data.get("creator_id")
    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    description = data.get("description", "").strip()
    scheduled_start = data.get("scheduled_start", "").strip()
    scheduled_end = data.get("scheduled_end", "").strip()

    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if creator_id != group["leader_id"]:
        return jsonify({"error": "Only the group leader can create tasks"}), 403

    if not title or not scheduled_start or not scheduled_end:
        return jsonify({"error": "Title, start and end are required"}), 400

    try:
        start_dt = datetime.fromisoformat(scheduled_start)
        end_dt = datetime.fromisoformat(scheduled_end)
        if end_dt <= start_dt:
            return jsonify({"error": "End time must be after start time"}), 400
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    creator = find_user(creator_id)

    new_task = {
        "id": task_id_counter,
        "group_id": group_id,
        "group_name": group["name"],
        "title": title,
        "category": category,
        "description": description,
        "created_by": creator_id,
        "created_by_name": creator["name"] if creator else "Unknown",
        "scheduled_start": scheduled_start,
        "scheduled_end": scheduled_end,
        "created_at": now_str()
    }

    group_tasks.append(new_task)

    for member in group["members"]:
        task_assignments.append({
            "task_id": task_id_counter,
            "user_id": member["user_id"],
            "user_name": member["name"],
            "status": "Pending",
            "study_minutes": 0,
            "points_earned": 0,
            "proof_submitted": False
        })

    task_id_counter += 1

    return jsonify({
        "message": "Task created and assigned to all group members",
        "task": new_task
    })

@app.route("/users/<int:user_id>/assigned-tasks", methods=["GET"])
def get_assigned_tasks(user_id):
    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    result = []
    user_assignments = [a for a in task_assignments if a["user_id"] == user_id]

    for assignment in user_assignments:
        task = find_task(assignment["task_id"])
        if task:
            active_session = get_active_group_session(task["group_id"], task["id"])
            task_data = {
                "task_id": task["id"],
                "title": task["title"],
                "category": task["category"],
                "description": task["description"],
                "group_id": task["group_id"],
                "group_name": task["group_name"],
                "created_by_name": task["created_by_name"],
                "scheduled_start": task["scheduled_start"],
                "scheduled_end": task["scheduled_end"],
                "window_status": task_window_status(task),
                "assignment_status": assignment["status"],
                "study_minutes": assignment["study_minutes"],
                "points_earned": assignment["points_earned"],
                "proof_submitted": assignment["proof_submitted"],
                "can_start_now": task_window_status(task) == "Active",
                "has_active_session": active_session is not None,
                "active_session_id": active_session["id"] if active_session else None
            }
            result.append(task_data)

    result.sort(key=lambda x: x["scheduled_start"])
    return jsonify(result)

# =========================================================
# GROUP STUDY SESSION FLOW
# =========================================================
@app.route("/group-sessions/start", methods=["POST"])
def start_group_session():
    global session_id_counter

    data = request.json
    user_id = data.get("user_id")
    group_id = data.get("group_id")
    task_id = data.get("task_id")

    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if not user_in_group(user_id, group):
        return jsonify({"error": "User is not part of this group"}), 403

    task = find_task(task_id)
    if not task or task["group_id"] != group_id:
        return jsonify({"error": "Task not found for this group"}), 404

    if task_window_status(task) != "Active":
        return jsonify({"error": "Task window is not active right now"}), 400

    existing = get_active_group_session(group_id, task_id)
    if existing:
        return jsonify({"error": "A group session is already active for this task"}), 400

    user = find_user(user_id)

    new_session = {
        "id": session_id_counter,
        "group_id": group_id,
        "group_name": group["name"],
        "task_id": task_id,
        "task_title": task["title"],
        "started_by": user_id,
        "started_by_name": user["name"] if user else "Unknown",
        "status": "active",
        "start_time": now_str(),
        "end_time": None,
        "participants": [
            {
                "user_id": user_id,
                "user_name": user["name"] if user else "Unknown",
                "joined_at": now_str(),
                "left_at": None
            }
        ]
    }

    group_sessions.append(new_session)

    for assignment in task_assignments:
        if assignment["task_id"] == task_id and assignment["user_id"] == user_id:
            assignment["status"] = "In Progress"

    session_id_counter += 1

    return jsonify({
        "message": "Group session started",
        "session": new_session
    })

@app.route("/groups/<int:group_id>/active-session", methods=["GET"])
def get_group_active_session(group_id):
    session = get_active_group_session(group_id)
    if not session:
        return jsonify(None)
    return jsonify(session)

@app.route("/group-sessions/join", methods=["POST"])
def join_group_session():
    data = request.json
    user_id = data.get("user_id")
    session_id = data.get("session_id")

    session = next((s for s in group_sessions if s["id"] == session_id), None)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session["status"] != "active":
        return jsonify({"error": "Session is not active"}), 400

    group = find_group(session["group_id"])
    if not group or not user_in_group(user_id, group):
        return jsonify({"error": "User is not part of this group"}), 403

    already_joined = any(p["user_id"] == user_id for p in session["participants"])
    if already_joined:
        return jsonify({"error": "User already joined this session"}), 400

    user = find_user(user_id)

    session["participants"].append({
        "user_id": user_id,
        "user_name": user["name"] if user else "Unknown",
        "joined_at": now_str(),
        "left_at": None
    })

    for assignment in task_assignments:
        if assignment["task_id"] == session["task_id"] and assignment["user_id"] == user_id:
            assignment["status"] = "In Progress"

    return jsonify({
        "message": "Joined group session",
        "session": session
    })

@app.route("/group-sessions/end", methods=["POST"])
def end_group_session():
    data = request.json
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    participant_minutes = data.get("participant_minutes", [])

    session = next((s for s in group_sessions if s["id"] == session_id), None)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session["status"] != "active":
        return jsonify({"error": "Session already ended"}), 400

    group = find_group(session["group_id"])
    if not group:
        return jsonify({"error": "Group not found"}), 404

    if user_id != group["leader_id"] and user_id != session["started_by"]:
        return jsonify({"error": "Only leader or starter can end the session"}), 403

    session["status"] = "ended"
    session["end_time"] = now_str()

    total_group_points = 0

    for entry in participant_minutes:
        participant_user_id = entry.get("user_id")
        minutes = int(entry.get("minutes", 0))

        if minutes < 0:
            minutes = 0

        points = study_points_from_minutes(minutes)
        total_group_points += points

        user = find_user(participant_user_id)
        if user:
            ensure_user_has_study_seconds(user)
            user["co2_points"] += points
            user["study_seconds"] += minutes * 60

        for assignment in task_assignments:
            if assignment["task_id"] == session["task_id"] and assignment["user_id"] == participant_user_id:
                assignment["study_minutes"] += minutes
                assignment["points_earned"] += points

    group["total_points"] += total_group_points

    return jsonify({
        "message": "Group session ended. Now submit proof for each participant.",
        "session": session,
        "group_points_added": total_group_points
    })

# =========================================================
# SESSION PROOF / COMPLETION FLOW
# =========================================================
@app.route("/tasks/<int:task_id>/submit-proof", methods=["POST"])
def submit_proof(task_id):
    global proof_id_counter

    data = request.json
    user_id = data.get("user_id")
    completed_work = data.get("completed_work", "").strip()
    learned_summary = data.get("learned_summary", "").strip()
    confidence = data.get("confidence", 0)

    task = find_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    assignment = next(
        (a for a in task_assignments if a["task_id"] == task_id and a["user_id"] == user_id),
        None
    )

    if not assignment:
        return jsonify({"error": "Task assignment not found"}), 404

    if not completed_work or not learned_summary:
        return jsonify({"error": "Completed work and learned summary are required"}), 400

    try:
        confidence = int(confidence)
    except:
        confidence = 0

    if confidence < 1 or confidence > 10:
        return jsonify({"error": "Confidence must be between 1 and 10"}), 400

    proof = {
        "id": proof_id_counter,
        "task_id": task_id,
        "user_id": user_id,
        "completed_work": completed_work,
        "learned_summary": learned_summary,
        "confidence": confidence,
        "submitted_at": now_str(),
        "validated": True
    }

    session_proofs.append(proof)
    proof_id_counter += 1

    assignment["proof_submitted"] = True
    assignment["status"] = "Completed"

    return jsonify({
        "message": "Proof submitted successfully",
        "proof": proof
    })

@app.route("/tasks/<int:task_id>/proofs", methods=["GET"])
def get_task_proofs(task_id):
    proofs = [p for p in session_proofs if p["task_id"] == task_id]
    return jsonify(proofs)

# =========================================================
# LEADERBOARDS
# =========================================================
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    for user in users:
        ensure_user_has_study_seconds(user)
    sorted_users = sorted(users, key=lambda x: x["co2_points"], reverse=True)
    return jsonify(sorted_users)

@app.route("/group-leaderboard", methods=["GET"])
def group_leaderboard():
    result = []

    for group in groups:
        result.append({
            "id": group["id"],
            "name": group["name"],
            "total_points": group["total_points"],
            "member_count": len(group["members"]),
            "your_contribution": get_user_group_contribution(group["id"], current_user_id)
        })

    result.sort(key=lambda x: x["total_points"], reverse=True)
    return jsonify(result)

@app.route("/groups/<int:group_id>/member-leaderboard", methods=["GET"])
def group_member_leaderboard(group_id):
    group = find_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    return jsonify(get_group_member_leaderboard(group_id))

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(debug=True)
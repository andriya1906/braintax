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
    {
        "id": 1,
        "name": "Andriya",
        "avatar_style": "focused",
        "co2_points": 120,
        "study_seconds": 0,
        "consistency_score": 4,
        "avatar_profile": {
            "hair_style": "short",
            "skin_tone": "warm",
            "outfit_color": "blue",
            "face_style": "soft",
            "accessory": "none"
        }
    },
    {
        "id": 2,
        "name": "Aisha",
        "avatar_style": "calm",
        "co2_points": 90,
        "study_seconds": 0,
        "consistency_score": 3,
        "avatar_profile": {
            "hair_style": "bob",
            "skin_tone": "light",
            "outfit_color": "green",
            "face_style": "round",
            "accessory": "glasses"
        }
    },
    {
        "id": 3,
        "name": "Rohan",
        "avatar_style": "energetic",
        "co2_points": 110,
        "study_seconds": 0,
        "consistency_score": 5,
        "avatar_profile": {
            "hair_style": "spiky",
            "skin_tone": "deep",
            "outfit_color": "orange",
            "face_style": "sharp",
            "accessory": "headband"
        }
    },
]

current_user_id = 1

# =========================================================
# SOLO SESSION / RESTRICTED APPS STATE
# =========================================================
solo_session = {
    "active": False,
    "started_at": None,
    "user_id": None
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

def ensure_user_defaults(user):
    if not user:
        return

    if "study_seconds" not in user:
        user["study_seconds"] = 0

    if "consistency_score" not in user:
        user["consistency_score"] = 0

    if "avatar_profile" not in user:
        user["avatar_profile"] = {}

    defaults = {
        "hair_style": "short",
        "skin_tone": "warm",
        "outfit_color": "blue",
        "face_style": "soft",
        "accessory": "none"
    }

    for key, value in defaults.items():
        if key not in user["avatar_profile"]:
            user["avatar_profile"][key] = value

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

def get_room_upgrade_level(consistency_score):
    if consistency_score >= 8:
        return "polished"
    elif consistency_score >= 4:
        return "improving"
    return "basic"

def get_room_upgrade_details(consistency_score):
    level = get_room_upgrade_level(consistency_score)

    if level == "polished":
        return {
            "level": "polished",
            "title": "Polished Room",
            "description": "Your room feels cleaner, more complete, and more encouraging because of consistent effort."
        }
    elif level == "improving":
        return {
            "level": "improving",
            "title": "Improving Room",
            "description": "Your room is getting more refined as your study habits become more consistent."
        }

    return {
        "level": "basic",
        "title": "Basic Room",
        "description": "A simple starting room that can improve over time through consistency."
    }

def reward_consistency(user, amount):
    ensure_user_defaults(user)
    user["consistency_score"] += amount
    if user["consistency_score"] < 0:
        user["consistency_score"] = 0

def penalize_consistency(user, amount):
    ensure_user_defaults(user)
    user["consistency_score"] -= amount
    if user["consistency_score"] < 0:
        user["consistency_score"] = 0

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

def task_window_status(task):
    now = now_dt()
    start = datetime.fromisoformat(task["scheduled_start"])
    end = datetime.fromisoformat(task["scheduled_end"])

    if now < start:
        return "Pending"
    elif start <= now <= end:
        return "Active"
    else:
        return "Expired"

def get_active_group_session_for_user(user_id):
    for session in group_sessions:
        if session["status"] == "active" and session["user_id"] == user_id:
            return session
    return None

def get_active_group_session_for_user_and_task(user_id, task_id):
    for session in group_sessions:
        if session["status"] == "active" and session["user_id"] == user_id and session["task_id"] == task_id:
            return session
    return None

def get_active_group_sessions_for_group(group_id):
    return [s for s in group_sessions if s["status"] == "active" and s["group_id"] == group_id]

def get_active_group_sessions_for_task(task_id):
    return [s for s in group_sessions if s["status"] == "active" and s["task_id"] == task_id]

def get_user_focus_state(user_id):
    if solo_session["active"] and solo_session["user_id"] == user_id and solo_session["started_at"]:
        return {
            "active": True,
            "type": "solo",
            "started_at": solo_session["started_at"],
            "group_id": None,
            "group_name": None,
            "task_id": None,
            "task_title": None,
            "session_id": None
        }

    group_session = get_active_group_session_for_user(user_id)
    if group_session:
        return {
            "active": True,
            "type": "group",
            "started_at": group_session["start_time"],
            "group_id": group_session["group_id"],
            "group_name": group_session["group_name"],
            "task_id": group_session["task_id"],
            "task_title": group_session["task_title"],
            "session_id": group_session["id"]
        }

    return {
        "active": False,
        "type": None,
        "started_at": None,
        "group_id": None,
        "group_name": None,
        "task_id": None,
        "task_title": None,
        "session_id": None
    }

def calculate_elapsed_seconds(started_at_iso):
    if not started_at_iso:
        return 0
    started_dt = datetime.fromisoformat(started_at_iso)
    elapsed_seconds = int((now_dt() - started_dt).total_seconds())
    return max(0, elapsed_seconds)

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

def get_assignment(user_id, task_id):
    return next(
        (a for a in task_assignments if a["user_id"] == user_id and a["task_id"] == task_id),
        None
    )

def get_active_assignments_for_user_in_active_task_windows(user_id):
    active_assignments = []
    for assignment in task_assignments:
        if assignment["user_id"] != user_id:
            continue
        task = find_task(assignment["task_id"])
        if task and task_window_status(task) == "Active":
            active_assignments.append((assignment, task))
    return active_assignments

def apply_group_penalty_if_active_window(user_id, penalty_points):
    active_assignments = get_active_assignments_for_user_in_active_task_windows(user_id)

    touched_groups = set()

    for assignment, task in active_assignments:
        assignment["points_earned"] -= penalty_points

        if task["group_id"] not in touched_groups:
            group = find_group(task["group_id"])
            if group:
                group["total_points"] -= penalty_points
            touched_groups.add(task["group_id"])

def close_open_apps_and_apply_penalty():
    user = get_current_user()
    total_penalty_points = 0
    total_penalty_seconds = 0

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
            total_penalty_seconds += elapsed_seconds

    if total_penalty_points > 0 and user:
        ensure_user_defaults(user)
        user["co2_points"] -= total_penalty_points
        apply_group_penalty_if_active_window(user["id"], total_penalty_points)

        if total_penalty_seconds >= 300:
            penalize_consistency(user, 1)

    return total_penalty_points

# =========================================================
# CURRENT USER SUPPORT
# =========================================================
@app.route("/current-user", methods=["GET"])
def get_current_user_route():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404
    ensure_user_defaults(user)
    return jsonify(user)

@app.route("/set-current-user", methods=["POST"])
def set_current_user():
    global current_user_id

    data = request.json
    user_id = data.get("user_id")

    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    ensure_user_defaults(user)
    current_user_id = user_id
    return jsonify({"message": f"Current user set to {user['name']}", "user": user})

# =========================================================
# FOCUS STATUS
# =========================================================
@app.route("/focus-status", methods=["GET"])
def focus_status():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_defaults(user)
    focus_state = get_user_focus_state(user["id"])

    live_seconds = 0
    if focus_state["active"] and focus_state["started_at"]:
        live_seconds = calculate_elapsed_seconds(focus_state["started_at"])

    return jsonify({
        "user_id": user["id"],
        "study_total_seconds": user["study_seconds"],
        "active": focus_state["active"],
        "type": focus_state["type"],
        "started_at": focus_state["started_at"],
        "group_id": focus_state["group_id"],
        "group_name": focus_state["group_name"],
        "task_id": focus_state["task_id"],
        "task_title": focus_state["task_title"],
        "session_id": focus_state["session_id"],
        "live_elapsed_seconds": live_seconds
    })

# =========================================================
# AVATAR / PROFILE / SOLO SESSION
# =========================================================
@app.route("/avatar-data", methods=["GET"])
def avatar_data():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_defaults(user)
    focus_state = get_user_focus_state(user["id"])
    room_upgrade = get_room_upgrade_details(user["consistency_score"])

    return jsonify({
        "name": user["name"],
        "co2_points": user["co2_points"],
        "mood": get_avatar_mood(user["co2_points"]),
        "room_state": get_room_state(user["co2_points"]),
        "room_upgrade_level": room_upgrade["level"],
        "room_upgrade_title": room_upgrade["title"],
        "room_upgrade_description": room_upgrade["description"],
        "consistency_score": user["consistency_score"],
        "avatar_type": user["avatar_style"],
        "avatar_profile": user["avatar_profile"],
        "session_active": focus_state["active"],
        "session_type": focus_state["type"],
        "active_session_started_at": focus_state["started_at"],
        "doom_scroll_total_seconds": get_total_doom_scroll_seconds(),
        "study_total_seconds": user["study_seconds"]
    })

@app.route("/profile", methods=["GET"])
def profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_defaults(user)

    return jsonify({
        "name": user["name"],
        "avatar_type": user["avatar_style"],
        "avatar_profile": user["avatar_profile"]
    })

@app.route("/update-profile", methods=["POST"])
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Current user not found"}), 404

    ensure_user_defaults(user)

    data = request.json
    name = data.get("name", "").strip()
    avatar_type = data.get("avatar_type", "").strip().lower()

    avatar_profile = data.get("avatar_profile", {})
    hair_style = str(avatar_profile.get("hair_style", user["avatar_profile"]["hair_style"])).strip().lower()
    skin_tone = str(avatar_profile.get("skin_tone", user["avatar_profile"]["skin_tone"])).strip().lower()
    outfit_color = str(avatar_profile.get("outfit_color", user["avatar_profile"]["outfit_color"])).strip().lower()
    face_style = str(avatar_profile.get("face_style", user["avatar_profile"]["face_style"])).strip().lower()
    accessory = str(avatar_profile.get("accessory", user["avatar_profile"]["accessory"])).strip().lower()

    valid_avatar_types = ["calm", "energetic", "focused"]
    valid_hair_styles = ["short", "bob", "spiky", "curly", "wavy"]
    valid_skin_tones = ["light", "warm", "tan", "deep"]
    valid_outfit_colors = ["blue", "green", "orange", "purple", "grey"]
    valid_face_styles = ["soft", "round", "sharp"]
    valid_accessories = ["none", "glasses", "headband", "clip"]

    if not name:
        return jsonify({"message": "Name cannot be empty"}), 400

    if avatar_type not in valid_avatar_types:
        return jsonify({"message": "Invalid avatar style"}), 400

    if hair_style not in valid_hair_styles:
        return jsonify({"message": "Invalid hair style"}), 400

    if skin_tone not in valid_skin_tones:
        return jsonify({"message": "Invalid skin tone"}), 400

    if outfit_color not in valid_outfit_colors:
        return jsonify({"message": "Invalid outfit color"}), 400

    if face_style not in valid_face_styles:
        return jsonify({"message": "Invalid face style"}), 400

    if accessory not in valid_accessories:
        return jsonify({"message": "Invalid accessory"}), 400

    user["name"] = name
    user["avatar_style"] = avatar_type
    user["avatar_profile"] = {
        "hair_style": hair_style,
        "skin_tone": skin_tone,
        "outfit_color": outfit_color,
        "face_style": face_style,
        "accessory": accessory
    }

    for group in groups:
        for member in group["members"]:
            if member["user_id"] == user["id"]:
                member["name"] = user["name"]

    for assignment in task_assignments:
        if assignment["user_id"] == user["id"]:
            assignment["user_name"] = user["name"]

    return jsonify({"message": "Profile updated successfully"})

@app.route("/start-session", methods=["POST"])
def start_session():
    user = get_current_user()
    if not user:
        return jsonify({"message": "Current user not found"}), 404

    ensure_user_defaults(user)

    focus_state = get_user_focus_state(user["id"])
    if focus_state["active"]:
        return jsonify({"message": "A focus session is already active"}), 400

    close_open_apps_and_apply_penalty()

    solo_session["active"] = True
    solo_session["started_at"] = now_str()
    solo_session["user_id"] = user["id"]

    return jsonify({"message": "Solo study session started"})

@app.route("/end-session", methods=["POST"])
def end_session():
    user = get_current_user()
    if not user:
        return jsonify({"message": "Current user not found"}), 404

    ensure_user_defaults(user)

    if not solo_session["active"] or not solo_session["started_at"] or solo_session["user_id"] != user["id"]:
        return jsonify({"message": "No solo session is active"}), 400

    elapsed_seconds = calculate_elapsed_seconds(solo_session["started_at"])
    elapsed_minutes = elapsed_seconds / 60.0
    earned_points = study_points_from_minutes(elapsed_minutes)

    user["co2_points"] += earned_points
    user["study_seconds"] += elapsed_seconds

    if elapsed_seconds >= 900:
        reward_consistency(user, 1)

    solo_session["active"] = False
    solo_session["started_at"] = None
    solo_session["user_id"] = None

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
    user = get_current_user()
    focus_state = get_user_focus_state(user["id"]) if user else {"active": False, "type": None}

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
        "session_active": focus_state["active"],
        "session_type": focus_state["type"],
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

    ensure_user_defaults(user)

    data = request.json
    app_id = data.get("app_id")

    app_item = find_restricted_app(app_id)
    if not app_item:
        return jsonify({"message": "App not found"}), 404

    if app_item["is_open"]:
        elapsed_seconds = calculate_elapsed_seconds(app_item["opened_at"])

        app_item["used_seconds"] += elapsed_seconds
        app_item["is_open"] = False
        app_item["opened_at"] = None

        penalty_minutes = elapsed_seconds / 60.0
        penalty_points = doom_points_from_minutes(penalty_minutes)

        user["co2_points"] -= penalty_points
        apply_group_penalty_if_active_window(user["id"], penalty_points)

        if elapsed_seconds >= 300:
            penalize_consistency(user, 1)

        return jsonify({
            "message": f"{app_item['name']} closed. Penalty applied.",
            "penalty_points": penalty_points
        })

    focus_state = get_user_focus_state(user["id"])
    if focus_state["active"]:
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
        ensure_user_defaults(user)
    return jsonify(users)

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = find_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    ensure_user_defaults(user)
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

    ensure_user_defaults(leader)

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

    ensure_user_defaults(user)

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

    active_session = get_active_group_session_for_user(user_id)
    if active_session and active_session["group_id"] == group_id:
        return jsonify({"error": "Leave the active study session first"}), 400

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
        active_sessions = get_active_group_sessions_for_task(task["id"])
        user_active_session = get_active_group_session_for_user_and_task(current_user_id, task["id"])

        result.append({
            **task,
            "window_status": task_window_status(task),
            "active_session_count": len(active_sessions),
            "has_active_sessions": len(active_sessions) > 0,
            "user_has_active_session": user_active_session is not None,
            "user_active_session_id": user_active_session["id"] if user_active_session else None
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
            "proof_submitted": False,
            "session_count": 0
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
            active_sessions = get_active_group_sessions_for_task(task["id"])
            user_active_session = get_active_group_session_for_user_and_task(user_id, task["id"])

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
                "session_count": assignment.get("session_count", 0),
                "can_start_now": task_window_status(task) == "Active",
                "active_session_count": len(active_sessions),
                "has_active_sessions": len(active_sessions) > 0,
                "user_has_active_session": user_active_session is not None,
                "user_active_session_id": user_active_session["id"] if user_active_session else None
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

    current_focus = get_user_focus_state(user_id)
    if current_focus["active"]:
        return jsonify({"error": "User already has an active focus session"}), 400

    existing_user_task_session = get_active_group_session_for_user_and_task(user_id, task_id)
    if existing_user_task_session:
        return jsonify({"error": "You already have an active session for this task"}), 400

    if user_id == current_user_id:
        close_open_apps_and_apply_penalty()

    user = find_user(user_id)
    ensure_user_defaults(user)
    assignment = get_assignment(user_id, task_id)

    new_session = {
        "id": session_id_counter,
        "group_id": group_id,
        "group_name": group["name"],
        "task_id": task_id,
        "task_title": task["title"],
        "user_id": user_id,
        "user_name": user["name"] if user else "Unknown",
        "status": "active",
        "start_time": now_str(),
        "end_time": None
    }

    group_sessions.append(new_session)

    if assignment:
        assignment["status"] = "In Progress"
        assignment["session_count"] = assignment.get("session_count", 0) + 1

    session_id_counter += 1

    return jsonify({
        "message": "Study session started",
        "session": new_session
    })

@app.route("/group-sessions/join", methods=["POST"])
def join_group_session():
    data = request.json
    user_id = data.get("user_id")
    session_id = data.get("session_id")

    target_session = next((s for s in group_sessions if s["id"] == session_id), None)
    if not target_session:
        return jsonify({"error": "Session not found"}), 404

    if target_session["status"] != "active":
        return jsonify({"error": "Session is not active"}), 400

    return start_group_session_internal(
        user_id=user_id,
        group_id=target_session["group_id"],
        task_id=target_session["task_id"]
    )

def start_group_session_internal(user_id, group_id, task_id):
    global session_id_counter

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

    current_focus = get_user_focus_state(user_id)
    if current_focus["active"]:
        return jsonify({"error": "User already has an active focus session"}), 400

    existing_user_task_session = get_active_group_session_for_user_and_task(user_id, task_id)
    if existing_user_task_session:
        return jsonify({"error": "You already have an active session for this task"}), 400

    if user_id == current_user_id:
        close_open_apps_and_apply_penalty()

    user = find_user(user_id)
    ensure_user_defaults(user)
    assignment = get_assignment(user_id, task_id)

    new_session = {
        "id": session_id_counter,
        "group_id": group_id,
        "group_name": group["name"],
        "task_id": task_id,
        "task_title": task["title"],
        "user_id": user_id,
        "user_name": user["name"] if user else "Unknown",
        "status": "active",
        "start_time": now_str(),
        "end_time": None
    }

    group_sessions.append(new_session)

    if assignment:
        assignment["status"] = "In Progress"
        assignment["session_count"] = assignment.get("session_count", 0) + 1

    session_id_counter += 1

    return jsonify({
        "message": "Study session started",
        "session": new_session
    })

@app.route("/group-sessions/leave", methods=["POST"])
def leave_group_session():
    data = request.json
    user_id = data.get("user_id")
    session_id = data.get("session_id")
    task_id = data.get("task_id")

    session = None

    if session_id:
        session = next(
            (s for s in group_sessions if s["id"] == session_id and s["status"] == "active"),
            None
        )
    elif task_id:
        session = get_active_group_session_for_user_and_task(user_id, task_id)
    else:
        session = get_active_group_session_for_user(user_id)

    if not session:
        return jsonify({"error": "No active session found"}), 404

    if session["user_id"] != user_id:
        return jsonify({"error": "You can only leave your own session"}), 403

    task = find_task(session["task_id"])
    group = find_group(session["group_id"])
    user = find_user(user_id)
    assignment = get_assignment(user_id, session["task_id"])

    if not task or not group or not user:
        return jsonify({"error": "Related task, group, or user not found"}), 404

    ensure_user_defaults(user)

    elapsed_seconds = calculate_elapsed_seconds(session["start_time"])
    elapsed_minutes = elapsed_seconds / 60.0
    earned_points = study_points_from_minutes(elapsed_minutes)

    session["status"] = "ended"
    session["end_time"] = now_str()

    user["co2_points"] += earned_points
    user["study_seconds"] += elapsed_seconds

    if elapsed_seconds >= 900:
        reward_consistency(user, 1)

    group["total_points"] += earned_points

    if assignment:
        assignment["study_minutes"] += int(elapsed_minutes)
        assignment["points_earned"] += earned_points
        if task_window_status(task) == "Expired":
            assignment["status"] = "Completed" if assignment["proof_submitted"] else "Pending Review"
        else:
            assignment["status"] = "In Progress"

    return jsonify({
        "message": "Study session ended",
        "session": session,
        "earned_points": earned_points,
        "study_seconds_added": elapsed_seconds
    })

@app.route("/group-sessions/end", methods=["POST"])
def end_group_session_compat():
    return leave_group_session()

@app.route("/groups/<int:group_id>/active-session", methods=["GET"])
def get_group_active_session(group_id):
    sessions = get_active_group_sessions_for_group(group_id)
    if not sessions:
        return jsonify(None)

    user_session = next((s for s in sessions if s["user_id"] == current_user_id), None)
    if user_session:
        return jsonify(user_session)

    return jsonify(sessions[0])

@app.route("/groups/<int:group_id>/active-sessions", methods=["GET"])
def get_group_active_sessions(group_id):
    sessions = get_active_group_sessions_for_group(group_id)
    return jsonify(sessions)

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

    assignment = get_assignment(user_id, task_id)

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

    active_session = get_active_group_session_for_user_and_task(user_id, task_id)
    if not active_session:
        assignment["status"] = "Completed"

    user = find_user(user_id)
    ensure_user_defaults(user)
    reward_consistency(user, 1)

    return jsonify({
        "message": "Proof submitted successfully",
        "proof": proof
    })

# =========================================================
# LEADERBOARDS
# =========================================================
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    for user in users:
        ensure_user_defaults(user)
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
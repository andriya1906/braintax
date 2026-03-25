const API_BASE = "http://127.0.0.1:5000";

let avatarData = null;
let focusStatusData = null;
let timerInterval = null;
let toastTimeout = null;
let restrictedAppsRefreshInterval = null;

let currentUserId = 1;
let selectedGroupId = null;
let selectedGroupData = null;

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    if (!toast) {
        alert(message);
        return;
    }

    toast.className = "toast " + type;
    toast.innerText = message;

    clearTimeout(toastTimeout);

    requestAnimationFrame(() => {
        toast.classList.add("show");
    });

    toastTimeout = setTimeout(() => {
        toast.classList.remove("show");
    }, 3200);
}

function setTheme(theme) {
    const body = document.body;
    const themeToggleMenu = document.getElementById("themeToggleMenu");

    if (theme === "dark") {
        body.classList.add("dark-theme");
        if (themeToggleMenu) themeToggleMenu.innerText = "Switch to Light Theme";
    } else {
        body.classList.remove("dark-theme");
        if (themeToggleMenu) themeToggleMenu.innerText = "Switch to Dark Theme";
    }

    localStorage.setItem("braintax-theme", theme);
}

function initTheme() {
    const savedTheme = localStorage.getItem("braintax-theme") || "light";
    setTheme(savedTheme);
}

function toggleTheme() {
    if (document.body.classList.contains("dark-theme")) {
        setTheme("light");
    } else {
        setTheme("dark");
    }
}

function formatTime(totalSeconds) {
    const value = Math.max(0, parseInt(totalSeconds || 0));
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const seconds = value % 60;

    const hh = hours < 10 ? "0" + hours : String(hours);
    const mm = minutes < 10 ? "0" + minutes : String(minutes);
    const ss = seconds < 10 ? "0" + seconds : String(seconds);

    return `${hh}:${mm}:${ss}`;
}

function formatStudySummary(totalSeconds) {
    const value = Math.max(0, parseInt(totalSeconds || 0));
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const seconds = value % 60;

    return `${hours}h ${minutes}m ${seconds}s`;
}

function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    return date.toLocaleString();
}

function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showSection(sectionName) {
    const dashboardSection = document.getElementById("dashboardSection");
    const profileSection = document.getElementById("profileSection");
    const restrictedAppsSection = document.getElementById("restrictedAppsSection");

    if (dashboardSection) dashboardSection.classList.remove("active");
    if (profileSection) profileSection.classList.remove("active");
    if (restrictedAppsSection) restrictedAppsSection.classList.remove("active");

    if (sectionName === "dashboard") {
        if (dashboardSection) dashboardSection.classList.add("active");
        stopRestrictedAppsLiveRefresh();
    }

    if (sectionName === "profile") {
        if (profileSection) profileSection.classList.add("active");
        stopRestrictedAppsLiveRefresh();
    }

    if (sectionName === "restrictedApps") {
        if (restrictedAppsSection) restrictedAppsSection.classList.add("active");
        loadRestrictedApps();
        startRestrictedAppsLiveRefresh();
    }
}

function switchBottomPanel(panelName) {
    const groupsPanel = document.getElementById("groupsPanel");
    const leaderboardPanel = document.getElementById("leaderboardPanel");
    const groupsTabBtn = document.getElementById("groupsTabBtn");
    const leaderboardTabBtn = document.getElementById("leaderboardTabBtn");

    if (groupsPanel) groupsPanel.classList.remove("active");
    if (leaderboardPanel) leaderboardPanel.classList.remove("active");
    if (groupsTabBtn) groupsTabBtn.classList.remove("active");
    if (leaderboardTabBtn) leaderboardTabBtn.classList.remove("active");

    if (panelName === "groups") {
        if (groupsPanel) groupsPanel.classList.add("active");
        if (groupsTabBtn) groupsTabBtn.classList.add("active");
    }

    if (panelName === "leaderboard") {
        if (leaderboardPanel) leaderboardPanel.classList.add("active");
        if (leaderboardTabBtn) leaderboardTabBtn.classList.add("active");
    }
}

/* =========================
   FOCUS STATUS + TIMER
========================= */

function stopSessionTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function startSessionTimer(startedAtIso) {
    stopSessionTimer();

    const timerDisplay = document.getElementById("timerDisplay");
    if (!startedAtIso) {
        if (timerDisplay) timerDisplay.innerText = "00:00:00";
        return;
    }

    const render = () => {
        const now = new Date().getTime();
        const started = new Date(startedAtIso).getTime();
        const elapsedSeconds = Math.max(0, Math.floor((now - started) / 1000));
        if (timerDisplay) timerDisplay.innerText = formatTime(elapsedSeconds);
    };

    render();
    timerInterval = setInterval(render, 1000);
}

function loadFocusStatus() {
    return fetch(`${API_BASE}/focus-status`)
        .then(response => response.json())
        .then(data => {
            focusStatusData = data;

            const sessionBadge = document.getElementById("sessionBadge");
            const sessionStatus = document.getElementById("sessionStatus");
            const focusTypeLabel = document.getElementById("focusTypeLabel");
            const studyTotalDisplay = document.getElementById("studyTotalDisplay");
            const timerDisplay = document.getElementById("timerDisplay");

            if (studyTotalDisplay) {
                studyTotalDisplay.innerText = formatTime(data.study_total_seconds || 0);
            }

            if (data.active) {
                if (sessionBadge) {
                    sessionBadge.innerText = data.type === "group" ? "Group Session Active" : "Solo Session Active";
                }

                if (focusTypeLabel) {
                    if (data.type === "group") {
                        focusTypeLabel.innerText = `Studying: ${data.task_title || "Task"} • ${data.group_name || "Group"}`;
                    } else {
                        focusTypeLabel.innerText = "Solo study session in progress";
                    }
                }

                if (sessionStatus) {
                    if (data.type === "group") {
                        sessionStatus.innerText = `You are currently in an active group task session. You can leave and rejoin anytime within the task window.`;
                    } else {
                        sessionStatus.innerText = `You are currently in an active solo session.`;
                    }
                }

                startSessionTimer(data.started_at);
            } else {
                if (sessionBadge) sessionBadge.innerText = "No Active Session";
                if (focusTypeLabel) focusTypeLabel.innerText = "No active focus session";
                if (sessionStatus) sessionStatus.innerText = "No study session is active.";
                stopSessionTimer();
                if (timerDisplay) timerDisplay.innerText = "00:00:00";
            }

            updatePrimarySessionButtons();
        })
        .catch(error => {
            console.log(error);
        });
}

function updatePrimarySessionButtons() {
    const startBtn = document.getElementById("startBtn");
    const endBtn = document.getElementById("endBtn");

    if (!startBtn || !endBtn || !focusStatusData) return;

    if (focusStatusData.active) {
        if (focusStatusData.type === "solo") {
            startBtn.disabled = true;
            endBtn.disabled = false;
        } else {
            startBtn.disabled = true;
            endBtn.disabled = true;
        }
    } else {
        startBtn.disabled = false;
        endBtn.disabled = false;
    }
}

/* =========================
   AVATAR / PROFILE
========================= */

function applyMascotState() {
    if (!avatarData) return;

    const room = document.getElementById("room");
    const mascotCharacter = document.getElementById("mascotCharacter");
    const mascotMouth = document.getElementById("mascotMouth");

    if (!room || !mascotCharacter || !mascotMouth) return;

    room.className = "mascot-room";
    mascotCharacter.className = "mascot";
    mascotMouth.className = "mascot-mouth";

    if (avatarData.room_state === "bright") room.classList.add("bright");
    if (avatarData.room_state === "normal") room.classList.add("normal");
    if (avatarData.room_state === "dim") room.classList.add("dim");

    if (avatarData.avatar_type === "calm") mascotCharacter.classList.add("mascot-calm");
    if (avatarData.avatar_type === "energetic") mascotCharacter.classList.add("mascot-energetic");
    if (avatarData.avatar_type === "focused") mascotCharacter.classList.add("mascot-focused");

    if (avatarData.mood === "happy") mascotCharacter.classList.add("mood-happy");
    if (avatarData.mood === "neutral") mascotCharacter.classList.add("mood-neutral");
    if (avatarData.mood === "sad") mascotCharacter.classList.add("mood-sad");

    if (avatarData.mood === "happy") mascotMouth.classList.add("mouth-happy");
    if (avatarData.mood === "neutral") mascotMouth.classList.add("mouth-neutral");
    if (avatarData.mood === "sad") mascotMouth.classList.add("mouth-sad");
}

function loadAvatarData() {
    return fetch(`${API_BASE}/avatar-data`)
        .then(response => response.json())
        .then(data => {
            avatarData = data;

            const heroNamePill = document.getElementById("heroNamePill");
            const heroPointsPill = document.getElementById("heroPointsPill");
            const heroMoodPill = document.getElementById("heroMoodPill");
            const heroDoomPill = document.getElementById("heroDoomPill");
            const previewName = document.getElementById("previewName");
            const previewAvatar = document.getElementById("previewAvatar");

            if (heroNamePill) heroNamePill.innerText = "Name: " + data.name;
            if (heroPointsPill) heroPointsPill.innerText = "CO₂ Points: " + data.co2_points;
            if (heroMoodPill) heroMoodPill.innerText = "Mood: " + data.mood;
            if (heroDoomPill) heroDoomPill.innerText = "Doom Scroll: " + formatTime(data.doom_scroll_total_seconds || 0);

            if (previewName) previewName.innerText = "Name: " + data.name;
            if (previewAvatar) previewAvatar.innerText = "Avatar Style: " + data.avatar_type;
        })
        .catch(error => {
            console.log(error);
        });
}

function loadProfile() {
    fetch(`${API_BASE}/profile`)
        .then(response => response.json())
        .then(data => {
            const profileName = document.getElementById("profileName");
            const avatarType = document.getElementById("avatarType");

            if (profileName) profileName.value = data.name;
            if (avatarType) avatarType.value = data.avatar_type;
        })
        .catch(error => {
            console.log(error);
        });
}

function saveProfile() {
    const name = document.getElementById("profileName")?.value || "";
    const avatarType = document.getElementById("avatarType")?.value || "";

    fetch(`${API_BASE}/update-profile`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            avatar_type: avatarType
        })
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Could not update profile.");

        const profileMessage = document.getElementById("profileMessage");
        if (profileMessage) profileMessage.innerText = data.message;

        showToast(data.message, "success");
        refreshAll();

        if (selectedGroupId) {
            openGroup(selectedGroupId);
        }
    })
    .catch(error => {
        showToast(error.message || "Could not update profile.", "error");
        console.log(error);
    });
}

/* =========================
   LEADERBOARDS
========================= */

function loadLeaderboard() {
    fetch(`${API_BASE}/leaderboard`)
        .then(response => response.json())
        .then(data => {
            let html = "";

            data.forEach((item, index) => {
                const points = item.co2_points || 0;

                html += `
                    <div class="leaderboard-item">
                        <div class="leaderboard-rank">
                            <div class="rank-badge">${index + 1}</div>
                            <span>${escapeHtml(item.name)}</span>
                        </div>
                        <span class="score-text">${points} pts</span>
                    </div>
                `;
            });

            const leaderboardList = document.getElementById("leaderboardList");
            if (leaderboardList) leaderboardList.innerHTML = html || "<p>No leaderboard data.</p>";
        })
        .catch(error => {
            console.log(error);
        });
}

function loadGroupLeaderboard() {
    fetch(`${API_BASE}/group-leaderboard`)
        .then(response => response.json())
        .then(data => {
            let html = "";

            data.forEach((item, index) => {
                const groupName = item.name || "Group";
                const points = item.total_points || 0;
                const yourContribution = item.your_contribution || 0;
                const memberCount = item.member_count || 0;

                html += `
                    <div class="leaderboard-item">
                        <div class="leaderboard-rank">
                            <div class="rank-badge">${index + 1}</div>
                            <div>
                                <div>${escapeHtml(groupName)}</div>
                                <div class="score-text">Members: ${memberCount} • Your contribution: ${yourContribution} pts</div>
                            </div>
                        </div>
                        <span class="score-text">${points} pts</span>
                    </div>
                `;
            });

            const groupLeaderboardList = document.getElementById("groupLeaderboardList");
            if (groupLeaderboardList) groupLeaderboardList.innerHTML = html || "<p>No groups yet.</p>";
        })
        .catch(error => {
            console.log(error);
        });
}

function loadLeaderboards() {
    loadLeaderboard();
    loadGroupLeaderboard();
}

/* =========================
   ASSIGNED TASKS
========================= */

function loadAssignedTasks() {
    fetch(`${API_BASE}/users/${currentUserId}/assigned-tasks`)
        .then(response => response.json())
        .then(data => {
            let html = "";

            data.forEach(task => {
                let sessionButtons = "";

                if (task.window_status === "Active") {
                    if (task.user_has_active_session) {
                        sessionButtons = `
                            <button class="secondary-btn" onclick="leaveTaskSession(${task.user_active_session_id}, ${task.task_id}, ${task.group_id})">
                                Leave Session
                            </button>
                        `;
                    } else {
                        sessionButtons = `
                            <button class="primary-btn" onclick="startTaskSessionFromAssigned(${task.group_id}, ${task.task_id})">
                                Start Session
                            </button>
                        `;
                    }
                }

                html += `
                    <div class="task-item">
                        <div class="task-title">${escapeHtml(task.title)}</div>
                        <div class="task-meta">Created by: ${escapeHtml(task.created_by_name || "-")}</div>
                        <div class="task-meta">Category: ${escapeHtml(task.category || "-")} • Group: ${escapeHtml(task.group_name || "-")}</div>
                        <div class="task-meta">Window: ${formatDateTime(task.scheduled_start)} to ${formatDateTime(task.scheduled_end)}</div>
                        <div class="task-meta">Study Minutes: ${task.study_minutes || 0} • Points Earned: ${task.points_earned || 0}</div>
                        <div class="task-meta">Sessions Joined: ${task.session_count || 0} • Others Active Now: ${task.active_session_count || 0}</div>
                        <div class="status-pill">Task Window: ${task.window_status || "Pending"}</div>
                        <div class="status-pill">Your Status: ${task.assignment_status || "Pending"}</div>
                        <div class="task-meta">Proof Submitted: ${task.proof_submitted ? "Yes" : "No"}</div>

                        <div class="task-actions">
                            ${sessionButtons}
                            <button class="ghost-btn" onclick="openProofModal(${task.task_id})">Submit Proof</button>
                        </div>
                    </div>
                `;
            });

            const tasksList = document.getElementById("tasksList");
            if (tasksList) tasksList.innerHTML = html || "<p>No assigned tasks yet.</p>";
        })
        .catch(error => {
            const tasksList = document.getElementById("tasksList");
            if (tasksList) tasksList.innerHTML = "<p>Could not load tasks.</p>";
            console.log(error);
        });
}

/* =========================
   RESTRICTED APPS
========================= */

function loadRestrictedApps() {
    fetch(`${API_BASE}/restricted-apps`)
        .then(response => response.json())
        .then(data => {
            const appsSessionIndicator = document.getElementById("appsSessionIndicator");
            const appsDoomIndicator = document.getElementById("appsDoomIndicator");

            if (appsSessionIndicator) {
                if (data.session_active) {
                    appsSessionIndicator.innerText = data.session_type === "group"
                        ? "Group Study Session Active"
                        : "Solo Study Session Active";
                } else {
                    appsSessionIndicator.innerText = "No Study Session Active";
                }
            }

            if (appsDoomIndicator) {
                appsDoomIndicator.innerText = "Total Doom Scroll: " + formatTime(data.doom_scroll_total_seconds || 0);
            }

            let html = "";

            data.apps.forEach(appItem => {
                const appStatusClass = appItem.is_open ? "open-indicator" : "closed-indicator";
                const appStatusText = appItem.is_open ? "Open" : "Closed";
                const buttonText = appItem.is_open ? "Close App" : "Open App";
                const buttonClass = appItem.is_open ? "secondary-btn" : "primary-btn";

                html += `
                    <div class="app-item">
                        <div class="app-row">
                            <div class="app-left">
                                <div class="app-icon">${appItem.icon}</div>
                                <div>
                                    <div class="app-title">${escapeHtml(appItem.name)}</div>
                                    <div class="app-meta ${appStatusClass}">Status: ${appStatusText}</div>
                                    <div class="app-meta">Used: ${formatTime(appItem.used_seconds)} • Remaining: ${formatTime(appItem.remaining_seconds)}</div>
                                    <div class="app-meta">Limit: ${appItem.limit_minutes} minutes</div>
                                </div>
                            </div>

                            <div style="min-width: 220px;">
                                <div class="limit-row" style="margin-bottom: 10px;">
                                    <input class="small-input" type="number" min="0" id="appLimit${appItem.id}" value="${appItem.limit_minutes}">
                                    <button class="ghost-btn" onclick="setAppLimit(${appItem.id})">Set Limit</button>
                                </div>

                                <div class="app-actions">
                                    <button class="${buttonClass}" onclick="toggleRestrictedApp(${appItem.id})">${buttonText}</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            const appsList = document.getElementById("appsList");
            if (appsList) appsList.innerHTML = html;
        })
        .catch(error => {
            console.log(error);
        });
}

function startRestrictedAppsLiveRefresh() {
    stopRestrictedAppsLiveRefresh();

    restrictedAppsRefreshInterval = setInterval(() => {
        const restrictedAppsSection = document.getElementById("restrictedAppsSection");
        if (restrictedAppsSection && restrictedAppsSection.classList.contains("active")) {
            loadRestrictedApps();
        }
    }, 1000);
}

function stopRestrictedAppsLiveRefresh() {
    if (restrictedAppsRefreshInterval) {
        clearInterval(restrictedAppsRefreshInterval);
        restrictedAppsRefreshInterval = null;
    }
}

function setAppLimit(appId) {
    const input = document.getElementById("appLimit" + appId);
    const limitValue = input ? input.value : 0;

    fetch(`${API_BASE}/set-app-limit`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            app_id: appId,
            limit_minutes: limitValue
        })
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message);

        showToast(data.message, "success");
        refreshAll();
    })
    .catch(error => {
        showToast(error.message, "warning");
    });
}

function toggleRestrictedApp(appId) {
    fetch(`${API_BASE}/toggle-restricted-app`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ app_id: appId })
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message);

        const messageBox = document.getElementById("messageBox");
        if (messageBox) messageBox.innerText = data.message;

        showToast(data.message, data.penalty_points && data.penalty_points > 0 ? "warning" : "success");

        refreshAll();
        if (selectedGroupId) openGroup(selectedGroupId);
        showSection("restrictedApps");
    })
    .catch(error => {
        const messageBox = document.getElementById("messageBox");
        if (messageBox) messageBox.innerText = error.message;

        showToast(error.message, "warning");
    });
}

/* =========================
   SOLO SESSION
========================= */

function startSession() {
    fetch(`${API_BASE}/start-session`, {
        method: "POST"
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message);

        const messageBox = document.getElementById("messageBox");
        if (messageBox) messageBox.innerText = data.message;

        showToast(data.message, "success");
        await refreshAll();
    })
    .catch(error => {
        showToast(error.message, "warning");
        const messageBox = document.getElementById("messageBox");
        if (messageBox) messageBox.innerText = error.message;
    });
}

function endSession() {
    fetch(`${API_BASE}/end-session`, {
        method: "POST"
    })
    .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Could not end session.");

        const messageBox = document.getElementById("messageBox");
        if (messageBox) {
            messageBox.innerText = `${data.message} • +${data.earned_points || 0} pts`;
        }

        showToast(data.message, "success");
        await refreshAll();
        loadLeaderboards();
        loadAssignedTasks();
        if (selectedGroupId) openGroup(selectedGroupId);
    })
    .catch(error => {
        showToast(error.message || "Could not end session.", "error");
        console.log(error);
    });
}

/* =========================
   GROUP FEATURES
========================= */

function createGroup() {
    const name = document.getElementById("groupNameInput")?.value.trim();

    if (!name) {
        showToast("Enter a group name", "warning");
        return;
    }

    fetch(`${API_BASE}/groups/create`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: name,
            leader_id: currentUserId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Failed to create group", "warning");
            return;
        }

        document.getElementById("groupNameInput").value = "";
        showToast(result.data.message, "success");
        loadMyGroups();
        loadLeaderboards();
        switchBottomPanel("groups");
    })
    .catch(error => {
        console.log(error);
        showToast("Failed to create group", "error");
    });
}

function joinGroup() {
    const code = document.getElementById("joinCodeInput")?.value.trim();

    if (!code) {
        showToast("Enter join code", "warning");
        return;
    }

    fetch(`${API_BASE}/groups/join`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            join_code: code,
            user_id: currentUserId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Failed to join group", "warning");
            return;
        }

        document.getElementById("joinCodeInput").value = "";
        showToast(result.data.message, "success");
        loadMyGroups();
        loadLeaderboards();
        switchBottomPanel("groups");
    })
    .catch(error => {
        console.log(error);
        showToast("Failed to join group", "error");
    });
}

function loadMyGroups() {
    fetch(`${API_BASE}/groups/my/${currentUserId}`)
        .then(response => response.json())
        .then(groups => {
            const container = document.getElementById("myGroupsList");
            if (!container) return;

            if (!groups.length) {
                container.innerHTML = "<p>No groups joined yet.</p>";
                return;
            }

            container.innerHTML = groups.map(group => `
                <div class="item-card">
                    <div class="group-list-card-head">
                        <div>
                            <p><strong>${escapeHtml(group.name)}</strong></p>
                            <p class="muted">Join Code: ${escapeHtml(group.join_code)}</p>
                            <p class="muted">Members: ${group.member_count || 0}</p>
                            <p class="muted">Your Contribution: ${group.your_contribution || 0} pts</p>
                        </div>
                    </div>
                    <div class="task-actions">
                        <button class="primary-btn" onclick="openGroup(${group.id})">Open Group</button>
                        <button class="secondary-btn" onclick="leaveGroup(${group.id})">Leave Group</button>
                    </div>
                </div>
            `).join("");
        })
        .catch(error => {
            console.log(error);
        });
}

function openGroup(groupId) {
    selectedGroupId = groupId;
    switchBottomPanel("groups");

    Promise.all([
        fetch(`${API_BASE}/groups/${groupId}`).then(r => r.json()),
        fetch(`${API_BASE}/groups/${groupId}/messages`).then(r => r.json()),
        fetch(`${API_BASE}/groups/${groupId}/tasks`).then(r => r.json()),
        fetch(`${API_BASE}/groups/${groupId}/active-sessions`).then(r => r.json()),
        fetch(`${API_BASE}/groups/${groupId}/member-leaderboard`).then(r => r.json())
    ])
    .then(([group, messages, tasks, activeSessions, memberLeaderboard]) => {
        selectedGroupData = group;

        const isLeader = group.leader_id === currentUserId;
        const groupDetails = document.getElementById("groupDetails");
        if (!groupDetails) return;

        const tasksHtml = tasks.length
            ? tasks.map(task => {
                let actionHtml = "";

                if (task.window_status === "Active") {
                    if (task.user_has_active_session) {
                        actionHtml = `
                            <button class="secondary-btn" onclick="leaveTaskSession(${task.user_active_session_id}, ${task.id}, ${group.id})">
                                Leave Session
                            </button>
                        `;
                    } else {
                        actionHtml = `
                            <button class="primary-btn" onclick="startGroupTaskSession(${task.id}, ${group.id})">
                                Start Session
                            </button>
                        `;
                    }
                }

                return `
                    <div class="item-card">
                        <p><strong>${escapeHtml(task.title)}</strong></p>
                        <p>Category: ${escapeHtml(task.category || "-")}</p>
                        <p>Description: ${escapeHtml(task.description || "-")}</p>
                        <p>Window: ${formatDateTime(task.scheduled_start)} to ${formatDateTime(task.scheduled_end)}</p>
                        <p>Status: ${task.window_status}</p>
                        <p>Members Active Now: ${task.active_session_count || 0}</p>
                        <div class="task-actions">
                            ${actionHtml}
                        </div>
                    </div>
                `;
            }).join("")
            : "<p>No tasks yet.</p>";

        const memberLeaderboardHtml = memberLeaderboard.length
            ? memberLeaderboard.map((member, index) => `
                <div class="leaderboard-item">
                    <div class="leaderboard-rank">
                        <div class="rank-badge">${index + 1}</div>
                        <div>
                            <div>${escapeHtml(member.name)}</div>
                            <div class="score-text">${escapeHtml(member.role)}</div>
                        </div>
                    </div>
                    <span class="score-text">${member.points || 0} pts</span>
                </div>
            `).join("")
            : "<p>No member contribution data yet.</p>";

        const activeSessionsHtml = activeSessions.length
            ? activeSessions.map(session => `
                <div class="leaderboard-item">
                    <div class="leaderboard-rank">
                        <div class="rank-badge">•</div>
                        <div>
                            <div>${escapeHtml(session.user_name)}</div>
                            <div class="score-text">${escapeHtml(session.task_title)}</div>
                        </div>
                    </div>
                    <span class="score-text">Started: ${formatDateTime(session.start_time)}</span>
                </div>
            `).join("")
            : "<p>No active study sessions in this group right now.</p>";

        groupDetails.innerHTML = `
            <div class="group-detail-stack">
                <div class="item-card">
                    <h3>${escapeHtml(group.name)}</h3>
                    <p><strong>Join Code:</strong> ${escapeHtml(group.join_code)}</p>
                    <p><strong>Total Group Points:</strong> ${group.total_points || 0}</p>
                    <p><strong>Your Contribution:</strong> ${group.your_contribution || 0} pts</p>
                    <p><strong>Members:</strong> ${group.members.map(m => `${escapeHtml(m.name)} (${escapeHtml(m.role)})`).join(", ")}</p>
                </div>

                <div class="group-detail-two-col">
                    <div class="item-card">
                        <h3>Group Chat</h3>
                        <div class="chat-box">
                            ${messages.length
                                ? messages.map(msg => `
                                    <div class="chat-message">
                                        <strong>${escapeHtml(msg.sender_name)}:</strong> ${escapeHtml(msg.text)}
                                    </div>
                                `).join("")
                                : "<p>No messages yet.</p>"
                            }
                        </div>

                        <textarea id="groupMessageInput" rows="2" placeholder="Type message"></textarea>
                        <button class="primary-btn" onclick="sendGroupMessage()">Send</button>
                    </div>

                    <div class="item-card">
                        <h3>Group Member Leaderboard</h3>
                        <div>${memberLeaderboardHtml}</div>
                    </div>
                </div>

                <div class="item-card">
                    <h3>Group Tasks</h3>
                    ${
                        isLeader
                            ? `
                                <div class="form-block">
                                    <h4>Create Task</h4>
                                    <input type="text" id="taskTitleInput" placeholder="Task title">
                                    <input type="text" id="taskCategoryInput" placeholder="Category">
                                    <textarea id="taskDescriptionInput" rows="3" placeholder="Description"></textarea>
                                    <label>Start</label>
                                    <input type="datetime-local" id="taskStartInput">
                                    <label>End</label>
                                    <input type="datetime-local" id="taskEndInput">
                                    <button class="primary-btn" onclick="createTaskForGroup()">Create Group Task</button>
                                </div>
                            `
                            : `<p>Only the leader can create tasks.</p>`
                    }

                    <div>${tasksHtml}</div>
                </div>

                <div class="item-card">
                    <h3>Active Study Sessions</h3>
                    <div>${activeSessionsHtml}</div>
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.log(error);
        showToast("Could not open group.", "error");
    });
}

function leaveGroup(groupId) {
    fetch(`${API_BASE}/groups/${groupId}/leave`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Could not leave group", "warning");
            return;
        }

        showToast(result.data.message, "success");

        if (selectedGroupId === groupId) {
            selectedGroupId = null;
            selectedGroupData = null;

            const groupDetails = document.getElementById("groupDetails");
            if (groupDetails) groupDetails.innerHTML = "Select a group to view chat, tasks, active sessions, and leaderboard.";
        }

        loadMyGroups();
        loadLeaderboards();
        loadAssignedTasks();
    })
    .catch(error => {
        console.log(error);
        showToast("Could not leave group", "error");
    });
}

function sendGroupMessage() {
    if (!selectedGroupId) {
        showToast("Select a group first", "warning");
        return;
    }

    const text = document.getElementById("groupMessageInput")?.value.trim();

    if (!text) {
        showToast("Message cannot be empty", "warning");
        return;
    }

    fetch(`${API_BASE}/groups/${selectedGroupId}/messages`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            text: text
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Failed to send message", "warning");
            return;
        }

        document.getElementById("groupMessageInput").value = "";
        openGroup(selectedGroupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Failed to send message", "error");
    });
}

function createTaskForGroup() {
    if (!selectedGroupId) {
        showToast("Select a group first", "warning");
        return;
    }

    const title = document.getElementById("taskTitleInput")?.value.trim() || "";
    const category = document.getElementById("taskCategoryInput")?.value.trim() || "";
    const description = document.getElementById("taskDescriptionInput")?.value.trim() || "";
    const scheduledStart = document.getElementById("taskStartInput")?.value || "";
    const scheduledEnd = document.getElementById("taskEndInput")?.value || "";

    if (!title || !scheduledStart || !scheduledEnd) {
        showToast("Fill title, start and end", "warning");
        return;
    }

    fetch(`${API_BASE}/groups/${selectedGroupId}/tasks/create`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            creator_id: currentUserId,
            title: title,
            category: category,
            description: description,
            scheduled_start: scheduledStart,
            scheduled_end: scheduledEnd
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Failed to create task", "warning");
            return;
        }

        showToast(result.data.message, "success");
        openGroup(selectedGroupId);
        loadAssignedTasks();
    })
    .catch(error => {
        console.log(error);
        showToast("Failed to create task", "error");
    });
}

function startGroupTaskSession(taskId, groupId) {
    fetch(`${API_BASE}/group-sessions/start`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            group_id: groupId,
            task_id: taskId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(async result => {
        if (!result.ok) {
            showToast(result.data.error || "Could not start session", "warning");
            return;
        }

        showToast(result.data.message, "success");
        await refreshAll();
        openGroup(groupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Could not start session", "error");
    });
}

function startTaskSessionFromAssigned(groupId, taskId) {
    fetch(`${API_BASE}/group-sessions/start`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            group_id: groupId,
            task_id: taskId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(async result => {
        if (!result.ok) {
            showToast(result.data.error || "Could not start session", "warning");
            return;
        }

        showToast(result.data.message, "success");
        await refreshAll();
        switchBottomPanel("groups");
        openGroup(groupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Could not start session", "error");
    });
}

function joinTaskSession(sessionId, groupId) {
    fetch(`${API_BASE}/group-sessions/join`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            session_id: sessionId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(async result => {
        if (!result.ok) {
            showToast(result.data.error || "Could not join session", "warning");
            return;
        }

        showToast(result.data.message, "success");
        await refreshAll();
        switchBottomPanel("groups");
        openGroup(groupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Could not join session", "error");
    });
}

function leaveTaskSession(sessionId, taskId, groupId) {
    fetch(`${API_BASE}/group-sessions/leave`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            session_id: sessionId,
            task_id: taskId
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(async result => {
        if (!result.ok) {
            showToast(result.data.error || "Could not leave session", "warning");
            return;
        }

        const earned = result.data.earned_points || 0;
        showToast(`${result.data.message} • +${earned} pts`, "success");

        await refreshAll();
        loadLeaderboards();
        if (groupId) openGroup(groupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Could not leave session", "error");
    });
}

/* =========================
   PROOF
========================= */

function openProofModal(taskId) {
    const proofTaskId = document.getElementById("proofTaskId");
    const completedWorkInput = document.getElementById("completedWorkInput");
    const learnedSummaryInput = document.getElementById("learnedSummaryInput");
    const confidenceInput = document.getElementById("confidenceInput");
    const proofModal = document.getElementById("proofModal");

    if (proofTaskId) proofTaskId.value = taskId;
    if (completedWorkInput) completedWorkInput.value = "";
    if (learnedSummaryInput) learnedSummaryInput.value = "";
    if (confidenceInput) confidenceInput.value = "";

    if (proofModal) proofModal.classList.remove("hidden");
}

function closeProofModal() {
    const proofModal = document.getElementById("proofModal");
    if (proofModal) proofModal.classList.add("hidden");
}

function submitProof() {
    const taskId = document.getElementById("proofTaskId")?.value;
    const completedWork = document.getElementById("completedWorkInput")?.value.trim() || "";
    const learnedSummary = document.getElementById("learnedSummaryInput")?.value.trim() || "";
    const confidence = document.getElementById("confidenceInput")?.value || "";

    if (!completedWork || !learnedSummary || !confidence) {
        showToast("Fill all proof fields", "warning");
        return;
    }

    fetch(`${API_BASE}/tasks/${taskId}/submit-proof`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_id: currentUserId,
            completed_work: completedWork,
            learned_summary: learnedSummary,
            confidence: confidence
        })
    })
    .then(response => response.json().then(data => ({ ok: response.ok, data })))
    .then(result => {
        if (!result.ok) {
            showToast(result.data.error || "Proof submission failed", "warning");
            return;
        }

        showToast(result.data.message, "success");
        closeProofModal();
        loadAssignedTasks();
        if (selectedGroupId) openGroup(selectedGroupId);
    })
    .catch(error => {
        console.log(error);
        showToast("Proof submission failed", "error");
    });
}

/* =========================
   REFRESH
========================= */

function refreshAll() {
    return Promise.all([
        loadAvatarData(),
        loadProfile(),
        loadFocusStatus()
    ])
    .then(() => {
        loadAssignedTasks();
        loadLeaderboards();
        loadRestrictedApps();
        loadMyGroups();
    })
    .catch(error => {
        console.log(error);
    });
}

/* =========================
   EVENT BINDING
========================= */

document.addEventListener("DOMContentLoaded", function() {
    initTheme();
    switchBottomPanel("groups");

    const menuBtn = document.getElementById("menuBtn");
    const dropdownMenu = document.getElementById("dropdownMenu");
    const dashboardMenu = document.getElementById("dashboardMenu");
    const profileMenu = document.getElementById("profileMenu");
    const restrictedAppsMenu = document.getElementById("restrictedAppsMenu");
    const themeToggleMenu = document.getElementById("themeToggleMenu");

    const startBtn = document.getElementById("startBtn");
    const endBtn = document.getElementById("endBtn");
    const saveProfileBtn = document.getElementById("saveProfileBtn");
    const refreshBtn = document.getElementById("refreshBtn");

    const co2Button = document.getElementById("co2Button");
    const avatarModal = document.getElementById("avatarModal");
    const closeModal = document.getElementById("closeModal");

    const currentUserSelect = document.getElementById("currentUserSelect");
    const groupsTabBtn = document.getElementById("groupsTabBtn");
    const leaderboardTabBtn = document.getElementById("leaderboardTabBtn");

    if (groupsTabBtn) {
        groupsTabBtn.addEventListener("click", function() {
            switchBottomPanel("groups");
        });
    }

    if (leaderboardTabBtn) {
        leaderboardTabBtn.addEventListener("click", function() {
            switchBottomPanel("leaderboard");
            loadLeaderboards();
        });
    }

    if (currentUserSelect) {
        currentUserSelect.value = currentUserId;

        fetch(`${API_BASE}/set-current-user`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ user_id: currentUserId })
        })
        .then(() => {
            refreshAll();
        })
        .catch(error => {
            console.log(error);
        });

        currentUserSelect.addEventListener("change", function() {
            currentUserId = parseInt(currentUserSelect.value);
            selectedGroupId = null;
            selectedGroupData = null;

            fetch(`${API_BASE}/set-current-user`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ user_id: currentUserId })
            })
            .then(() => {
                const groupDetails = document.getElementById("groupDetails");
                if (groupDetails) {
                    groupDetails.innerHTML = "Select a group to view chat, tasks, active sessions, and leaderboard.";
                }
                refreshAll();
                switchBottomPanel("groups");
            })
            .catch(error => {
                console.log(error);
                showToast("Could not switch user.", "error");
            });
        });
    } else {
        refreshAll();
    }

    if (menuBtn && dropdownMenu) {
        menuBtn.addEventListener("click", function(event) {
            event.stopPropagation();
            dropdownMenu.style.display = dropdownMenu.style.display === "block" ? "none" : "block";
        });
    }

    if (dashboardMenu && dropdownMenu) {
        dashboardMenu.addEventListener("click", function() {
            showSection("dashboard");
            dropdownMenu.style.display = "none";
        });
    }

    if (profileMenu && dropdownMenu) {
        profileMenu.addEventListener("click", function() {
            showSection("profile");
            dropdownMenu.style.display = "none";
        });
    }

    if (restrictedAppsMenu && dropdownMenu) {
        restrictedAppsMenu.addEventListener("click", function() {
            showSection("restrictedApps");
            dropdownMenu.style.display = "none";
        });
    }

    if (themeToggleMenu && dropdownMenu) {
        themeToggleMenu.addEventListener("click", function() {
            toggleTheme();
            dropdownMenu.style.display = "none";
        });
    }

    window.addEventListener("click", function(event) {
        if (dropdownMenu && menuBtn && !dropdownMenu.contains(event.target) && event.target !== menuBtn) {
            dropdownMenu.style.display = "none";
        }
    });

    if (startBtn) startBtn.addEventListener("click", startSession);
    if (endBtn) endBtn.addEventListener("click", endSession);
    if (saveProfileBtn) saveProfileBtn.addEventListener("click", saveProfile);
    if (refreshBtn) {
        refreshBtn.addEventListener("click", function() {
            refreshAll();
            if (selectedGroupId) openGroup(selectedGroupId);
        });
    }

    if (co2Button && avatarModal) {
        co2Button.addEventListener("click", function() {
            if (!avatarData) return;

            const pointsInfo = document.getElementById("pointsInfo");
            const moodInfo = document.getElementById("moodInfo");
            const roomInfo = document.getElementById("roomInfo");
            const avatarTypeInfo = document.getElementById("avatarTypeInfo");

            if (pointsInfo) pointsInfo.innerText = "CO₂ Points: " + avatarData.co2_points;
            if (moodInfo) moodInfo.innerText = "Mood: " + avatarData.mood;
            if (roomInfo) roomInfo.innerText = "Room State: " + avatarData.room_state;
            if (avatarTypeInfo) avatarTypeInfo.innerText = "Avatar Style: " + avatarData.avatar_type;

            applyMascotState();
            avatarModal.style.display = "flex";
        });
    }

    if (closeModal && avatarModal) {
        closeModal.addEventListener("click", function() {
            avatarModal.style.display = "none";
        });
    }

    window.addEventListener("click", function(event) {
        if (avatarModal && event.target === avatarModal) {
            avatarModal.style.display = "none";
        }
    });
});
// ============================================================================
// EduPulse — Client Application & Alarm Engine
// ============================================================================

let currentTab = 'dashboard';
let dashboardData = null;
let allNotifications = [];
let allSubjects = [];
let weeklyChartInstance = null;
let subjectChartInstance = null;

// Timer State
let timerMode = 'pomodoro'; // pomodoro, shortBreak, longBreak, stopwatch
let timerSeconds = 25 * 60;
let timerRunning = false;
let timerInterval = null;
let timerStartTime = null;

// Audio Context for Web Audio API Sound Synthesizer
let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audioCtx = new AudioContext();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

// ============================================================================
// REAL WEB AUDIO SYNTHESIZED ALARMS
// ============================================================================
function playAlarmTone(type = 'urgent') {
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const masterGain = ctx.createGain();
  masterGain.connect(ctx.destination);
  masterGain.gain.setValueAtTime(0.3, now);

  if (type === 'urgent') {
    // Oscillating Urgent Alarm Siren (for overdue tasks & low attendance)
    const osc = ctx.createOscillator();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(800, now);
    osc.frequency.linearRampToValueAtTime(1200, now + 0.2);
    osc.frequency.linearRampToValueAtTime(800, now + 0.4);
    osc.frequency.linearRampToValueAtTime(1200, now + 0.6);
    osc.frequency.linearRampToValueAtTime(800, now + 0.8);

    masterGain.gain.setValueAtTime(0.4, now);
    masterGain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);

    osc.connect(masterGain);
    osc.start(now);
    osc.stop(now + 1.2);

  } else if (type === 'warning') {
    // Dual pulse chord
    [523.25, 659.25].forEach((freq) => {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);
      osc.connect(masterGain);
      osc.start(now);
      osc.stop(now + 0.4);
    });
    masterGain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

  } else if (type === 'chime' || type === 'gentle') {
    // Soft high chime
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, now); // A5
    osc.frequency.exponentialRampToValueAtTime(1760, now + 0.3);
    masterGain.gain.exponentialRampToValueAtTime(0.01, now + 0.8);
    osc.connect(masterGain);
    osc.start(now);
    osc.stop(now + 0.8);

  } else if (type === 'bell') {
    // Crystal bell for Pomodoro finish
    [587.33, 880, 1174.66].forEach((f, idx) => {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(f, now + (idx * 0.1));
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.25, now + (idx * 0.1));
      gain.gain.exponentialRampToValueAtTime(0.001, now + 1.5 + (idx * 0.1));
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + (idx * 0.1));
      osc.stop(now + 1.6 + (idx * 0.1));
    });
  }

  // Trigger mobile vibration if available
  if (navigator.vibrate) {
    navigator.vibrate([200, 100, 200, 100, 200]);
  }
}

function testAlarmSound(type = 'urgent') {
  playAlarmTone(type);
  showToast(`Testing Alarm Tone: ${type.toUpperCase()}`, 'info');
}

// ============================================================================
// TOAST NOTIFICATIONS & BANNER
// ============================================================================
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  const bg = type === 'critical' ? 'bg-red-600 border-red-500' :
             type === 'urgent' ? 'bg-orange-600 border-orange-500' :
             type === 'success' ? 'bg-green-600 border-green-500' :
             'bg-purple-700 border-purple-500';

  toast.className = `fixed top-16 right-4 z-50 px-4 py-3 rounded-2xl text-white font-medium text-xs shadow-2xl border flex items-center gap-2 transform transition-all duration-300 translate-y-[-20px] opacity-0 ${bg}`;
  toast.innerHTML = `
    <span class="w-2 h-2 rounded-full bg-white animate-ping"></span>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('translate-y-[-20px]', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-[-20px]');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ============================================================================
// NAVIGATION & TAB SWITCHING
// ============================================================================
function switchTab(tabId) {
  currentTab = tabId;

  // Hide all contents
  document.querySelectorAll('.tab-content').forEach((el) => el.classList.add('hidden'));
  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.remove('hidden');

  // Update desktop sidebar styles
  document.querySelectorAll('.nav-item').forEach((btn) => {
    if (btn.dataset.tab === tabId) {
      btn.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-white bg-purple-900/60 border border-purple-700/50';
    } else {
      btn.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition text-slate-400 hover:text-white hover:bg-navy-800';
    }
  });

  // Update mobile bottom nav
  document.querySelectorAll('.mobile-nav-item').forEach((btn) => {
    if (btn.dataset.tab === tabId) {
      btn.className = 'mobile-nav-item flex flex-col items-center gap-0.5 text-cyan-400 font-bold';
    } else {
      btn.className = 'mobile-nav-item flex flex-col items-center gap-0.5 text-slate-400';
    }
  });

  // Page title mapping
  const titles = {
    dashboard: 'Student Academic Dashboard',
    timetable: 'Smart Study Planner & Weekly Timetable',
    tasks: 'Tasks, Deadlines & Assignments',
    study: 'Study Time Tracker & Focus Engine',
    alerts: 'Complete Academic Notification Center',
    subjects: 'Subject & Academic Management',
    library: 'Modules & Study Materials Library',
    reports: 'Academic Analytics & Certified Reports',
    settings: 'System Preferences & Rules'
  };
  document.getElementById('page-title').innerText = titles[tabId] || 'EduPulse';

  // Load specific tab data
  if (tabId === 'dashboard') loadDashboard();
  else if (tabId === 'timetable') loadTimetable();
  else if (tabId === 'tasks') loadTasks();
  else if (tabId === 'study') loadStudyStats();
  else if (tabId === 'alerts') loadNotifications();
  else if (tabId === 'subjects') loadSubjectsManagement();
  else if (tabId === 'library') loadLibrary();

  if (window.lucide) window.lucide.createIcons();
}

// ============================================================================
// DATA FETCHING & RENDERING
// ============================================================================
async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    dashboardData = await res.json();

    // Render Metrics
    document.getElementById('metric-overall-attendance').innerText = `${dashboardData.overall_attendance}%`;
    const attBadge = document.getElementById('metric-attendance-badge');
    const attBar = document.getElementById('metric-attendance-bar');
    attBar.style.width = `${Math.min(100, dashboardData.overall_attendance)}%`;

    if (dashboardData.overall_attendance >= 80) {
      attBadge.innerText = 'Safe';
      attBadge.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-status-safe/20 text-status-safe';
    } else if (dashboardData.overall_attendance >= 75) {
      attBadge.innerText = 'Warning';
      attBadge.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-status-warning/20 text-status-warning';
    } else {
      attBadge.innerText = 'Critical';
      attBadge.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded bg-status-critical/20 text-status-critical';
    }

    // Study metric
    document.getElementById('metric-study-today').innerText = `${dashboardData.today_study_mins}m`;
    const studyPct = Math.min(100, Math.round((dashboardData.today_study_mins / Math.max(1, dashboardData.daily_study_goal)) * 100));
    document.getElementById('metric-study-bar').style.width = `${studyPct}%`;

    // Tasks metric
    document.getElementById('metric-tasks-pending').innerText = dashboardData.tasks_pending;
    const odSpan = document.getElementById('metric-tasks-overdue');
    if (dashboardData.tasks_overdue > 0) {
      odSpan.innerText = `${dashboardData.tasks_overdue} Overdue`;
      odSpan.classList.remove('hidden');
    } else {
      odSpan.classList.add('hidden');
    }

    // Unread count
    document.getElementById('sidebar-notif-count').innerText = dashboardData.unread_notifications;
    document.getElementById('header-unread-badge').innerText = dashboardData.unread_notifications;
    document.getElementById('mobile-unread-badge').innerText = dashboardData.unread_notifications;
    document.getElementById('critical-count').innerText = dashboardData.critical_issues_count;

    // ACTION REQUIRED LIST
    renderActionRequired(dashboardData.action_required);

    // TODAY'S TIMETABLE
    renderDashboardTimetable(dashboardData.today_timetable);

    // ATTENDANCE GRID
    renderAttendanceGrid(dashboardData.subjects);

    // UPCOMING EXAMS
    renderDashboardExams(dashboardData.upcoming_exams);

    // PROJECTS
    renderDashboardProjects(dashboardData.projects);

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

function renderActionRequired(actions) {
  const container = document.getElementById('action-required-list');
  if (!actions || actions.length === 0) {
    container.innerHTML = `
      <div class="p-4 bg-navy-850 border border-green-800/40 rounded-xl flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-status-safe/20 text-status-safe flex items-center justify-center">
          <i data-lucide="check" class="w-4 h-4"></i>
        </div>
        <div>
          <h4 class="text-xs font-bold text-white">All Clear — No Urgent Issues Detected</h4>
          <p class="text-[11px] text-slate-400">All assignments on track, attendance safely above threshold, and no overdue work.</p>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = actions.map((item) => {
    const isCritical = item.color === 'red';
    const isWarning = item.color === 'orange';
    const border = isCritical ? 'border-red-700/80 bg-red-950/40 critical-glow' :
                   isWarning ? 'border-orange-700/80 bg-orange-950/30' :
                   'border-yellow-700/60 bg-yellow-950/20';

    const badgeBg = isCritical ? 'bg-red-600' : isWarning ? 'bg-orange-600' : 'bg-yellow-600';
    const icon = isCritical ? 'alert-octagon' : isWarning ? 'alert-triangle' : 'clock';

    return `
      <div class="p-3.5 border rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${border}">
        <div class="flex items-start sm:items-center gap-3">
          <div class="w-8 h-8 rounded-xl ${badgeBg}/20 flex items-center justify-center text-${item.color}-400 shrink-0 mt-0.5 sm:mt-0">
            <i data-lucide="${icon}" class="w-4 h-4"></i>
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[9px] font-black uppercase px-1.5 py-0.5 rounded text-white ${badgeBg}">${item.badge}</span>
              <h4 class="text-xs font-bold text-white">${item.title}</h4>
            </div>
            <p class="text-[11px] text-slate-300 mt-0.5">${item.description}</p>
          </div>
        </div>
        <button onclick="handleActionClick('${item.link_type}', '${item.link_id}')" class="px-3 py-1.5 ${badgeBg} hover:opacity-90 rounded-xl text-xs font-bold text-white whitespace-nowrap self-end sm:self-center transition">
          ${item.action_text}
        </button>
      </div>
    `;
  }).join('');
}

function handleActionClick(type, id) {
  if (type === 'subject') {
    openAttendanceModal(id);
  } else if (type === 'assignment' || type === 'task') {
    switchTab('tasks');
  } else if (type === 'study') {
    switchTab('study');
  } else if (type === 'project') {
    switchTab('dashboard');
  }
}

function renderDashboardTimetable(entries) {
  const container = document.getElementById('dashboard-timetable-list');
  if (!entries || entries.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-4 text-center">No classes scheduled for today.</p>`;
    return;
  }

  container.innerHTML = entries.map((e) => `
    <div class="p-3 bg-navy-900 border border-navy-800 rounded-xl flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-2 h-10 rounded-full" style="background-color: ${e.subject_color}"></div>
        <div>
          <h4 class="text-xs font-bold text-white">${e.subject_name} (${e.subject_code})</h4>
          <p class="text-[11px] text-slate-400">${e.classroom} • ${e.faculty_name || 'Staff'}</p>
        </div>
      </div>
      <div class="text-right">
        <span class="text-xs font-mono font-bold text-purple-300">${e.start_time} - ${e.end_time}</span>
        <span class="block text-[10px] text-slate-500">Scheduled</span>
      </div>
    </div>
  `).join('');
}

function renderAttendanceGrid(subjects) {
  const container = document.getElementById('dashboard-attendance-grid');
  if (!subjects) return;

  container.innerHTML = subjects.map((s) => {
    const m = s.metrics;
    const isCritical = m.status === 'Critical' || m.status === 'Recovery';
    const isWarning = m.status === 'Warning';
    const statusColor = isCritical ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-green-400';
    const badgeBg = isCritical ? 'bg-red-500/20 text-red-400 border-red-500/40' :
                    isWarning ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' :
                    'bg-green-500/20 text-green-400 border-green-500/40';

    return `
      <div class="p-4 bg-navy-900 border border-navy-800 rounded-xl space-y-3 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="text-xs font-bold text-white truncate">${s.name}</h4>
            <span class="text-[10px] font-mono text-slate-400">${s.code}</span>
          </div>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeBg}">${m.status}</span>
        </div>

        <div class="flex items-baseline justify-between">
          <div>
            <span class="text-xl font-black ${statusColor}">${m.percentage}%</span>
            <span class="text-[10px] text-slate-400 ml-1">(${s.attended_classes}/${s.total_classes})</span>
          </div>
          <span class="text-[10px] text-slate-400">Target: ${s.target_attendance}%</span>
        </div>

        <div class="w-full bg-navy-800 h-1.5 rounded-full overflow-hidden">
          <div class="h-full rounded-full ${isCritical ? 'bg-red-500' : isWarning ? 'bg-yellow-500' : 'bg-green-500'}" style="width: ${m.percentage}%"></div>
        </div>

        <div class="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px]">
          <span class="${statusColor} font-semibold">
            ${m.classes_needed > 0 ? `Need ${m.classes_needed} classes` : `Can miss ${m.can_miss} classes`}
          </span>
          <button onclick="openAttendanceModal('${s.id}')" class="text-cyan-400 hover:text-cyan-300 font-bold">
            + Log
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderDashboardExams(exams) {
  const container = document.getElementById('dashboard-exams-list');
  if (!exams || exams.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-3">No examinations scheduled.</p>`;
    return;
  }

  container.innerHTML = exams.map((e) => `
    <div class="p-3 bg-navy-900 border border-navy-800 rounded-xl flex items-center justify-between">
      <div>
        <div class="flex items-center gap-1.5">
          <span class="text-[9px] font-bold uppercase px-1.5 py-0.2 rounded bg-purple-900 text-purple-200">${e.exam_type.replace('_', ' ')}</span>
          <h4 class="text-xs font-bold text-white">${e.title}</h4>
        </div>
        <p class="text-[11px] text-slate-400 mt-0.5">${e.subject_name} • Venue: ${e.classroom || 'Hall'}</p>
      </div>
      <div class="text-right">
        <span class="text-xs font-bold text-yellow-400">${e.exam_date}</span>
        <span class="block text-[10px] text-slate-400">${e.start_time}</span>
      </div>
    </div>
  `).join('');
}

function renderDashboardProjects(projects) {
  const container = document.getElementById('dashboard-projects-list');
  if (!projects || projects.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-3">No active projects.</p>`;
    return;
  }

  container.innerHTML = projects.map((p) => `
    <div class="p-3.5 bg-navy-900 border border-navy-800 rounded-xl space-y-2">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-white">${p.title}</h4>
        <span class="text-[10px] font-bold text-cyan-400 font-mono">${p.progress_percentage}%</span>
      </div>
      <div class="w-full bg-navy-800 h-1.5 rounded-full overflow-hidden">
        <div class="h-full bg-gradient-to-r from-purple-500 to-cyan-400 rounded-full" style="width: ${p.progress_percentage}%"></div>
      </div>
      <div class="flex items-center justify-between text-[10px] text-slate-400">
        <span>Supervisor: ${p.supervisor_name || 'Staff'}</span>
        <span>Deadline: ${p.deadline}</span>
      </div>
    </div>
  `).join('');
}

// ============================================================================
// TIMETABLE & PLANNER TAB
// ============================================================================
async function loadTimetable() {
  try {
    const res = await fetch('/api/timetable');
    const scheduleByDay = await res.json();
    filterTimetableDay(0, scheduleByDay);
  } catch (err) {
    console.error('Error loading timetable:', err);
  }
}

async function filterTimetableDay(dayIndex, cachedSchedule = null) {
  // Update day buttons
  document.querySelectorAll('.day-tab').forEach((b) => {
    if (parseInt(b.dataset.day) === dayIndex) {
      b.className = 'day-tab px-4 py-2 rounded-xl text-xs font-bold transition bg-purple-600 text-white';
    } else {
      b.className = 'day-tab px-4 py-2 rounded-xl text-xs font-bold transition bg-navy-800 text-slate-400 hover:text-white';
    }
  });

  const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  document.getElementById('selected-day-heading').innerText = `${dayNames[dayIndex]} Classes & Alarms`;

  let schedule = cachedSchedule;
  if (!schedule) {
    const res = await fetch('/api/timetable');
    schedule = await res.json();
  }

  const items = schedule[dayIndex] || [];
  const container = document.getElementById('timetable-schedule-items');
  if (items.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-6 text-center">No scheduled lectures on ${dayNames[dayIndex]}. Enjoy your study time!</p>`;
    return;
  }

  container.innerHTML = items.map((e) => `
    <div class="p-4 bg-navy-900 border border-navy-800 rounded-2xl flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-purple-900/40 flex items-center justify-center font-bold text-xs text-purple-300">
          ${e.subject_code}
        </div>
        <div>
          <h4 class="text-xs font-bold text-white">${e.subject_name}</h4>
          <p class="text-[11px] text-slate-400">${e.classroom || 'Room 101'} • ${e.faculty_name || 'Faculty'}</p>
          ${e.notes ? `<p class="text-[10px] text-cyan-300 mt-0.5">${e.notes}</p>` : ''}
        </div>
      </div>
      <div class="text-right">
        <span class="text-xs font-mono font-bold text-white">${e.start_time} - ${e.end_time}</span>
        <div class="flex items-center gap-1.5 mt-1 justify-end">
          <span class="w-2 h-2 rounded-full bg-green-400"></span>
          <span class="text-[10px] text-slate-400">Alarm: 15m prior</span>
        </div>
      </div>
    </div>
  `).join('');

  if (window.lucide) window.lucide.createIcons();
}

// ============================================================================
// TASKS & DEADLINES TAB
// ============================================================================
async function loadTasks() {
  try {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    renderTasksList(tasks);
    renderTasksKanban(tasks);
  } catch (err) {
    console.error('Error loading tasks:', err);
  }
}

function renderTasksList(tasks) {
  const container = document.getElementById('tasks-list-container');
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-6 text-center">No tasks recorded.</p>`;
    return;
  }

  container.innerHTML = tasks.map((t) => {
    const isCompleted = t.status === 'completed';
    const isOverdue = t.status === 'overdue';
    const isUrgent = t.priority === 'urgent';

    const border = isOverdue ? 'border-red-700/80 bg-red-950/20' :
                   isCompleted ? 'border-green-800/40 bg-navy-900/60 opacity-75' :
                   'border-navy-800 bg-navy-850';

    const prioColor = isUrgent ? 'bg-red-600' :
                      t.priority === 'high' ? 'bg-orange-600' : 'bg-purple-700';

    return `
      <div class="p-4 border rounded-2xl flex items-center justify-between gap-4 transition ${border}">
        <div class="flex items-center gap-3">
          <button onclick="markTaskComplete('${t.id}')" class="w-6 h-6 rounded-lg border ${isCompleted ? 'bg-status-safe border-status-safe' : 'border-slate-500 hover:border-cyan-400'} flex items-center justify-center transition">
            ${isCompleted ? '<i data-lucide="check" class="w-4 h-4 text-white"></i>' : ''}
          </button>
          <div>
            <div class="flex items-center gap-2">
              <span class="text-[9px] font-bold uppercase px-1.5 py-0.2 rounded text-white ${prioColor}">${t.priority}</span>
              <h4 class="text-xs font-bold ${isCompleted ? 'line-through text-slate-400' : 'text-white'}">${t.title}</h4>
            </div>
            <p class="text-[11px] text-slate-400 mt-0.5">${t.subject_name || 'General Task'} • Due: ${t.due_date} ${t.due_time || ''}</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          ${isOverdue ? '<span class="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-red-600 text-white">OVERDUE</span>' : ''}
          ${isCompleted ? '<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-green-500/20 text-green-400">DONE</span>' : ''}
        </div>
      </div>
    `;
  }).join('');

  if (window.lucide) window.lucide.createIcons();
}

function renderTasksKanban(tasks) {
  const notStarted = tasks.filter((t) => t.status === 'not_started');
  const inProgress = tasks.filter((t) => t.status === 'in_progress');
  const completed = tasks.filter((t) => t.status === 'completed');

  document.getElementById('kanban-count-not-started').innerText = notStarted.length;
  document.getElementById('kanban-count-in-progress').innerText = inProgress.length;
  document.getElementById('kanban-count-completed').innerText = completed.length;

  const renderCol = (list) => list.map((t) => `
    <div class="p-3 bg-navy-900 border border-navy-800 rounded-xl space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-[9px] font-bold uppercase px-1.5 py-0.2 rounded bg-purple-900 text-purple-200">${t.priority}</span>
        <span class="text-[10px] text-slate-400">${t.due_date}</span>
      </div>
      <h5 class="text-xs font-bold text-white">${t.title}</h5>
      <p class="text-[10px] text-slate-400 truncate">${t.subject_name || ''}</p>
    </div>
  `).join('');

  document.getElementById('kanban-col-not-started').innerHTML = renderCol(notStarted);
  document.getElementById('kanban-col-in-progress').innerHTML = renderCol(inProgress);
  document.getElementById('kanban-col-completed').innerHTML = renderCol(completed);
}

function toggleTaskView(view) {
  if (view === 'list') {
    document.getElementById('tasks-list-container').classList.remove('hidden');
    document.getElementById('tasks-kanban-container').classList.add('hidden');
    document.getElementById('btn-view-list').className = 'p-1.5 rounded-lg bg-purple-600 text-white text-xs';
    document.getElementById('btn-view-kanban').className = 'p-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs';
  } else {
    document.getElementById('tasks-list-container').classList.add('hidden');
    document.getElementById('tasks-kanban-container').classList.remove('hidden');
    document.getElementById('btn-view-list').className = 'p-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs';
    document.getElementById('btn-view-kanban').className = 'p-1.5 rounded-lg bg-purple-600 text-white text-xs';
  }
}

async function markTaskComplete(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/complete`, { method: 'PATCH' });
    if (res.ok) {
      if (window.confetti) {
        window.confetti({ particleCount: 60, spread: 55, origin: { y: 0.7 } });
      }
      playAlarmTone('chime');
      showToast('Task marked completed & reminders cancelled!', 'success');
      loadTasks();
      loadDashboard();
    }
  } catch (err) {
    console.error('Error completing task:', err);
  }
}

// ============================================================================
// STUDY TIME TRACKER & CHARTS
// ============================================================================
function setTimerMode(mode, mins) {
  timerMode = mode;
  timerRunning = false;
  clearInterval(timerInterval);
  timerSeconds = mins * 60;
  updateTimerDisplay();

  document.querySelectorAll('[id^="timer-mode-"]').forEach((btn) => {
    btn.className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition text-slate-400 hover:text-white';
  });
  document.getElementById(`timer-mode-${mode}`).className = 'px-4 py-1.5 rounded-xl text-xs font-bold transition bg-purple-600 text-white';

  document.getElementById('timer-btn-text').innerText = 'Start Focus Session';
  document.getElementById('timer-status-label').innerText = `${mode.toUpperCase()} READY`;
}

function updateTimerDisplay() {
  const mins = Math.floor(timerSeconds / 60);
  const secs = timerSeconds % 60;
  document.getElementById('timer-display').innerText =
    `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function toggleTimer() {
  if (timerRunning) {
    // Pause
    timerRunning = false;
    clearInterval(timerInterval);
    document.getElementById('timer-btn-text').innerText = 'Resume';
    document.getElementById('timer-status-label').innerText = 'SESSION PAUSED';
  } else {
    // Start
    getAudioContext(); // Enable sound
    timerRunning = true;
    timerStartTime = new Date();
    document.getElementById('timer-btn-text').innerText = 'Pause';
    document.getElementById('timer-status-label').innerText = 'FOCUSING IN PROGRESS...';

    timerInterval = setInterval(() => {
      if (timerMode === 'stopwatch') {
        timerSeconds++;
      } else {
        if (timerSeconds > 0) {
          timerSeconds--;
        } else {
          // Timer finished!
          clearInterval(timerInterval);
          timerRunning = false;
          playAlarmTone('bell');
          showToast('Pomodoro session completed! Take a well-deserved break.', 'success');
          saveTimerSession();
          return;
        }
      }
      updateTimerDisplay();
    }, 1000);
  }
}

function resetTimer() {
  clearInterval(timerInterval);
  timerRunning = false;
  timerSeconds = (timerMode === 'pomodoro' ? 25 : timerMode === 'shortBreak' ? 5 : 15) * 60;
  updateTimerDisplay();
  document.getElementById('timer-btn-text').innerText = 'Start Focus Session';
  document.getElementById('timer-status-label').innerText = 'READY TO FOCUS';
}

async function saveTimerSession() {
  const subSelect = document.getElementById('timer-subject-select');
  const subjectId = subSelect ? subSelect.value : null;

  try {
    await fetch('/api/study/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject_id: subjectId,
        start_time: timerStartTime ? timerStartTime.toISOString() : new Date().toISOString(),
        end_time: new Date().toISOString(),
        duration_minutes: 25,
        session_type: 'pomodoro',
        notes: 'Pomodoro focus sprint completed.'
      })
    });
    loadStudyStats();
    loadDashboard();
  } catch (e) {
    console.error('Error saving study session:', e);
  }
}

async function loadStudyStats() {
  try {
    const res = await fetch('/api/study/stats');
    const data = await res.json();

    // Render Weekly Bar Chart
    const ctxWeekly = document.getElementById('chart-weekly-study');
    if (ctxWeekly && window.Chart) {
      if (weeklyChartInstance) weeklyChartInstance.destroy();
      weeklyChartInstance = new Chart(ctxWeekly, {
        type: 'bar',
        data: {
          labels: data.weekly_chart.map((d) => d.day),
          datasets: [{
            label: 'Study Hours',
            data: data.weekly_chart.map((d) => d.hours),
            backgroundColor: '#6366F1',
            borderRadius: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
            y: { grid: { color: '#1E293B' }, ticks: { color: '#94A3B8' } }
          }
        }
      });
    }

    // Render Subject Distribution Chart
    const ctxSub = document.getElementById('chart-subject-study');
    if (ctxSub && window.Chart && data.subject_distribution.length > 0) {
      if (subjectChartInstance) subjectChartInstance.destroy();
      subjectChartInstance = new Chart(ctxSub, {
        type: 'doughnut',
        data: {
          labels: data.subject_distribution.map((s) => s.code),
          datasets: [{
            data: data.subject_distribution.map((s) => s.total_mins),
            backgroundColor: data.subject_distribution.map((s) => s.color || '#38BDF8'),
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { color: '#CBD5E1', boxWidth: 12 } }
          }
        }
      });
    }
  } catch (err) {
    console.error('Error loading study stats:', err);
  }
}

// ============================================================================
// NOTIFICATION CENTER
// ============================================================================
async function loadNotifications(cat = 'all') {
  try {
    const url = cat === 'all' ? '/api/notifications' : `/api/notifications?category=${cat}`;
    const res = await fetch(url);
    allNotifications = await res.json();

    const container = document.getElementById('notification-center-list');
    if (!allNotifications || allNotifications.length === 0) {
      container.innerHTML = `<p class="text-xs text-slate-400 py-8 text-center">No notifications in this category.</p>`;
      return;
    }

    container.innerHTML = allNotifications.map((n) => {
      const isCritical = n.category === 'critical' || n.category === 'overdue';
      const isUnread = !n.is_read;

      const badgeBg = n.category === 'critical' ? 'bg-red-600' :
                      n.category === 'overdue' ? 'bg-red-700' :
                      n.category === 'assignment' ? 'bg-orange-600' :
                      n.category === 'exam' ? 'bg-yellow-600' :
                      n.category === 'timetable' ? 'bg-cyan-600' : 'bg-purple-600';

      return `
        <div class="p-4 bg-navy-850 border ${isUnread ? 'border-purple-600/80 bg-navy-800/80' : 'border-navy-800'} rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-start gap-3">
            <span class="w-2.5 h-2.5 rounded-full ${isUnread ? 'bg-cyan-400 animate-pulse' : 'bg-transparent'} mt-1.5 shrink-0"></span>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[9px] font-black uppercase px-1.5 py-0.2 rounded text-white ${badgeBg}">${n.category}</span>
                <h4 class="text-xs font-bold text-white">${n.title}</h4>
              </div>
              <p class="text-[11px] text-slate-300 mt-1">${n.message}</p>
              <span class="text-[10px] text-slate-500 mt-1 block">${new Date(n.trigger_time || n.created_at).toLocaleString()}</span>
            </div>
          </div>

          <div class="flex items-center gap-2 self-end sm:self-center">
            <button onclick="snoozeNotification('${n.id}', 15)" class="px-2.5 py-1 bg-navy-800 hover:bg-navy-700 text-slate-300 rounded-lg text-xs font-semibold">
              Snooze
            </button>
            <button onclick="resolveNotification('${n.id}')" class="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-bold">
              Resolve
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    console.error('Error loading notifications:', err);
  }
}

function filterNotifs(cat) {
  document.querySelectorAll('.notif-tab').forEach((b) => {
    if (b.dataset.cat === cat) {
      b.className = 'notif-tab px-3 py-1.5 rounded-xl text-xs font-bold bg-purple-600 text-white';
    } else {
      b.className = 'notif-tab px-3 py-1.5 rounded-xl text-xs font-bold bg-navy-800 text-slate-400 hover:text-white';
    }
  });
  loadNotifications(cat);
}

async function markAllNotificationsAsRead() {
  await fetch('/api/notifications/mark-all-read', { method: 'POST' });
  loadNotifications();
  loadDashboard();
  showToast('All notifications marked as read', 'success');
}

async function snoozeNotification(id, mins = 15) {
  await fetch(`/api/notifications/${id}/snooze?minutes=${mins}`, { method: 'POST' });
  loadNotifications();
  loadDashboard();
  showToast(`Notification snoozed for ${mins} minutes`, 'info');
}

async function resolveNotification(id) {
  await fetch(`/api/notifications/${id}/resolve`, { method: 'POST' });
  loadNotifications();
  loadDashboard();
  showToast('Underlying issue resolved', 'success');
}

async function triggerEngineTick() {
  const res = await fetch('/api/reminder-engine/trigger', { method: 'POST' });
  const data = await res.json();
  showToast('Reminder Engine evaluated all academic rules!', 'info');
  loadNotifications();
  loadDashboard();
}

// ============================================================================
// SUBJECTS MANAGEMENT TAB
// ============================================================================
async function loadSubjectsManagement() {
  try {
    const res = await fetch('/api/subjects');
    allSubjects = await res.json();

    const container = document.getElementById('subjects-management-grid');
    container.innerHTML = allSubjects.map((s) => {
      const m = s.metrics;
      return `
        <div class="p-5 bg-navy-850 border border-navy-800 rounded-3xl space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-900/60 text-purple-200 font-bold">${s.code}</span>
              <h3 class="text-sm font-bold text-white mt-1">${s.name}</h3>
            </div>
            <span class="text-2xl font-black ${m.percentage < s.target_attendance ? 'text-red-400' : 'text-green-400'}">${m.percentage}%</span>
          </div>

          <div class="grid grid-cols-3 gap-2 text-center p-3 bg-navy-900 rounded-2xl">
            <div>
              <span class="text-[10px] text-slate-400">Attended</span>
              <p class="text-xs font-bold text-white">${s.attended_classes}</p>
            </div>
            <div>
              <span class="text-[10px] text-slate-400">Total</span>
              <p class="text-xs font-bold text-white">${s.total_classes}</p>
            </div>
            <div>
              <span class="text-[10px] text-slate-400">Missed</span>
              <p class="text-xs font-bold text-red-400">${m.missed}</p>
            </div>
          </div>

          <p class="text-[11px] text-slate-300">${m.message}</p>

          <div class="pt-2 border-t border-navy-800 flex items-center justify-between">
            <span class="text-[11px] text-slate-400">Faculty: ${s.faculty_name || 'Staff'}</span>
            <button onclick="openAttendanceModal('${s.id}')" class="px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold text-white transition">
              Log Class Attendance
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading subjects management:', err);
  }
}

// ============================================================================
// DIGITAL ACADEMIC LIBRARY TAB
// ============================================================================
async function loadLibrary() {
  try {
    const res = await fetch('/api/library');
    const library = await res.json();

    const container = document.getElementById('library-hierarchy-container');
    container.innerHTML = library.map((s) => `
      <div class="p-5 bg-navy-850 border border-navy-800 rounded-3xl space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-xl bg-purple-900/60 flex items-center justify-center font-bold text-xs text-purple-300">
              ${s.code}
            </div>
            <div>
              <h3 class="text-sm font-bold text-white">${s.name}</h3>
              <p class="text-[11px] text-slate-400">${s.modules.length} Units • ${s.materials.length} Resources & PYQs</p>
            </div>
          </div>
        </div>

        <!-- Units / Modules -->
        <div class="space-y-2">
          <h4 class="text-[11px] font-bold uppercase tracking-wider text-purple-300">Syllabus Units & Progress</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            ${s.modules.map((m) => `
              <div class="p-2.5 bg-navy-900 border border-navy-800 rounded-xl flex items-center justify-between">
                <div>
                  <span class="text-[9px] font-bold text-cyan-400">Unit ${m.unit_number}</span>
                  <p class="text-xs font-semibold text-white truncate">${m.title}</p>
                </div>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded ${m.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}">
                  ${m.syllabus_percentage}%
                </span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Materials & PYQs -->
        <div class="space-y-2 pt-2 border-t border-navy-800">
          <h4 class="text-[11px] font-bold uppercase tracking-wider text-purple-300">Uploaded Study Materials & PYQ Papers</h4>
          <div class="space-y-2">
            ${s.materials.map((mat) => `
              <div class="p-2.5 bg-navy-900 border border-navy-800 rounded-xl flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="${mat.material_type === 'pyq' ? 'award' : 'file-text'}" class="w-4 h-4 text-cyan-400"></i>
                  <div>
                    <h5 class="text-xs font-bold text-white">${mat.title}</h5>
                    <p class="text-[10px] text-slate-400">${mat.material_type.toUpperCase()} ${mat.exam_year ? `• Year ${mat.exam_year}` : ''}</p>
                  </div>
                </div>
                <a href="${mat.file_url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-navy-800 hover:bg-navy-700 text-xs font-semibold text-cyan-400 flex items-center gap-1">
                  <i data-lucide="download" class="w-3.5 h-3.5"></i> Download
                </a>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    console.error('Error loading library:', err);
  }
}

// ============================================================================
// MODAL CONTROLS & SUBMISSIONS
// ============================================================================
function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

async function populateSubjectDropdowns() {
  try {
    const res = await fetch('/api/subjects');
    const subjects = await res.json();
    const options = subjects.map((s) => `<option value="${s.id}">${s.code} - ${s.name}</option>`).join('');

    ['qa-asg-subject', 'qa-task-subject', 'qa-exam-subject', 'modal-att-subject', 'manual-study-subject', 'timer-subject-select'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = options;
    });
  } catch (e) {
    console.error('Error populating dropdowns:', e);
  }
}

function openQuickAddModal(type = 'asg') {
  populateSubjectDropdowns();
  switchQuickAddTab(type);
  openModal('modal-quick-add');
}

function switchQuickAddTab(tab) {
  document.querySelectorAll('.qa-tab').forEach((b) => {
    b.className = 'qa-tab flex-1 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white';
  });
  document.getElementById(`qa-tab-${tab}`).className = 'qa-tab flex-1 py-1.5 rounded-lg text-xs font-bold bg-purple-600 text-white';

  ['asg', 'task', 'exam'].forEach((t) => {
    document.getElementById(`qa-form-${t}`).classList.add('hidden');
  });
  document.getElementById(`qa-form-${tab}`).classList.remove('hidden');
}

async function submitQuickAssignment(e) {
  e.preventDefault();
  const data = {
    title: document.getElementById('qa-asg-title').value,
    subject_id: document.getElementById('qa-asg-subject').value,
    priority: document.getElementById('qa-asg-priority').value,
    due_date: document.getElementById('qa-asg-date').value,
    due_time: document.getElementById('qa-asg-time').value,
    description: document.getElementById('qa-asg-desc').value
  };

  await fetch('/api/assignments', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  closeModal('modal-quick-add');
  showToast('Assignment created & 6 deadline alarm jobs scheduled!', 'success');
  loadDashboard();
}

async function submitQuickTask(e) {
  e.preventDefault();
  const data = {
    title: document.getElementById('qa-task-title').value,
    subject_id: document.getElementById('qa-task-subject').value,
    task_type: document.getElementById('qa-task-type').value,
    priority: document.getElementById('qa-task-priority').value,
    due_date: document.getElementById('qa-task-date').value
  };

  await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  closeModal('modal-quick-add');
  showToast('Task added to schedule!', 'success');
  loadTasks();
  loadDashboard();
}

async function submitQuickExam(e) {
  e.preventDefault();
  const data = {
    title: document.getElementById('qa-exam-title').value,
    subject_id: document.getElementById('qa-exam-subject').value,
    exam_type: document.getElementById('qa-exam-type').value,
    exam_date: document.getElementById('qa-exam-date').value,
    start_time: document.getElementById('qa-exam-time').value
  };

  await fetch('/api/exams', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  closeModal('modal-quick-add');
  showToast('Exam scheduled with 14d, 7d, 3d, 1d reminder alarms!', 'success');
  loadDashboard();
}

// Attendance Modal
function openAttendanceModal(subjectId = null) {
  populateSubjectDropdowns();
  openModal('modal-attendance');
  if (subjectId) {
    setTimeout(() => {
      const el = document.getElementById('modal-att-subject');
      if (el) el.value = subjectId;
      previewAttendanceChange();
    }, 50);
  }
}

async function recordAttendanceAction(status) {
  const subjectId = document.getElementById('modal-att-subject').value;
  const res = await fetch(`/api/subjects/${subjectId}/attendance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject_id: subjectId, status: status })
  });
  const data = await res.json();
  closeModal('modal-attendance');

  if (data.metrics && data.metrics.status === 'Critical') {
    playAlarmTone('urgent');
    showToast(`Low Attendance Warning: ${data.metrics.percentage}%`, 'critical');
  } else {
    showToast(`Attendance recorded (${status.toUpperCase()})!`, 'success');
  }
  loadDashboard();
}

function previewAttendanceChange() {
  // Live calculation preview in modal
  const el = document.getElementById('att-prev-current');
  if (el) el.innerText = 'Dynamic Preview Ready';
}

// Linways Modal
function openLinwaysModal() {
  openModal('modal-linways');
}

function loadSampleCSV() {
  document.getElementById('csv-content-box').value =
`SubjectCode,Attended,Total
CS301,27,37
CS302,36,42
CS303,31,40
CS304,33,42
CS305,32,38`;
}

async function submitCSVImport() {
  const fileType = document.getElementById('csv-import-type').value;
  const content = document.getElementById('csv-content-box').value;
  const formData = new FormData();
  formData.append('file_type', fileType);
  formData.append('content', content);

  const res = await fetch('/api/integration/import-csv', {
    method: 'POST',
    body: formData
  });
  const data = await res.json();
  closeModal('modal-linways');
  showToast(data.message, 'success');
  loadDashboard();
}

// Manual study time
function openManualTimeModal() {
  populateSubjectDropdowns();
  openModal('modal-manual-time');
}

async function submitManualStudy(e) {
  e.preventDefault();
  const data = {
    subject_id: document.getElementById('manual-study-subject').value,
    duration_minutes: parseInt(document.getElementById('manual-study-mins').value),
    notes: document.getElementById('manual-study-notes').value,
    start_time: new Date().toISOString(),
    end_time: new Date().toISOString(),
    session_type: 'manual'
  };

  await fetch('/api/study/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  closeModal('modal-manual-time');
  showToast('Study session recorded to academic record!', 'success');
  loadStudyStats();
  loadDashboard();
}

// Settings
async function saveSettings(e) {
  e.preventDefault();
  const thresh = parseFloat(document.getElementById('setting-threshold').value);
  const goal = parseInt(document.getElementById('setting-study-goal').value);
  const quietStart = document.getElementById('setting-quiet-start').value;
  const quietEnd = document.getElementById('setting-quiet-end').value;
  const sound = document.getElementById('setting-sound').checked;
  const push = document.getElementById('setting-push').checked;

  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      default_attendance_threshold: thresh,
      daily_study_goal_minutes: goal,
      quiet_hours_start: quietStart,
      quiet_hours_end: quietEnd,
      in_app_sound: sound,
      browser_push: push
    })
  });
  showToast('Settings saved successfully!', 'success');
}

async function resetDemoData() {
  if (confirm('Reset EduPulse dataset to original demo state (Alex Chen CS Sem 5)?')) {
    await fetch('/api/demo/reset', { method: 'POST' });
    showToast('Database reset to clean demo state!', 'info');
    loadDashboard();
  }
}

// ============================================================================
// LIVE CLOCK & COUNTDOWN TICKER
// ============================================================================
function startLiveClock() {
  setInterval(() => {
    const now = new Date();
    const clockEl = document.getElementById('live-clock');
    if (clockEl) {
      clockEl.innerText = now.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
  }, 1000);
}

// ============================================================================
// INITIALIZATION
// ============================================================================
window.addEventListener('DOMContentLoaded', () => {
  startLiveClock();
  loadDashboard();
  populateSubjectDropdowns();

  // Register PWA Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service-worker.js').catch((e) => {
      console.log('SW registration error:', e);
    });
  }

  // Request browser notification permission politely
  if ('Notification' in window && Notification.permission === 'default') {
    setTimeout(() => {
      Notification.requestPermission();
    }, 2000);
  }

  if (window.lucide) window.lucide.createIcons();
});

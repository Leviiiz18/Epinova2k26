/**
 * Study Buddy - Core Application Logic
 */

// Toast notifications
function showToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const isSuccess = type === "success";
  const isError = type === "error";
  const isInfo = type === "info";

  let bgClass = "bg-slate-900 border-indigo-500 text-indigo-200";
  let icon = `<svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;

  if (isSuccess) {
    bgClass = "bg-slate-900 border-emerald-500 text-emerald-100";
    icon = `<svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
  } else if (isError) {
    bgClass = "bg-slate-900 border-rose-500 text-rose-100";
    icon = `<svg class="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
  }

  toast.className = `toast flex items-center gap-3 px-4 py-3.5 rounded-xl border shadow-2xl backdrop-blur-xl ${bgClass} transition-all duration-300`;
  toast.innerHTML = `
    <div class="flex-shrink-0">${icon}</div>
    <div class="text-sm font-medium leading-snug">${message}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// User session helpers
function logout() {
  localStorage.removeItem("study_buddy_current_user");
  window.location.href = "login.html";
}

function checkAuth(expectedRole = null) {
  const user = DB.getCurrentUser();
  if (expectedRole && user.role !== expectedRole) {
    // If not matching role, redirect
    if (user.role === "faculty") {
      window.location.href = "faculty-dashboard.html";
    } else {
      window.location.href = "student-dashboard.html";
    }
    return null;
  }
  return user;
}

// Quick demo login switchers
function loginAsDemo(role, specificId = null) {
  if (role === "student") {
    const studentUser = {
      role: "student",
      id: "student-alex",
      name: "Alex Morgan",
      yearId: "year-3",
      yearName: "3rd Year (Junior)",
      email: "alex.morgan@student.studybuddy.edu",
      avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150"
    };
    DB.setCurrentUser(studentUser);
    showToast("Signed in as Alex Morgan (3rd Year Student)");
    setTimeout(() => { window.location.href = "student-dashboard.html"; }, 500);
  } else if (role === "faculty") {
    const facId = specificId || "fac-ai-01";
    const faculty = DB.getFacultyById(facId);
    const facultyUser = {
      role: "faculty",
      id: faculty.id,
      name: faculty.name,
      title: faculty.title,
      domain: faculty.domain,
      email: faculty.email,
      avatar: faculty.avatar,
      status: faculty.status
    };
    DB.setCurrentUser(facultyUser);
    showToast(`Signed in as ${faculty.name} (${faculty.domain})`);
    setTimeout(() => { window.location.href = "faculty-dashboard.html"; }, 500);
  }
}

// Global modal helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    document.body.style.overflow = "";
  }
}

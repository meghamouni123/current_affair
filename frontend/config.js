// CA Daily Portal — Config
// Supabase credentials — local browser use, no server needed

// ⚠️ Must match the Supabase project used in DATABASE_URL (backend/.env + GitHub secret)
const SUPABASE_URL = "https://xcycwbibjpkspdmsqbwu.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhjeWN3YmlianBrc3BkbXNxYnd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyODIzMjgsImV4cCI6MjA5Mjg1ODMyOH0.AX6goJRi8ybMeKrLvwY9J_owN2w78u5G6kP7oJt9s9M"; // Replace with anon key from Supabase dashboard → Settings → API

window.SB_URL = SUPABASE_URL;
window.SB_KEY = SUPABASE_KEY;
window.API    = `${SUPABASE_URL}/rest/v1`;
window.HDR    = {
  "apikey":        SUPABASE_KEY,
  "Authorization": `Bearer ${SUPABASE_KEY}`,
  "Content-Type":  "application/json",
  "Prefer":        "return=representation",
};

// Initialize Supabase client (UMD build)
window.supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// Auth helpers — hybrid: Supabase for Google, localStorage for admin demo
window.getUser  = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    const profile = await sbFetch('profiles', { user_id: `eq.${user.id}` });
    return { ...user, ...profile.data[0], role: profile.data[0]?.role || 'user' };
  }
  // Fallback to localStorage for demo admin
  return JSON.parse(localStorage.getItem("ca_user") || "null");
};
window.setUser  = (u) => localStorage.setItem("ca_user", JSON.stringify(u));
window.clearUser= async () => {
  await supabase.auth.signOut();
  localStorage.removeItem("ca_user");
};
window.isAdmin  = async () => { 
  const u = await getUser(); 
  return u && u.role === "admin";
};
window.isLogged = async () => { 
  const u = await getUser(); 
  return !!u;
};

// Redirect guards — async now
window.requireLogin = async () => { if (!(await isLogged())) { window.location.href = "login.html"; return false; } return true; };
window.requireAdmin = async () => { if (!(await isAdmin())) { window.location.href = "index.html"; return false; } return true; };

// Supabase fetch helper
window.sbFetch = async (table, params = {}, method = "GET", body = null) => {
  const url = new URL(`${window.API}/${table}`);
  Object.entries(params).forEach(([k, v]) => v !== undefined && url.searchParams.set(k, v));
  const opts = { method, headers: { ...window.HDR, "Prefer": "count=exact,return=representation" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  const count = res.headers.get('content-range')?.split('/')[1] || 0;
  return { data, count: parseInt(count), ok: res.ok };
};

// Quiz localStorage helpers
window.getQuizHistory = () => { try { return JSON.parse(localStorage.getItem("ca_quiz") || "[]"); } catch { return []; } };
window.saveQuizResult = (r) => { const h = getQuizHistory(); h.unshift(r); localStorage.setItem("ca_quiz", JSON.stringify(h.slice(0, 50))); };
window.getBookmarks   = () => { try { return JSON.parse(localStorage.getItem("ca_bookmarks") || "{}"); } catch { return {}; } };
window.saveBookmarks  = (b) => localStorage.setItem("ca_bookmarks", JSON.stringify(b));
window.getReadHistory = () => { try { return JSON.parse(localStorage.getItem("ca_read") || "[]"); } catch { return []; } };
window.markRead       = (id) => { const h = getReadHistory(); if (!h.includes(id)) { h.unshift(id); localStorage.setItem("ca_read", JSON.stringify(h.slice(0, 200))); } };

// Visitors tracking
window.trackVisit = () => {
  const user = getUser();
  const visits = JSON.parse(localStorage.getItem("ca_visits") || "[]");
  visits.push({ time: new Date().toISOString(), page: location.pathname, user: user?.email || "guest" });
  localStorage.setItem("ca_visits", JSON.stringify(visits.slice(-500)));
};

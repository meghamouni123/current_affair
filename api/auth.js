// api/auth.js — User registration, login, session tracking
const { Client } = require('pg');

function getClient() {
  return new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
}

async function initTables(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS ca_users (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'user',
      created_at TIMESTAMPTZ DEFAULT NOW()
    )
  `);
  await client.query(`
    CREATE TABLE IF NOT EXISTS ca_sessions (
      id SERIAL PRIMARY KEY,
      email TEXT NOT NULL,
      name TEXT,
      page TEXT,
      device TEXT,
      logged_in_at TIMESTAMPTZ DEFAULT NOW()
    )
  `);
}

function hashPass(p) {
  // Simple base64 — same as frontend btoa()
  return Buffer.from(p).toString('base64');
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { action, name, email, password, page, device } = req.body || {};
  const client = getClient();
  try {
    await client.connect();
    await initTables(client);

    if (action === 'register') {
      if (!name || !email || !password) return res.status(400).json({ error: 'Missing fields' });
      const exists = await client.query('SELECT id FROM ca_users WHERE email=$1', [email.toLowerCase()]);
      if (exists.rows.length) return res.status(409).json({ error: 'Account already exists' });
      await client.query(
        'INSERT INTO ca_users (name, email, password_hash) VALUES ($1, $2, $3)',
        [name, email.toLowerCase(), hashPass(password)]
      );
      // Log session
      await client.query('INSERT INTO ca_sessions (email, name, page, device) VALUES ($1,$2,$3,$4)',
        [email.toLowerCase(), name, page || 'register', device || 'unknown']);
      return res.status(200).json({ success: true, user: { name, email: email.toLowerCase(), role: 'user' } });
    }

    if (action === 'login') {
      if (!email || !password) return res.status(400).json({ error: 'Missing fields' });
      const result = await client.query('SELECT * FROM ca_users WHERE email=$1', [email.toLowerCase()]);
      if (!result.rows.length) return res.status(404).json({ error: 'No account found' });
      const user = result.rows[0];
      if (user.password_hash !== hashPass(password)) return res.status(401).json({ error: 'Invalid password' });
      // Log session
      await client.query('INSERT INTO ca_sessions (email, name, page, device) VALUES ($1,$2,$3,$4)',
        [user.email, user.name, page || 'login', device || 'unknown']);
      return res.status(200).json({ success: true, user: { name: user.name, email: user.email, role: user.role } });
    }

    if (action === 'track') {
      if (!email) return res.status(400).json({ error: 'Missing email' });
      await client.query('INSERT INTO ca_sessions (email, name, page, device) VALUES ($1,$2,$3,$4)',
        [email, name || '', page || '/', device || 'unknown']);
      return res.status(200).json({ success: true });
    }

    if (action === 'get_sessions') {
      const sessions = await client.query(
        'SELECT email, name, page, device, logged_in_at FROM ca_sessions ORDER BY logged_in_at DESC LIMIT 100'
      );
      const users = await client.query('SELECT name, email, role, created_at FROM ca_users ORDER BY created_at DESC');
      return res.status(200).json({ sessions: sessions.rows, users: users.rows });
    }

    return res.status(400).json({ error: 'Unknown action' });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  } finally {
    await client.end();
  }
};

"use client";
import { useState, useEffect } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Field, inputStyle, selectStyle, Bar } from "./shared";
import { subscribeToProfiles, updateProfile, deleteProfile, type Profile } from "../../lib/db";

interface UserRow {
  id: string; name: string; email: string; role: string;
  papers: number; tasks: number; status: "active" | "inactive" | "suspended";
  joined: string; institution: string; lastSeen: string;
}

function UserCard({ user, onEdit, onSuspend, onDelete, onActivate }: {
  user: UserRow;
  onEdit: (u: UserRow) => void;
  onSuspend: (u: UserRow) => void;
  onDelete: (u: UserRow) => void;
  onActivate: (u: UserRow) => void;
}) {
  const [hov, setHov] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const statusColor = { active: C.green, inactive: C.inkLight, suspended: C.red }[user.status] || C.inkLight;

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => { setHov(false); setMenuOpen(false); }}
      style={{
        display: "grid",
        gridTemplateColumns: "28px 2fr 2fr 1fr 60px 60px 100px 100px 40px",
        alignItems: "center",
        gap: 0,
        padding: "13px 16px",
        background: hov ? C.white : "transparent",
        borderBottom: `1px solid ${C.border}`,
        transition: "background .2s",
        position: "relative",
      }}
    >
      <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 11, fontWeight: 700, color: C.cream, flexShrink: 0 }}>
        {user.name.charAt(0)}
      </div>
      <div style={{ paddingLeft: 10 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, fontWeight: 500, color: C.inkDark }}>{user.name}</div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>{user.institution}</div>
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{user.email}</div>
      <div>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.umber, background: `${C.umber}14`, border: `1px solid ${C.umber}33`, borderRadius: 2, padding: "2px 8px", letterSpacing: "0.06em", textTransform: "uppercase" }}>{user.role}</span>
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{user.papers}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{user.tasks}</div>
      <div><Badge label={user.status} color={statusColor} pulse={user.status === "active"} /></div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{user.lastSeen}</div>
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setMenuOpen(m => !m)}
          style={{ background: "transparent", border: "none", cursor: "pointer", color: C.inkLight, fontSize: 16, padding: "2px 6px", borderRadius: 3, transition: "all .2s" }}
        >⋮</button>
        {menuOpen && (
          <div style={{ position: "absolute", right: 0, top: "100%", zIndex: 50, background: C.white, border: `1px solid ${C.borderGold}`, borderRadius: 4, boxShadow: `0 8px 24px ${C.shadowMd}`, minWidth: 160, overflow: "hidden" }}>
            {[
              { label: "✎ Edit User",    action: () => { onEdit(user); setMenuOpen(false); }, color: C.inkDark },
              { label: user.status === "suspended" ? "✓ Activate" : "⊘ Suspend", action: () => { user.status === "suspended" ? onActivate(user) : onSuspend(user); setMenuOpen(false); }, color: user.status === "suspended" ? C.green : C.gold },
              { label: "✕ Delete",       action: () => { onDelete(user); setMenuOpen(false); }, color: C.red },
            ].map(item => (
              <button key={item.label} onClick={item.action} style={{ display: "block", width: "100%", textAlign: "left", padding: "10px 14px", background: "transparent", border: "none", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: item.color, cursor: "pointer", transition: "background .15s" }}
              >{item.label}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EditUserModal({ user, onClose, onSave }: { user: UserRow; onClose: () => void; onSave: (u: Partial<Profile>) => void }) {
  const [form, setForm] = useState({ ...user });
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  return (
    <Modal title="Edit User" onClose={onClose}>
      <Field label="Full Name"><input style={inputStyle} value={form.name} onChange={e => set("name", e.target.value)} /></Field>
      <Field label="Institution"><input style={inputStyle} value={form.institution} onChange={e => set("institution", e.target.value)} /></Field>
      <Field label="Role">
        <select style={selectStyle} value={form.role} onChange={e => set("role", e.target.value)}>
          <option value="admin">Admin</option>
          <option value="student">Researcher</option>
          <option value="viewer">Viewer</option>
        </select>
      </Field>
      <Field label="Status">
        <select style={selectStyle} value={form.status} onChange={e => set("status", e.target.value)}>
          <option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option>
        </select>
      </Field>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 24 }}>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-ink" onClick={() => { onSave({ full_name: form.name, institution: form.institution, role: form.role, status: form.status }); onClose(); }}>Save Changes</button>
      </div>
    </Modal>
  );
}

function ConfirmModal({ title, message, confirmLabel, confirmClass, onClose, onConfirm }: {
  title: string; message: string; confirmLabel: string; confirmClass: string;
  onClose: () => void; onConfirm: () => void;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: C.inkMid, marginBottom: 24, lineHeight: 1.6 }}>{message}</p>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className={confirmClass} onClick={() => { onConfirm(); onClose(); }}>{confirmLabel}</button>
      </div>
    </Modal>
  );
}

export default function UsersPage() {
  const [dbUsers, setDbUsers] = useState<Profile[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [editUser, setEditUser] = useState<UserRow | null>(null);
  const [suspendUser, setSuspendUser] = useState<UserRow | null>(null);
  const [deleteUser, setDeleteUser] = useState<UserRow | null>(null);
  const [activateUser, setActivateUser] = useState<UserRow | null>(null);

  useEffect(() => {
    return subscribeToProfiles(setDbUsers);
  }, []);

  const users: UserRow[] = dbUsers.map(u => ({
    id: u.id,
    name: u.full_name,
    email: u.email,
    role: u.role,
    papers: 0,
    tasks: 0,
    status: u.status as any,
    joined: new Date(u.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" }),
    institution: u.institution,
    lastSeen: u.last_seen_at ? new Date(u.last_seen_at).toLocaleDateString() : "Never"
  }));

  const filtered = users.filter(u => {
    const q = search.toLowerCase();
    const matchQ = !q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || u.institution.toLowerCase().includes(q);
    const matchR = roleFilter === "All" || u.role === roleFilter;
    const matchS = statusFilter === "All" || u.status === statusFilter;
    return matchQ && matchR && matchS;
  });

  const stats = {
    total: users.length,
    active: users.filter(u => u.status === "active").length,
    inactive: users.filter(u => u.status === "inactive").length,
    suspended: users.filter(u => u.status === "suspended").length,
  };

  const handleUpdate = async (uid: string, updates: Partial<Profile>) => {
    await updateProfile(uid, updates);
  };

  const handleDelete = async (uid: string) => {
    await deleteProfile(uid);
  };

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="User Management"
        sub="Administration"
        actions={<><button className="btn-ghost">Export CSV</button><button className="btn-gold">+ Invite User</button></>}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Users", value: stats.total, color: C.gold },
          { label: "Active",      value: stats.active, color: C.green },
          { label: "Inactive",    value: stats.inactive, color: C.inkLight },
          { label: "Suspended",   value: stats.suspended, color: C.red },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "16px 18px" }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 900, color: s.color }}>{s.value}</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase" }}>{s.label}</div>
            <Bar value={stats.total > 0 ? (s.value / stats.total) * 100 : 0} color={s.color} />
          </div>
        ))}
      </div>

      <div className="card">
        <div style={{ padding: "14px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
            <input placeholder="Search users…" value={search} onChange={e => setSearch(e.target.value)}
              style={{ ...inputStyle, paddingLeft: 32 }}
            />
          </div>
          <select style={{ ...selectStyle, width: "auto", minWidth: 120 }} value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
            <option value="All">All Roles</option>
            <option value="admin">Admin</option>
            <option value="student">Researcher</option>
            <option value="viewer">Viewer</option>
          </select>
          <select style={{ ...selectStyle, width: "auto", minWidth: 130 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="All">All Statuses</option>
            <option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option>
          </select>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{filtered.length} of {users.length}</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "28px 2fr 2fr 1fr 60px 60px 100px 100px 40px", padding: "9px 16px", background: C.creamDark, borderBottom: `1.5px solid ${C.border}` }}>
          {["", "Name", "Email", "Role", "Papers", "Tasks", "Status", "Last Seen", ""].map((h, i) => (
            <span key={i} style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase" }}>{h}</span>
          ))}
        </div>

        {filtered.length === 0
          ? <div style={{ padding: "40px", textAlign: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.inkLight }}>No users found.</div>
          : filtered.map(u => (
            <UserCard key={u.id} user={u}
              onEdit={setEditUser}
              onSuspend={setSuspendUser}
              onDelete={setDeleteUser}
              onActivate={setActivateUser}
            />
          ))
        }
      </div>

      {editUser && <EditUserModal user={editUser} onClose={() => setEditUser(null)} onSave={updates => handleUpdate(editUser.id, updates)} />}
      {suspendUser && <ConfirmModal title="Suspend User" message={`Suspend ${suspendUser.name}? They will lose access to GenResearch immediately.`} confirmLabel="Suspend User" confirmClass="btn-red" onClose={() => setSuspendUser(null)} onConfirm={() => handleUpdate(suspendUser.id, { status: "suspended" })} />}
      {activateUser && <ConfirmModal title="Activate User" message={`Re-activate ${activateUser.name}? They will regain full access.`} confirmLabel="Activate" confirmClass="btn-green" onClose={() => setActivateUser(null)} onConfirm={() => handleUpdate(activateUser.id, { status: "active" })} />}
      {deleteUser && <ConfirmModal title="Delete User" message={`Permanently delete ${deleteUser.name}? This action cannot be undone and will remove all their data.`} confirmLabel="Delete Permanently" confirmClass="btn-red" onClose={() => setDeleteUser(null)} onConfirm={() => handleDelete(deleteUser.id)} />}
    </div>
  );
}

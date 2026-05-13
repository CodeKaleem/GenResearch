"use client";
import { useState } from "react";
import { C, SectionHead, PageTitle, Modal, Field, selectStyle, Bar, Num, Sparkline } from "./shared";

const DAILY_SPEND = [2.1, 3.4, 2.8, 4.1, 3.7, 5.2, 4.3, 3.9, 4.0, 4.32];
const BUDGET_LIMIT = 10;
const MONTHLY_BUDGET = 150;

interface CostEntry { agent: string; model: string; tokens: string; tokenCount: number; cost: string; costNum: number; pct: number; color: string; calls: number; }

const COST_BREAKDOWN: CostEntry[] = [
  { agent: "Summarization Agent",     model: "gpt-3.5-turbo", tokens: "841K",  tokenCount: 841000,  cost: "$1.68", costNum: 1.68, pct: 40, color: C.gold,   calls: 842 },
  { agent: "Literature Review Agent", model: "gpt-3.5-turbo", tokens: "562K",  tokenCount: 562000,  cost: "$1.12", costNum: 1.12, pct: 27, color: C.sienna, calls: 287 },
  { agent: "Proposal Drafting Agent", model: "gpt-3.5-turbo", tokens: "390K",  tokenCount: 390000,  cost: "$0.78", costNum: 0.78, pct: 19, color: C.umber,  calls: 134 },
  { agent: "Citation Agent",          model: "CrossRef API",  tokens: "370K",  tokenCount: 370000,  cost: "$0.74", costNum: 0.74, pct: 14, color: C.blue,   calls: 411 },
];

interface BudgetModalProps { onClose: () => void; daily: number; monthly: number; onSave: (d: number, m: number) => void; }
function BudgetModal({ onClose, daily, monthly, onSave }: BudgetModalProps) {
  const [d, setD] = useState(daily.toString()); const [m, setM] = useState(monthly.toString());
  return (
    <Modal title="Configure Budget Limits" onClose={onClose}>
      <Field label="Daily Spend Limit ($)">
        <input style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: "white", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, outline: "none" }}
          type="number" value={d} onChange={e => setD(e.target.value)} />
      </Field>
      <Field label="Monthly Budget ($)">
        <input style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: "white", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, outline: "none" }}
          type="number" value={m} onChange={e => setM(e.target.value)} />
      </Field>
      <div style={{ padding: "12px 14px", background: C.goldFaint, border: `1px solid ${C.borderGold}`, borderRadius: 3, marginBottom: 16 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkMid }}>⚑ Alerts will be sent when daily spend exceeds 80% of limit. API calls will be blocked at 100%.</div>
      </div>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-gold" onClick={() => { onSave(Number(d), Number(m)); onClose(); }}>Save Limits</button>
      </div>
    </Modal>
  );
}

export default function CostsPage() {
  const [daily, setDaily] = useState(BUDGET_LIMIT);
  const [monthly, setMonthly] = useState(MONTHLY_BUDGET);
  const [showBudget, setShowBudget] = useState(false);
  const todaySpend = 4.32;
  const monthlySpend = 67.40;
  const pctDaily = (todaySpend / daily) * 100;
  const pctMonthly = (monthlySpend / monthly) * 100;

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="API Cost Tracker"
        sub="Finance & Billing"
        actions={<><button className="btn-ghost" onClick={() => alert("Exporting cost report…")}>↓ Export CSV</button><button className="btn-ink" onClick={() => setShowBudget(true)}>⚙ Set Budget</button></>}
      />

      {/* Summary KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 28 }}>
        {[
          { label: "Today's Spend",    value: `$${todaySpend.toFixed(2)}`, sub: `${pctDaily.toFixed(0)}% of daily limit`, color: pctDaily > 80 ? C.red : C.gold },
          { label: "Monthly Spend",    value: `$${monthlySpend.toFixed(2)}`, sub: `${pctMonthly.toFixed(0)}% of budget`, color: pctMonthly > 80 ? C.red : C.sienna },
          { label: "Monthly Budget",   value: `$${monthly}`,               sub: `${(monthly - monthlySpend).toFixed(2)} remaining`, color: C.umber },
          { label: "Total API Calls",  value: "1,674",                     sub: "today across all agents", color: C.blue },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "18px 20px" }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 900, color: s.color, marginBottom: 4 }}>{s.value}</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase" }}>{s.label}</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight, marginTop: 4 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 22, marginBottom: 22 }}>
        {/* Agent breakdown */}
        <div className="card" style={{ padding: "22px 24px" }}>
          <SectionHead label="Cost by Agent — Today" />
          {COST_BREAKDOWN.map((row) => (
            <div key={row.agent} style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8 }}>
                <div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 500, color: C.inkDark }}>{row.agent}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{row.model} · {row.calls} calls · {row.tokens} tokens</div>
                </div>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 20, fontWeight: 900, color: row.color }}>{row.cost}</div>
              </div>
              <Bar value={row.pct} color={row.color} />
            </div>
          ))}
          <div style={{ paddingTop: 16, borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>Daily limit: ${daily}.00</span>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: pctDaily > 80 ? C.red : C.inkDark }}>${todaySpend} <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, fontWeight: 400, color: C.inkLight }}>/ ${daily}</span></span>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {/* Spend trend */}
          <div className="card" style={{ padding: "20px 18px" }}>
            <SectionHead label="10-Day Spend Trend" />
            <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 12 }}>
              {DAILY_SPEND.map((v, i) => {
                const isToday = i === DAILY_SPEND.length - 1;
                const pct = (v / daily) * 100;
                return (
                  <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: isToday ? C.gold : C.inkLight }}>${v}</div>
                    <div style={{ width: 20, height: `${Math.round((v / Math.max(...DAILY_SPEND)) * 70)}px`, background: isToday ? C.gold : C.umber, borderRadius: "2px 2px 0 0", opacity: isToday ? 1 : 0.55 }} />
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9, color: C.inkLight }}>{i === DAILY_SPEND.length - 1 ? "Today" : `D-${DAILY_SPEND.length - 1 - i}`}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Budget gauges */}
          <div className="card" style={{ padding: "20px 18px" }}>
            <SectionHead label="Budget Utilization" action="Configure" onAction={() => setShowBudget(true)} />
            {[
              { label: "Daily",   value: todaySpend,   max: daily,   color: pctDaily > 80 ? C.red : C.gold,   pct: pctDaily },
              { label: "Monthly", value: monthlySpend, max: monthly, color: pctMonthly > 80 ? C.red : C.sienna, pct: pctMonthly },
            ].map(g => (
              <div key={g.label} style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark }}>{g.label} Budget</span>
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: 600, color: g.color }}>${g.value.toFixed(2)} / ${g.max}</span>
                </div>
                <Bar value={g.pct} color={g.color} />
                <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: g.pct > 80 ? C.red : C.inkLight, marginTop: 4 }}>
                  {g.pct > 80 ? "⚠ Approaching limit" : `${(100 - g.pct).toFixed(0)}% remaining`}
                </div>
              </div>
            ))}
          </div>

          {/* Rate per model */}
          <div className="card" style={{ padding: "20px 18px" }}>
            <SectionHead label="Pricing Reference" />
            {[
              { model: "GPT-3.5-turbo", input: "$0.0005", output: "$0.0015" },
              { model: "GPT-4o",        input: "$0.005",  output: "$0.015" },
              { model: "CrossRef API",  input: "Free",    output: "Rate-limited" },
            ].map(r => (
              <div key={r.model} style={{ padding: "8px 0", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark }}>{r.model}</span>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>In: {r.input}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>Out: {r.output}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showBudget && <BudgetModal daily={daily} monthly={monthly} onClose={() => setShowBudget(false)} onSave={(d, m) => { setDaily(d); setMonthly(m); }} />}
    </div>
  );
}

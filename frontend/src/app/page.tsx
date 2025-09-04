"use client";
import { useEffect, useState } from "react";

type RiskResp = {
  date: string;
  risk_score: number;
  risk_level: "Low"|"Medium"|"High";
  top_contributors: {name:string; weight:number}[];
};

type ActionsResp = {
  actions: { title: string; explanation: string }[];
  source?: string;
};

export default function Home() {
  const [risk, setRisk] = useState<RiskResp|null>(null);
  const [forecast, setForecast] = useState<number[]>([]);
  const [actions, setActions] = useState<ActionsResp["actions"]>([]);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [loadingActions, setLoadingActions] = useState(false);
  const [actionsError, setActionsError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const r = await fetch("/api/risk").then(res=>res.json());
      const f = await fetch("/api/forecast").then(res=>res.json());
      const a = await fetch("/api/actions").then(res=>res.json()).catch(()=>({actions:[]}));
      setRisk(r);
      setForecast(f.forecast || []);
      setActions(a.actions || []);
    })();
  }, []);

  const badgeColor =
    risk?.risk_level === "High" ? "bg-red-600"
    : risk?.risk_level === "Medium" ? "bg-yellow-500"
    : "bg-green-600";

  const accent =
    risk?.risk_level === "High" ? "#dc2626"
    : risk?.risk_level === "Medium" ? "#f59e0b"
    : "#16a34a";

  const pct = Math.round((risk?.risk_score || 0) * 100);

  const formatContributorName = (name: string) => {
    const map: Record<string, string> = {
      "HRV low": "HRV (RMSSD)",
      "Workload": "Workload Index",
      "Sentiment": "Sentiment (%)",
    };
    return map[name] || name;
  };

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-rose-500 to-sky-500 bg-clip-text text-transparent">
              PreBurn
            </h1>
                        <p className="text-sm text-gray-600 mt-1">
              Personalized, preventive nudges to reduce burnout <span className="text-red-600">(Helping you not crash out)</span>.
            </p>
          </div>
        </header>

        {risk && (
          <section className="rounded-3xl p-6 bg-white/70 dark:bg-neutral-900/60 border border-black/10 dark:border-white/10 shadow-sm backdrop-blur">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 items-center">
              <div className="sm:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-500">Today • {risk.date}</div>
                    <div className="text-5xl font-extrabold">{pct}%</div>
                  </div>
                  <span className={`text-white px-3 py-1 rounded-full ${badgeColor}`}>
                    {risk.risk_level}
                  </span>
                </div>

                <div className="flex gap-2 flex-wrap">
                  {risk.top_contributors.map((c, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-full text-sm bg-gray-50 dark:bg-neutral-800 border border-black/10 dark:border-white/10"
                    >
                      {formatContributorName(c.name)} • {(c.weight * 100).toFixed(0)}%
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex justify-center sm:justify-end">
                <div
                  className="relative w-40 h-40 rounded-full"
                  style={{
                    background: `conic-gradient(${accent} ${pct}%, #e5e7eb 0)`
                  }}
                >
                  <div className="absolute inset-3 rounded-full bg-white dark:bg-neutral-900 border border-black/10 dark:border-white/10 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-3xl font-bold">{pct}%</div>
                      <div className="text-xs text-gray-500">risk</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        <section className="rounded-3xl p-6 bg-white/70 dark:bg-neutral-900/60 border border-black/10 dark:border-white/10 shadow-sm backdrop-blur">
          <div className="text-sm text-gray-500 mb-3">3-Day Forecast</div>
          <div className="grid grid-cols-3 gap-3">
            {forecast.map((v,i)=>(
              <button
                key={i}
                onClick={async ()=>{
                  setSelectedDay(i+1);
                  setLoadingActions(true);
                  setActionsError(null);
                  try {
                    const res = await fetch(`/api/actions?day=${i+1}`);
                    const a: ActionsResp = await res.json();
                    setActions(a.actions || []);
                  } catch (e) {
                    setActions([]);
                    setActionsError("Could not load actions.");
                  } finally {
                    setLoadingActions(false);
                  }
                }}
                className={`rounded-2xl p-4 text-center bg-gray-50 dark:bg-neutral-800 border border-black/10 dark:border-white/10 transition ring-0 ${selectedDay===i+1?"outline outline-2 outline-sky-400": "hover:bg-gray-100 dark:hover:bg-neutral-700"}`}
              >
                <div className="text-xl font-semibold">{(v*100).toFixed(0)}%</div>
                <div className="text-gray-500 text-xs">+{i+1}d</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-3xl p-6 bg-white/70 dark:bg-neutral-900/60 border border-black/10 dark:border-white/10 shadow-sm backdrop-blur">
          <div className="text-sm text-gray-500 mb-2">Actions</div>
          {loadingActions && (
            <div className="text-sm text-gray-500">Loading actions…</div>
          )}
          {actionsError && (
            <div className="text-sm text-red-600">{actionsError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {actions.map((act, i)=> (
              <div key={i} className="rounded-2xl p-4 bg-gray-50 dark:bg-neutral-800 border border-black/10 dark:border-white/10">
                <div className="font-semibold">{act.title}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">{act.explanation}</div>
              </div>
            ))}
            {actions.length === 0 && (
              <div className="text-sm text-gray-500">No suggestions available.</div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
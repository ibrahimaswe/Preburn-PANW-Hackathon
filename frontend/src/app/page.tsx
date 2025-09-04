"use client";
import { useEffect, useState } from "react";

type RiskResp = {
  date: string;
  risk_score: number;
  risk_level: "Low"|"Medium"|"High";
  top_contributors: {name:string; weight:number}[];
};

export default function Home() {
  const [risk, setRisk] = useState<RiskResp|null>(null);
  const [forecast, setForecast] = useState<number[]>([]);

  useEffect(() => {
    (async () => {
      const r = await fetch("http://127.0.0.1:8000/risk").then(res=>res.json());
      const f = await fetch("http://127.0.0.1:8000/forecast").then(res=>res.json());
      setRisk(r);
      setForecast(f.forecast || []);
    })();
  }, []);

  const badgeColor = risk?.risk_level === "High" ? "bg-red-600"
                    : risk?.risk_level === "Medium" ? "bg-yellow-500" : "bg-green-600";

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold">PreBurn</h1>

        {risk && (
          <div className="rounded-2xl p-6 bg-white shadow">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-500">Today • {risk.date}</div>
                <div className="text-5xl font-bold">{(risk.risk_score*100).toFixed(0)}%</div>
              </div>
              <span className={`text-white px-3 py-1 rounded-full ${badgeColor}`}>
                {risk.risk_level}
              </span>
            </div>

            <div className="mt-4 flex gap-2 flex-wrap">
              {risk.top_contributors.map((c, i) => (
                <span key={i} className="px-3 py-1 bg-gray-100 rounded-full text-sm">
                  {c.name} • {c.weight.toFixed(2)}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-2xl p-6 bg-white shadow">
          <div className="text-sm text-gray-500 mb-2">3-Day Forecast</div>
          <div className="flex gap-3">
            {forecast.map((v,i)=>(
              <div key={i} className="flex-1 text-center">
                <div className="text-xl font-semibold">{(v*100).toFixed(0)}%</div>
                <div className="text-gray-500 text-sm">+{i+1}d</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl p-6 bg-white shadow">
          <div className="text-sm text-gray-500 mb-2">Actions</div>
          <button className="px-4 py-2 rounded-xl bg-black text-white">Start 3-min breathing</button>
        </div>
      </div>
    </main>
  );
}

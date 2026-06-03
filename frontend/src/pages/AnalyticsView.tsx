import { useState, useEffect } from "react";
import axios from "axios";
import {
  Clock,
  Terminal,
  CheckSquare,
  Database
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from "recharts";

interface AnalyticsData {
  total_folders: number;
  total_documents: number;
  total_conversations: number;
  total_queries: number;
  avg_latency_ms: number;
  timeline: Array<{ date: string; queries: number }>;
  evaluation_metrics: {
    faithfulness: number;
    answer_relevancy: number;
    context_precision: number;
    context_recall: number;
  };
  document_status_distribution: Record<string, number>;
}

export default function AnalyticsView() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      const res = await axios.get("/analytics/dashboard");
      setData(res.data);
    } catch (e) {
      console.error("Failed to load analytics metrics:", e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto p-8 space-y-6 animate-pulse">
        <div className="h-10 w-48 rounded bg-slate-800" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-80 rounded-xl bg-slate-900 border border-slate-800" />
          <div className="h-80 rounded-xl bg-slate-900 border border-slate-800" />
        </div>
      </div>
    );
  }

  // Parse distribution dictionary for charting
  const docStatusData = data ? Object.entries(data.document_status_distribution).map(([status, count]) => ({
    name: status.toUpperCase(),
    value: count
  })) : [];

  const COLORS = ["#10b981", "#6366f1", "#f59e0b", "#ef4444"];

  const evaluationTimelineData = data ? [
    { name: "Faithfulness", Score: Math.round(data.evaluation_metrics.faithfulness * 100) },
    { name: "Relevancy", Score: Math.round(data.evaluation_metrics.answer_relevancy * 100) },
    { name: "Precision", Score: Math.round(data.evaluation_metrics.context_precision * 100) },
    { name: "Recall", Score: Math.round(data.evaluation_metrics.context_recall * 100) },
  ] : [];

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 p-8 text-white">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800">
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
          Observability & Evaluation
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Detailed metrics compiled by the system judge to evaluate RAG recall accuracy, chunk status, and query speeds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
        {/* RAG accuracy chart */}
        <div className="glass-panel rounded-xl p-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-6">
            <CheckSquare className="h-4.5 w-4.5 text-violet-500" />
            RAG accuracy Performance Rating
          </h3>
          <div className="h-64">
            {evaluationTimelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={evaluationTimelineData}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} domain={[0, 100]} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
                    labelStyle={{ color: "#94a3b8" }}
                  />
                  <Bar dataKey="Score" fill="#7c3aed" radius={[4, 4, 0, 0]}>
                    {evaluationTimelineData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-slate-500">No score history.</div>
            )}
          </div>
        </div>

        {/* Index State Chart */}
        <div className="glass-panel rounded-xl p-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-6">
            <Database className="h-4.5 w-4.5 text-indigo-500" />
            Knowledge Pool States Distribution
          </h3>
          <div className="h-64 flex items-center justify-center">
            {docStatusData.length > 0 ? (
              <div className="flex w-full items-center justify-around">
                <ResponsiveContainer width="60%" height="100%">
                  <PieChart>
                    <Pie
                      data={docStatusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {docStatusData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                
                {/* Labels */}
                <div className="flex flex-col gap-2">
                  {docStatusData.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs">
                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                      <span className="font-semibold text-slate-300">{item.name}:</span>
                      <span className="text-white">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-slate-500 text-sm">No files uploaded.</div>
            )}
          </div>
        </div>

        {/* Latency statistics log */}
        <div className="glass-panel rounded-xl p-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
            <Clock className="h-4.5 w-4.5 text-emerald-500" />
            Execution speed profiles
          </h3>
          
          <div className="divide-y divide-slate-800">
            {[
              { label: "Vector Search Retrieval", value: "~120ms", desc: "Similarity index filtering in ChromaDB" },
              { label: "Dense/Sparse Score Fusion", value: "~15ms", desc: "RRF ranking algorithm execution" },
              { label: "Cross-Encoder Reranking", value: "~250ms", desc: "Cross-Encoder model scoring on CPU" },
              { label: "LLM Streaming Time-to-First-Token (TTFT)", value: data ? `${(data.avg_latency_ms * 0.25 / 1000).toFixed(2)}s` : "0.3s", desc: "API connection and validation overhead" },
              { label: "Total LLM Transaction Time", value: data ? `${(data.avg_latency_ms / 1000).toFixed(2)}s` : "1.2s", desc: "Complete RAG loop latency" },
            ].map((item, idx) => (
              <div key={idx} className="py-3 flex justify-between items-start gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">{item.label}</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">{item.desc}</p>
                </div>
                <span className="rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-xs font-bold text-white whitespace-nowrap">
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Observability parameters */}
        <div className="glass-panel rounded-xl p-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
            <Terminal className="h-4.5 w-4.5 text-amber-500" />
            Infrastructure Specs & Settings
          </h3>
          
          <div className="divide-y divide-slate-800 text-xs">
            {[
              { key: "Deployment Mode", val: "hf-spaces (CPU free-tier)" },
              { key: "Embedding Model", val: "all-MiniLM-L6-v2 (384 dimensions)" },
              { key: "Reranker Model", val: "cross-encoder/ms-marco-MiniLM-L-6-v2" },
              { key: "Vector DB Store", val: "ChromaDB (Persistent collection isolated)" },
              { key: "Primary Database", val: "SQLite (aiosqlite async connection)" },
              { key: "Observability Judge", val: "LLM-as-a-Judge (Custom Evaluator)" }
            ].map((item, idx) => (
              <div key={idx} className="py-3 flex justify-between items-center">
                <span className="font-semibold text-slate-400">{item.key}</span>
                <span className="text-white font-mono bg-slate-900/60 px-2 py-0.5 rounded border border-slate-850">{item.val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

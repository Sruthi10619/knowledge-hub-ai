import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { 
  Folder, 
  FileText, 
  MessageSquare, 
  Clock, 
  TrendingUp, 
  Activity,
  ArrowRight,
  ShieldCheck,
  ChevronRight
} from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";

interface Stats {
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

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const res = await axios.get("/analytics/dashboard");
      setStats(res.data);
      setError(null);
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  if (error && !stats) {
    return (
      <div className="flex-1 overflow-y-auto p-8">
        <div className="rounded-lg border border-red-800/40 bg-red-950/50 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto p-8 space-y-6 animate-pulse">
        <div className="h-10 w-48 rounded bg-slate-800" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-28 rounded-xl bg-slate-900 border border-slate-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-80 md:col-span-2 rounded-xl bg-slate-900 border border-slate-800" />
          <div className="h-80 rounded-xl bg-slate-900 border border-slate-800" />
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: "Active Workspaces",
      value: stats?.total_folders || 0,
      icon: Folder,
      color: "text-violet-500 bg-violet-600/10",
      desc: "Isolated vector spaces"
    },
    {
      title: "Knowledge Files",
      value: stats?.total_documents || 0,
      icon: FileText,
      color: "text-indigo-500 bg-indigo-600/10",
      desc: "Uploaded PDFs, DOCX, CSVs"
    },
    {
      title: "Total RAG Queries",
      value: stats?.total_queries || 0,
      icon: MessageSquare,
      color: "text-emerald-500 bg-emerald-600/10",
      desc: "Answers provided by LLM"
    },
    {
      title: "Avg Response Speed",
      value: stats ? `${(stats.avg_latency_ms / 1000).toFixed(2)}s` : "0.0s",
      icon: Clock,
      color: "text-amber-500 bg-amber-600/10",
      desc: "Retrieval + generation latency"
    }
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 p-8 text-white">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            System Operations Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Observe multi-tenant indices, performance graphs, and response accuracy judges.
          </p>
        </div>
        <Link 
          to="/analytics" 
          className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold hover:bg-violet-500 transition-colors"
        >
          Detailed Observability
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-8">
        {statCards.map((card, idx) => (
          <div key={idx} className="glass-panel rounded-xl p-5 hover:border-slate-700 transition-all">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{card.title}</p>
                <h3 className="text-3xl font-extrabold mt-1 text-white">{card.value}</h3>
              </div>
              <div className={`p-2.5 rounded-lg ${card.color}`}>
                <card.icon className="h-5 w-5" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 flex items-center gap-1">
              <Activity className="h-3.5 w-3.5 text-slate-500" />
              {card.desc}
            </p>
          </div>
        ))}
      </div>

      {/* Charts section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {/* Timeline query flow Chart */}
        <div className="glass-panel rounded-xl p-5 md:col-span-2">
          <div className="flex justify-between items-center mb-6">
            <h4 className="text-base font-bold text-white flex items-center gap-2">
              <TrendingUp className="text-violet-500 h-4.5 w-4.5" />
              Query Traffic Volume (Last 7 Days)
            </h4>
          </div>
          
          <div className="h-64">
            {stats?.timeline && stats.timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={stats.timeline}>
                  <defs>
                    <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
                    labelStyle={{ color: "#94a3b8" }}
                  />
                  <Area type="monotone" dataKey="queries" stroke="#7c3aed" strokeWidth={2} fillOpacity={1} fill="url(#colorQueries)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-slate-500 text-sm">
                No query traffic recorded. Talk to your document folders to generate logs.
              </div>
            )}
          </div>
        </div>

        {/* RAGAS Evaluation metric scores */}
        <div className="glass-panel rounded-xl p-5">
          <h4 className="text-base font-bold text-white flex items-center gap-2 mb-6">
            <ShieldCheck className="text-indigo-500 h-4.5 w-4.5" />
            Accuracy & Evaluation (AI Judge)
          </h4>

          <div className="space-y-4">
            {[
              { label: "Faithfulness", score: stats?.evaluation_metrics.faithfulness || 0.0, color: "bg-emerald-500", desc: "Hallucination reduction score" },
              { label: "Answer Relevancy", score: stats?.evaluation_metrics.answer_relevancy || 0.0, color: "bg-violet-500", desc: "Question-answer similarity match" },
              { label: "Context Precision", score: stats?.evaluation_metrics.context_precision || 0.0, color: "bg-indigo-500", desc: "Noise filtering in retrieved data" },
              { label: "Context Recall", score: stats?.evaluation_metrics.context_recall || 0.0, color: "bg-amber-500", desc: "Complete facts retrieval match" }
            ].map((metric, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300">{metric.label}</span>
                  <span className="font-bold text-white">{Math.round(metric.score * 100)}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${metric.color} transition-all duration-500`} 
                    style={{ width: `${metric.score * 100}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500">{metric.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Guide Card for Onboarding */}
      <div className="mt-8 rounded-xl bg-gradient-to-r from-violet-600/20 to-indigo-600/20 border border-violet-500/20 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h4 className="text-lg font-bold text-white">Getting started with isolated knowledge spaces</h4>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            To build your first pipeline: create a folder workspace in the left sidebar, upload a pdf/docx file, wait for parsing completion, and query it directly using vector retrieval.
          </p>
        </div>
        <ChevronRight className="h-6 w-6 text-violet-500" />
      </div>
    </div>
  );
}

import { useState, useEffect, FormEvent } from "react";
import { useAppStore } from "../stores/useAppStore";
import {
  User as UserIcon,
  Cpu,
  Key,
} from "lucide-react";

export default function SettingsView() {
  const { user, theme, toggleTheme } = useAppStore();

  const [fullName, setFullName] = useState(user?.full_name || "");
  const [language, setLanguage] = useState(user?.preferred_language || "en");
  const [provider, setProvider] = useState("groq");
  

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setLanguage(user.preferred_language || "en");
    }
  }, [user]);

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    // Profile API not implemented yet — theme changes apply immediately via toggle
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-950 p-8 text-white">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800">
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
          System Settings
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure default LLM providers, interface themes, and profile details.
        </p>
      </div>

      <div className="max-w-2xl space-y-8 mt-8">
        {/* Profile Card */}
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
            <UserIcon className="h-4.5 w-4.5 text-violet-500" />
            Profile Preferences
          </h3>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400">Account Email</label>
              <input
                type="email"
                disabled
                value={user?.email}
                className="mt-1.5 w-full rounded-lg border border-slate-800 bg-slate-950/40 py-2.5 px-3.5 text-sm text-slate-500 cursor-not-allowed focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-sm text-white focus:border-violet-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400">Language Preference</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-sm text-white focus:border-violet-500 focus:outline-none"
                >
                  <option value="en">English (US)</option>
                  <option value="es">Español (ES)</option>
                  <option value="fr">Français (FR)</option>
                  <option value="de">Deutsch (DE)</option>
                  <option value="zh">中文 (ZH)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400">Appearance Theme</label>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="mt-1.5 flex w-full justify-between items-center rounded-lg border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-sm text-white hover:bg-slate-900 focus:outline-none"
                >
                  <span>Active Theme:</span>
                  <span className="font-bold text-violet-400 capitalize">{theme}</span>
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-500 pt-1">
              Profile save is coming soon. Theme changes apply immediately using the control above.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled
                title="Profile update API is not available yet"
                className="rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-semibold text-slate-500 cursor-not-allowed"
              >
                Save Changes (coming soon)
              </button>
            </div>
          </form>
        </div>

        {/* LLM Model Abstraction config */}
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
            <Cpu className="h-4.5 w-4.5 text-indigo-500" />
            LLM Provider abstraction config
          </h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400">Default Model Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-sm text-white focus:border-violet-500 focus:outline-none"
              >
                <option value="groq">Groq (llama-3.3-70b-versatile) [Default]</option>
                <option value="openai">OpenAI (gpt-4o-mini)</option>
                <option value="anthropic">Anthropic (claude-3-5-sonnet-20241022)</option>
                <option value="huggingface">Hugging Face (Inference API)</option>
              </select>
            </div>

            <div className="rounded-lg bg-slate-900/40 p-4 border border-slate-900 space-y-2 text-xs text-slate-400">
              <p className="font-semibold text-white flex items-center gap-1">
                <Key className="h-3.5 w-3.5 text-amber-500" />
                Configuring API Secrets & Keys
              </p>
              <p>
                To override model providers, add environment variables inside the Space Settings or in the local `.env` configuration:
              </p>
              <pre className="mt-2 bg-slate-950 p-2.5 rounded border border-slate-850 text-[10px] font-mono text-slate-300">
                GROQ_API_KEY=gsk_...{"\n"}
                OPENAI_API_KEY=sk-proj-...{"\n"}
                ANTHROPIC_API_KEY=sk-ant-...{"\n"}
                HF_API_TOKEN=hf_...
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

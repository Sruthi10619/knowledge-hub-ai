import React, { useState, useEffect } from "react";
import { Link, Outlet, useNavigate, useParams, useLocation } from "react-router-dom";
import { useAppStore } from "../stores/useAppStore";
import { 
  FolderPlus, 
  LogOut, 
  Settings as SettingsIcon, 
  BarChart3, 
  Brain, 
  Folder, 
  Sun, 
  Moon, 
  ChevronLeft, 
  ChevronRight,
  Plus,
  Compass,
  X
} from "lucide-react";

export default function Layout() {
  const { 
    user, 
    folders, 
    fetchFolders, 
    createFolder, 
    setCurrentFolder, 
    currentFolder, 
    logout, 
    theme, 
    toggleTheme 
  } = useAppStore();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [newFolderDesc, setNewFolderDesc] = useState("");
  const [newFolderIcon, setNewFolderIcon] = useState("📁");
  const [newFolderColor, setNewFolderColor] = useState("#6366f1");

  const navigate = useNavigate();
  const location = useLocation();
  const { folderId } = useParams();

  useEffect(() => {
    fetchFolders();
  }, []);

  // Update current folder state based on URL parameters
  useEffect(() => {
    if (folderId && folders.length > 0) {
      const active = folders.find(f => f.id === folderId);
      if (active) setCurrentFolder(active);
    } else {
      setCurrentFolder(null);
    }
  }, [folderId, folders]);

  const handleCreateFolderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    
    try {
      const folder = await createFolder(
        newFolderName.trim(),
        newFolderDesc.trim(),
        newFolderIcon,
        newFolderColor
      );
      setShowCreateModal(false);
      setNewFolderName("");
      setNewFolderDesc("");
      navigate(`/folders/${folder.id}`);
    } catch (e) {
      console.error("Folder creation failed:", e);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActiveRoute = (path: string) => location.pathname === path;

  return (
    <div className={`flex h-screen overflow-hidden ${theme === "dark" ? "bg-slate-950 text-slate-100" : "bg-slate-50 text-slate-900"}`}>
      {/* Sidebar Navigation */}
      <aside 
        className={`relative z-20 flex flex-col border-r border-slate-800 bg-slate-900/40 backdrop-blur-lg transition-all duration-300 ${
          sidebarOpen ? "w-64" : "w-16"
        }`}
      >
        {/* Sidebar Header Brand */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-slate-800">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Brain className="h-6 w-6 text-violet-500" />
            {sidebarOpen && <span className="font-sans text-lg tracking-wide text-white">KnowledgeHub</span>}
          </Link>
          {sidebarOpen && (
            <button 
              onClick={() => setSidebarOpen(false)} 
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Create Workspace Quick Button */}
        {sidebarOpen ? (
          <button
            onClick={() => setShowCreateModal(true)}
            className="m-4 flex items-center justify-center gap-2 rounded-xl bg-violet-600/10 border border-violet-500/20 py-2.5 text-sm font-medium text-violet-400 hover:bg-violet-600/20 hover:text-white transition-colors"
          >
            <FolderPlus className="h-4 w-4" />
            Create Workspace
          </button>
        ) : (
          <button
            onClick={() => setShowCreateModal(true)}
            className="mx-auto my-4 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600/10 border border-violet-500/20 text-violet-400 hover:bg-violet-600/20 hover:text-white transition-colors"
          >
            <Plus className="h-5 w-5" />
          </button>
        )}

        {/* Scrollable Folder Navigation List */}
        <nav className="flex-1 overflow-y-auto px-2 space-y-1">
          {/* Main Links */}
          <Link
            to="/"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActiveRoute("/") 
                ? "bg-violet-600/10 text-violet-400" 
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            <Compass className="h-5 w-5" />
            {sidebarOpen && <span>Dashboard</span>}
          </Link>

          <Link
            to="/analytics"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActiveRoute("/analytics") 
                ? "bg-violet-600/10 text-violet-400" 
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            <BarChart3 className="h-5 w-5" />
            {sidebarOpen && <span>Analytics</span>}
          </Link>

          <div className="pt-4 pb-2">
            {sidebarOpen && <span className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Workspaces</span>}
          </div>

          {/* Dynamic Folders list */}
          {folders.map(folder => (
            <Link
              key={folder.id}
              to={`/folders/${folder.id}`}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                currentFolder?.id === folder.id
                  ? "bg-slate-800 text-white border-l-2 border-violet-500"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <div className="flex items-center gap-3 truncate">
                <span className="text-base" style={{ color: folder.color }}>{folder.icon}</span>
                {sidebarOpen && <span className="truncate">{folder.name}</span>}
              </div>
              {sidebarOpen && folder.document_count > 0 && (
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                  {folder.document_count}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* Sidebar Footer User controls */}
        <div className="mt-auto border-t border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between">
            {sidebarOpen && (
              <div className="flex items-center gap-2 truncate">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-violet-600 to-indigo-600 text-sm font-bold text-white uppercase">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
                  ) : (
                    user?.full_name[0] || "U"
                  )}
                </div>
                <div className="truncate">
                  <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
              </div>
            )}
            
            {!sidebarOpen && (
              <button 
                onClick={() => setSidebarOpen(true)}
                className="mx-auto rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            )}

            {sidebarOpen && (
              <button 
                onClick={toggleTheme}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
            )}
          </div>

          {sidebarOpen && (
            <div className="flex gap-2">
              <Link
                to="/settings"
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/40 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <SettingsIcon className="h-3.5 w-3.5" />
                Settings
              </Link>
              <button
                onClick={handleLogout}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-800 bg-red-950/20 py-2 text-xs font-medium text-red-400 hover:bg-red-900/20 hover:text-red-300 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Workspace viewport */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>

      {/* Folder Creation Modal Popup */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Folder className="text-violet-500" />
                Create Workspace
              </h3>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateFolderSubmit} className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300">Workspace Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Product Docs, HR Policies"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Description (Optional)</label>
                <textarea
                  placeholder="Briefly summarize what kind of documents will live in here."
                  value={newFolderDesc}
                  onChange={(e) => setNewFolderDesc(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-300">Select Icon</label>
                  <select
                    value={newFolderIcon}
                    onChange={(e) => setNewFolderIcon(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 py-2 px-3 text-sm text-white focus:border-violet-500 focus:outline-none"
                  >
                    <option value="📁">📁 Folder</option>
                    <option value="⚖️">⚖️ Legal</option>
                    <option value="👥">👥 HR/Staff</option>
                    <option value="🛠️">🛠️ Eng/Product</option>
                    <option value="💬">💬 Support</option>
                    <option value="📊">📊 Finance</option>
                    <option value="🔒">🔒 Security</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300">Select Theme Color</label>
                  <div className="flex gap-2 mt-2">
                    {["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#ef4444"].map(c => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setNewFolderColor(c)}
                        className={`h-6 w-6 rounded-full border transition-all ${
                          newFolderColor === c ? "scale-110 border-white" : "border-transparent"
                        }`}
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-800 bg-transparent px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:from-violet-500 hover:to-indigo-500"
                >
                  Build Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

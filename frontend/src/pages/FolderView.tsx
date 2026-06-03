import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useAppStore } from "../stores/useAppStore";
import axios from "axios";
import {
  Upload,
  Trash2,
  MessageSquare,
  FileText,
  Brain,
  Send,
  Loader2,
  BookOpen,
  ChevronRight,
  AlertTriangle,
  FileSpreadsheet,
  CheckCircle
} from "lucide-react";

const ALLOWED_EXTENSIONS = ["pdf", "docx", "txt", "md", "csv"];
const MAX_UPLOAD_MB = 50;
const STREAMING_ASSISTANT_ID = "streaming-assistant";

// Module-level dedup: tracks the last submitted query per folder to prevent
// double-submits caused by StrictMode, re-renders, or fast repeated clicks.
// Key = folderId, value = { text, time }
const lastQueryByFolder = new Map<string, { text: string; time: number }>();
let isGlobalQuerying = false;

function formatApiError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: string }).msg) : String(d)))
      .join("; ");
  }
  return "Request failed. Please try again.";
}

function validateFileClient(file: File): string | null {
  const ext = file.name.includes(".") ? file.name.split(".").pop()?.toLowerCase() : "";
  if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
    return `File type '.${ext || "unknown"}' is not allowed. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }
  const sizeMb = file.size / (1024 * 1024);
  if (sizeMb > MAX_UPLOAD_MB) {
    return `File size (${sizeMb.toFixed(1)}MB) exceeds maximum (${MAX_UPLOAD_MB}MB)`;
  }
  return null;
}

interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  error_message?: string;
}

interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
}

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Record<string, {
    source: string;
    page?: number;
    row?: number;
    snippet: string;
    document_id?: string;
  }>;
  latency_ms?: number;
}

export default function FolderView() {
  const { folderId } = useParams();
  const { currentFolder } = useAppStore();

  const [activeTab, setActiveTab] = useState<"chat" | "documents">("chat");

  // Document states
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Chat states
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationItem | null>(null);
  // Ref to track activeConversation synchronously (avoids stale closures in async functions)
  const activeConversationRef = useRef<ConversationItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [query, setQuery] = useState("");

  const [streamingFollowups, setStreamingFollowups] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const isGeneratingRef = useRef(false);
  // Tracks the conversation ID that is currently being streamed into,
  // so the activeConversation effect won't overwrite messages mid-flight.
  const streamingConvIdRef = useRef<string | null>(null);
  // Tracks which conv ID is currently being fetched to prevent concurrent duplicate fetches.
  const fetchingMessagesForRef = useRef<string | null>(null);

  // Selected citation side-pane
  const [activeCitationSource, setActiveCitationSource] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Keep activeConversationRef in sync with state
  const setActiveConversationSafe = (conv: ConversationItem | null) => {
    activeConversationRef.current = conv;
    setActiveConversation(conv);
  };

  useEffect(() => {
    if (folderId) {
      activeConversationRef.current = null;
      setActiveConversation(null);
      setMessages([]);
      isGeneratingRef.current = false;
      setIsGenerating(false);
      streamingConvIdRef.current = null;
      fetchingMessagesForRef.current = null;
      fetchDocuments();
      fetchConversations();
    }
  }, [folderId]);

  useEffect(() => {
    // Do NOT fetch messages if:
    // 1. We're currently generating (isGeneratingRef) — the query handler owns the message list.
    // 2. The conversation that just became active is the one we're actively streaming into.
    if (
      activeConversation &&
      !isGeneratingRef.current &&
      streamingConvIdRef.current !== activeConversation.id
    ) {
      fetchMessages(activeConversation.id);
    }
  }, [activeConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // ── Documents operations ──────────────────────────────────────────────
  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`/folders/${folderId}/documents`);
      setDocuments(res.data);
      setDocumentsError(null);
    } catch (e: any) {
      setDocumentsError(formatApiError(e.response?.data?.detail) || "Failed to load documents.");
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files?.length) {
      await handleFilesUpload(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      await handleFilesUpload(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const handleFilesUpload = async (files: File[]) => {
    setUploadError(null);
    for (const file of files) {
      await handleFileUpload(file);
    }
  };

  const handleFileUpload = async (file: File) => {
    const clientErr = validateFileClient(file);
    if (clientErr) {
      setUploadError(clientErr);
      return;
    }

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post(`/folders/${folderId}/documents`, formData);
      await fetchDocuments();
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (e: any) {
      setUploadError(formatApiError(e.response?.data?.detail) || "Upload failed. Verify file details.");
    } finally {
      setUploading(false);
    }
  };

  const handleReprocessDocument = async (docId: string) => {
    setUploadError(null);
    try {
      await axios.post(`/documents/${docId}/reprocess`);
      await fetchDocuments();
    } catch (e: any) {
      setUploadError(formatApiError(e.response?.data?.detail) || "Could not retry indexing.");
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm("Are you sure you want to permanently delete this document and remove its embeddings from ChromaDB?")) return;
    try {
      await axios.delete(`/documents/${docId}`);
      setDocuments(documents.filter(d => d.id !== docId));
      setUploadError(null);
    } catch (e: any) {
      setUploadError(formatApiError(e.response?.data?.detail) || "Deletion failed.");
    }
  };

  // Poll for document parsing states if processing
  useEffect(() => {
    const isProcessing = documents.some(d => d.status === "pending" || d.status === "processing");
    if (isProcessing) {
      const interval = setInterval(() => {
        fetchDocuments();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [documents]);

  // ── Conversation operations ──────────────────────────────────────────
  const fetchConversations = async () => {
    try {
      const res = await axios.get(`/chat/folders/${folderId}/conversations`);
      setConversations(res.data);
      // Use the ref (not state) to avoid stale closure — state value may be
      // stale inside this async function by the time the await resolves.
      if (res.data.length > 0 && !activeConversationRef.current) {
        setActiveConversationSafe(res.data[0]);
      }
    } catch (e) {
      console.error("Failed to load conversations:", e);
    }
  };

  const handleCreateConversation = async () => {
    try {
      const res = await axios.post("/chat/conversations", {
        folder_id: folderId,
        title: `Workspace Discussion ${conversations.length + 1}`
      });
      setConversations([res.data, ...conversations]);
      setActiveConversation(res.data);
    } catch (e) {
      console.error("Failed to create conversation:", e);
    }
  };

  const fetchMessages = async (convId: string) => {
    // Prevent concurrent fetches for the same conversation (e.g. from effect + manual call).
    if (fetchingMessagesForRef.current === convId) return;
    fetchingMessagesForRef.current = convId;
    try {
      const res = await axios.get(`/chat/conversations/${convId}/messages`);
      // Step 1: Deduplicate by ID
      const seenIds = new Set<string>();
      const uniqueById = (res.data as MessageItem[]).filter(msg => {
        if (seenIds.has(msg.id)) return false;
        seenIds.add(msg.id);
        return true;
      });
      // Step 2: Remove consecutive messages with the same role+content.
      // This handles pre-existing duplicate DB rows written by the now-fixed double-write bug
      // (where mem_store.add_message AND db.add were both called for every message).
      const deduped = uniqueById.filter((msg, idx, arr) => {
        if (idx === 0) return true;
        const prev = arr[idx - 1];
        return !(prev.role === msg.role && prev.content === msg.content);
      });
      setMessages(deduped);
    } catch (e) {
      console.error("Failed to load messages:", e);
    } finally {
      // Only clear the guard if this fetch is still the current one
      if (fetchingMessagesForRef.current === convId) {
        fetchingMessagesForRef.current = null;
      }
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!confirm("Delete this conversation thread?")) return;
    try {
      await axios.delete(`/chat/conversations/${convId}`);
      const updated = conversations.filter(c => c.id !== convId);
      setConversations(updated);
      if (activeConversation?.id === convId) {
        setActiveConversation(updated.length > 0 ? updated[0] : null);
        setMessages([]);
      }
    } catch (e) {
      console.error("Delete conversation failed:", e);
    }
  };

  // ── Chat execution (SSE) ──────────────────────────────────────────────
  const handleSendQuery = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || isGenerating || isGeneratingRef.current || isGlobalQuerying) return;

    // Per-folder dedup: reject identical queries submitted within 3 seconds.
    const now = Date.now();
    const lastForFolder = lastQueryByFolder.get(folderId ?? "");
    if (lastForFolder && lastForFolder.text === trimmed && (now - lastForFolder.time) < 3000) {
      console.warn("Prevented duplicate query submission:", trimmed);
      return;
    }
    lastQueryByFolder.set(folderId ?? "", { text: trimmed, time: now });

    // Lock generation FIRST — before any await — so re-entrant calls are blocked immediately.
    isGeneratingRef.current = true;
    setIsGenerating(true);
    isGlobalQuerying = true;

    let conv = activeConversation;
    if (!conv) {
      // Auto create conversation if none exists
      try {
        const res = await axios.post("/chat/conversations", {
          folder_id: folderId,
          title: queryText.slice(0, 30) + (queryText.length > 30 ? "..." : "")
        });
        setConversations([res.data]);
        setActiveConversationSafe(res.data);
        conv = res.data;
      } catch (e) {
        console.error("Failed to auto-create conversation:", e);
        setIsGenerating(false);
        isGeneratingRef.current = false;
        return;
      }
    }

    if (!conv) {
      setIsGenerating(false);
      isGeneratingRef.current = false;
      isGlobalQuerying = false;
      return;
    }

    // Mark this conversation as the one being streamed into BEFORE touching message state.
    // This prevents the activeConversation useEffect from calling fetchMessages mid-flight.
    streamingConvIdRef.current = conv.id;

    if (messages.some((msg) => msg.id === STREAMING_ASSISTANT_ID)) {
      // Prevent duplicate streaming placeholders when a response is already in progress.
      streamingConvIdRef.current = null;
      setIsGenerating(false);
      isGeneratingRef.current = false;
      isGlobalQuerying = false;
      return;
    }

    // Append user query to UI state immediately and reserve a single streaming assistant bubble.
    const userMsg: MessageItem = {
      id: Math.random().toString(),
      role: "user",
      content: queryText
    };
    const assistantPlaceholder: MessageItem = {
      id: STREAMING_ASSISTANT_ID,
      role: "assistant",
      content: "",
      citations: {}
    };

    setMessages((prev) => {
      // Extra safety to prevent double-appends in React Strict Mode
      if (prev.some((msg) => msg.id === STREAMING_ASSISTANT_ID)) return prev;
      return [...prev, userMsg, assistantPlaceholder];
    });
    setQuery("");
    setStreamingFollowups([]);
    setChatError(null);

    // Connect to Server Sent Events (SSE) stream
    try {
      const token = localStorage.getItem("access_token");

      const response = await fetch(`/api/v1/chat/conversations/${conv.id}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ query: queryText })
      });

      if (!response.ok) {
        let errDetail = `Request failed (${response.status})`;
        try {
          const errBody = await response.json();
          errDetail = formatApiError(errBody.detail);
        } catch {
          /* ignore parse errors */
        }
        setMessages((prev) => prev.filter((msg) => msg.id !== STREAMING_ASSISTANT_ID));
        setChatError(errDetail);
        streamingConvIdRef.current = null;
        setIsGenerating(false);
        isGeneratingRef.current = false;
        isGlobalQuerying = false;
        return;
      }

      if (!response.body) throw new Error("Null response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;

        if (value) {
          buffer += decoder.decode(value, { stream: !done });

          // Split events
          const lines = buffer.split("\n\n");
          // Keep the last incomplete block in buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim()) continue;

            // Extract event type and data
            const matchEvent = line.match(/^event:\s*(\w+)/m);
            const matchData = line.match(/^data:\s*(.+)/m);

            if (matchEvent && matchData) {
              const eventType = matchEvent[1];
              const rawData = matchData[1];

              if (eventType === "token") {
                const tokenText = JSON.parse(rawData);
                setMessages(prev => prev.map(msg =>
                  msg.id === STREAMING_ASSISTANT_ID
                    ? { ...msg, content: msg.content + tokenText }
                    : msg
                ));
              } else if (eventType === "citations") {
                const citations = JSON.parse(rawData);
                setMessages(prev => prev.map(msg =>
                  msg.id === STREAMING_ASSISTANT_ID
                    ? { ...msg, citations }
                    : msg
                ));
              } else if (eventType === "followup") {
                const followups = JSON.parse(rawData);
                setStreamingFollowups(followups);
              } else if (eventType === "error") {
                const errorObj = JSON.parse(rawData);
                setMessages(prev => prev.map(msg =>
                  msg.id === STREAMING_ASSISTANT_ID
                    ? { ...msg, content: `${msg.content}\n\n[Error: ${errorObj.detail}]` }
                    : msg
                ));
              } else if (eventType === "done") {
                // Streaming complete. Fetch canonical messages from server (real IDs)
                // to replace the optimistic local state (which has fake STREAMING_ASSISTANT_ID).
                // This is the ONE authoritative fetch — the activeConversation effect is
                // suppressed by streamingConvIdRef so it won't fire a second fetch.
                const convIdToFetch = conv!.id;
                streamingConvIdRef.current = null;
                isGeneratingRef.current = false;
                setIsGenerating(false);
                await fetchMessages(convIdToFetch);
              }
            }
          }
        }
      }

      // Stream ended. If `done` event already handled cleanup + fetch, these are no-ops.
      setStreamingFollowups([]);
      streamingConvIdRef.current = null;
      if (isGeneratingRef.current) {
        // `done` event didn't fire (server closed without it) — fetch canonical messages now.
        isGeneratingRef.current = false;
        setIsGenerating(false);
        await fetchMessages(conv!.id);
      }
      isGlobalQuerying = false;

    } catch (e: any) {
      setMessages((prev) => prev.filter((msg) => msg.id !== STREAMING_ASSISTANT_ID));
      setChatError(e.message || "Connection error while streaming response.");
      setStreamingFollowups([]);
      streamingConvIdRef.current = null;
      setIsGenerating(false);
      isGeneratingRef.current = false;
      isGlobalQuerying = false;
    }
  };

  // Convert raw text into clickable bracketed numbers [1] matching citations
  const renderMessageContent = (msg: MessageItem) => {
    const text = msg.content;
    const citations = msg.citations || {};

    const parts = [];
    let lastIdx = 0;
    const regex = /\[(\d+)\]/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const matchIdx = match.index;
      const num = match[1];

      // Add text leading up to citation
      if (matchIdx > lastIdx) {
        parts.push(text.slice(lastIdx, matchIdx));
      }

      // Add citation link
      if (citations[num]) {
        parts.push(
          <button
            key={matchIdx}
            onClick={() => setActiveCitationSource(citations[num])}
            className="mx-0.5 inline-flex h-5 w-5 items-center justify-center rounded bg-violet-600/20 text-xs font-bold text-violet-400 border border-violet-500/20 hover:bg-violet-500 hover:text-white transition-colors"
          >
            {num}
          </button>
        );
      } else {
        parts.push(`[${num}]`);
      }

      lastIdx = regex.lastIndex;
    }

    if (lastIdx < text.length) {
      parts.push(text.slice(lastIdx));
    }

    return (
      <div className="whitespace-pre-wrap leading-relaxed text-sm">
        {parts.length > 0 ? parts : text}
      </div>
    );
  };

  return (
    <div className="flex h-full flex-1 overflow-hidden">
      {/* Sidebar - Conversation list */}
      {activeTab === "chat" && (
        <div className="hidden md:flex w-60 flex-col border-r border-slate-800 bg-slate-950/40 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Discussions</span>
            <button
              onClick={handleCreateConversation}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <ChevronRight className="h-4 w-4 rotate-90" />
            </button>
          </div>

          <button
            onClick={handleCreateConversation}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-800 bg-slate-900/30 py-2 text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            New Discussion
          </button>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => setActiveConversation(conv)}
                className={`group flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium cursor-pointer transition-colors ${activeConversation?.id === conv.id
                    ? "bg-slate-900 text-white"
                    : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200"
                  }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
                  <span className="truncate">{conv.title}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 rounded p-0.5 text-slate-500 hover:bg-slate-800 hover:text-red-400 transition-all"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Panel View */}
      <div className="flex flex-1 flex-col overflow-hidden bg-slate-950">
        {/* Workspace Toolbar */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xl" style={{ color: currentFolder?.color }}>{currentFolder?.icon || "📁"}</span>
            <div>
              <h2 className="text-base font-bold text-white leading-tight">{currentFolder?.name}</h2>
              <p className="text-[10px] text-slate-500 truncate max-w-sm">{currentFolder?.description || "Workspace folder isolated vector store."}</p>
            </div>
          </div>

          {/* Toggle Tab controls */}
          <div className="flex rounded-lg bg-slate-900/80 p-0.5 border border-slate-800">
            <button
              onClick={() => setActiveTab("chat")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-colors ${activeTab === "chat" ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
            >
              <Brain className="h-3.5 w-3.5" />
              RAG Chat
            </button>
            <button
              onClick={() => setActiveTab("documents")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-colors ${activeTab === "documents" ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
            >
              <FileText className="h-3.5 w-3.5" />
              Documents
              {documents.length > 0 && (
                <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px]">{documents.length}</span>
              )}
            </button>
          </div>
        </div>

        {/* Tab content - RAG Chat Interface */}
        {activeTab === "chat" && (
          <div className="flex flex-1 overflow-hidden">
            <div className="flex flex-1 flex-col overflow-hidden">
              {/* Message History pane */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center text-center p-8">
                    <BookOpen className="h-10 w-10 text-slate-600 mb-3" />
                    <h3 className="text-sm font-semibold text-slate-300">Isolated Chat Workspace</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-md">
                      Ask any questions. The system will search exclusively inside the document files uploaded to this folder and cite its sources.
                    </p>
                  </div>
                ) : (
                  <>
                    {messages.map(msg => (
                      <div
                        key={msg.id}
                        className={`flex gap-4 max-w-3xl ${msg.role === "user" ? "ml-auto flex-row-reverse" : ""
                          }`}
                      >
                        {/* Avatar */}
                        <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-sm font-bold uppercase text-white ${msg.role === "user"
                            ? "bg-violet-600"
                            : "bg-slate-800 border border-slate-700 text-violet-400"
                          }`}>
                          {msg.role === "user" ? "U" : "AI"}
                        </div>

                        {/* Speech Bubble */}
                        <div className={`rounded-xl px-4 py-3 border shadow-sm ${msg.role === "user"
                            ? "bg-slate-900 border-slate-800 text-slate-200"
                            : "bg-slate-900/30 border-slate-800 text-slate-300"
                          }`}>
                          {renderMessageContent(msg)}

                          {/* Metadata / Latency display */}
                          {msg.role === "assistant" && msg.latency_ms && (
                            <p className="text-[9px] text-slate-500 mt-2 flex items-center gap-1.5 border-t border-slate-900 pt-1.5">
                              Latency: {(msg.latency_ms / 1000).toFixed(2)}s
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* suggested followups pane */}
              {streamingFollowups.length > 0 && !isGenerating && (
                <div className="px-6 py-2 flex flex-wrap gap-2 border-t border-slate-900 bg-slate-950/20">
                  {streamingFollowups.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendQuery(q)}
                      className="rounded-full border border-slate-800 bg-slate-900/40 px-3 py-1 text-xs text-slate-400 hover:border-violet-500 hover:text-white transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              {chatError && (
                <div className="mx-6 mb-2 rounded-lg border border-red-800/40 bg-red-950/50 px-3 py-2 text-xs text-red-400">
                  {chatError}
                </div>
              )}

              {/* Chat Input form */}
              <div className="p-4 border-t border-slate-800 bg-slate-950">
                <div className="relative flex items-center">
                  <input
                    type="text"
                    disabled={isGenerating}
                    placeholder="Query this folder's knowledge base..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (query.trim() && !isGenerating && !isGeneratingRef.current) {
                          const q = query;
                          setQuery("");
                          handleSendQuery(q);
                        }
                      }
                    }}
                    className="w-full rounded-xl border border-slate-800 bg-slate-900/50 py-3 pl-4 pr-12 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (query.trim() && !isGenerating && !isGeneratingRef.current) {
                        const q = query;
                        setQuery("");
                        handleSendQuery(q);
                      }
                    }}
                    disabled={!query.trim() || isGenerating}
                    className="absolute right-3 rounded-lg bg-violet-600 p-1.5 text-white hover:bg-violet-500 disabled:opacity-40 transition-colors"
                  >
                    {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Collapsible Citations / Sources details panel */}
            {activeCitationSource && (
              <div className="w-80 border-l border-slate-800 bg-slate-950/90 p-5 overflow-y-auto space-y-4 animate-in slide-in-from-right duration-200">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                    <BookOpen className="h-4 w-4 text-violet-400" />
                    Source Citation
                  </h4>
                  <button
                    onClick={() => setActiveCitationSource(null)}
                    className="rounded text-xs text-slate-500 hover:text-white"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="rounded-lg bg-slate-900 p-3 border border-slate-850">
                    <p className="text-[10px] text-slate-500 uppercase font-semibold">Document name</p>
                    <p className="text-xs font-bold text-white mt-0.5 break-all">{activeCitationSource.source}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-slate-900 p-2.5 border border-slate-850">
                      <p className="text-[10px] text-slate-500 uppercase">Page number</p>
                      <p className="text-xs font-bold text-white mt-0.5">{activeCitationSource.page || "N/A"}</p>
                    </div>
                    <div className="rounded-lg bg-slate-900 p-2.5 border border-slate-850">
                      <p className="text-[10px] text-slate-500 uppercase">Row index</p>
                      <p className="text-xs font-bold text-white mt-0.5">{activeCitationSource.row || "N/A"}</p>
                    </div>
                  </div>

                  <div className="rounded-lg bg-slate-900 p-3 border border-slate-850">
                    <p className="text-[10px] text-slate-500 uppercase font-semibold mb-1">Grounded passage</p>
                    <div className="text-xs text-slate-400 leading-relaxed italic bg-slate-950/40 p-2.5 rounded border border-slate-900 max-h-60 overflow-y-auto">
                      "{activeCitationSource.snippet}"
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab content - Documents Management view */}
        {activeTab === "documents" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {(uploadError || documentsError) && (
              <div className="rounded-lg border border-red-800/40 bg-red-950/50 px-4 py-3 text-sm text-red-400 flex items-start justify-between gap-3">
                <span>{uploadError || documentsError}</span>
                <button
                  type="button"
                  onClick={() => { setUploadError(null); setDocumentsError(null); }}
                  className="text-red-300 hover:text-white shrink-0"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Drag & Drop zone */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex h-44 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all ${dragActive
                  ? "border-violet-500 bg-violet-600/5"
                  : "border-slate-800 hover:border-slate-700 bg-slate-900/20"
                }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.docx,.txt,.md,.csv"
                className="hidden"
              />
              {uploading ? (
                <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
              ) : (
                <Upload className="h-8 w-8 text-slate-500 mb-2" />
              )}
              <h4 className="text-sm font-semibold text-white">Drag & drop knowledge files here</h4>
              <p className="text-xs text-slate-500 mt-1">Supports PDF, DOCX, TXT, Markdown, CSV up to 50MB</p>
            </div>

            {/* Uploaded Documents List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Document Pool</h3>

              {documents.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/10 p-6 text-center text-xs text-slate-500">
                  No files uploaded to this folder yet.
                </div>
              ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-900/10 divide-y divide-slate-800/80 overflow-hidden">
                  {documents.map(doc => (
                    <div key={doc.id} className="flex items-center justify-between p-4 hover:bg-slate-900/30">
                      <div className="flex items-center gap-3 truncate">
                        {doc.file_type === "csv" ? (
                          <FileSpreadsheet className="h-8 w-8 text-amber-500 bg-amber-600/10 p-1.5 rounded-lg flex-shrink-0" />
                        ) : (
                          <FileText className="h-8 w-8 text-violet-500 bg-violet-600/10 p-1.5 rounded-lg flex-shrink-0" />
                        )}
                        <div className="truncate">
                          <h4 className="text-sm font-semibold text-white truncate">{doc.filename}</h4>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {(doc.file_size / (1024 * 1024)).toFixed(2)} MB • {doc.chunk_count} vector chunks
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        {/* Status Badge */}
                        <div className="flex items-center gap-1.5 text-xs font-semibold">
                          {doc.status === "ready" && (
                            <span className="flex items-center gap-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5">
                              <CheckCircle className="h-3 w-3" /> Ready
                            </span>
                          )}
                          {doc.status === "processing" && (
                            <span className="flex items-center gap-1 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5">
                              <Loader2 className="h-3 w-3 animate-spin" /> Indexing
                            </span>
                          )}
                          {doc.status === "pending" && (
                            <span className="flex items-center gap-1 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20 px-2 py-0.5">
                              Pending
                            </span>
                          )}
                          {doc.status === "failed" && (
                            <span
                              title={doc.error_message}
                              className="flex items-center gap-1 rounded bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 cursor-help"
                            >
                              <AlertTriangle className="h-3 w-3" /> Failed
                            </span>
                          )}
                          {(doc.status === "failed" || doc.status === "pending") && (
                            <button
                              type="button"
                              onClick={() => handleReprocessDocument(doc.id)}
                              className="rounded-lg px-2 py-1 text-xs font-semibold text-violet-400 border border-violet-500/30 hover:bg-violet-600/10"
                            >
                              Retry
                            </button>
                          )}
                        </div>

                        {/* Delete Button */}
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

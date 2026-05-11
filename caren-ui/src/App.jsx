import React, { useState, useRef, useCallback, useEffect, memo } from 'react'
import axios from 'axios'
import {
  ShieldCheck, Send, Sparkles, X, Zap, Layers,
  Paperclip, FileText, CheckCircle2, AlertCircle, Mic, ChevronRight,
  MailCheck, BarChart3, Trash2, Sun, Moon, Lock, LogOut
} from 'lucide-react'

// ================================================================
// AUTH — JWT in localStorage + cookie set by backend on login.
// All cross-origin calls send withCredentials so the cookie reaches
// the /voice iframe; the JWT is also sent as a Bearer header for /api.
// ================================================================
const BACKEND = import.meta.env.VITE_BACKEND_URL || ''
const TOKEN_KEY = 'caren-token'

axios.defaults.withCredentials = true

function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
function setToken(t) {
  if (t) {
    localStorage.setItem(TOKEN_KEY, t)
    axios.defaults.headers.common['Authorization'] = `Bearer ${t}`
  } else {
    localStorage.removeItem(TOKEN_KEY)
    delete axios.defaults.headers.common['Authorization']
  }
}
// Re-attach header on hard reload.
const _initialToken = getToken()
if (_initialToken) axios.defaults.headers.common['Authorization'] = `Bearer ${_initialToken}`

// ================================================================
// THEME HOOK — persists "light" | "dark" to localStorage and
// reflects it on <html data-theme="…"> for CSS to react to.
// ================================================================
function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = window.localStorage.getItem('caren-theme')
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('caren-theme', theme)
  }, [theme])

  const toggle = useCallback(() => setTheme(t => (t === 'dark' ? 'light' : 'dark')), [])
  return { theme, toggle }
}

// ================================================================
// TOAST SYSTEM
// ================================================================
function Toast({ toasts, remove }) {
  return (
    <div className="fixed top-6 right-6 z-[999] flex flex-col gap-3 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl border text-sm font-semibold toast-enter ${
            t.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-950/90 border-rose-500/30 text-rose-300'
          }`}
        >
          {t.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{t.message}</span>
          <button onClick={() => remove(t.id)} className="ml-2 opacity-50 hover:opacity-100 transition-opacity">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}

function useToast() {
  const [toasts, setToasts] = useState([])
  const add = useCallback((message, type = 'success') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])
  const remove = useCallback(id => setToasts(prev => prev.filter(t => t.id !== id)), [])
  return { toasts, add, remove }
}

// ================================================================
// VOICE IFRAME (memo'd so it doesn't remount on tab switch)
// ================================================================
const VoiceBridge = memo(({ active, token }) => {
  // Token is in the URL because iframes can't set Authorization headers.
  // The cookie set on login also works when same-origin to backend.
  const src = token
    ? `${BACKEND}/voice/?t=${encodeURIComponent(token)}`
    : `${BACKEND}/voice/`
  return (
    <div
      className="absolute inset-0 top-[96px] bottom-[72px] md:bottom-0 p-3 md:p-8 z-10"
      style={{
        visibility: active ? 'visible' : 'hidden',
        opacity: active ? 1 : 0,
        pointerEvents: active ? 'auto' : 'none',
        transition: 'opacity 0.4s, visibility 0.4s',
      }}
    >
      <div className="h-full w-full rounded-[1.5rem] md:rounded-[2.5rem] glass-panel overflow-hidden shadow-[0_0_60px_rgba(0,0,0,0.5)]">
        <iframe src={src} className="w-full h-full border-none" allow="microphone" />
      </div>
    </div>
  )
})

// ================================================================
// LOGIN SCREEN
// ================================================================
function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await axios.post(`${BACKEND}/api/auth/login`, { password })
      onLogin(res.data.token)
    } catch (err) {
      console.error('[login error]', err?.response?.status, err?.message, err?.response?.data)
      setError(err.response?.status === 401 ? 'Wrong password.' : `Login failed: ${err?.response?.data?.detail || err?.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 font-sans">
      <form
        onSubmit={submit}
        className="glass-panel rounded-[2.5rem] p-10 w-full max-w-md space-y-6 animate-modal"
      >
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-500 to-violet-600 flex items-center justify-center logo-glow">
            <Lock className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter gradient-text leading-none">CAREN</h1>
            <p className="text-[9px] text-slate-600 uppercase tracking-[0.25em] font-bold mt-1">Authentication Required</p>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-[9px] font-black text-slate-600 uppercase tracking-[0.2em] ml-1 block">Access Key</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoFocus
            placeholder="••••••••"
            className="w-full bg-white/[0.03] border border-white/[0.08] px-5 py-3.5 rounded-2xl outline-none text-white placeholder-slate-700 text-sm neon-input"
          />
          {error && (
            <p className="text-rose-400 text-xs flex items-center gap-1.5 mt-2">
              <AlertCircle size={12} /> {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !password}
          className="w-full py-4 rounded-[1.5rem] bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 text-white font-black text-xs uppercase tracking-[0.25em] shadow-[0_4px_24px_rgba(34,211,238,0.3)] hover:shadow-[0_4px_40px_rgba(34,211,238,0.5)] hover:scale-[1.01] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          style={{ transition: 'transform 0.15s, box-shadow 0.2s' }}
        >
          {loading ? 'Authenticating…' : 'Unlock'}
        </button>
      </form>
    </div>
  )
}

// ================================================================
// MAIN APP
// ================================================================
function App() {
  const [activeTab, setActiveTab] = useState('chat')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState([])
  const [isComposing, setIsComposing] = useState(false)
  const [fetchLimit, setFetchLimit] = useState(10)

  const [emailForm, setEmailForm] = useState({ to: '', subject: '', body: '' })
  const [attachmentFile, setAttachmentFile] = useState(null)
  const [generating, setGenerating] = useState(false)

  // Auth state — null = unknown/loading, '' = logged out, string = JWT
  const [token, setTokenState] = useState(getToken)

  const fileInputRef = useRef(null)
  const { toasts, add: addToast, remove: removeToast } = useToast()
  const { theme, toggle: toggleTheme } = useTheme()

  const API = `${BACKEND}/api/mail`

  // ── Global 401 interceptor: any expired/invalid token → log out ──
  useEffect(() => {
    const id = axios.interceptors.response.use(
      r => r,
      err => {
        if (err.response?.status === 401) {
          setToken(null)
          setTokenState(null)
        }
        return Promise.reject(err)
      }
    )
    return () => axios.interceptors.response.eject(id)
  }, [])

  // ── Verify token on mount; if backend rejects, log out ──
  useEffect(() => {
    if (!token) return
    axios.get(`${BACKEND}/api/auth/check`).catch(() => {
      setToken(null)
      setTokenState(null)
    })
  }, [token])

  const handleLogin = (jwt) => {
    setToken(jwt)
    setTokenState(jwt)
  }

  const handleLogout = async () => {
    try { await axios.post(`${BACKEND}/api/auth/logout`) } catch { /* ignore */ }
    setToken(null)
    setTokenState(null)
    setData([])
  }

  if (!token) return <LoginScreen onLogin={handleLogin} />

  // ── Fetch data (summaries or spam) ──
  const handleFetchData = async (endpoint, tab) => {
    setActiveTab(tab)
    setLoading(true)
    setData([])
    try {
      const res = await axios.get(`${API}/${endpoint}?limit=${fetchLimit}`)
      setData(res.data.data || [])
    } catch (err) {
      console.error('[fetchData error]', err?.response?.status, err?.message, err?.response?.data)
      addToast(err?.response?.data?.detail || 'Failed to fetch data.', 'error')
    } finally {
      setLoading(false)
    }
  }

  // ── AI body generation ──
  const handleGenerateBody = async () => {
    if (!emailForm.subject) return addToast('Enter a subject first.', 'error')
    setGenerating(true)
    try {
      const res = await axios.post(`${API}/generate-body`, { subject: emailForm.subject })
      setEmailForm(f => ({ ...f, body: res.data.body }))
    } catch (err) {
      console.error('[generate-body error]', err?.response?.status, err?.message, err?.response?.data)
      addToast(err?.response?.data?.detail || 'AI generation failed.', 'error')
    } finally {
      setGenerating(false)
    }
  }

  // ── Send email (multipart FormData for attachment support) ──
  const handleSendEmail = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('to', emailForm.to)
      fd.append('subject', emailForm.subject)
      fd.append('body', emailForm.body)
      if (attachmentFile) fd.append('attachment', attachmentFile)
      await axios.post(`${API}/send`, fd)
      addToast('Email sent successfully!', 'success')
      closeCompose()
    } catch (err) {
      console.error('[send error]', err?.response?.status, err?.message, err?.response?.data)
      addToast(err?.response?.data?.detail || 'Failed to send email.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const closeCompose = () => {
    setIsComposing(false)
    setEmailForm({ to: '', subject: '', body: '' })
    setAttachmentFile(null)
  }

  // ════════════════════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════════════════════
  return (
    <div className="flex h-screen w-full md:p-5 md:gap-5 font-sans">
      <Toast toasts={toasts} remove={removeToast} />

      {/* ═══════════ SIDEBAR (desktop only) ═══════════ */}
      <aside className="hidden md:flex w-72 glass-panel rounded-[3rem] p-7 flex-col z-50 shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-12">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-500 to-violet-600 flex items-center justify-center logo-glow">
            <Zap className="text-white fill-white" size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter gradient-text leading-none">CAREN</h1>
            <p className="text-[9px] text-slate-600 uppercase tracking-[0.25em] font-bold mt-0.5">AI Mail System</p>
          </div>
        </div>

        {/* Nav buttons */}
        <nav className="flex flex-col gap-2">
          <NavBtn active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} icon={<Mic size={18} />} label="Neural Hub" sublabel="Voice assistant" color="cyan" />
          <NavBtn active={activeTab === 'summaries'} onClick={() => handleFetchData('summarize', 'summaries')} icon={<Layers size={18} />} label="Intel Brief" sublabel="Inbox summaries" color="purple" loading={loading && activeTab === 'summaries'} />
          <NavBtn active={activeTab === 'spam'} onClick={() => handleFetchData('classify', 'spam')} icon={<ShieldCheck size={18} />} label="Security Scan" sublabel="Spam classifier" color="emerald" loading={loading && activeTab === 'spam'} />
        </nav>

        {/* Scan depth slider */}
        <div className="mt-auto px-1 pt-6 border-t border-white/[0.05]">
          <div className="flex justify-between items-center mb-3">
            <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Scan Depth</span>
            <span className="text-cyan-400 font-mono text-xs font-bold bg-cyan-400/10 px-2 py-0.5 rounded-lg">{fetchLimit}</span>
          </div>
          <input type="range" min="5" max="50" step="5" value={fetchLimit} onChange={e => setFetchLimit(e.target.value)} className="w-full h-1 rounded-full cursor-pointer" />
        </div>

        {/* Theme toggle + logout */}
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-pressed={theme === 'light'}
            className="theme-toggle flex-1"
          >
            <span className="icon-swap">
              <Sun size={16} className="icon-sun" />
              <Moon size={16} className="icon-moon" />
            </span>
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Sign out"
            title="Sign out"
            className="theme-toggle"
            style={{ width: 'auto', padding: '0.65rem 0.9rem' }}
          >
            <LogOut size={16} />
          </button>
        </div>

        {/* Compose button */}
        <button
          onClick={() => setIsComposing(true)}
          className="mt-3 py-4 rounded-[1.5rem] bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 text-white font-black text-[11px] uppercase tracking-[0.2em] shadow-[0_8px_32px_rgba(34,211,238,0.25)] hover:shadow-[0_8px_40px_rgba(34,211,238,0.45)] hover:scale-[1.02] active:scale-95 flex items-center justify-center gap-2"
          style={{ transition: 'transform 0.15s, box-shadow 0.2s' }}
        >
          <Send size={14} /> New Transmission
        </button>
      </aside>

      {/* ═══════════ MAIN PANEL ═══════════ */}
      <main className="flex-1 relative glass-panel rounded-none md:rounded-[3rem] overflow-hidden">
        {/* Header bar */}
        <header className="px-4 md:px-10 py-5 md:py-7 flex justify-between items-center border-b border-white/[0.04] relative z-40">
          <div className="flex items-center gap-3 md:gap-5">
            {/* Mobile: logo + current tab name */}
            <div className="flex items-center gap-2.5 md:hidden">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-500 to-violet-600 flex items-center justify-center logo-glow shrink-0">
                <Zap className="text-white fill-white" size={16} />
              </div>
              <div>
                <h1 className="text-base font-black tracking-tighter gradient-text leading-none">CAREN</h1>
                <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">
                  {activeTab === 'chat' ? 'Neural Hub' : activeTab === 'summaries' ? 'Intel Brief' : 'Security Scan'}
                </p>
              </div>
            </div>
            {/* Desktop: accent bar + tab name */}
            <div className="hidden md:flex items-center gap-5">
              <div className="h-9 w-[2px] rounded-full bg-gradient-to-b from-cyan-400 via-blue-500 to-transparent" />
              <div>
                <p className="text-[9px] uppercase tracking-[0.4em] font-bold text-slate-600">Protocol v4.2</p>
                <h2 className="text-white font-black text-base uppercase tracking-wide leading-tight">
                  {activeTab === 'chat' ? 'Neural Hub' : activeTab === 'summaries' ? 'Intel Brief' : 'Security Scan'}
                </h2>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 md:gap-3 bg-white/[0.03] border border-white/[0.07] px-3 md:px-5 py-2 md:py-2.5 rounded-full">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400" />
              </span>
              <span className="hidden sm:block text-[9px] font-mono font-bold text-cyan-400 tracking-widest uppercase">Link Active</span>
            </div>
            {/* Mobile-only: theme toggle + logout */}
            <div className="flex md:hidden items-center gap-1">
              <button
                type="button"
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                className="p-2 rounded-xl border border-white/[0.08] text-slate-500 hover:text-white transition-colors"
              >
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                aria-label="Sign out"
                className="p-2 rounded-xl border border-white/[0.08] text-slate-500 hover:text-rose-400 transition-colors"
              >
                <LogOut size={15} />
              </button>
            </div>
          </div>
        </header>

        {/* Voice iframe (always mounted, toggled via visibility) */}
        <VoiceBridge active={activeTab === 'chat'} token={token} />

        {/* Data content pane */}
        <div
          className="absolute inset-0 top-[88px] bottom-[72px] md:bottom-0 p-4 md:p-8 overflow-y-auto z-20"
          style={{
            visibility: activeTab !== 'chat' ? 'visible' : 'hidden',
            opacity: activeTab !== 'chat' ? 1 : 0,
            transition: 'opacity 0.4s, visibility 0.4s',
          }}
        >
          {loading ? (
            <LoadingSkeleton />
          ) : (
            <div className="max-w-4xl mx-auto space-y-4 pb-4 md:pb-20">
              {/* Summaries */}
              {activeTab === 'summaries' && data.map((item, i) => (
                <div key={i} className="glossy-button rounded-[2rem] p-7 animate-float-up" style={{ animationDelay: `${i * 60}ms` }}>
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-purple-500/15 flex items-center justify-center shrink-0">
                        <MailCheck size={15} className="text-purple-400" />
                      </div>
                      <h4 className="font-bold text-white text-sm leading-snug">{item.subject}</h4>
                    </div>
                    <span className="text-[9px] font-black uppercase tracking-widest text-purple-400/60 bg-purple-400/10 px-3 py-1 rounded-full shrink-0">Summary</span>
                  </div>
                  <p className="text-slate-400 text-sm leading-relaxed pl-11">{item.summary}</p>
                </div>
              ))}

              {/* Spam classification table */}
              {activeTab === 'spam' && data.length > 0 && (
                <div className="glossy-button rounded-[2rem] overflow-hidden animate-float-up">
                  <div className="px-7 py-5 border-b border-white/[0.06] flex items-center gap-3">
                    <BarChart3 size={16} className="text-emerald-400" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">{data.length} emails scanned</span>
                    <span className="ml-auto text-[10px] text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full font-bold">{data.filter(d => d.label === 'Clean').length} clean</span>
                    <span className="text-[10px] text-rose-400 bg-rose-400/10 px-3 py-1 rounded-full font-bold">{data.filter(d => d.label === 'Spam').length} spam</span>
                  </div>
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-white/[0.04]">
                        <th className="px-7 py-3 text-[9px] font-black uppercase tracking-widest text-slate-600">Subject</th>
                        <th className="px-7 py-3 text-[9px] font-black uppercase tracking-widest text-slate-600 text-right">Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {data.map((item, i) => (
                        <tr key={i} className="hover:bg-white/[0.03] transition-colors">
                          <td className="px-7 py-4 text-sm text-slate-300 font-medium max-w-xs truncate">{item.subject}</td>
                          <td className="px-7 py-4 text-right">
                            {item.label === 'Spam' ? (
                              <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-rose-400 bg-rose-400/10 border border-rose-400/20 px-3 py-1 rounded-full">
                                <AlertCircle size={11} /> Spam
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-3 py-1 rounded-full">
                                <CheckCircle2 size={11} /> Clean
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Empty state */}
              {!loading && data.length === 0 && (
                <div className="mt-40 flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-[1.5rem] bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                    <Zap size={28} className="text-slate-700" />
                  </div>
                  <p className="text-slate-600 font-mono text-xs uppercase tracking-widest">Awaiting data stream…</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* ═══════════ MOBILE BOTTOM NAV ═══════════ */}
      <MobileNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onFetchData={handleFetchData}
        onCompose={() => setIsComposing(true)}
        loading={loading}
      />

      {/* ═══════════ COMPOSE MODAL ═══════════ */}
      {isComposing && (
        <div className="fixed inset-0 z-[100] flex items-end md:items-center justify-center md:p-6 glass-blur bg-black/70">
          <div className="glass-panel w-full md:max-w-2xl rounded-t-[2.5rem] md:rounded-[2.5rem] shadow-[0_0_80px_rgba(34,211,238,0.1)] animate-slide-up md:animate-modal overflow-hidden">
            <div className="max-h-[90vh] md:max-h-none overflow-y-auto">
            {/* Header */}
            <div className="px-6 md:px-10 pt-8 md:pt-10 pb-5 md:pb-6 flex justify-between items-start border-b border-white/[0.05]">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-7 h-7 rounded-xl bg-cyan-500/15 flex items-center justify-center">
                    <Send size={14} className="text-cyan-400" />
                  </div>
                  <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">Outbound Mail</h2>
                </div>
                <div className="flex items-center gap-2 pl-10">
                  <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
                  <p className="text-[9px] font-mono text-slate-600 uppercase tracking-[0.3em]">Secure Link Ready</p>
                </div>
              </div>
              <button
                onClick={closeCompose}
                className="p-3 hover:bg-white/[0.06] rounded-2xl border border-transparent hover:border-white/[0.08] text-slate-500 hover:text-white"
                style={{ transition: 'background 0.15s, border-color 0.15s, color 0.15s' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSendEmail} className="px-6 md:px-10 py-6 md:py-8 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-600 uppercase tracking-[0.2em] ml-1">Recipient</label>
                  <input type="email" placeholder="target@domain.com" required className="w-full bg-white/[0.03] border border-white/[0.08] px-5 py-3.5 rounded-2xl outline-none text-white placeholder-slate-700 text-sm neon-input" value={emailForm.to} onChange={e => setEmailForm(f => ({ ...f, to: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-600 uppercase tracking-[0.2em] ml-1">Subject</label>
                  <input type="text" placeholder="Message subject…" required className="w-full bg-white/[0.03] border border-white/[0.08] px-5 py-3.5 rounded-2xl outline-none text-white placeholder-slate-700 text-sm neon-input" value={emailForm.subject} onChange={e => setEmailForm(f => ({ ...f, subject: e.target.value }))} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center ml-1">
                  <label className="text-[9px] font-black text-slate-600 uppercase tracking-[0.2em]">Message</label>
                  <button
                    type="button" onClick={handleGenerateBody} disabled={generating}
                    className="flex items-center gap-1.5 bg-violet-500/10 text-violet-400 border border-violet-500/20 px-4 py-1.5 rounded-full text-[10px] font-black disabled:opacity-50"
                    style={{ transition: 'background 0.15s, color 0.15s' }}
                  >
                    <Sparkles size={12} className={generating ? 'animate-spin' : ''} />
                    {generating ? 'Generating…' : 'AI Generate'}
                  </button>
                </div>
                <textarea rows="6" placeholder="Write your message…" required className="w-full bg-white/[0.03] border border-white/[0.08] px-5 py-4 rounded-2xl outline-none resize-none text-white placeholder-slate-700 text-sm neon-input" value={emailForm.body} onChange={e => setEmailForm(f => ({ ...f, body: e.target.value }))} />
              </div>

              {/* Attachment */}
              <div className="flex items-center gap-3">
                <input type="file" ref={fileInputRef} className="hidden" onChange={e => setAttachmentFile(e.target.files[0] || null)} />
                <button
                  type="button" onClick={() => fileInputRef.current.click()}
                  className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-cyan-500/30 text-slate-400 hover:text-cyan-400 px-4 py-2.5 rounded-2xl text-xs font-bold"
                  style={{ transition: 'background 0.15s, border-color 0.15s, color 0.15s' }}
                >
                  <Paperclip size={15} /> Attach File
                </button>
                {attachmentFile && (
                  <div className="flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 px-4 py-2 rounded-2xl text-xs font-semibold max-w-xs">
                    <FileText size={13} className="shrink-0" />
                    <span className="truncate">{attachmentFile.name}</span>
                    <span className="text-cyan-500/60 shrink-0">{(attachmentFile.size / 1024).toFixed(0)} KB</span>
                    <button type="button" onClick={() => { setAttachmentFile(null); fileInputRef.current.value = '' }} className="ml-1 text-cyan-500/60 hover:text-rose-400 transition-colors">
                      <Trash2 size={12} />
                    </button>
                  </div>
                )}
              </div>

              {/* Send button */}
              <button
                type="submit" disabled={loading}
                className="w-full py-4 rounded-[1.5rem] bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-600 text-white font-black text-xs uppercase tracking-[0.25em] shadow-[0_4px_24px_rgba(34,211,238,0.3)] hover:shadow-[0_4px_40px_rgba(34,211,238,0.5)] hover:scale-[1.01] active:scale-95 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                style={{ transition: 'transform 0.15s, box-shadow 0.2s' }}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Transmitting…
                  </span>
                ) : (
                  <><Send size={15} /> Execute Transmission</>
                )}
              </button>
            </form>
            </div>{/* end scrollable wrapper */}
          </div>
        </div>
      )}
    </div>
  )
}

// ================================================================
// NAV BUTTON
// ================================================================
function NavBtn({ active, onClick, icon, label, sublabel, color, loading }) {
  const palette = {
    cyan:    { active: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/20 shadow-[0_0_20px_rgba(34,211,238,0.15)]', dot: 'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,1)]' },
    purple:  { active: 'text-purple-300 bg-purple-400/10 border-purple-400/20 shadow-[0_0_20px_rgba(168,85,247,0.15)]', dot: 'bg-purple-400 shadow-[0_0_8px_rgba(168,85,247,1)]' },
    emerald: { active: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20 shadow-[0_0_20px_rgba(16,185,129,0.15)]', dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,1)]' },
  }
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-4 w-full px-5 py-4 rounded-[1.5rem] border font-semibold text-sm ${
        active ? palette[color].active : 'border-transparent text-slate-600 hover:text-slate-300 hover:bg-white/[0.03]'
      }`}
      style={{ transition: 'background 0.15s, color 0.15s, border-color 0.15s, box-shadow 0.15s' }}
    >
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${active ? 'bg-white/10' : 'bg-white/[0.03]'}`}>
        {loading ? <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" /> : icon}
      </div>
      <div className="flex flex-col items-start leading-none">
        <span className="font-bold text-sm">{label}</span>
        <span className="text-[10px] opacity-50 mt-0.5">{sublabel}</span>
      </div>
      {active && (
        <div className="ml-auto flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${palette[color].dot}`} />
          <ChevronRight size={14} className="opacity-40" />
        </div>
      )}
    </button>
  )
}

// ================================================================
// LOADING SKELETON
// ================================================================
function LoadingSkeleton() {
  return (
    <div className="max-w-4xl mx-auto w-full mt-6 space-y-4">
      <div className="flex items-center gap-3 animate-pulse mb-6">
        <div className="h-px w-12 bg-cyan-400 rounded-full" />
        <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-[0.4em] font-bold">Scanning servers…</span>
      </div>
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="h-36 w-full glass-panel rounded-[2rem] animate-shimmer relative overflow-hidden">
          <div className="p-8 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 bg-white/[0.04] rounded-xl" />
              <div className="h-4 w-2/5 bg-white/[0.04] rounded-lg" />
            </div>
            <div className="h-3 w-full bg-white/[0.04] rounded-md ml-10" />
            <div className="h-3 w-3/5 bg-white/[0.04] rounded-md ml-10" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ================================================================
// MOBILE BOTTOM NAV
// ================================================================
function MobileNavBtn({ active, onClick, icon, label, color, loading }) {
  const colors = {
    cyan:    'text-cyan-400',
    purple:  'text-purple-400',
    emerald: 'text-emerald-400',
  }
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1 flex-1 py-2 rounded-2xl transition-colors ${active ? colors[color] : 'text-slate-600'}`}
    >
      {loading
        ? <span className="w-5 h-5 border-2 border-current/30 border-t-current rounded-full animate-spin" />
        : icon
      }
      <span className="text-[9px] font-black uppercase tracking-wider">{label}</span>
    </button>
  )
}

function MobileNav({ activeTab, onTabChange, onFetchData, onCompose, loading }) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden">
      <div className="glass-panel border-t border-white/[0.07] flex items-center px-3 pt-2 pb-safe">
        <MobileNavBtn
          active={activeTab === 'chat'}
          onClick={() => onTabChange('chat')}
          icon={<Mic size={20} />}
          label="Hub"
          color="cyan"
        />
        <MobileNavBtn
          active={activeTab === 'summaries'}
          onClick={() => onFetchData('summarize', 'summaries')}
          icon={<Layers size={20} />}
          label="Brief"
          color="purple"
          loading={loading && activeTab === 'summaries'}
        />
        <button
          onClick={onCompose}
          className="flex flex-col items-center gap-1 flex-1 py-2 rounded-2xl text-white"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-violet-600 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.35)] active:scale-95" style={{ transition: 'transform 0.15s' }}>
            <Send size={16} />
          </div>
          <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">New</span>
        </button>
        <MobileNavBtn
          active={activeTab === 'spam'}
          onClick={() => onFetchData('classify', 'spam')}
          icon={<ShieldCheck size={20} />}
          label="Scan"
          color="emerald"
          loading={loading && activeTab === 'spam'}
        />
      </div>
    </nav>
  )
}

export default App
import { useState } from 'react'
import axios from 'axios'
import { Mail, ShieldCheck, Send, RefreshCw, MessageSquare, Mic, StopCircle, User } from 'lucide-react'

function App() {
  // --- State Management ---
  const [activeTab, setActiveTab] = useState('chat') // 'chat', 'summaries', 'spam'
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState([]) // Stores summaries or spam results
  
  // Compose Email State
  const [emailForm, setEmailForm] = useState({ to: '', subject: '', body: '' })
  const [isComposing, setIsComposing] = useState(false)

  const API_BASE = "http://localhost:8000/api/mail"

  // --- API Functions ---

  const handleSummarize = async () => {
    setLoading(true); setActiveTab('summaries');
    try {
      const res = await axios.get(`${API_BASE}/summarize`)
      setData(res.data.data)
    } catch (err) { alert("Error fetching summaries") }
    finally { setLoading(false) }
  }

  const handleClassify = async () => {
    setLoading(true); setActiveTab('spam');
    try {
      const res = await axios.get(`${API_BASE}/classify`)
      setData(res.data.data)
    } catch (err) { alert("Error classifying spam") }
    finally { setLoading(false) }
  }

  const handleGenerateBody = async () => {
    if (!emailForm.subject) return alert("Enter a subject first!")
    setLoading(true)
    try {
      const res = await axios.post(`${API_BASE}/generate-body`, { subject: emailForm.subject })
      setEmailForm({ ...emailForm, body: res.data.body })
    } catch (err) { alert("Error generating body") }
    finally { setLoading(false) }
  }

  const handleSendEmail = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await axios.post(`${API_BASE}/send`, emailForm)
      alert("Email Sent Successfully!")
      setIsComposing(false)
      setEmailForm({ to: '', subject: '', body: '' })
    } catch (err) { alert("Failed to send email") }
    finally { setLoading(false) }
  }

  return (
    <div className="flex h-screen bg-slate-900 text-white font-sans">
      
      {/* --- SIDEBAR --- */}
      <div className="w-64 bg-slate-800 border-r border-slate-700 p-4 flex flex-col gap-4">
        <h2 className="text-xl font-bold text-sky-400 mb-4 px-2">Caren AI</h2>
        
        <button onClick={() => setActiveTab('chat')} className={`flex items-center gap-3 p-3 rounded-lg transition ${activeTab === 'chat' ? 'bg-sky-600' : 'hover:bg-slate-700'}`}>
          <MessageSquare size={20}/> Voice Assistant
        </button>

        <button onClick={handleSummarize} className={`flex items-center gap-3 p-3 rounded-lg transition ${activeTab === 'summaries' ? 'bg-sky-600' : 'hover:bg-slate-700'}`}>
          <RefreshCw size={20} className={loading && activeTab === 'summaries' ? "animate-spin" : ""}/> Summarize Inbox
        </button>

        <button onClick={handleClassify} className={`flex items-center gap-3 p-3 rounded-lg transition ${activeTab === 'spam' ? 'bg-sky-600' : 'hover:bg-slate-700'}`}>
          <ShieldCheck size={20}/> Spam Filter
        </button>

        <div className="mt-auto">
          <button onClick={() => setIsComposing(true)} className="w-full bg-indigo-600 hover:bg-indigo-500 p-3 rounded-lg font-bold flex items-center justify-center gap-2">
            <Send size={18}/> Compose
          </button>
        </div>
      </div>

      {/* --- MAIN CONTENT AREA --- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        <header className="p-4 border-b border-slate-700 flex justify-between items-center">
          <h3 className="capitalize font-medium text-slate-400">{activeTab.replace('-',' ')}</h3>
          <div className="bg-slate-800 px-3 py-1 rounded-full text-xs text-sky-400 border border-sky-400">System Active</div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          
          {/* VOICE MODE VIEW */}
          {activeTab === 'chat' && (
            <div className="h-full flex flex-col items-center justify-center text-center">
               <div className="w-32 h-32 bg-sky-500/10 rounded-full flex items-center justify-center border-2 border-sky-500 animate-pulse mb-6">
                 <Mic size={48} className="text-sky-500"/>
               </div>
               <h2 className="text-2xl font-bold mb-2">Voice Assistant Active</h2>
               <p className="text-slate-400 max-w-md">The stand-alone voice mode is running on the backend. You can speak to Caren at any time.</p>
               <a href="http://localhost:8000/" target="_blank" className="mt-6 text-sky-400 underline text-sm">Open Voice Bridge</a>
            </div>
          )}

          {/* SUMMARIES VIEW */}
          {activeTab === 'summaries' && (
            <div className="grid gap-4">
              {data.map((item, i) => (
                <div key={i} className="bg-slate-800 p-4 rounded-xl border border-slate-700">
                  <h4 className="font-bold text-sky-400 mb-1">{item.subject}</h4>
                  <p className="text-slate-300 text-sm">{item.summary}</p>
                </div>
              ))}
            </div>
          )}

          {/* SPAM VIEW */}
          {activeTab === 'spam' && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-700 text-slate-400 text-sm uppercase">
                  <tr><th className="p-4">Subject</th><th className="p-4">Status</th></tr>
                </thead>
                <tbody>
                  {data.map((item, i) => (
                    <tr key={i} className="border-t border-slate-700">
                      <td className="p-4 text-sm">{item.subject}</td>
                      <td className="p-4 text-sm font-bold">
                        <span className={item.label === 'Spam' ? 'text-red-400' : 'text-green-400'}>{item.label}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>

      {/* --- COMPOSE MODAL --- */}
      {isComposing && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 w-full max-w-2xl rounded-2xl border border-slate-700 p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">New Message</h2>
              <button onClick={() => setIsComposing(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleSendEmail} className="flex flex-col gap-4">
              <input type="email" placeholder="To" required className="bg-slate-900 border border-slate-700 p-3 rounded-lg" value={emailForm.to} onChange={e => setEmailForm({...emailForm, to: e.target.value})}/>
              <input type="text" placeholder="Subject" required className="bg-slate-900 border border-slate-700 p-3 rounded-lg" value={emailForm.subject} onChange={e => setEmailForm({...emailForm, subject: e.target.value})}/>
              <div className="flex gap-2">
                 <button type="button" onClick={handleGenerateBody} className="text-xs bg-sky-600/20 text-sky-400 border border-sky-400 px-3 py-1 rounded-full hover:bg-sky-600/40 transition">AI Auto-Generate Body</button>
              </div>
              <textarea placeholder="Message Body..." rows="6" required className="bg-slate-900 border border-slate-700 p-3 rounded-lg resize-none" value={emailForm.body} onChange={e => setEmailForm({...emailForm, body: e.target.value})}></textarea>
              <button type="submit" className="bg-indigo-600 p-3 rounded-lg font-bold hover:bg-indigo-500 mt-2">Send Email</button>
            </form>
          </div>
        </div>
      )}

    </div>
  )
}

export default App

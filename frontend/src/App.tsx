import { useEffect, useState } from 'react'
type Result = {id:number;sample_id:string;patient_reference?:string;analyzer:string;device_id:string;received_at:string;status:string;values:Record<string,{value:number;unit?:string;flag?:string}>}
const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export default function App() {
 const [results,setResults]=useState<Result[]>([]); const [error,setError]=useState('')
 useEffect(()=>{fetch(`${API}/api/v1/results`).then(r=>{if(!r.ok)throw new Error();return r.json()}).then(setResults).catch(()=>setError('Cannot reach CBC Connect API. Check that Docker services are running.'))},[])
 const pending=results.filter(r=>r.status==='PENDING_REVIEW').length
 return <main className="shell">
  <header className="topbar"><div className="brand"><span className="logo">CBC</span><div><strong>CBC Connect</strong><small>Laboratory results workspace</small></div></div><span className="badge">Standalone mode</span></header>
  <section className="intro"><div><p className="eyebrow">LABORATORY OVERVIEW</p><h1>Complete blood count results</h1><p className="muted">Receive, organize and review analyzer results in one workspace.</p></div><div className="device"><span className="dot"></span><div><b>Analyzer receiver</b><small>Protocol configuration pending</small></div></div></section>
  <section className="stats"><article><span>Received results</span><b>{results.length}</b><small>Latest 200 records</small></article><article><span>Pending review</span><b>{pending}</b><small>Requires authorized review</small></article><article><span>Connected analyzers</span><b>—</b><small>Device setup not configured</small></article></section>
  <section className="panel"><div className="panel-head"><div><h2>Recent CBC results</h2><p className="muted">Analyzer values are preserved as received.</p></div><span className="tag">Review queue</span></div>
   {error&&<p className="error">{error}</p>}{!error&&results.length===0&&<div className="empty"><div className="empty-icon">＋</div><b>No results received yet</b><p>Connect an analyzer adapter or send a normalized test payload to the API.</p></div>}
   {results.length>0&&<div className="table-wrap"><table><thead><tr><th>Sample ID</th><th>Patient reference</th><th>Analyzer</th><th>Received</th><th>Status</th></tr></thead><tbody>{results.map(r=><tr key={r.id}><td><b>{r.sample_id}</b></td><td>{r.patient_reference||'—'}</td><td>{r.analyzer}</td><td>{new Date(r.received_at).toLocaleString()}</td><td><span className="status">{r.status.replace('_',' ')}</span></td></tr>)}</tbody></table></div>}
  </section><footer>CBC Connect · Initial development scaffold · Results require qualified staff review.</footer>
 </main>
}

import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { PDFDocument } from 'pdf-lib'

GlobalWorkerOptions.workerSrc = workerUrl

type Doc = {id:number;filename:string;content_type:string}
type Tool = 'highlight'|'pen'|'text'|'comment'
type Mark = {page:number;x:number;y:number;text:string}
type Props = {document:Doc;resultId:number;onClose:()=>void;onSave:(blob:Blob,data:Record<string,unknown>)=>Promise<void>}
const API=import.meta.env.VITE_API_BASE_URL||'http://localhost:8900'

export default function DocumentAnnotator({document,resultId,onClose,onSave}:Props){
 const baseRef=useRef<HTMLCanvasElement>(null), overlayRef=useRef<HTMLCanvasElement>(null), pdfRef=useRef<any>(null), imageRef=useRef<HTMLImageElement|null>(null)
 const overlays=useRef<Record<number,string>>({}), drawing=useRef(false), last=useRef<{x:number;y:number}|null>(null)
 const [page,setPage]=useState(1),[pages,setPages]=useState(1),[tool,setTool]=useState<Tool>('highlight'),[comments,setComments]=useState<Mark[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[dimensions,setDimensions]=useState({width:0,height:0})
 const isPdf=document.content_type==='application/pdf'
 useEffect(()=>{let active=true;(async()=>{try{
  const response=await fetch(API+'/api/v1/results/'+resultId+'/documents/'+document.id,{headers:{Authorization:'Bearer '+localStorage.getItem('cbc_token')}})
  if(!response.ok)throw new Error('Unable to load source document')
  const data=await response.arrayBuffer()
  if(isPdf){pdfRef.current=await getDocument({data}).promise;if(!active)return;setPages(pdfRef.current.numPages);await renderPage(1)}
  else{const blob=new Blob([data],{type:document.content_type}),url=URL.createObjectURL(blob),img=new Image();img.onload=()=>{if(!active)return;imageRef.current=img;const scale=Math.min(1,900/img.naturalWidth);const w=Math.round(img.naturalWidth*scale),h=Math.round(img.naturalHeight*scale);setDimensions({width:w,height:h});const c=baseRef.current;if(c){c.width=w;c.height=h;c.getContext('2d')?.drawImage(img,0,0,w,h);setupOverlay(w,h)}};img.onerror=()=>setError('This image could not be displayed.');img.src=url}
 }catch(e){setError((e as Error).message)}})();return()=>{active=false}},[document.id])
 function setupOverlay(w:number,h:number,pageNo=page){const c=overlayRef.current;if(!c)return;c.width=w;c.height=h;c.getContext('2d')?.clearRect(0,0,w,h);const saved=overlays.current[pageNo];if(saved){const img=new Image();img.onload=()=>c.getContext('2d')?.drawImage(img,0,0,w,h);img.src=saved}setDimensions({width:w,height:h})}
 async function renderPage(pageNo:number){if(!pdfRef.current)return;const p=await pdfRef.current.getPage(pageNo);const raw=p.getViewport({scale:1});const scale=Math.min(1.5,900/raw.width);const vp=p.getViewport({scale});const c=baseRef.current;if(!c)return;c.width=Math.ceil(vp.width);c.height=Math.ceil(vp.height);await p.render({canvasContext:c.getContext('2d')!,viewport:vp}).promise;setupOverlay(c.width,c.height,pageNo)}
 function changePage(next:number){const c=overlayRef.current;if(c)overlays.current[page]=c.toDataURL('image/png');const target=Math.max(1,Math.min(pages,next));setPage(target);if(isPdf)void renderPage(target)}
 function point(e:PointerEvent<HTMLCanvasElement>){const r=e.currentTarget.getBoundingClientRect();return{x:(e.clientX-r.left)*e.currentTarget.width/r.width,y:(e.clientY-r.top)*e.currentTarget.height/r.height}}
 function pointerDown(e:PointerEvent<HTMLCanvasElement>){const c=overlayRef.current;if(!c)return;const p=point(e),ctx=c.getContext('2d')!;if(tool==='text'||tool==='comment'){const text=window.prompt(tool==='text'?'Text to place on the report:':'Comment for this location:');if(!text?.trim())return;ctx.save();ctx.fillStyle=tool==='comment'?'#a32626':'#153c72';ctx.font='bold 16px Arial';ctx.fillText(tool==='comment'?'● '+text.trim():text.trim(),p.x,p.y);ctx.restore();if(tool==='comment')setComments(v=>[...v,{page,x:p.x,y:p.y,text:text.trim()}]);overlays.current[page]=c.toDataURL('image/png');return}
 drawing.current=true;last.current=p;e.currentTarget.setPointerCapture(e.pointerId)}
 function pointerMove(e:PointerEvent<HTMLCanvasElement>){if(!drawing.current||!last.current)return;const c=overlayRef.current;if(!c)return;const p=point(e),ctx=c.getContext('2d')!;ctx.save();ctx.beginPath();ctx.moveTo(last.current.x,last.current.y);ctx.lineTo(p.x,p.y);ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=tool==='highlight'?20:3;ctx.strokeStyle=tool==='highlight'?'#ffe45c':'#e12d39';ctx.globalAlpha=tool==='highlight'?.34:1;ctx.stroke();ctx.restore();last.current=p}
 function pointerUp(){drawing.current=false;last.current=null;const c=overlayRef.current;if(c)overlays.current[page]=c.toDataURL('image/png')}
 async function save(){setBusy(true);setError('');try{const c=overlayRef.current;if(c)overlays.current[page]=c.toDataURL('image/png');let blob:Blob
  if(isPdf){const original=await fetch(API+'/api/v1/results/'+resultId+'/documents/'+document.id,{headers:{Authorization:'Bearer '+localStorage.getItem('cbc_token')}}).then(r=>r.arrayBuffer());const pdf=await PDFDocument.load(original);for(let i=0;i<pdf.getPageCount();i++){const data=overlays.current[i+1];if(!data)continue;const png=await pdf.embedPng(data);const pg=pdf.getPage(i);pg.drawImage(png,{x:0,y:0,width:pg.getWidth(),height:pg.getHeight()})}blob=new Blob([await pdf.save()],{type:'application/pdf'})}
  else{const base=baseRef.current!,out=globalThis.document.createElement('canvas');out.width=base.width;out.height=base.height;const ctx=out.getContext('2d')!;ctx.drawImage(base,0,0);if(overlays.current[1]){const mark=new Image();await new Promise<void>((resolve,reject)=>{mark.onload=()=>resolve();mark.onerror=()=>reject(new Error('Unable to render annotations'));mark.src=overlays.current[1]});ctx.drawImage(mark,0,0)}blob=await new Promise<Blob>((resolve,reject)=>out.toBlob(b=>b?resolve(b):reject(new Error('Could not create annotated image')),'image/png'))}
  await onSave(blob,{toolset:['highlight','pen','text','comment'],comments,pages:Object.keys(overlays.current).map(Number),saved_at:new Date().toISOString()})
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <div className="annotator-overlay"><section className="annotator"><header className="annotator-head"><div><strong>Annotate: {document.filename}</strong><div className="annotator-help">Annotations are saved as a separate copy. Existing report text and CBC values are not edited.</div></div><button className="secondary" onClick={onClose}>Close</button></header><nav className="annotator-toolbar">{(['highlight','pen','text','comment'] as Tool[]).map(t=><button key={t} className={tool===t?'active':''} onClick={()=>setTool(t)}>{t==='pen'?'Draw':t[0].toUpperCase()+t.slice(1)}</button>)}{isPdf&&<><button className="secondary" disabled={page<=1} onClick={()=>changePage(page-1)}>Previous page</button><span className="annotator-help">Page {page} of {pages}</span><button className="secondary" disabled={page>=pages} onClick={()=>changePage(page+1)}>Next page</button></>}</nav><main className="annotator-stage"><div className="annotator-canvas-wrap" style={{width:dimensions.width||'auto'}}><canvas ref={baseRef}/><canvas ref={overlayRef} className="annotation-layer" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp}/></div></main><footer className="annotator-foot"><span className="annotator-help">Tool: {tool}. {tool==='highlight'?'Drag over a value or area to highlight.':tool==='pen'?'Drag to draw.':tool==='text'?'Click where the text should appear.':'Click where the comment marker should appear.'}</span><button disabled={busy||!dimensions.width} onClick={save}>{busy?'Saving…':'Save annotated copy'}</button></footer>{error&&<div className="alert error">{error}</div>}</section></div>
}

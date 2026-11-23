import { FormEvent, useEffect, useState } from 'react'

type Profile = {
  clinic_name:string; address:string; phone:string; email:string; theme_color:string;
  header_text:string; footer_text:string; has_logo:boolean; logo_display_mode:'header'|'watermark'|'background'|'both'; logo_opacity:number
}
type Props = { api:string; token:string }
const defaults:Profile = {
  clinic_name:'Clinic', address:'', phone:'0775-872-454, 0751-319-201', email:'',
  theme_color:'#0879D9', header_text:'', footer_text:'Powered by ClinicHIS', has_logo:false, logo_display_mode:'header', logo_opacity:0.10
}
export default function ClinicBranding({api,token}:Props){
 const [profile,setProfile]=useState<Profile>(defaults)
 const [logo,setLogo]=useState<File|null>(null)
 const [logoUrl,setLogoUrl]=useState('')
 const [selectedLogoUrl,setSelectedLogoUrl]=useState('')
 const [busy,setBusy]=useState(false)
 const [message,setMessage]=useState('')
 const [error,setError]=useState('')
 const headers={Authorization:'Bearer '+token}
 async function load(){
  try{
   const response=await fetch(api+'/api/v1/clinic-profile',{headers})
   if(!response.ok)throw new Error('Unable to load clinic branding')
   const data=await response.json();setProfile({...defaults,...data})
   if(data.has_logo){
    const image=await fetch(api+'/api/v1/clinic-profile/logo',{headers})
    if(image.ok){const blob=await image.blob();setLogoUrl(old=>{if(old)URL.revokeObjectURL(old);return URL.createObjectURL(blob)})}
   }else setLogoUrl('')
  }catch(e){setError((e as Error).message)}
 }
 useEffect(()=>{load()},[token])
 useEffect(()=>{if(!logo){setSelectedLogoUrl('');return}const url=URL.createObjectURL(logo);setSelectedLogoUrl(url);return()=>URL.revokeObjectURL(url)},[logo])
 async function save(e:FormEvent){
  e.preventDefault();setBusy(true);setError('');setMessage('')
  try{
   const response=await fetch(api+'/api/v1/clinic-profile',{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(profile)})
   const data=await response.json();if(!response.ok)throw new Error(data.detail||'Unable to save clinic settings')
   if(logo){
    const form=new FormData();form.append('file',logo)
    const upload=await fetch(api+'/api/v1/clinic-profile/logo',{method:'POST',headers,body:form})
    const result=await upload.json();if(!upload.ok)throw new Error(result.detail||'Clinic settings saved, but logo upload failed')
    setLogo(null)
   }
   setProfile({...defaults,...data,has_logo:data.has_logo||Boolean(logoUrl)||profile.has_logo})
   setMessage('Clinic document branding saved. It will be applied to newly generated final CBC reports.')
   await load()
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 function field(name:Exclude<keyof Profile,'has_logo'>,label:string,wide=false){
  return <label className={wide?'branding-wide':''}>{label}
   {name==='address'||name==='header_text'||name==='footer_text'
    ?<textarea rows={name==='address'?3:2} value={String(profile[name]||'')} onChange={e=>setProfile({...profile,[name]:e.target.value})}/>
    :<input value={String(profile[name]||'')} type={name==='theme_color'?'color':'text'} onChange={e=>setProfile({...profile,[name]:e.target.value})}/>}
  </label>
 }
 return <section className="panel clinic-branding">
  <div className="panel-head"><div><h2>Clinic document branding</h2><p className="muted">Configure this clinic's identity once. Saved settings are reused on every newly generated final CBC report.</p></div><span className="branding-swatch" style={{background:profile.theme_color}}/></div>
  {error&&<div className="alert error">{error}</div>}{message&&<div className="alert success">{message}</div>}
  <form className="form branding-form" onSubmit={save}>
   {field('clinic_name','Clinic name')}
   {field('theme_color','Theme colour (hex, e.g. #0879D9)')}
   {field('address','Clinic address',true)}
   {field('phone','Contact numbers')}
   {field('email','Email address')}
   {field('header_text','Additional header text',true)}
   {field('footer_text','Footer text',true)}
   <label className="branding-wide">Logo placement on final PDF
    <select value={profile.logo_display_mode} onChange={e=>setProfile({...profile,logo_display_mode:e.target.value as Profile['logo_display_mode']})}>
     <option value="header">Header only</option><option value="watermark">Faint centered watermark</option><option value="background">Full-page background image</option><option value="both">Header and watermark</option>
    </select>
   </label>
   {(profile.logo_display_mode==='watermark'||profile.logo_display_mode==='background'||profile.logo_display_mode==='both')&&<label className="branding-wide">Watermark / background opacity ({Math.round(profile.logo_opacity*100)}%)
    <input type="range" min="0.03" max="0.30" step="0.01" value={profile.logo_opacity} onChange={e=>setProfile({...profile,logo_opacity:Number(e.target.value)})}/>
    <small className="muted">Keep the logo faint so CBC values and patient details remain easy to read.</small>
   </label>}
   <label className="branding-wide">Clinic logo (PNG or JPG, maximum 2 MB)
    <input type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" onChange={e=>setLogo(e.target.files?.[0]||null)}/>
   </label>
   {(logoUrl||logo)&&<div className="branding-logo-preview branding-wide"><img src={logo?selectedLogoUrl:logoUrl} alt="Clinic logo preview"/><span>{logo?.name||'Current saved logo'}</span></div>}
   <div className="branding-wide branding-preview" style={{borderTopColor:profile.theme_color}}>
    <strong style={{color:profile.theme_color}}>{profile.clinic_name||'Clinic name'}</strong>
    <span>{profile.address||'Clinic address appears in the document header'}</span>
    <small>{profile.footer_text||'Powered by ClinicHIS'} · {profile.phone||'0775-872-454, 0751-319-201'}</small>
   </div>
   <div className="branding-wide"><button disabled={busy}>{busy?'Saving…':'Save clinic branding'}</button></div>
  </form>
  <p className="muted">The clinic logo can appear in the header, as a faint centered watermark, as a full-page background image, or in both header and watermark positions. Opacity is saved with the clinic profile and reused on newly generated final PDFs. Keep watermark/background opacity low to preserve report readability. The standard footer always includes “Powered by ClinicHIS” and the clinic contact numbers. Existing uploaded source documents are never changed.</p>
 </section>
}

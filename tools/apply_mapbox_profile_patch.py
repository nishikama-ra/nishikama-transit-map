from pathlib import Path
import re

INDEX = Path('index.html')
text = INDEX.read_text(encoding='utf-8')

if 'MAPBOX_ROUTE_PROFILE_PATCH_APPLIED' in text:
    print('Mapbox route profile patch is already applied.')
else:
    css = """
  /* Mapbox route profile controls */
  button:disabled{opacity:.55;cursor:not-allowed;}
  #mapboxStatus{font-size:10.5px;color:#777;line-height:1.5;margin-top:-2px;}
  .routeBtn.active{background:#d81b60;color:#fff;border-color:#d81b60;}
"""
    if '#mapboxStatus' not in text:
        text = text.replace('</style>', css + '</style>', 1)

    old_html = """    <div class="btnrow">
      <button id="modeElev" class="active">クリックで標高</button>
      <button id="modeProfile">断面図モード</button>
      <button id="btnClear">クリア</button>
    </div>
    <div id="clickInfo">地図をクリックすると標高を表示します。</div>"""
    new_html = """    <div class="btnrow">
      <button id="modeElev" class="active">クリックで標高</button>
      <button id="modeProfile">断面図モード</button>
      <button id="btnClear">クリア</button>
    </div>
    <div class="btnrow" id="routeModeRow">
      <button class="routeBtn active" id="routeStraight">直線</button>
      <button class="routeBtn" id="routeWalk">徒歩</button>
      <button class="routeBtn" id="routeDrive">車</button>
    </div>
    <div class="sub" id="mapboxStatus">断面図モードで2点以上をクリックします。徒歩・車はMapbox public token設定後に利用できます。</div>
    <div id="clickInfo">地図をクリックすると標高を表示します。</div>"""
    if old_html in text and 'id="routeModeRow"' not in text:
        text = text.replace(old_html, new_html, 1)
    elif 'id="routeModeRow"' not in text:
        raise SystemExit('Could not find elevation tool button block to patch.')

    config_marker = "const SHEET_CSV_URL='';\n"
    config_insert = """const SHEET_CSV_URL='';

/* ================= Mapbox Directions設定 =================
   MAPBOX_ROUTE_PROFILE_PATCH_APPLIED
   Mapboxのpk...で始まるpublic tokenを入れる。secret tokenは入れない。
   公開時は、このアプリ専用tokenにURL制限をかける。
   想定URL: https://nishikama-ra.github.io/nishikama-transit-map/
*/
const MAPBOX_TOKEN='';
const PROFILE_ROUTE_MAX_WAYPOINTS=20;
const PROFILE_ROUTE_MAX_DIRECT_DISTANCE_M=20000;
const PROFILE_ROUTE_MAX_POINTS=900;
"""
    if 'const MAPBOX_TOKEN=' not in text:
        text = text.replace(config_marker, config_insert, 1)

    new_profile_block = r'''/* ================= クリック標高 / 断面図 ================= */
let mode='elev';
let profileRouteMode='straight';
let routeBusy=false;
let routeRunId=0;
const clickMarkers=L.layerGroup().addTo(map);
let profilePts=[],profileLine=null;
const ROUTE_LABEL={straight:'直線',walk:'徒歩',drive:'車'};
const ROUTE_PROFILE={walk:'walking',drive:'driving'};
const ROUTE_BUTTONS={straight:'routeStraight',walk:'routeWalk',drive:'routeDrive'};

document.getElementById('modeElev').onclick=()=>setMode('elev');
document.getElementById('modeProfile').onclick=()=>setMode('profile');
document.getElementById('btnClear').onclick=clearAll;
document.getElementById('routeStraight').onclick=()=>setRouteMode('straight');
document.getElementById('routeWalk').onclick=()=>setRouteMode('walk');
document.getElementById('routeDrive').onclick=()=>setRouteMode('drive');

function updateMapboxStatus(msg,ok){
  const el=document.getElementById('mapboxStatus');
  if(!el)return;
  el.textContent=msg;
  el.style.color=ok===true?'#0a7':(ok===false?'#c60':'#777');
}
function profileHelpText(){
  if(profileRouteMode==='straight')return '直線モード：地図を順にクリックすると、直線経路の断面図を作成します。';
  if(!MAPBOX_TOKEN)return `${ROUTE_LABEL[profileRouteMode]}モード：Mapbox public tokenを設定すると利用できます。`;
  return `${ROUTE_LABEL[profileRouteMode]}モード：地図を順にクリックすると、Mapboxの経路に沿って断面図を作成します。`;
}
function setRouteBusy(b){
  routeBusy=b;
  Object.values(ROUTE_BUTTONS).forEach(id=>{const el=document.getElementById(id);if(el)el.disabled=b;});
  const modeBtn=document.getElementById('modeProfile');
  if(modeBtn)modeBtn.disabled=b;
}
function setMode(m){
  mode=m;
  document.getElementById('modeElev').classList.toggle('active',m==='elev');
  document.getElementById('modeProfile').classList.toggle('active',m==='profile');
  document.getElementById('clickInfo').textContent=m==='elev'
    ?'地図をクリックすると標高を表示します。'
    :profileHelpText();
}
function setRouteMode(m){
  if(routeBusy)return;
  profileRouteMode=m;
  Object.entries(ROUTE_BUTTONS).forEach(([key,id])=>{
    const el=document.getElementById(id);
    if(el)el.classList.toggle('active',key===m);
  });
  updateMapboxStatus(
    MAPBOX_TOKEN
      ?`${ROUTE_LABEL[m]}モードを選択中。徒歩・車はMapbox Directions APIを使用します。`
      :'徒歩・車ルートは MAPBOX_TOKEN 設定後に利用できます。',
    !!MAPBOX_TOKEN || m==='straight'
  );
  if(mode==='profile')document.getElementById('clickInfo').textContent=profileHelpText();
  if(profilePts.length>1)updateProfileRoute();
}
function clearAll(){
  routeRunId++;
  setRouteBusy(false);
  clickMarkers.clearLayers();profilePts=[];
  if(profileLine){map.removeLayer(profileLine);profileLine=null;}
  document.getElementById('clickInfo').textContent='クリアしました。';
  const c=document.getElementById('profileCanvas');
  c.getContext('2d').clearRect(0,0,c.width,c.height);
  document.getElementById('profileStats').textContent='—';
}
map.on('click',async e=>{
  if(routeBusy){
    document.getElementById('clickInfo').textContent='ルート取得中です。完了後にクリックしてください。';
    return;
  }
  if(mode==='elev'){
    const h=await elevAt(e.latlng.lat,e.latlng.lng);
    L.popup().setLatLng(e.latlng).setContent(`<div class="popup-el"><b>${h===null?'—':h.toFixed(1)+' m'}</b><br><span style="color:#666;font-size:11px;">${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}</span></div>`).openOn(map);
    document.getElementById('clickInfo').textContent=h===null?'標高データなし（海域など）':`標高 約 ${h.toFixed(1)} m`;
  }else{
    profilePts.push(e.latlng);
    clickMarkers.addLayer(L.circleMarker(e.latlng,{radius:4,color:'#d81b60',fillColor:'#fff',fillOpacity:1,weight:2}));
    if(profilePts.length>1){
      await updateProfileRoute();
    }else{
      document.getElementById('clickInfo').textContent='続けて次の地点をクリックしてください。';
    }
  }
});
function hav(a,b){
  const Rr=6371000,dLa=(b.lat-a.lat)*Math.PI/180,dLo=(b.lng-a.lng)*Math.PI/180;
  const la1=a.lat*Math.PI/180,la2=b.lat*Math.PI/180;
  const x=Math.sin(dLa/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dLo/2)**2;
  return 2*Rr*Math.asin(Math.sqrt(x));
}
function pathDistance(pts){
  let total=0;
  for(let i=0;i<pts.length-1;i++)total+=hav(pts[i],pts[i+1]);
  return total;
}
function thinRoutePoints(pts,maxPts){
  if(pts.length<=maxPts)return pts;
  const out=[pts[0]];
  const step=Math.ceil((pts.length-2)/(maxPts-2));
  for(let i=1;i<pts.length-1;i+=step)out.push(pts[i]);
  out.push(pts[pts.length-1]);
  return out;
}
async function fetchMapboxRoute(pts,routeMode){
  const profile=ROUTE_PROFILE[routeMode];
  const coords=pts.map(p=>`${p.lng.toFixed(6)},${p.lat.toFixed(6)}`).join(';');
  const params=new URLSearchParams({
    access_token:MAPBOX_TOKEN,
    geometries:'geojson',
    overview:'full',
    steps:'false',
    alternatives:'false'
  });
  const url=`https://api.mapbox.com/directions/v5/mapbox/${profile}/${coords}?${params.toString()}`;
  const res=await fetch(url,{cache:'no-store'});
  let data=null;
  try{data=await res.json();}catch(e){data=null;}
  if(!res.ok)throw new Error((data&&data.message)||`Mapbox API HTTP ${res.status}`);
  if(!data||data.code!=='Ok'||!data.routes||!data.routes[0])throw new Error((data&&data.message)||'Mapboxでルートを取得できませんでした。');
  const route=data.routes[0];
  const coordsOut=route.geometry&&route.geometry.coordinates;
  if(!Array.isArray(coordsOut)||coordsOut.length<2)throw new Error('Mapboxのルート形状が取得できませんでした。');
  return {
    points:coordsOut.map(c=>L.latLng(c[1],c[0])),
    distance:route.distance,
    duration:route.duration
  };
}
async function updateProfileRoute(){
  const info=document.getElementById('clickInfo');
  if(profileLine){map.removeLayer(profileLine);profileLine=null;}
  if(profilePts.length<2){info.textContent='続けて次の地点をクリックしてください。';return;}
  if(profileRouteMode==='straight'){
    profileLine=L.polyline(profilePts,{color:'#d81b60',weight:3,dashArray:'4 5'}).addTo(map);
    await drawProfile(profilePts,ROUTE_LABEL.straight);
    return;
  }
  if(!MAPBOX_TOKEN){
    info.textContent='Mapbox public token が未設定です。index.html の MAPBOX_TOKEN に、このアプリ専用の public token を入れてください。';
    return;
  }
  if(profilePts.length>PROFILE_ROUTE_MAX_WAYPOINTS){
    info.textContent=`地点数が多すぎます。${PROFILE_ROUTE_MAX_WAYPOINTS}点以内にしてください。`;
    return;
  }
  const directDistance=pathDistance(profilePts);
  if(directDistance>PROFILE_ROUTE_MAX_DIRECT_DISTANCE_M){
    info.textContent=`直線距離が長すぎます。約${(PROFILE_ROUTE_MAX_DIRECT_DISTANCE_M/1000).toFixed(0)}km以内で指定してください。`;
    return;
  }
  const runId=++routeRunId;
  try{
    setRouteBusy(true);
    info.textContent=`${ROUTE_LABEL[profileRouteMode]}ルートを取得中…`;
    const route=await fetchMapboxRoute(profilePts,profileRouteMode);
    if(runId!==routeRunId)return;
    const routePts=thinRoutePoints(route.points,PROFILE_ROUTE_MAX_POINTS);
    profileLine=L.polyline(routePts,{color:'#d81b60',weight:4,opacity:0.9}).addTo(map);
    await drawProfile(routePts,ROUTE_LABEL[profileRouteMode]);
  }catch(e){
    if(runId===routeRunId){
      info.textContent=`${ROUTE_LABEL[profileRouteMode]}ルートを取得できませんでした：${e.message}`;
    }
  }finally{
    if(runId===routeRunId)setRouteBusy(false);
  }
}
async function drawProfile(linePts=profilePts,label='直線'){
  const info=document.getElementById('clickInfo');
  if(!linePts||linePts.length<2){info.textContent='断面図には2点以上が必要です。';return;}
  info.textContent='断面図を計算中…';
  const segs=[];let total=0;
  for(let i=0;i<linePts.length-1;i++){const d=hav(linePts[i],linePts[i+1]);segs.push(d);total+=d;}
  if(!isFinite(total)||total<=0){info.textContent='距離を計算できませんでした。';return;}
  const N=Math.min(240,Math.max(60,Math.round(total/12)));
  const samples=[];
  for(let k=0;k<=N;k++){
    let target=total*k/N,acc=0,i=0;
    while(i<segs.length-1&&acc+segs[i]<target){acc+=segs[i];i++;}
    const t=segs[i]===0?0:(target-acc)/segs[i];
    const a=linePts[i],b=linePts[i+1];
    samples.push({lat:a.lat+(b.lat-a.lat)*t,lng:a.lng+(b.lng-a.lng)*t,d:target});
  }
  const els=await Promise.all(samples.map(s=>elevAt(s.lat,s.lng)));
  const pts=samples.map((s,i)=>({d:s.d,h:els[i]})).filter(p=>p.h!==null);
  if(pts.length<2){info.textContent='標高データが取得できませんでした。';return;}
  let up=0,down=0,maxG=0;
  for(let i=1;i<pts.length;i++){
    const dh=pts[i].h-pts[i-1].h,dd=pts[i].d-pts[i-1].d;
    if(dh>0)up+=dh;else down-=dh;
    if(dd>3)maxG=Math.max(maxG,Math.abs(dh/dd*100));
  }
  const hs=pts.map(p=>p.h),hMin=Math.min(...hs),hMax=Math.max(...hs);
  const c=document.getElementById('profileCanvas'),ctx=c.getContext('2d');
  const W=c.width,H=c.height,L0=52,R0=14,T0=14,B0=34;
  ctx.clearRect(0,0,W,H);
  const y0=Math.floor(Math.min(0,hMin)/10)*10,y1=Math.ceil((hMax+3)/10)*10||10;
  const xw=W-L0-R0,yh=H-T0-B0;
  const X=d=>L0+d/total*xw,Y=h=>T0+(1-(h-y0)/(y1-y0))*yh;
  ctx.strokeStyle='#e8e8e8';ctx.fillStyle='#888';ctx.font='11px sans-serif';ctx.textAlign='right';
  const step=(y1-y0)<=40?10:((y1-y0)<=100?20:25);
  for(let h=y0;h<=y1;h+=step){ctx.beginPath();ctx.moveTo(L0,Y(h));ctx.lineTo(W-R0,Y(h));ctx.stroke();ctx.fillText(h+'m',L0-5,Y(h)+4);}
  ctx.textAlign='center';
  const kmStep=total>4000?1000:(total>1500?500:250);
  for(let d=0;d<=total;d+=kmStep){ctx.beginPath();ctx.moveTo(X(d),T0);ctx.lineTo(X(d),H-B0);ctx.stroke();ctx.fillText((d>=1000?(d/1000).toFixed(1)+'km':Math.round(d)+'m'),X(d),H-B0+16);}
  ctx.beginPath();ctx.moveTo(X(pts[0].d),Y(pts[0].h));
  pts.forEach(p=>ctx.lineTo(X(p.d),Y(p.h)));
  ctx.lineTo(X(pts[pts.length-1].d),Y(y0));ctx.lineTo(X(pts[0].d),Y(y0));ctx.closePath();
  const grad=ctx.createLinearGradient(0,T0,0,H-B0);
  grad.addColorStop(0,'rgba(244,109,67,0.55)');grad.addColorStop(1,'rgba(50,136,189,0.35)');
  ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();ctx.moveTo(X(pts[0].d),Y(pts[0].h));
  pts.forEach(p=>ctx.lineTo(X(p.d),Y(p.h)));
  ctx.strokeStyle='#c0392b';ctx.lineWidth=2;ctx.stroke();ctx.lineWidth=1;
  document.getElementById('profileStats').innerHTML=
    `${label}距離 <b>${(total/1000).toFixed(2)} km</b> ／ 最低 <b>${hMin.toFixed(1)}m</b> → 最高 <b>${hMax.toFixed(1)}m</b><br>`+
    `累積上り <b>+${up.toFixed(0)}m</b> ／ 累積下り <b>−${down.toFixed(0)}m</b> ／ 最大勾配 約<b>${maxG.toFixed(0)}%</b>`;
  info.textContent=`${label}断面図を更新しました。続けてクリックで延長できます。`;
}
updateMapboxStatus(
  MAPBOX_TOKEN
    ?'Mapbox public token設定済み。徒歩・車ルートを利用できます。'
    :'徒歩・車ルートは MAPBOX_TOKEN 設定後に利用できます。',
  !!MAPBOX_TOKEN
);
'''
    pattern = r"/\* ================= クリック標高 / 断面図 ================= \*/.*?</script>"
    text, count = re.subn(pattern, new_profile_block + "\n</script>", text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit('Could not replace elevation/profile script block.')

    INDEX.write_text(text, encoding='utf-8')
    print('Applied Mapbox route profile patch to index.html.')

# Delete the one-time patch machinery after it has applied.
Path('tools/apply_mapbox_profile_patch.py').unlink(missing_ok=True)
Path('.github/workflows/apply-mapbox-profile-patch.yml').unlink(missing_ok=True)

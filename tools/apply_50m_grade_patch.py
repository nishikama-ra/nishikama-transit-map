from pathlib import Path

INDEX = Path('index.html')
text = INDEX.read_text(encoding='utf-8')

if 'PROFILE_GRADE_WINDOW_M' not in text:
    text = text.replace(
        "const PROFILE_ROUTE_MAX_POINTS=900;",
        "const PROFILE_ROUTE_MAX_POINTS=900;\nconst PROFILE_GRADE_WINDOW_M=50;\nconst PROFILE_GRADE_STEP_M=10;",
        1,
    )

helper = """function interpProfileHeight(pts,d){
  if(!pts||!pts.length)return null;
  if(d<=pts[0].d)return pts[0].h;
  for(let i=1;i<pts.length;i++){
    if(d<=pts[i].d){
      const a=pts[i-1],b=pts[i],dd=b.d-a.d;
      if(dd<=0)return b.h;
      const t=(d-a.d)/dd;
      return a.h+(b.h-a.h)*t;
    }
  }
  return pts[pts.length-1].h;
}
function maxAverageGrade(pts,windowM){
  if(!pts||pts.length<2)return null;
  const start=pts[0].d,end=pts[pts.length-1].d-windowM;
  if(end<start)return null;
  let maxG=0;
  const check=d=>{
    const h0=interpProfileHeight(pts,d),h1=interpProfileHeight(pts,d+windowM);
    if(h0===null||h1===null)return;
    const g=Math.abs((h1-h0)/windowM*100);
    if(isFinite(g))maxG=Math.max(maxG,g);
  };
  for(let d=start;d<=end+1e-6;d+=PROFILE_GRADE_STEP_M)check(d);
  check(end);
  return maxG;
}
"""
if 'function interpProfileHeight' not in text:
    text = text.replace("async function drawProfile(linePts=profilePts,label='直線'){", helper + "async function drawProfile(linePts=profilePts,label='直線'){", 1)

old_loop = """  let up=0,down=0,maxG=0;
  for(let i=1;i<pts.length;i++){
    const dh=pts[i].h-pts[i-1].h,dd=pts[i].d-pts[i-1].d;
    if(dh>0)up+=dh;else down-=dh;
    if(dd>3)maxG=Math.max(maxG,Math.abs(dh/dd*100));
  }
"""
new_loop = """  let up=0,down=0;
  for(let i=1;i<pts.length;i++){
    const dh=pts[i].h-pts[i-1].h;
    if(dh>0)up+=dh;else down-=dh;
  }
  const maxG50=maxAverageGrade(pts,PROFILE_GRADE_WINDOW_M);
"""
if old_loop in text:
    text = text.replace(old_loop, new_loop, 1)
else:
    print('Warning: old max gradient loop was not found or already replaced.')

old_stats = """  document.getElementById('profileStats').innerHTML=
    `${label}距離 <b>${(total/1000).toFixed(2)} km</b> ／ 最低 <b>${hMin.toFixed(1)}m</b> → 最高 <b>${hMax.toFixed(1)}m</b><br>`+
    `累積上り <b>+${up.toFixed(0)}m</b> ／ 累積下り <b>−${down.toFixed(0)}m</b> ／ 最大勾配 約<b>${maxG.toFixed(0)}%</b>`;
"""
new_stats = """  const maxG50Label=maxG50===null?'—':`約${maxG50.toFixed(0)}%`;
  document.getElementById('profileStats').innerHTML=
    `${label}距離 <b>${(total/1000).toFixed(2)} km</b> ／ 最低 <b>${hMin.toFixed(1)}m</b> → 最高 <b>${hMax.toFixed(1)}m</b><br>`+
    `累積上り <b>+${up.toFixed(0)}m</b> ／ 累積下り <b>−${down.toFixed(0)}m</b><br>`+
    `50m平均最大勾配 <b>${maxG50Label}</b>`;
"""
if old_stats in text:
    text = text.replace(old_stats, new_stats, 1)
else:
    print('Warning: old stats block was not found or already replaced.')

INDEX.write_text(text, encoding='utf-8')
Path('tools/apply_50m_grade_patch.py').unlink(missing_ok=True)
Path('.github/workflows/apply-50m-grade-patch.yml').unlink(missing_ok=True)
print('Applied 50m average grade patch.')

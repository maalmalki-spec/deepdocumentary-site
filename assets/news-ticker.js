(function(){
'use strict';
if(document.getElementById('dd-ticker'))return;
const box=document.createElement('div');box.id='dd-ticker';box.setAttribute('aria-label','Latest headlines');
const label=document.createElement('b'),viewport=document.createElement('div'),track=document.createElement('div');
viewport.className='dd-ticker-viewport';track.className='dd-ticker-track';viewport.append(track);box.append(label,viewport);
const css=document.createElement('style');
css.textContent=`#dd-ticker{display:flex;align-items:stretch;background:#111;color:#f7f7f7;border-block:1px solid #b9944b;overflow:hidden;font:600 16px/1.5 Arial,sans-serif;height:52px;max-width:100%}#dd-ticker>b{background:#a32329;color:white;padding:13px 18px;flex-shrink:0;white-space:nowrap;z-index:1}#dd-ticker .dd-ticker-viewport{overflow:hidden;flex:1;min-width:0;display:flex;align-items:center;direction:ltr}#dd-ticker .dd-ticker-track{direction:ltr;display:flex;align-items:center;width:max-content;min-width:max-content;white-space:nowrap;will-change:transform;animation:dd-ticker-scroll var(--dd-duration,75s) linear infinite}#dd-ticker .dd-ticker-group{direction:ltr;display:flex;align-items:center;flex:none;white-space:nowrap}#dd-ticker .dd-ticker-item{display:inline-flex;align-items:center;gap:12px;padding:0 30px;flex:none}#dd-ticker .dd-ticker-item::before{content:'◆';font-size:9px;color:#d8b45c}#dd-ticker .dd-ticker-category{font-size:12px;font-weight:800;padding:4px 9px;border-radius:5px;background:#242424;border:1px solid currentColor;white-space:nowrap}#dd-ticker .dd-ticker-source{color:#d8b45c;font-size:12px}#dd-ticker:hover .dd-ticker-track{animation-play-state:paused}@keyframes dd-ticker-scroll{from{transform:translateX(0)}to{transform:translateX(calc(-1 * var(--dd-distance,500px)))}}#dd-ticker .dd-ticker-category[data-cat='politics'],#dd-ticker .dd-ticker-category[data-cat='world']{color:#7db7ef}#dd-ticker .dd-ticker-category[data-cat='economy']{color:#70d19a}#dd-ticker .dd-ticker-category[data-cat='sports']{color:#f3aa6c}#dd-ticker .dd-ticker-category[data-cat='science']{color:#c49cf2}#dd-ticker .dd-ticker-category[data-cat='saudi'],#dd-ticker .dd-ticker-category[data-cat='gulf']{color:#81c9a5}#dd-ticker .dd-ticker-category[data-cat='general']{color:#e4c16f}@media(max-width:600px){#dd-ticker{font-size:13px;height:40px}#dd-ticker>b{padding:10px}#dd-ticker .dd-ticker-category{font-size:10px;padding:2px 6px}#dd-ticker .dd-ticker-item{padding:0 18px}}@media(prefers-reduced-motion:reduce){#dd-ticker .dd-ticker-track{animation:none;will-change:auto}}`;
document.head.append(css);
const header=document.querySelector('header');if(header)header.after(box);else document.body.prepend(box);
let news=[],lastLang='',resizeTimer;
function render(){
 const en=document.documentElement.lang==='en'||localStorage.getItem('dd-language')==='en';
 lastLang=en?'en':'ar';label.textContent=en?'LATEST NEWS':'آخر الأخبار';track.replaceChildren();
 const rows=news.filter(x=>x.lang===lastLang&&x.title).slice(0,25);
 if(!rows.length){track.style.animation='none';track.textContent=en?'No recent news available':'لا توجد أخبار حديثة حاليًا';return}
 const group=document.createElement('div');group.className='dd-ticker-group';
 const categories={ar:{saudi:'السعودية',gulf:'الخليج',world:'سياسة وعالم',politics:'سياسة',economy:'اقتصاد',sports:'رياضة',science:'علوم وتقنية',general:'أخبار'},en:{saudi:'SAUDI',gulf:'GULF',world:'WORLD',politics:'POLITICS',economy:'ECONOMY',sports:'SPORTS',science:'SCIENCE & TECH',general:'NEWS'}};
 rows.forEach(x=>{const item=document.createElement('span');item.className='dd-ticker-item';item.dir=en?'ltr':'rtl';const badge=document.createElement('span');badge.className='dd-ticker-category';badge.dataset.cat=x.category||'general';badge.textContent=categories[lastLang][x.category]||categories[lastLang].general;const title=document.createElement('span');title.textContent=x.title;const source=document.createElement('small');source.className='dd-ticker-source';source.textContent=x.source||'';item.append(badge,title,source);group.append(item)});
 track.append(group);
 // Fill the viewport before duplicating, so the animation never leaves empty space.
 const original=Array.from(group.children).map(n=>n.cloneNode(true));
 const minWidth=Math.max(viewport.clientWidth*1.6,900);
 while(group.scrollWidth<minWidth&&group.childElementCount<150){for(const node of original){group.append(node.cloneNode(true));if(group.scrollWidth>=minWidth)break}}
 const copy=group.cloneNode(true);copy.setAttribute('aria-hidden','true');track.append(copy);
 const width=group.scrollWidth;
 track.style.setProperty('--dd-distance',width+'px');
 track.style.setProperty('--dd-duration',Math.max(35,Math.round(width/65))+'s');
 track.style.animation='none';void track.offsetWidth;track.style.animation='';
}
async function refresh(){
 const urls=['/assets/data/news-ticker.json','https://raw.githubusercontent.com/maalmalki-spec/deepdocumentary-site/main/assets/data/news-ticker.json'];
 for(const url of urls){try{const response=await fetch(url+'?v='+Date.now(),{cache:'no-store'});if(!response.ok)continue;const data=await response.json();if(Array.isArray(data.items)&&data.items.length){news=data.items;render();return}}catch(e){}}
 render();
}
render();refresh();setInterval(refresh,300000);
new MutationObserver(()=>{const en=document.documentElement.lang==='en'||localStorage.getItem('dd-language')==='en';if(lastLang!==(en?'en':'ar'))render()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,250)});
window.addEventListener('storage',e=>{if(e.key==='dd-language')render()});
})();

(function(){
var box=document.createElement('div');box.id='dd-ticker';box.setAttribute('aria-label','Latest headlines');
var label=document.createElement('b');var windowBox=document.createElement('div');var textBox=document.createElement('div');
box.append(label,windowBox);windowBox.append(textBox);
var css=document.createElement('style');
css.textContent='#dd-ticker{display:flex;align-items:center;background:#111;color:#eee;border-bottom:1px solid #b9944b;overflow:hidden;font:600 13px Arial,sans-serif;min-height:40px}#dd-ticker>b{background:#a32329;color:white;padding:12px;flex-shrink:0;white-space:nowrap}#dd-ticker>div{overflow:hidden;flex:1}#dd-ticker>div>div{display:flex;gap:38px;width:max-content;white-space:nowrap;animation:ddticker 110s linear infinite}#dd-ticker:hover>div>div{animation-play-state:paused}#dd-ticker span{padding:10px 0}#dd-ticker small{color:#d8b45c;margin:0 10px}@keyframes ddticker{to{transform:translateX(-50%)}}@media(prefers-reduced-motion:reduce){#dd-ticker>div>div{animation:none;white-space:normal;flex-wrap:wrap}}';
document.head.append(css);
var header=document.querySelector('header');if(header)header.after(box);else document.body.prepend(box);
var news=[];
function render(){var en=document.documentElement.lang==='en';label.textContent=en?'LATEST NEWS':'آخر الأخبار';textBox.replaceChildren();var rows=news.filter(function(x){return x.lang===(en?'en':'ar')}).slice(0,20);if(!rows.length){textBox.textContent=en?'No recent news available':'لا توجد أخبار حديثة حاليًا';return}for(var n=0;n<2;n++)rows.forEach(function(x){var item=document.createElement('span');item.dir=en?'ltr':'rtl';item.textContent=x.title;var source=document.createElement('small');source.textContent=' — '+x.source;item.append(source);textBox.append(item)})}
async function refresh(){try{var response=await fetch('/assets/data/news-ticker.json?'+Date.now(),{cache:'no-store'});if(!response.ok)return;var data=await response.json();if(Array.isArray(data.items)){news=data.items;render()}}catch(e){render()}}
render();refresh();setInterval(refresh,300000);new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
})();
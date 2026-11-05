const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const pages = ['index.html','games.html','about.html','contact.html',...fs.readdirSync('articles').filter(x=>x.endsWith('.html')).map(x=>'articles/'+x)];
const output = path.resolve('audit-output');
fs.mkdirSync(output, {recursive:true});
(async()=>{
 const browser = await chromium.launch({headless:true});
 const results = [];
 for (const width of [390, 768, 820, 1024, 1440]) {
  const context = await browser.newContext({viewport:{width,height:width===768||width===820||width===1024?1024:900}, deviceScaleFactor:1});
  for (const name of pages) {
   const page = await context.newPage();
   const uri = 'http://127.0.0.1:8765/' + name;
   try {
    await page.goto(uri, {waitUntil:'load',timeout:20000});
    await page.waitForTimeout(450);
    // Force lazy-loaded images to load before evaluating image health.
    await page.evaluate(() => { for (const img of document.images) img.loading = 'eager'; });
    await page.waitForTimeout(1200);
    if(name.startsWith('articles/')) await page.waitForSelector('#dd-story-explore .dd-story-card',{timeout:6000});
    const result = await page.evaluate(() => ({
     title:document.title,
     overflow:document.documentElement.scrollWidth > window.innerWidth + 3,
     width:document.documentElement.scrollWidth,
     viewport:window.innerWidth,
     relatedCount:document.querySelectorAll('#dd-story-explore .dd-story-card').length,
     relatedUnique:new Set([...document.querySelectorAll('#dd-story-explore .dd-story-card')].map(a=>a.getAttribute('href'))).size,
     relatedSections:document.querySelectorAll('#dd-story-explore').length,
     footers:document.querySelectorAll('footer').length,
     brokenLocalImages:[...document.images].filter(i=>i.complete && i.naturalWidth===0).map(i=>i.getAttribute('src')).filter(x=>x&&!/^https?:|^\/\//.test(x))
    }));
    const file = name.replace(/[^a-z0-9]+/gi,'-') + '-' + width + '.png';
    await page.screenshot({path:path.join(output,file),fullPage:true,animations:'disabled'});
    results.push({page:name,width,...result});
   } catch(err){results.push({page:name,width,error:String(err)})}
   await page.close();
  }
  await context.close();
 }
 await browser.close();
 fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(results,null,2));
 for(const item of results) console.log(JSON.stringify(item));
 const failed=results.filter(x=>x.error||x.overflow||x.brokenLocalImages?.length||(x.page.startsWith('articles/')&&(x.relatedCount>3||x.relatedCount!==x.relatedUnique||x.relatedSections!==1||x.footers>1)));
 if(failed.length){console.error('Visual audit failed on '+failed.length+' page/view combinations');process.exitCode=1}
})().catch(err=>{console.error(err);process.exitCode=1});

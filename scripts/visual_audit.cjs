const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const pages = ['index.html', 'games.html', 'about.html', 'contact.html', 'articles/apollo-11.html', 'articles/canva-video-editor-beginners-guide.html'];
const output = path.resolve('audit-output');
fs.mkdirSync(output, {recursive:true});
(async()=>{
 const browser = await chromium.launch({headless:true});
 const results = [];
 for (const width of [390, 1440]) {
  const context = await browser.newContext({viewport:{width,height:900}, deviceScaleFactor:1});
  for (const name of pages) {
   const page = await context.newPage();
   const uri = 'file://' + path.resolve(name);
   try {
    await page.goto(uri, {waitUntil:'load',timeout:20000});
    await page.waitForTimeout(450);
    const result = await page.evaluate(() => ({
     title:document.title,
     overflow:document.documentElement.scrollWidth > window.innerWidth + 3,
     width:document.documentElement.scrollWidth,
     viewport:window.innerWidth,
     brokenLocalImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.getAttribute('src')).filter(x=>x&&!/^https?:|^\/\//.test(x))
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
 const failed=results.filter(x=>x.error||x.overflow||x.brokenLocalImages?.length);
 if(failed.length){console.error('Visual audit failed on '+failed.length+' page/view combinations');process.exitCode=1}
})().catch(err=>{console.error(err);process.exitCode=1});

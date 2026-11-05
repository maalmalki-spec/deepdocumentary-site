const { test, expect } = require('playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
test.beforeEach(async ({ page }) => {
  await page.route('https://membership.test/**', route => {
    const filename = new URL(route.request().url()).pathname.slice(1) || 'account.html';
    const file = path.resolve(root, filename);
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) return route.fulfill({status:404});
    const contentType = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.svg') ? 'image/svg+xml' : 'text/html';
    return route.fulfill({body:fs.readFileSync(file), contentType});
  });
});
test('disabled deployment is readable, responsive and makes no external requests', async ({ page }) => {
  const requests = [];
  page.on('request', req => { if (!req.url().startsWith('https://membership.test/')) requests.push(req.url()); });
  await page.goto('https://membership.test/account.html');
  await expect(page.locator('#status')).toContainText('قيد التجهيز');
  await expect(page.locator('#auth')).toBeHidden();
  await expect(page.locator('#admin')).toBeDisabled();
  for (const width of [390, 1280]) {
    await page.setViewportSize({width, height:900});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  expect(requests).toEqual([]);
});
test('secret keys cannot activate browser authentication', async ({ page }) => {
  await page.route('**/assets/member-config.js', route => route.fulfill({contentType:'text/javascript', body:`window.DD_MEMBER_CONFIG={enabled:true,supabaseUrl:'https://example.supabase.co',publishableKey:'sb_secret_do_not_use'};`}));
  await page.goto('https://membership.test/account.html');
  await expect(page.locator('#auth')).toBeHidden();
});
test('SDK failure leaves reading available and forms hidden', async ({ page }) => {
  await page.route('**/assets/member-config.js', route => route.fulfill({contentType:'text/javascript', body:`window.DD_MEMBER_CONFIG={enabled:true,supabaseUrl:'https://example.supabase.co',publishableKey:'sb_publishable_testing_only'};`}));
  await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
  await page.goto('https://membership.test/account.html');
  await expect(page.locator('#status')).toContainText('غير متاحة');
  await expect(page.locator('#auth')).toBeHidden();
  await expect(page.locator('header a[href="index.html"]').last()).toBeVisible();
});
test('member content stays text and signout clears private data', async ({ page }) => {
  await page.route('**/assets/member-config.js', route => route.fulfill({contentType:'text/javascript', body:`window.DD_MEMBER_CONFIG={enabled:true,supabaseUrl:'https://example.supabase.co',publishableKey:'sb_publishable_testing_only'};`}));
  await page.route('https://cdn.jsdelivr.net/**', route => route.fulfill({contentType:'text/javascript', body:`
    export function createClient() {
      let signedIn = true;
      const data = {
        member_profiles:{full_name:'<img src=x onerror=alert(1)>'},
        member_favorites:[{article_slug:'apollo-11'}],
        member_reading:[], member_awards:[{points:10,badge:'<script>alert(1)</script>'}]
      };
      return {
        auth:{getUser:async()=>({data:{user:signedIn?{id:'member-a',email:'member@example.com'}:null}}),onAuthStateChange:()=>{},signOut:async()=>{signedIn=false;return {data:{}};}},
        from:table=>{const query={select:()=>query,eq:()=>query,single:()=>Promise.resolve({data:data[table]}),order:()=>query,limit:()=>Promise.resolve({data:data[table]})}; return query;},
        rpc:async()=>({error:{message:'Forbidden'}})
      };
    }
  `}));
  await page.goto('https://membership.test/account.html');
  await expect(page.locator('#profile')).toBeVisible();
  await expect(page.locator('#name input')).toHaveValue('<img src=x onerror=alert(1)>');
  await expect(page.locator('#badges')).toHaveText('<script>alert(1)</script>');
  await expect(page.locator('#badges script')).toHaveCount(0);
  await expect(page.locator('#favorites a')).toHaveAttribute('href','articles/apollo-11.html');
  await page.locator('summary').click();
  await page.locator('#admin').click();
  await expect(page.locator('#admin-result')).toContainText('غير مصرح');
  await page.locator('#signout').click();
  await expect(page.locator('#profile')).toBeHidden();
  await expect(page.locator('#email')).toBeEmpty();
  await expect(page.locator('#favorites')).toBeEmpty();
  await expect(page.locator('#admin-result')).toBeEmpty();
  await expect(page.locator('#auth')).toBeVisible();
});



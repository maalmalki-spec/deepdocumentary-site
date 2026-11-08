import { createClient } from "npm:@supabase/supabase-js@2";
import { SignJWT, importPKCS8 } from "npm:jose@5";
const origins=new Set(["https://deepdocumentary.com","https://www.deepdocumentary.com"]);
function reply(body:unknown,status:number,origin:string){const headers:Record<string,string>={"Content-Type":"application/json","Cache-Control":"no-store","Vary":"Origin"};if(origins.has(origin)){headers["Access-Control-Allow-Origin"]=origin;headers["Access-Control-Allow-Headers"]="authorization,apikey,content-type";headers["Access-Control-Allow-Methods"]="POST,OPTIONS"}return new Response(JSON.stringify(body),{status,headers})}
Deno.serve(async req=>{const origin=req.headers.get("origin")??"";if(origin&&!origins.has(origin))return reply({error:"Forbidden origin"},403,origin);if(req.method==="OPTIONS")return reply({},200,origin);if(req.method!=="POST")return reply({error:"Method not allowed"},405,origin);
try{const bearer=req.headers.get("authorization")??"";if(!bearer.startsWith("Bearer "))return reply({error:"Unauthorized"},401,origin);
const url=Deno.env.get("SUPABASE_URL"),anon=Deno.env.get("SUPABASE_ANON_KEY");if(!url||!anon)throw Error("Missing Supabase configuration");
const db=createClient(url,anon,{global:{headers:{Authorization:bearer}},auth:{persistSession:false,autoRefreshToken:false}});
const {data:{user},error}=await db.auth.getUser(bearer.slice(7));if(error||!user)return reply({error:"Unauthorized"},401,origin);
const {data:admin,error:adminError}=await db.from("dashboard_admins").select("user_id").eq("user_id",user.id).maybeSingle();if(adminError||!admin)return reply({error:"Forbidden"},403,origin);
const input=await req.json().catch(()=>({}));const days=Number(input.days);if(![7,30,90].includes(days))return reply({error:"Invalid period"},400,origin);
const property=Deno.env.get("GA4_PROPERTY_ID");const credentialsRaw=Deno.env.get("GOOGLE_SERVICE_ACCOUNT_JSON");let credentials:{client_email?:string;private_key?:string}={};try{credentials=JSON.parse(credentialsRaw??"{}")}catch{console.error("Invalid service account JSON")}const email=credentials.client_email,privateKey=credentials.private_key;if(!property||!email||!privateKey)return reply({error:"Analytics service not configured"},503,origin);
const key=await importPKCS8(privateKey,"RS256");const now=Math.floor(Date.now()/1000);
const jwt=await new SignJWT({scope:"https://www.googleapis.com/auth/analytics.readonly"}).setProtectedHeader({alg:"RS256",typ:"JWT"}).setIssuer(email).setAudience("https://oauth2.googleapis.com/token").setIssuedAt(now).setExpirationTime(now+3600).sign(key);
const tokenResponse=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer",assertion:jwt})});if(!tokenResponse.ok)throw Error("GA authentication failed");const token=(await tokenResponse.json()).access_token;
const endpoint="https://analyticsdata.googleapis.com/v1beta/properties/"+encodeURIComponent(property)+":runReport";
async function query(event:string,dimension?:string,metric="eventCount"){
 const body:any={dateRanges:[{startDate:(days-1)+"daysAgo",endDate:"today"}],metrics:[{name:metric}],dimensionFilter:{filter:{fieldName:"eventName",stringFilter:{value:event,matchType:"EXACT"}}},limit:100};
 if(dimension)body.dimensions=[{name:dimension}];
 const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},body:JSON.stringify(body)});
 if(!response.ok){console.warn("Behavior report unavailable",event,dimension,response.status);return {available:false,rows:[]}}
 return {available:true,rows:(await response.json()).rows??[]};
}
const names=["article_scroll","article_read_time","site_click","site_search"];
const totals:any={};const available:any={};
for(const name of names){const result=await query(name);totals[name]=Number(result.rows[0]?.metricValues?.[0]?.value??0);available[name]=result.available}
const depth=await query("article_scroll","customEvent:scroll_percent");
const times=await query("article_read_time","customEvent:read_seconds");
const clicks=await query("site_click","customEvent:click_category");
const pages=await query("article_scroll","customEvent:content_path");
const map=(r:any)=>r.rows.map((row:any)=>({label:String(row.dimensionValues?.[0]?.value??""),count:Number(row.metricValues?.[0]?.value??0)})).filter((x:any)=>x.label&&x.label!=="(not set)").sort((a:any,b:any)=>b.count-a.count);
return reply({success:true,days,totals,available,dimensions:{scroll_percent:depth.available,read_seconds:times.available,click_category:clicks.available,content_path:pages.available},depth:map(depth),readingTime:map(times),clicks:map(clicks),articlePages:map(pages)},200,origin);
}catch(e){console.error("behavior-dashboard error",e);return reply({error:"Unable to retrieve behavior analytics"},500,origin)}});

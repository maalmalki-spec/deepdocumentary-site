import { createClient } from "npm:@supabase/supabase-js@2";
const allowed = new Set(["https://deepdocumentary.com","https://www.deepdocumentary.com"]);
function reply(body:unknown,status:number,origin:string){
 const headers:Record<string,string>={"Content-Type":"application/json","Cache-Control":"no-store","Vary":"Origin"};
 if(allowed.has(origin)){headers["Access-Control-Allow-Origin"]=origin;headers["Access-Control-Allow-Headers"]="authorization, apikey, content-type, x-client-info";headers["Access-Control-Allow-Methods"]="POST, OPTIONS";}
 return new Response(JSON.stringify(body),{status,headers});
}
Deno.serve(async req=>{
 const origin=req.headers.get("origin")??"";
 if(origin&&!allowed.has(origin))return reply({error:"Forbidden origin"},403,origin);
 if(req.method==="OPTIONS")return reply({},200,origin);
 if(req.method!=="POST")return reply({error:"Method not allowed"},405,origin);
 try{
  const token=req.headers.get("authorization")?.replace(/^Bearer /,"");
  if(!token)return reply({error:"Authentication required"},401,origin);
  const url=Deno.env.get("SUPABASE_URL"),anon=Deno.env.get("SUPABASE_ANON_KEY"),service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),apiKey=Deno.env.get("BREVO_API_KEY");
  if(!url||!anon||!service||!apiKey)return reply({error:"Service not configured"},503,origin);
  const auth=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:{user},error}=await auth.auth.getUser(token);
  if(error||!user)return reply({error:"Unauthorized"},401,origin);
  // Check administrator membership using a server-side privileged client after verifying the caller JWT.
  const privileged=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:admin,error:adminError}=await privileged.from("dashboard_admins").select("user_id").eq("user_id",user.id).maybeSingle();
  if(adminError||!admin)return reply({error:"Forbidden"},403,origin);
  const input=await req.json().catch(()=>({}));
  const page=Number(input.page??1);
  if(!Number.isInteger(page)||page<1||page>10000)return reply({error:"Invalid page"},400,origin);
  const limit=50,offset=(page-1)*limit;
  const response=await fetch("https://api.brevo.com/v3/contacts/lists/3/contacts?limit="+limit+"&offset="+offset+"&sort=desc",{headers:{"api-key":apiKey,"accept":"application/json"}});
  if(!response.ok)return reply({error:"Newsletter provider unavailable"},502,origin);
  const data=await response.json();
  const contacts=Array.isArray(data.contacts)?data.contacts:[];
  return reply({success:true,page,total:Number(data.count??contacts.length),hasMore:offset+contacts.length<Number(data.count??0),contacts:contacts.map((c:any)=>({email:String(c.email??""),createdAt:c.createdAt??null,modifiedAt:c.modifiedAt??null,subscribed:!c.emailBlacklisted}))},200,origin);
 }catch(e){console.error("newsletter-dashboard error",e instanceof Error?e.message:"unknown");return reply({error:"Unable to load newsletter subscribers"},500,origin);}
});

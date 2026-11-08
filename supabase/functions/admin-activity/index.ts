import { createClient } from "npm:@supabase/supabase-js@2";

// Best-effort error reporting. Never log user data, tokens or raw exception text.
async function recordFunctionError(code: string, message: string) {
  try {
    const url = Deno.env.get("SUPABASE_URL");
    const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !service) return;
    const db = createClient(url, service, {auth:{persistSession:false,autoRefreshToken:false}});
    const {error} = await db.from("edge_function_errors").insert({function_name:"admin-activity",error_code:code,message});
    if (error) console.warn("Error monitoring insert failed", error.code);
  } catch { console.warn("Error monitoring unavailable"); }
}
const origins = new Set(["https://deepdocumentary.com", "https://www.deepdocumentary.com"]);
function respond(data: unknown, status: number, origin: string) {
  const headers: Record<string,string> = {"Content-Type":"application/json","Cache-Control":"no-store","Vary":"Origin"};
  if(origins.has(origin)) Object.assign(headers,{"Access-Control-Allow-Origin":origin,"Access-Control-Allow-Headers":"authorization,apikey,content-type","Access-Control-Allow-Methods":"POST,OPTIONS"});
  return new Response(JSON.stringify(data),{status,headers});
}
Deno.serve(async (req) => {
  const origin=req.headers.get("origin")??"";
  if(origin && !origins.has(origin)) return respond({error:"Forbidden origin"},403,origin);
  if(req.method==="OPTIONS") return respond({},200,origin);
  if(req.method!=="POST") return respond({error:"Method not allowed"},405,origin);
  try {
    const token=(req.headers.get("authorization")??"").replace(/^Bearer /,"");
    if(!token) return respond({error:"Unauthorized"},401,origin);
    const url=Deno.env.get("SUPABASE_URL")!,anon=Deno.env.get("SUPABASE_ANON_KEY")!,service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    if(!url||!anon||!service) { await recordFunctionError("CONFIG_MISSING","Server configuration missing"); return respond({error:"Server configuration missing"},503,origin); }
    const userDb=createClient(url,anon,{global:{headers:{Authorization:"Bearer "+token}},auth:{persistSession:false,autoRefreshToken:false}});
    const {data:{user},error}=await userDb.auth.getUser(token);
    if(error||!user) return respond({error:"Unauthorized"},401,origin);
    const {data:admin,error:adminError}=await userDb.from("dashboard_admins").select("user_id").eq("user_id",user.id).maybeSingle();
    if(adminError||!admin) return respond({error:"Forbidden"},403,origin);
    const input=await req.json().catch(()=>({}));
    const action=input.action;
    if(!["record_dashboard_access","list","verify_error_logging"].includes(action)) return respond({error:"Invalid action"},400,origin);
    const db=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    if(action==="verify_error_logging"){
      // Administrator-only end-to-end write verification. No sensitive details are stored.
      const {data:probe,error:probeError}=await db.from("edge_function_errors")
        .insert({function_name:"admin-activity",error_code:"MONITORING_PROBE",message:"Administrator-initiated monitoring verification"})
        .select("id").single();
      if(probeError||!probe?.id){
        console.warn("Monitoring probe failed",probeError?.code??"NO_ID");
        return respond({success:false,monitoring:"unavailable"},503,origin);
      }
      const {error:cleanupError}=await db.from("edge_function_errors").delete().eq("id",probe.id);
      if(cleanupError){
        console.warn("Monitoring probe cleanup failed",cleanupError.code);
        return respond({success:true,monitoring:"write_ok",cleanup:"failed"},200,origin);
      }
      return respond({success:true,monitoring:"write_ok",cleanup:"ok"},200,origin);
    }
    if(action==="record_dashboard_access"){
      const {error:insertError}=await db.from("admin_activity_logs").insert({actor_user_id:user.id,event_type:"dashboard_access",description:"Administrator opened dashboard",metadata:{}});
      if(insertError) throw insertError;
    }
    const {data:events,error:listError}=await db.from("admin_activity_logs").select("id,created_at,actor_user_id,event_type,description").order("created_at",{ascending:false}).limit(50);
    if(listError) throw listError;
    return respond({success:true,events},200,origin);
  } catch(e) {console.error("admin activity error",e);await recordFunctionError("UNHANDLED_EXCEPTION","Unable to process activity log");return respond({error:"Unable to process activity log"},500,origin)}
});

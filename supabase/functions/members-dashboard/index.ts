import { createClient } from "npm:@supabase/supabase-js@2";

const ORIGINS = new Set(["https://deepdocumentary.com", "https://www.deepdocumentary.com"]);
function respond(body: unknown, status: number, origin: string) {
  const headers: Record<string,string> = {"Content-Type":"application/json","Cache-Control":"no-store","Vary":"Origin"};
  if (ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "authorization, apikey, content-type, x-client-info";
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  }
  return new Response(JSON.stringify(body), {status, headers});
}

Deno.serve(async (request) => {
  const origin = request.headers.get("origin") ?? "";
  if (origin && !ORIGINS.has(origin)) return respond({error:"Origin not allowed"},403,origin);
  if (request.method === "OPTIONS") return respond({},200,origin);
  if (request.method !== "POST") return respond({error:"Method not allowed"},405,origin);
  try {
    const authorization = request.headers.get("authorization") ?? "";
    if (!authorization.startsWith("Bearer ")) return respond({error:"Authentication required"},401,origin);
    const url = Deno.env.get("SUPABASE_URL");
    const anon = Deno.env.get("SUPABASE_ANON_KEY");
    const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !anon || !service) throw new Error("Missing Supabase environment variables");

    const visitor = createClient(url, anon, {
      global:{headers:{Authorization:authorization}},
      auth:{persistSession:false,autoRefreshToken:false},
    });
    const {data:{user},error:authError} = await visitor.auth.getUser(authorization.slice(7));
    if (authError || !user) return respond({error:"Invalid session"},401,origin);
    const {data:admin,error:adminError} = await visitor.from("dashboard_admins").select("user_id").eq("user_id",user.id).maybeSingle();
    if (adminError) throw new Error("Admin authorization check failed");
    if (!admin) return respond({error:"Access denied"},403,origin);

    const input = await request.json().catch(()=>({}));
    const page = Number(input?.page ?? 1);
    if (!Number.isSafeInteger(page) || page < 1 || page > 10000) return respond({error:"Invalid page"},400,origin);
    const perPage = 100;
    // Service role remains server-side only. Never return tokens or provider identities.
    const privileged = createClient(url, service, {auth:{persistSession:false,autoRefreshToken:false}});
    const {data,error} = await privileged.auth.admin.listUsers({page,perPage});
    if (error) throw error;
    const users = data.users.map(u=>({
      id:u.id,
      name:typeof u.user_metadata?.full_name === "string" ? u.user_metadata.full_name :
           typeof u.user_metadata?.name === "string" ? u.user_metadata.name : "",
      email:u.email ?? "",
      createdAt:u.created_at,
      confirmed:!!(u.email_confirmed_at || u.confirmed_at),
      provider:typeof u.app_metadata?.provider === "string" ? u.app_metadata.provider : "email",
    }));
    return respond({success:true,users,page,perPage,hasMore:users.length===perPage},200,origin);
  } catch(error) {
    console.error("members-dashboard:",error instanceof Error?error.message:"unknown");
    return respond({error:"Unable to retrieve members"},500,origin);
  }
});

// Public newsletter opt-in. Requires BREVO_API_KEY and BREVO_DOI_TEMPLATE_ID Supabase secrets.
// Deploy with: supabase functions deploy newsletter-subscribe --no-verify-jwt
const cors = {
  "Access-Control-Allow-Origin": "https://deepdocumentary.com",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type, apikey, authorization",
  "Content-Type": "application/json; charset=utf-8",
};
const reply = (status: number, body: object) => new Response(JSON.stringify(body), {status, headers:cors});
Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response(null, {status:204,headers:cors});
  if (request.method !== "POST") return reply(405,{error:"method_not_allowed"});
  const origin=request.headers.get("origin");
  if (origin !== "https://deepdocumentary.com") return reply(403,{error:"origin_not_allowed"});
  let data: {email?: unknown; website?: unknown};
  try {data=await request.json();} catch {return reply(400,{error:"invalid_request"});}
  // Honeypot; do not expose subscriber details.
  if (data.website) return reply(200,{success:true});
  const email=typeof data.email==="string"?data.email.trim().toLowerCase():"";
  if (email.length>254 || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)) return reply(400,{error:"invalid_email"});
  const key=Deno.env.get("BREVO_API_KEY");
  const template=Number(Deno.env.get("BREVO_DOI_TEMPLATE_ID"));
  if (!key || !Number.isSafeInteger(template) || template<1) return reply(503,{error:"subscription_unavailable"});
  try {
    const response=await fetch("https://api.brevo.com/v3/contacts/doubleOptinConfirmation",{
      method:"POST",
      headers:{"api-key":key,"Content-Type":"application/json","accept":"application/json"},
      body:JSON.stringify({
        email,
        includeListIds:[3],
        templateId:template,
        redirectionUrl:"https://deepdocumentary.com/?newsletter=confirmed",
      }),
      signal:AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      console.error("Brevo double opt-in failed, status:",response.status);
      return reply(502,{error:"subscription_unavailable"});
    }
    return reply(200,{success:true});
  } catch {
    return reply(502,{error:"subscription_unavailable"});
  }
});

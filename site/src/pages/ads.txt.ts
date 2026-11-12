import type { APIRoute } from "astro";
import { ADSENSE_PUB_ID } from "../config";

export const GET: APIRoute = () =>
  new Response(`google.com, ${ADSENSE_PUB_ID}, DIRECT, f08c47fec0942fa0\n`, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });

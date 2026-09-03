import { apiFetch } from "./client";

export function getWaifu2xStatus(): Promise<{ available: boolean }> {
  return apiFetch("/tools/waifu2x/status");
}

export function resolveDns(host: string): Promise<{
  ok: boolean;
  host: string;
  ips: string[];
  error?: string;
}> {
  return apiFetch("/tools/dns/resolve", {
    method: "POST",
    body: JSON.stringify({ host, port: 443 }),
  });
}

export function testProxy(): Promise<{
  ok: boolean;
  status?: number;
  elapsed?: number;
  error?: string;
}> {
  return apiFetch("/tools/proxy/test");
}

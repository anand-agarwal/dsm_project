const WINDOW_MS = 10 * 60 * 1000;
const MAX_POSTS = 20;

const hits = new Map<string, number[]>();

export function resetChatRateLimit() {
  hits.clear();
}

export function clientIpFromRequest(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) return first;
  }
  return request.headers.get("x-real-ip")?.trim() || "unknown";
}

export function checkChatRateLimit(
  key: string,
  now = Date.now(),
  max = MAX_POSTS,
  windowMs = WINDOW_MS,
): { allowed: true } | { allowed: false; retryAfterSec: number } {
  const cutoff = now - windowMs;
  const recent = (hits.get(key) ?? []).filter((t) => t > cutoff);
  if (recent.length >= max) {
    hits.set(key, recent);
    const retryAfterSec = Math.max(1, Math.ceil((recent[0]! + windowMs - now) / 1000));
    return { allowed: false, retryAfterSec };
  }
  recent.push(now);
  hits.set(key, recent);
  return { allowed: true };
}

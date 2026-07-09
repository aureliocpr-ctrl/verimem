/**
 * Verimem TypeScript client — thin, typed, zero-dependency (native fetch).
 *
 * Talks to the self-hosted Verimem gateway (`verimem gateway serve`): every
 * write goes through the anti-confabulation gate server-side, every read
 * carries provenance, and `/v1/stats` exposes the tenant's trust odometer.
 * The API key is sent ONLY as an Authorization header — never in a URL.
 */

export interface VerimemClientOptions {
  /** Gateway base URL, e.g. "http://127.0.0.1:8377". */
  baseUrl: string;
  /** Tenant API key (vm_ prefix) — travels only as a Bearer header. */
  apiKey: string;
  /** Custom fetch (tests / non-Node runtimes). Defaults to globalThis.fetch. */
  fetch?: typeof fetch;
}

export interface Message {
  role: "user" | "assistant" | string;
  content: string;
}

export interface AddOptions {
  topic?: string;
  /** Provenance refs, e.g. ["ci:main:green", "doc:contract.pdf#3"]. */
  verifiedBy?: string[];
  /** Source text for write-time grounding (with ground: true). */
  source?: string;
  ground?: boolean;
  gateMode?: "downgrade" | "reject";
  /** Event time (epoch seconds) — bi-temporal "when it happened". */
  assertedAt?: number;
  conversationId?: string;
  /** Identity fix: the app-provided subject of extracted facts. */
  userName?: string;
}

export interface AddResult {
  stored: boolean;
  id?: string;
  status: string;
  grounding_score: number | null;
  warnings: Array<Record<string, unknown>>;
  advice?: string;
}

export interface SearchOptions {
  k?: number;
  deep?: boolean;
  /** Time travel: epoch seconds — the store as of that moment. */
  asOf?: number;
  withHistory?: boolean;
}

export interface TenantStats {
  tenant: string;
  trust: {
    ledger: {
      admitted: number;
      quarantined: number;
      rejected: number;
      abstained: number;
    };
    by_layer: Record<string, number>;
    since: number | null;
    store: Record<string, number>;
  };
  usage: Record<string, number>;
}

/** Error carrying the HTTP status and the gateway's error body. */
export class VerimemError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "VerimemError";
    this.status = status;
    this.body = body;
  }
}

export class VerimemClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: VerimemClientOptions) {
    if (!options.baseUrl) throw new Error("baseUrl is required");
    if (!options.apiKey) throw new Error("apiKey is required");
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.apiKey = options.apiKey;
    this.fetchImpl = options.fetch ?? fetch;
  }

  private async request<T>(
    method: string,
    path: string,
    opts: { body?: unknown; query?: Record<string, unknown> } = {},
  ): Promise<T> {
    const url = new URL(this.baseUrl + path);
    for (const [k, v] of Object.entries(opts.query ?? {})) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
    const res = await this.fetchImpl(url, {
      method,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        ...(opts.body !== undefined
          ? { "Content-Type": "application/json" }
          : {}),
      },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
    const text = await res.text();
    let parsed: unknown = text;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      /* non-JSON error body: keep the raw text */
    }
    if (!res.ok) {
      const detail =
        typeof parsed === "object" && parsed !== null && "detail" in parsed
          ? String((parsed as { detail: unknown }).detail)
          : res.statusText;
      throw new VerimemError(
        `verimem gateway ${res.status}: ${detail}`,
        res.status,
        parsed,
      );
    }
    return parsed as T;
  }

  /** Liveness + gateway version. No auth required by the server. */
  health(): Promise<{ ok: boolean; version: string }> {
    return this.request("GET", "/v1/health");
  }

  /**
   * Store a fact (string) or ingest a conversation (Message[]) THROUGH the
   * gate. Unsupported hype is quarantined; contradictions can be rejected.
   */
  add(content: string | Message[], opts: AddOptions = {}): Promise<AddResult> {
    const body: Record<string, unknown> = {
      topic: opts.topic,
      source: opts.source,
      verified_by: opts.verifiedBy,
      ground: opts.ground,
      gate_mode: opts.gateMode,
      asserted_at: opts.assertedAt,
      conversation_id: opts.conversationId,
      user_name: opts.userName,
    };
    if (typeof content === "string") body.content = content;
    else body.messages = content;
    return this.request("POST", "/v1/memories", { body });
  }

  /** Semantic recall with provenance on every hit. */
  search(
    query: string,
    opts: SearchOptions = {},
  ): Promise<Array<Record<string, unknown>>> {
    return this.request("GET", "/v1/search", {
      query: {
        q: query,
        k: opts.k,
        deep: opts.deep,
        as_of: opts.asOf,
        with_history: opts.withHistory,
      },
    }).then(
      (r) =>
        (r as { hits?: Array<Record<string, unknown>> }).hits ??
        (r as Array<Record<string, unknown>>),
    );
  }

  /** The evidence dossier — or an explicit abstention with its reason. */
  explain(
    query: string,
    opts: { k?: number; asOf?: number } = {},
  ): Promise<Record<string, unknown>> {
    return this.request("GET", "/v1/explain", {
      query: { q: query, k: opts.k, as_of: opts.asOf },
    });
  }

  /** One fact by id (with provenance), or null when it does not exist. */
  async get(factId: string): Promise<Record<string, unknown> | null> {
    try {
      return await this.request("GET", `/v1/memories/${encodeURIComponent(factId)}`);
    } catch (err) {
      if (err instanceof VerimemError && err.status === 404) return null;
      throw err;
    }
  }

  /** Delete a fact; purgeHistory removes its whole supersession chain (GDPR). */
  delete(
    factId: string,
    opts: { purgeHistory?: boolean } = {},
  ): Promise<{ removed: boolean }> {
    return this.request("DELETE", `/v1/memories/${encodeURIComponent(factId)}`, {
      query: { purge_history: opts.purgeHistory },
    });
  }

  /** The tenant's own trust odometer + usage. */
  stats(): Promise<TenantStats> {
    return this.request("GET", "/v1/stats");
  }
}

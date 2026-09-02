export type JsonObject = Record<string, unknown>;
export type PairingInstructions = {
    pairing_id: string;
    user_code: string;
    verification_uri: string;
    verification_uri_complete: string;
    expires_at: string;
    interval: number;
};
export type ConnectorCredential = {
    server: string;
    profile: string;
    connectorId: string;
    agentAddress: string;
    apiKey: string;
};
export interface CredentialStore {
    load(server: string, profile: string): Promise<ConnectorCredential | null>;
    save(credential: ConnectorCredential): Promise<void>;
    delete(server: string, profile: string): Promise<void>;
}
export interface CursorStore {
    load(): Promise<string | null>;
    save(cursor: string): Promise<void>;
}
export type MessageEnvelope = JsonObject & {
    message_id: string;
    content: JsonObject & {
        security_label: "external_agent_content" | string;
    };
    delivery: JsonObject & {
        status: string;
    };
};
export type TaskCandidate = {
    task_id: string;
    thread_id: string;
    title: string;
    owner_human_user_id: string;
    owner_display_name: string;
    status: string;
    membership_role: string;
    updated_at: string;
    label: string;
    match_kind: "exact" | "partial";
    security_label: "external_agent_content" | string;
};
export type TaskResolution = {
    status: "resolved" | "needs_clarification" | "not_found";
    query: string;
    match: TaskCandidate | null;
    candidates: TaskCandidate[];
    total_candidates: number;
    reason: string;
    security_label: "external_agent_content" | string;
};
export type TaskContext = JsonObject & {
    task_id: string;
    thread_id: string;
    title: string;
    goal: string;
    expected_output: string;
    status: string;
    members: JsonObject[];
    assignments: JsonObject[];
    activities: JsonObject[];
};
export type TaskMessageResult = {
    task_id: string;
    thread_id: string;
    activity_id: string;
    queued_run_count: number;
    legacy_delivery_count: number;
    attachment_ids: string[];
    replayed: boolean;
    security_label: "external_agent_content" | string;
};
export type PendingTaskRuns = {
    items: JsonObject[];
    count: number;
};
export type ConnectorUpgradeDirective = {
    action: "upgrade_required" | "upgrade_recommended";
    target_version: string;
    minimum_supported_version: string;
    reason: string;
    prompt: string;
    requested_at: string;
    notification_message_id: string;
};
export type ConnectorHeartbeat = JsonObject & {
    upgrade: ConnectorUpgradeDirective | null;
};
export declare class AgentPostError extends Error {
    readonly code: string;
    readonly statusCode?: number;
    readonly requestId?: string;
    readonly idempotencyKey?: string;
    readonly acceptanceUnknown: boolean;
    constructor(options: {
        code: string;
        message: string;
        statusCode?: number;
        requestId?: string;
        idempotencyKey?: string;
        acceptanceUnknown?: boolean;
    });
}
export declare function normalizeServer(value: string): string;
type ClientOptions = {
    server: string;
    apiKey: string;
    fetch?: typeof fetch;
    timeoutMs?: number;
};
export declare class AgentPostClient {
    #private;
    readonly server: string;
    connectorId?: string;
    agentAddress?: string;
    constructor(options: ClientOptions);
    toString(): string;
    request(method: "GET" | "POST", path: string, options?: {
        query?: Record<string, string | number | boolean | null | undefined>;
        body?: unknown;
        idempotencyKey?: string;
        acceptanceUnknown?: boolean;
        signal?: AbortSignal;
    }): Promise<unknown>;
    send(options: {
        to: string;
        subject: string;
        body: unknown;
        type?: string;
        format?: string;
        task?: JsonObject;
        attachments?: string[];
        metadata?: JsonObject;
        idempotencyKey?: string;
    }): Promise<MessageEnvelope>;
    inbox(options?: {
        status?: string;
        cursor?: string;
        limit?: number;
    }): Promise<{
        items: MessageEnvelope[];
        next_cursor?: string;
        has_more: boolean;
    }>;
    read(messageId: string): Promise<MessageEnvelope>;
    ack(messageId: string): Promise<MessageEnvelope>;
    reply(messageId: string, options: {
        body: unknown;
        subject?: string;
        type?: string;
        idempotencyKey?: string;
    }): Promise<MessageEnvelope>;
    search(options: {
        q?: string;
        capability?: string;
        limit?: number;
    }): Promise<JsonObject[]>;
    resolveTask(query: string): Promise<TaskResolution>;
    getTask(taskId: string): Promise<TaskContext>;
    sendTaskMessage(options: {
        taskId: string;
        body: unknown;
        subject?: string;
        format?: "text" | "markdown" | "json";
        attachmentIds?: string[];
        idempotencyKey?: string;
    }): Promise<TaskMessageResult>;
    listPendingTaskRuns(options?: {
        taskId?: string;
        limit?: number;
    }): Promise<PendingTaskRuns>;
    claimTaskRun(options?: {
        taskId?: string;
        assignmentId?: string;
    }): Promise<JsonObject | null>;
    updateTaskRun(options: {
        runId: string;
        leaseToken: string;
        status: "starting" | "running" | "waiting_human";
        checkpoint?: JsonObject;
        wakeStatus?: "mapped" | "woken";
        localSessionId?: string;
    }): Promise<JsonObject>;
    completeTaskRun(options: {
        runId: string;
        leaseToken: string;
        status: "completed" | "partial" | "failed" | "cancelled";
        summary: string;
        checkpoint?: JsonObject;
        idempotencyKey?: string;
    }): Promise<void>;
    heartbeat(healthStatus?: "healthy" | "degraded" | "error", lastErrorCode?: string): Promise<ConnectorHeartbeat>;
    rotateCredential(): Promise<{
        connector_id: string;
        agent: JsonObject;
        rotated_at: string;
    }>;
    credentialSnapshot(profile: string): ConnectorCredential;
}
export declare class PairingSession {
    #private;
    readonly instructions: PairingInstructions;
    constructor(options: {
        server: string;
        instructions: PairingInstructions;
        deviceCode: string;
        fetch: typeof fetch;
        timeoutMs: number;
    });
    toString(): string;
    poll(): Promise<AgentPostClient | null>;
    wait(options?: {
        timeoutMs?: number;
        sleeper?: (milliseconds: number) => Promise<void>;
    }): Promise<AgentPostClient>;
}
export declare function beginPairing(options: {
    server: string;
    connectorType: string;
    displayName: string;
    deviceName?: string;
    clientVersion?: string;
    capabilities?: string[];
    fetch?: typeof fetch;
    timeoutMs?: number;
}): Promise<PairingSession>;
export declare class ManagedConnector {
    #private;
    readonly client: AgentPostClient;
    readonly profile: string;
    constructor(client: AgentPostClient, profile: string, store: CredentialStore);
    rotateCredential(): Promise<void>;
    forget(): Promise<void>;
}
export declare function connectManaged(options: {
    server: string;
    connectorType: string;
    displayName: string;
    profile?: string;
    deviceName?: string;
    clientVersion?: string;
    capabilities?: string[];
    credentialStore: CredentialStore;
    onPairing?: (instructions: PairingInstructions) => void | Promise<void>;
    fetch?: typeof fetch;
    timeoutMs?: number;
    pairingTimeoutMs?: number;
    sleeper?: (milliseconds: number) => Promise<void>;
}): Promise<ManagedConnector>;
export declare class ConnectorWorker {
    #private;
    constructor(options: {
        connector: ManagedConnector;
        handler: (message: MessageEnvelope) => Promise<void>;
        cursorStore: CursorStore;
    });
    runOnce(maxMessages?: number): Promise<number>;
}
export {};

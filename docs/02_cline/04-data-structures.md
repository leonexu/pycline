# Cline核心代码片段与数据结构

## 1. 任务类核心结构

### Task类定义
```typescript
// src/core/task/index.ts:94-149
export class Task {
    // 核心标识
    readonly taskId: string
    private taskIsFavorited?: boolean
    private cwd: string
    
    // 任务状态管理
    taskState: TaskState
    
    // 依赖组件
    api: ApiHandler
    terminalManager: TerminalManager
    browserSession: BrowserSession
    contextManager: ContextManager
    toolExecutor: ToolExecutor
    
    // 消息状态处理器
    messageStateHandler: MessageStateHandler
    
    // 配置信息
    autoApprovalSettings: AutoApprovalSettings
    browserSettings: BrowserSettings
    chatSettings: ChatSettings
}
```

### 任务状态数据结构
```typescript
// src/core/task/TaskState.ts
export class TaskState {
    isStreaming: boolean = false
    isWaitingForFirstChunk: boolean = false
    didFinishAbortingStream: boolean = false
    abandoned: boolean = false
    isAwaitingPlanResponse: boolean = false
    didRespondToPlanAskBySwitchingMode: boolean = false
    checkpointTrackerErrorMessage?: string
}
```

## 2. 工具系统数据结构

### 基础工具定义
```typescript
// src/core/tools/readTool.ts:6-19
export const readToolDefinition = (cwd: string) => ({
    name: "Read",
    descriptionForAgent,
    inputSchema: {
        type: "object",
        properties: {
            file_path: {
                type: "string",
                description: `The path of the file to read (relative to the current working directory ${cwd.toPosix()})`,
            },
        },
        required: ["file_path"],
    },
})
```

### 工具执行结果结构
```typescript
// src/core/task/index.ts:91-93
export type ToolResponse = string | Array<Anthropic.TextBlockParam | Anthropic.ImageBlockParam>
type UserContent = Array<Anthropic.ContentBlockParam>
```

## 3. 扩展消息接口

### 扩展消息结构
```typescript
// src/shared/ExtensionMessage.ts:13-23
export interface ExtensionMessage {
    type: "grpc_response"
    grpc_response?: {
        message?: any // JSON序列化的protobuf消息
        request_id: string // 请求ID
        error?: string // 错误消息
        is_streaming?: boolean // 是否流式响应
        sequence_number?: number // 流式响应的顺序号
    }
}
```

### 扩展状态结构
```typescript
// src/shared/ExtensionMessage.ts:29-50
export interface ExtensionState {
    isNewUser: boolean
    welcomeViewCompleted: boolean
    apiConfiguration?: ApiConfiguration
    autoApprovalSettings: AutoApprovalSettings
    browserSettings: BrowserSettings
    chatSettings: ChatSettings
    clineMessages: ClineMessage[]
    currentTaskItem?: HistoryItem
    taskHistory: HistoryItem[]
    platform: Platform
    shouldShowAnnouncement: boolean
}
```

## 4. API配置数据结构

### API配置接口
```typescript
// src/shared/api.ts
export interface ApiConfiguration {
    apiProvider?: ApiProvider
    apiModel?: string
    apiKey?: string
    apiBaseUrl?: string
    openRouterApiKey?: string
    openRouterModelId?: string
    openRouterModelInfo?: ModelInfo
    clineApiKey?: string
    azureApiVersion?: string
    geminiApiKey?: string
    deepSeekApiKey?: string
}
```

### 模型信息结构
```typescript
export interface ModelInfo {
    maxTokens?: number
    contextWindow?: number
    supportsImages?: boolean
    supportsPromptCache?: boolean
    inputPrice?: number
    outputPrice?: number
    description?: string
}
```

## 5. 上下文管理数据结构

### 上下文窗口信息
```typescript
// src/core/context/context-management/context-window-utils.ts
export interface ContextWindowInfo {
    totalTokens: number
    maxTokens: number
    contextWindow: number
    maxAllowedSize: number
    currentSize: number
    thresholdReached: boolean
}
```

### 文件跟踪器状态
```typescript
// src/core/context/context-tracking/FileContextTracker.ts
interface TrackedFile {
    path: string
    lastModified: number
    content: string
    tokenCount: number
    priority: number
}
```

## 6. 消息系统数据结构

### Cline消息类型
```typescript
// src/shared/ExtensionMessage.ts
export interface ClineMessage {
    ts: number
    type: "ask" | "say"
    ask?: ClineAsk
    say?: ClineSay
    text?: string
    images?: string[]
    fileImages?: string[]
    partial?: boolean
    conversationHistoryIndex?: number
}
```

### 询问类型枚举
```typescript
export type ClineAsk =
    | "request_limit"
    | "command"
    | "command_output"
    | "completion_result"
    | "tool"
    | "mistake_limit_reached"
    | "followup"
    | "plan_mode_response"
```

### 响应类型枚举
```typescript
export type ClineSay =
    | "task"
    | "error"
    | "api_req_started"
    | "api_req_finished"
    | "text"
    | "user_feedback"
    | "completion_result"
```

## 7. 自动批准设置

### 自动批准配置
```typescript
// src/shared/AutoApprovalSettings.ts
export interface AutoApprovalSettings {
    enabled: boolean
    actions: AutoApprovalAction[]
    maxRequests: number
    maxTokens: number
    cooldownPeriod: number
}

export interface AutoApprovalAction {
    type: string
    pattern?: string
    enabled: boolean
}
```

## 8. MCP集成数据结构

### MCP服务器配置
```typescript
// src/shared/mcp.ts
export interface McpServer {
    name: string
    description?: string
    command: string
    args?: string[]
    env?: Record<string, string>
    disabled?: boolean
    autoApprove?: string[]
    timeout?: number
}
```

### MCP工具定义
```typescript
export interface McpTool {
    name: string
    description: string
    inputSchema: object
}
```

## 9. 历史记录数据结构

### 历史项目
```typescript
// src/shared/HistoryItem.ts
export interface HistoryItem {
    id: string
    ts: number
    task: string
    tokensIn: number
    tokensOut: number
    cacheWrites?: number
    cacheReads?: number
    totalCost: number
    folderName?: string
    apiProvider?: string
    apiModel?: string
    isFavorite?: boolean
    size?: number
}
```

## 10. 检查点系统数据结构

### 检查点配置
```typescript
// src/integrations/checkpoints/CheckpointTracker.ts
interface CheckpointConfig {
    enabled: boolean
    maxCheckpoints: number
    excludePatterns: string[]
    compressionEnabled: boolean
}
```

### 检查点记录
```typescript
interface Checkpoint {
    id: string
    timestamp: number
    commitHash: string
    description: string
    fileCount: number
    size: number
}
```

## 11. 浏览器会话配置

### 浏览器设置
```typescript
// src/shared/BrowserSettings.ts
export interface BrowserSettings {
    remoteBrowserHost?: string
    remoteBrowserEnabled: boolean
    remoteBrowserPort?: number
    chromeExecutablePath?: string
    browserViewport?: {
        width: number
        height: number
    }
}
```

## 12. 终端配置数据结构

### 终端设置
```typescript
// 终端相关配置
export interface TerminalSettings {
    shellIntegrationTimeout: number
    terminalReuseEnabled: boolean
    defaultTerminalProfile: string
    terminalOutputLineLimit: number
}
```

## 13. 聊天消息数据结构

### 聊天消息
```typescript
// 聊天消息结构
export interface ChatMessage {
    role: "user" | "assistant" | "system"
    content: string | Array<{
        type: "text" | "image_url"
        text?: string
        image_url?: { url: string }
    }>
    timestamp: number
    tokenCount?: number
}
```

## 14. 错误处理数据结构

### 错误信息
```typescript
// 错误类型定义
export interface ClineError {
    type: ClineErrorType
    message: string
    details?: any
    timestamp: number
    taskId?: string
}

export enum ClineErrorType {
    API_ERROR = "API_ERROR",
    CONTEXT_WINDOW_ERROR = "CONTEXT_WINDOW_ERROR",
    TOOL_ERROR = "TOOL_ERROR",
    NETWORK_ERROR = "NETWORK_ERROR",
    PERMISSION_ERROR = "PERMISSION_ERROR",
}
```

## 15. 遥测数据结构

### 使用统计
```typescript
// 遥测事件
export interface TelemetryEvent {
    event: string
    properties: {
        taskId?: string
        model?: string
        provider?: string
        action?: string
        duration?: number
        tokensIn?: number
        tokensOut?: number
        cost?: number
    }
    timestamp: number
}
```

## 使用示例

### 创建任务示例
```typescript
// 任务创建调用示例
await controller.initTask(
    "创建一个React组件",
    ["data:image/png;base64,..."], // 设计图
    ["/src/components"]            // 相关文件夹
)
```

### 工具调用示例
```typescript
// 工具使用示例
const toolResponse = await toolExecutor.executeTool({
    name: "read_file",
    params: { file_path: "src/main.js" }
})
```

### 消息发送示例
```typescript
// 发送消息到Webview
await postMessageToWebview({
    type: "say",
    say: "text",
    text: "任务执行完成",
    ts: Date.now()
})
```
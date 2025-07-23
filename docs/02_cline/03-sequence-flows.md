# Cline任务执行流程 - Mermaid时序图

## 1. 任务启动完整流程

```mermaid
sequenceDiagram
    participant User
    participant VSCode
    participant Extension
    participant Controller
    participant Task
    participant ContextManager
    participant ToolExecutor
    participant API
    
    User->>VSCode: 输入任务描述
    VSCode->>Extension: cline.newTask命令
    Extension->>Controller: initTask(taskText, images, files)
    
    Note over Controller: 任务初始化阶段
    Controller->>Controller: clearTask() - 清理旧任务
    Controller->>Controller: getAllExtensionState() - 获取配置
    Controller->>Task: new Task(...) - 创建任务实例
    
    Note over Task: 任务配置阶段
    Task->>ContextManager: 初始化上下文管理器
    Task->>ToolExecutor: 初始化工具执行器
    Task->>API: buildApiHandler() - 创建API处理器
    
    Note over Task: 执行阶段
    Task->>ContextManager: getContextWindowInfo() - 获取上下文信息
    ContextManager->>Task: 返回上下文限制
    
    Task->>API: 发送初始消息
    API-->>Task: 返回AI响应
    
    loop 每个工具调用
        Task->>ToolExecutor: 执行工具命令
        ToolExecutor->>ToolExecutor: 验证权限
        ToolExecutor->>User: 请求批准(如需要)
        User-->>ToolExecutor: 批准/拒绝
        ToolExecutor->>工具: 执行具体操作
        工具-->>ToolExecutor: 返回结果
        ToolExecutor-->>Task: 返回执行结果
    end
    
    Task->>Controller: 任务完成
    Controller->>VSCode: 更新UI状态
    VSCode-->>User: 显示完成结果
```

## 2. 文件编辑操作流程

```mermaid
sequenceDiagram
    participant AI
    participant Task
    participant ToolExecutor
    participant FileTool
    participant DiffViewProvider
    participant User
    
    AI->>Task: 提议编辑文件
    Task->>ToolExecutor: executeTool("edit_file", params)
    
    Note over ToolExecutor: 权限检查
    ToolExecutor->>ToolExecutor: checkAutoApproval()
    alt 需要用户确认
        ToolExecutor->>User: 显示差异对比
        User-->>ToolExecutor: 批准/修改/拒绝
    end
    
    ToolExecutor->>FileTool: 执行文件修改
    FileTool->>FileTool: 读取原文件
    FileTool->>FileTool: 应用修改
    FileTool->>FileTool: 验证语法
    FileTool->>DiffViewProvider: 创建差异视图
    
    DiffViewProvider->>User: 显示修改对比
    User-->>DiffViewProvider: 接受/拒绝修改
    
    DiffViewProvider-->>FileTool: 确认修改
    FileTool-->>ToolExecutor: 返回操作结果
    ToolExecutor-->>Task: 完成工具调用
    Task-->>AI: 继续对话
```

## 3. 终端命令执行流程

```mermaid
sequenceDiagram
    participant AI
    participant Task
    participant ToolExecutor
    participant TerminalTool
    participant TerminalManager
    participant User
    
    AI->>Task: 需要执行终端命令
    Task->>ToolExecutor: executeTool("execute_command", {command: "npm install"})
    
    Note over ToolExecutor: 权限验证
    ToolExecutor->>ToolExecutor: checkCommandRisk()
    alt 高风险命令
        ToolExecutor->>User: 警告提示
        User-->>ToolExecutor: 确认执行
    end
    
    ToolExecutor->>TerminalTool: 执行命令
    TerminalTool->>TerminalManager: 获取可用终端
    TerminalManager-->>TerminalTool: 返回终端实例
    
    TerminalTool->>TerminalManager: 发送命令
    TerminalManager->>Shell: 执行实际命令
    
    loop 实时输出
        Shell-->>TerminalManager: 输出流
        TerminalManager-->>TerminalTool: 转发输出
        TerminalTool-->>Task: 流式结果
        Task-->>AI: 实时反馈
    end
    
    Shell-->>TerminalManager: 命令完成
    TerminalManager-->>TerminalTool: 最终输出
    TerminalTool-->>ToolExecutor: 返回执行结果
    ToolExecutor-->>Task: 完成工具调用
```

## 4. MCP工具调用流程

```mermaid
sequenceDiagram
    participant AI
    participant Task
    participant McpHub
    participant McpServer
    participant ToolExecutor
    participant User
    
    AI->>Task: 需要使用MCP工具
    Task->>ToolExecutor: executeTool("use_mcp_tool", {server: "github", tool: "create_pr"})
    
    ToolExecutor->>McpHub: 获取MCP服务器
    McpHub->>McpHub: 检查服务器状态
    
    alt 服务器未运行
        McpHub->>McpServer: 启动MCP服务器
        McpServer-->>McpHub: 服务器就绪
    end
    
    McpHub->>McpServer: 调用工具方法
    McpServer->>McpServer: 执行工具逻辑
    
    alt 需要用户输入
        McpServer->>ToolExecutor: 请求额外参数
        ToolExecutor->>User: 显示输入表单
        User-->>ToolExecutor: 提供参数
        ToolExecutor-->>McpServer: 发送参数
    end
    
    McpServer->>外部API: 执行实际操作
    外部API-->>McpServer: 返回结果
    McpServer-->>McpHub: 工具执行结果
    McpHub-->>ToolExecutor: 返回结果
    ToolExecutor-->>Task: 完成工具调用
    Task-->>AI: 结果反馈
```

## 5. 上下文管理流程

```mermaid
sequenceDiagram
    participant Task
    participant ContextManager
    participant FileContextTracker
    participant ModelContextTracker
    participant ContextWindowUtils
    
    Task->>ContextManager: 请求构建上下文
    ContextManager->>FileContextTracker: 获取相关文件
    FileContextTracker->>FileContextTracker: 分析文件依赖
    FileContextTracker-->>ContextManager: 返回文件列表
    
    ContextManager->>ModelContextTracker: 计算token使用量
    ModelContextTracker->>ContextWindowUtils: 获取窗口限制
    ContextWindowUtils-->>ModelContextTracker: 返回限制信息
    
    ModelContextTracker->>ModelContextTracker: 优先级排序
    ModelContextTracker->>ModelContextTracker: 裁剪低优先级内容
    
    loop 动态调整
        ModelContextTracker->>ContextManager: 当前使用量
        alt 超出限制
            ContextManager->>ModelContextTracker: 移除低优先级内容
        end
    end
    
    ModelContextTracker-->>ContextManager: 优化后上下文
    ContextManager-->>Task: 构建完成的上下文
```

## 6. 检查点(Checkpoint)系统

```mermaid
sequenceDiagram
    participant Task
    participant CheckpointTracker
    participant GitOperations
    participant FileSystem
    participant User
    
    Note over Task: 任务执行过程中
    Task->>CheckpointTracker: 创建检查点
    CheckpointTracker->>GitOperations: 创建git commit
    GitOperations->>FileSystem: 保存当前状态
    FileSystem-->>GitOperations: 状态保存完成
    GitOperations-->>CheckpointTracker: 返回commit hash
    CheckpointTracker-->>Task: 检查点创建成功
    
    Note over User: 需要回滚时
    User->>Task: 请求恢复检查点
    Task->>CheckpointTracker: restoreCheckpoint(commitHash)
    CheckpointTracker->>GitOperations: 获取历史状态
    GitOperations->>FileSystem: 恢复文件状态
    FileSystem-->>GitOperations: 恢复完成
    GitOperations-->>CheckpointTracker: 返回状态差异
    CheckpointTracker-->>Task: 恢复成功
    Task-->>User: 显示恢复结果
```

## 7. 多模态交互流程

```mermaid
sequenceDiagram
    participant User
    participant WebviewUI
    participant Controller
    participant Task
    participant ImageProcessor
    
    User->>WebviewUI: 拖拽图片到输入框
    WebviewUI->>WebviewUI: 验证图片格式
    WebviewUI->>Controller: 发送图片数据
    
    Controller->>ImageProcessor: 处理图片
    ImageProcessor->>ImageProcessor: 压缩/格式转换
    ImageProcessor->>ImageProcessor: 提取元数据
    ImageProcessor-->>Controller: 返回处理结果
    
    Controller->>Task: 附带图片启动任务
    Task->>Task: 构建多模态消息
    Task->>API: 发送文本+图片
    API-->>Task: 返回分析结果
    Task-->>Controller: 更新UI状态
    Controller-->>WebviewUI: 显示响应
```

## 8. 实时协作编辑

```mermaid
sequenceDiagram
    participant User1
    participant User2
    participant VSCode
    participant Controller
    participant Task
    participant DiffView
    
    User1->>VSCode: 编辑文件
    VSCode->>Controller: 文件变更事件
    Controller->>Task: 暂停当前任务
    
    Task->>DiffView: 创建临时检查点
    DiffView->>Task: 返回检查点ID
    
    User2->>VSCode: 查看实时修改
    VSCode->>Controller: 获取最新状态
    Controller->>DiffView: 请求差异对比
    DiffView-->>Controller: 返回差异结果
    
    User1->>VSCode: 确认修改
    VSCode->>Controller: 提交修改
    Controller->>Task: 恢复任务执行
    Task-->>User1: 继续AI对话
```

## 9. 错误处理与恢复

```mermaid
sequenceDiagram
    participant Task
    participant ErrorService
    participant ContextManager
    participant FallbackHandler
    participant User
    
    Task->>API: 发送请求
    API-->>Task: 返回错误(例如: 429限流)
    
    Task->>ErrorService: 处理错误
    ErrorService->>ErrorService: 分析错误类型
    
    alt 可恢复错误
        ErrorService->>ContextManager: 减少上下文
        ContextManager->>ContextManager: 裁剪内容
        ContextManager-->>ErrorService: 返回优化上下文
        ErrorService->>FallbackHandler: 切换备用API
        FallbackHandler-->>Task: 重新发送请求
    else 不可恢复错误
        ErrorService->>User: 显示错误信息
        User-->>ErrorService: 选择操作(重试/取消)
    end
    
    Note over Task: 保持任务连续性
    Task-->>User: 错误处理完成
```

## 10. 任务完成与清理

```mermaid
sequenceDiagram
    participant Task
    participant ToolExecutor
    participant ContextManager
    participant FileSystem
    participant Telemetry
    participant User
    
    Note over Task: 任务执行完成
    Task->>ToolExecutor: 清理所有工具
    ToolExecutor->>ToolExecutor: 关闭终端会话
    ToolExecutor->>ToolExecutor: 清理浏览器实例
    
    Task->>ContextManager: 保存最终上下文
    ContextManager->>FileSystem: 写入历史记录
    FileSystem-->>ContextManager: 保存完成
    
    Task->>Telemetry: 发送使用统计
    Telemetry->>Telemetry: 计算token使用量
    Telemetry->>Telemetry: 记录任务时长
    Telemetry-->>Task: 统计完成
    
    Task->>Task: 生成总结报告
    Task-->>User: 显示任务结果
    Task-->>Controller: 任务结束通知
    Controller-->>User: 清理UI状态
```
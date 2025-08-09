// 全局变量
let autoScrollEnabled = true;  // 默认启用自动滚动
let buttonStatusTimeout = null;  // 按钮状态恢复定时器

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化WebSocket连接
    initWebSocket();

    // 检查翻译器状态
    checkTranslatorStatus();

    // 加载任务列表
    loadTasks();

    // 自动加载术语库
    loadTerminology();

    // 绑定事件处理器
    document.getElementById('check-status-btn').addEventListener('click', checkTranslatorStatus);
    document.getElementById('translation-form').addEventListener('submit', submitTranslation);
    document.getElementById('refresh-tasks').addEventListener('click', loadTasks);
    document.getElementById('open-output-dir').addEventListener('click', openOutputDirectory);
    document.getElementById('load-terminology').addEventListener('click', loadTerminology);
    document.getElementById('save-terminology').addEventListener('click', saveTerminology);

    // 绑定语言选择事件，更新翻译方向指示器
    document.getElementById('source-lang').addEventListener('change', updateTranslationDirection);
    document.getElementById('target-lang').addEventListener('change', updateTranslationDirection);

    // 初始化翻译方向指示器
    updateTranslationDirection();

    // 导出/导入术语库
    document.getElementById('export-terminology').addEventListener('click', function() {
        exportTerminologyToExcel();
    });
    document.getElementById('import-terminology').addEventListener('click', importTerminologyFromExcel);

    // 系统日志相关事件处理
    document.getElementById('clear-logs').addEventListener('click', clearSystemLogs);
    document.getElementById('toggle-auto-scroll').addEventListener('click', toggleAutoScroll);

    // 监听系统日志滚动事件
    const systemLog = document.getElementById('system-log');
    systemLog.addEventListener('scroll', function() {
        // 如果用户手动滚动到底部，重新启用自动滚动
        if (systemLog.scrollHeight - systemLog.scrollTop === systemLog.clientHeight) {
            autoScrollEnabled = true;
            updateAutoScrollButton();
        } else if (autoScrollEnabled) {
            // 如果用户手动滚动到其他位置，禁用自动滚动
            autoScrollEnabled = false;
            updateAutoScrollButton();
        }
    });

    // 翻译器类型选择事件
    const translatorRadios = document.querySelectorAll('input[name="translator-type"]');
    translatorRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            setTranslatorType(this.value);
        });
    });

    // 添加Bootstrap模态框事件处理
    document.addEventListener('shown.bs.modal', function(event) {
        // 当模态框显示时，如果是任务进度模态框，滚动日志到底部
        if (event.target.id === 'task-progress-modal') {
            const logContainer = document.getElementById('task-log');
            if (logContainer) {
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
    });

    // 初始化翻译按钮状态
    updateTranslationButtonStatus('idle');

    // 添加全局测试函数（用于调试）
    window.testTranslationStatus = function(status) {
        console.log('测试状态标签功能，状态:', status);
        const button = document.getElementById('start-translation-btn');
        const statusBadge = document.getElementById('translation-status');

        console.log('按钮元素:', button);
        console.log('状态标签元素:', statusBadge);

        if (!button) {
            console.error('找不到翻译按钮元素');
            return;
        }

        if (!statusBadge) {
            console.error('找不到状态标签元素');
            return;
        }

        console.log('状态标签当前样式:', statusBadge.style.display);
        console.log('状态标签当前类名:', statusBadge.className);

        if (['idle', 'submitting', 'processing', 'completed', 'failed'].includes(status)) {
            updateTranslationButtonStatus(status);
            addSystemLog(`手动测试状态: ${status}`, 'info');

            // 再次检查状态
            setTimeout(() => {
                console.log('更新后状态标签样式:', statusBadge.style.display);
                console.log('更新后状态标签类名:', statusBadge.className);
                console.log('更新后状态标签内容:', statusBadge.innerHTML);
            }, 100);
        } else {
            console.log('可用状态: idle, submitting, processing, completed, failed');
        }
    };

    // 添加手动恢复按钮状态的函数
    window.resetTranslationButton = function() {
        console.log('手动重置翻译按钮状态');
        addSystemLog('手动重置翻译按钮状态', 'info');
        updateTranslationButtonStatus('idle');
    };

    // 初始化系统日志
    addSystemLog('系统初始化完成', 'info');
    addSystemLog('提示：可在浏览器控制台使用 testTranslationStatus("状态名") 测试状态显示', 'info');
    addSystemLog('提示：如果翻译按钮状态异常，可在控制台使用 resetTranslationButton() 手动恢复', 'info');
    addSystemLog('实时日志监控已启动', 'info');

    // 启动实时日志监控
    startRealtimeLogMonitoring();

    // 启动异常状态监控
    startExceptionMonitoring();
});

// 检查翻译器状态
async function checkTranslatorStatus() {
    const statusIndicator = document.getElementById('status-indicator');
    statusIndicator.textContent = '检查中...';

    // 重置状态图标
    document.querySelectorAll('#status-container .bi-circle-fill').forEach(icon => {
        icon.className = 'bi bi-circle-fill text-secondary';
    });

    // 重置状态文本
    document.getElementById('zhipuai-status').textContent = '智谱AI: 检查中...';
    document.getElementById('ollama-status').textContent = 'Ollama: 检查中...';
    document.getElementById('siliconflow-status').textContent = '硅基流动: 检查中...';
    document.getElementById('intranet-status').textContent = '内网OPENAI: 检查中...';

    try {
        const response = await fetch('/api/translators');
        const data = await response.json();

        // 更新翻译器选择状态
        document.getElementById(data.current).checked = true;

        // 更新可用状态
        let availableCount = 0;
        for (const [type, available] of Object.entries(data.available)) {
            let status, iconClass;

            if (available === null) {
                // 内网翻译器按需检测
                status = '按需检测';
                iconClass = 'bi bi-circle-fill text-warning';
            } else if (available) {
                status = '可用';
                iconClass = 'bi bi-circle-fill text-success';
                availableCount++;
            } else {
                status = '不可用';
                iconClass = 'bi bi-circle-fill text-danger';
            }

            const statusElement = document.getElementById(`${type}-status`);
            const iconElement = statusElement.previousElementSibling;

            statusElement.textContent = `${getTranslatorName(type)}: ${status}`;
            iconElement.className = iconClass;
        }

        // 更新总体状态
        if (availableCount > 0) {
            statusIndicator.textContent = `${availableCount} 个翻译服务可用`;
        } else {
            statusIndicator.textContent = '所有翻译服务不可用，请检查配置和网络';
        }

        // 加载模型列表
        loadModels();
    } catch (error) {
        statusIndicator.textContent = '检查失败: ' + error.message;

        // 更新状态为错误
        document.getElementById('zhipuai-status').textContent = '智谱AI: 检查失败';
        document.getElementById('ollama-status').textContent = 'Ollama: 检查失败';
        document.getElementById('siliconflow-status').textContent = '硅基流动: 检查失败';
        document.getElementById('intranet-status').textContent = '内网OPENAI: 检查失败';
    }
}

// 获取翻译器名称
function getTranslatorName(type) {
    const names = {
        'zhipuai': '智谱AI',
        'ollama': 'Ollama',
        'siliconflow': '硅基流动',
        'intranet': '内网OPENAI'
    };
    return names[type] || type;
}

// 设置翻译器类型
async function setTranslatorType(type) {
    try {
        const formData = new FormData();
        formData.append('translator_type', type);

        const response = await fetch('/api/translator/set', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // 加载对应的模型列表
            loadModels();
        } else {
            const data = await response.json();
            alert('设置翻译器失败: ' + data.detail);
        }
    } catch (error) {
        alert('设置翻译器出错: ' + error.message);
    }
}

// 加载模型列表
async function loadModels() {
    const modelSelect = document.getElementById('model-select');
    modelSelect.innerHTML = '<option value="">加载中...</option>';

    try {
        const response = await fetch('/api/models');
        const data = await response.json();

        modelSelect.innerHTML = '';
        data.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            if (model === data.current) {
                option.selected = true;
            }
            modelSelect.appendChild(option);
        });

        // 添加模型选择事件
        modelSelect.addEventListener('change', function() {
            setModel(this.value);
        });
    } catch (error) {
        modelSelect.innerHTML = '<option value="">加载失败</option>';
    }
}

// 设置模型
async function setModel(model) {
    try {
        const formData = new FormData();
        formData.append('model', model);

        const response = await fetch('/api/model/set', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const data = await response.json();
            alert('设置模型失败: ' + data.detail);
        }
    } catch (error) {
        alert('设置模型出错: ' + error.message);
    }
}

// WebSocket连接
let socket = null;
let clientId = null;
let currentTaskId = null;
let heartbeatInterval = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5; // 减少最大重连次数
let reconnectDelay = 5000; // 增加初始重连延迟到5秒
let maxLogEntries = 1000; // 最大日志条目数
let logLevels = ['debug', 'info', 'warning', 'error']; // 日志级别
let currentLogLevel = 'info'; // 当前日志级别
let lastLogTimestamp = null; // 最后一条日志的时间戳
let logPollingInterval = null; // 日志轮询定时器
let exceptionCount = 0; // 异常计数
let lastExceptionTime = null; // 最后一次异常时间
let isReconnecting = false; // 重连状态标志
let connectionStable = false; // 连接稳定性标志

// 初始化WebSocket连接
function initWebSocket() {
    // 如果正在重连，避免重复连接
    if (isReconnecting) {
        console.log('正在重连中，跳过新的连接请求');
        return;
    }

    // 生成唯一的客户端ID
    if (!clientId) {
        clientId = 'client_' + Math.random().toString(36).slice(2, 11);
    }

    // 关闭现有连接和心跳
    if (socket) {
        socket.close();
    }

    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }

    // 创建新连接
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;

    console.log(`尝试连接WebSocket: ${wsUrl}`);
    socket = new WebSocket(wsUrl);

    // 连接打开时
    socket.onopen = function() {
        console.log('WebSocket连接已建立');
        addSystemLog('实时日志连接已建立，系统日志将实时同步', 'success');

        // 重置重连状态
        reconnectAttempts = 0;
        reconnectDelay = 5000;
        isReconnecting = false;
        connectionStable = false;

        // 延迟启动心跳检测，确保连接稳定
        setTimeout(() => {
            connectionStable = true;
            startHeartbeat();
        }, 1000);
    };

    // 接收消息
    socket.onmessage = function(event) {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    // 连接关闭时
    socket.onclose = function(event) {
        connectionStable = false;

        // 停止心跳
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }

        if (event.wasClean) {
            console.log(`WebSocket连接已关闭，代码=${event.code} 原因=${event.reason}`);
            addSystemLog(`WebSocket连接已关闭: ${event.reason}`, 'warning');
            isReconnecting = false;
        } else {
            console.log('WebSocket连接意外断开');

            // 避免重复重连
            if (!isReconnecting && reconnectAttempts < maxReconnectAttempts) {
                isReconnecting = true;
                reconnectAttempts++;

                // 使用指数退避策略，避免过于频繁的重连
                const delay = Math.min(60000, reconnectDelay * Math.pow(2, reconnectAttempts - 1));
                console.log(`尝试第 ${reconnectAttempts} 次重连，延迟 ${delay}ms`);
                addSystemLog(`WebSocket连接意外断开，正在尝试重新连接...`, 'warning');

                setTimeout(() => {
                    initWebSocket();
                }, delay);
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                console.error(`已达到最大重连次数 (${maxReconnectAttempts})，停止重连`);
                addSystemLog(`WebSocket重连失败，已达到最大重连次数。请刷新页面重试。`, 'error');
                isReconnecting = false;
            }
        }
    };

    // 连接错误
    socket.onerror = function(error) {
        console.error('WebSocket错误:', error);
        // 只在连接稳定时记录错误，避免重连过程中的错误日志过多
        if (connectionStable) {
            addSystemLog('WebSocket连接错误', 'error');
        }
    };

    return socket;
}

// 启动心跳检测
function startHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }

    // 每30秒发送一次心跳，确保在后端超时前发送
    heartbeatInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN && connectionStable) {
            try {
                socket.send('ping');
                console.log('发送心跳包');
            } catch (error) {
                console.error('发送心跳包失败:', error);
                // 心跳发送失败，停止心跳检测
                clearInterval(heartbeatInterval);
                heartbeatInterval = null;
            }
        } else {
            // 如果连接已关闭或不稳定，停止心跳
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }, 30000); // 改为30秒，确保在后端70秒超时前发送
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log('收到WebSocket消息:', message);

    switch (message.type) {
        case 'task_created':
            // 任务创建通知
            currentTaskId = message.data.task_id;
            showTaskProgress(message.data);
            addSystemLog(`创建翻译任务: ${message.data.filename}`, 'info');
            break;

        case 'task_status':
            // 任务状态更新
            updateTaskProgress(message.data);

            // 更新翻译按钮状态
            console.log(`收到任务状态更新: ${message.data.status}, 任务ID: ${message.data.task_id}, 当前任务ID: ${currentTaskId}`);

            if (message.data.task_id === currentTaskId) {
                console.log(`任务ID匹配，更新按钮状态: ${message.data.status}`);
                if (message.data.status === 'completed') {
                    updateTranslationButtonStatus('completed');
                } else if (message.data.status === 'failed') {
                    updateTranslationButtonStatus('failed');
                } else if (message.data.status === 'processing') {
                    updateTranslationButtonStatus('processing');
                }
            } else {
                console.log(`任务ID不匹配，跳过按钮状态更新`);
            }

            // 添加到系统日志
            if (message.data.status === 'completed') {
                addSystemLog(`翻译任务完成: ${message.data.task_id}`, 'success');
                // 确保按钮状态正确更新（备用机制）
                if (message.data.task_id === currentTaskId) {
                    setTimeout(() => {
                        console.log('备用机制：确保按钮状态为完成状态');
                        updateTranslationButtonStatus('completed');
                    }, 100);
                }
            } else if (message.data.status === 'failed') {
                addSystemLog(`翻译任务失败: ${message.data.message || message.data.task_id}`, 'error');
                // 确保按钮状态正确更新（备用机制）
                if (message.data.task_id === currentTaskId) {
                    setTimeout(() => {
                        console.log('备用机制：确保按钮状态为失败状态');
                        updateTranslationButtonStatus('failed');
                    }, 100);
                }
            } else if (message.data.progress >= 0) {
                const progress = Math.round(message.data.progress * 100);
                if (progress % 10 === 0) { // 每10%记录一次进度，避免日志过多
                    addSystemLog(`翻译进度 ${progress}%: ${message.data.message || ''}`, 'info');
                }
            }
            break;

        case 'log':
            // 日志消息
            appendLogMessage(message.data);
            // 同时添加到系统日志
            addSystemLog(message.data, getLogLevel(message.data));
            break;

        case 'system_log':
            // 系统日志消息
            addSystemLog(message.data, getLogLevel(message.data));
            break;

        case 'pong':
            // 心跳响应，不需要特殊处理
            console.log('收到心跳响应');
            break;

        case 'echo':
            // 回显消息，不需要特殊处理
            console.log('收到回显消息:', message.data);
            break;

        default:
            console.log('未处理的消息类型:', message.type);
    }
}

// 根据日志内容判断日志级别
function getLogLevel(logMessage) {
    const lowerMsg = logMessage.toLowerCase();
    if (lowerMsg.includes('error') || lowerMsg.includes('错误') || lowerMsg.includes('失败')) {
        return 'error';
    } else if (lowerMsg.includes('warning') || lowerMsg.includes('警告')) {
        return 'warning';
    } else if (lowerMsg.includes('success') || lowerMsg.includes('成功') || lowerMsg.includes('完成')) {
        return 'success';
    } else {
        return 'info';
    }
}

// 显示任务进度界面
function showTaskProgress(taskData) {
    // 创建任务进度模态框
    if (!document.getElementById('task-progress-modal')) {
        const modalHtml = `
            <div class="modal fade" id="task-progress-modal" tabindex="-1" aria-labelledby="taskProgressModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="taskProgressModalLabel">翻译任务进度</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="task-info mb-3">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p><strong>文件名:</strong> <span id="task-filename"></span></p>
                                        <p><strong>任务ID:</strong> <span id="task-id"></span></p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>状态:</strong> <span id="task-status" class="badge bg-primary">处理中</span></p>
                                        <p><strong>进度:</strong> <span id="task-progress-text">0%</span></p>
                                    </div>
                                </div>
                                <div class="progress mb-3">
                                    <div id="task-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
                                         role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                                <div class="task-message alert alert-info" id="task-message">
                                    正在准备翻译任务...
                                </div>
                            </div>
                            <div class="card">
                                <div class="card-header bg-light">
                                    <h6 class="mb-0">翻译日志</h6>
                                </div>
                                <div class="card-body p-0">
                                    <div id="task-log" class="log-container p-3" style="height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.85rem; background-color: #f8f9fa;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            <a id="download-result" href="#" class="btn btn-primary d-none">下载结果</a>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加模态框到页面
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer.firstChild);
    }

    // 更新任务信息
    document.getElementById('task-filename').textContent = taskData.filename || '未知文件';
    document.getElementById('task-id').textContent = taskData.task_id;
    document.getElementById('task-status').textContent = getStatusText(taskData.status);
    document.getElementById('task-status').className = `badge ${getStatusInfo(taskData.status).badgeClass}`;
    document.getElementById('task-progress-text').textContent = '0%';
    document.getElementById('task-progress-bar').style.width = '0%';
    document.getElementById('task-progress-bar').setAttribute('aria-valuenow', '0');
    document.getElementById('task-message').textContent = '正在准备翻译任务...';
    document.getElementById('task-log').innerHTML = '';
    document.getElementById('download-result').classList.add('d-none');

    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('task-progress-modal'));
    modal.show();
}

// 更新任务进度
function updateTaskProgress(taskData) {
    // 更新状态
    const statusElement = document.getElementById('task-status');
    statusElement.textContent = getStatusText(taskData.status);
    statusElement.className = `badge ${getStatusInfo(taskData.status).badgeClass}`;

    // 更新进度条
    const progressPercent = Math.round(taskData.progress * 100);
    document.getElementById('task-progress-text').textContent = `${progressPercent}%`;
    document.getElementById('task-progress-bar').style.width = `${progressPercent}%`;
    document.getElementById('task-progress-bar').setAttribute('aria-valuenow', progressPercent);

    // 更新消息
    if (taskData.message) {
        document.getElementById('task-message').textContent = taskData.message;
    }

    // 如果任务完成，显示下载按钮
    if (taskData.status === 'completed' && taskData.output_file) {
        const downloadBtn = document.getElementById('download-result');
        downloadBtn.href = `/api/download/${taskData.task_id}`;
        downloadBtn.classList.remove('d-none');

        // 获取文件名（如果是完整路径，只显示文件名部分）
        const fileName = taskData.output_file.split(/[\/\\]/).pop();
        downloadBtn.textContent = `下载 ${fileName}`;

        // 添加下载事件处理
        downloadBtn.onclick = function() {
            // 显示下载中提示
            const taskMessage = document.getElementById('task-message');
            const originalMessage = taskMessage.textContent;
            taskMessage.textContent = `正在准备下载文件: ${fileName}...`;

            // 添加下载完成或失败的处理
            setTimeout(() => {
                taskMessage.textContent = originalMessage;
            }, 3000);
        };

        // 更新进度条样式
        document.getElementById('task-progress-bar').classList.remove('progress-bar-animated');
        document.getElementById('task-progress-bar').classList.remove('progress-bar-striped');
        document.getElementById('task-progress-bar').classList.add('bg-success');

        // 刷新任务列表
        loadTasks();
    }

    // 如果任务失败，更新进度条样式
    if (taskData.status === 'failed') {
        document.getElementById('task-progress-bar').classList.remove('progress-bar-animated');
        document.getElementById('task-progress-bar').classList.remove('progress-bar-striped');
        document.getElementById('task-progress-bar').classList.add('bg-danger');

        // 刷新任务列表
        loadTasks();
    }
}

// 添加日志消息到任务日志
function appendLogMessage(logMessage) {
    const logContainer = document.getElementById('task-log');
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = logMessage;

    // 添加日志条目
    logContainer.appendChild(logEntry);

    // 滚动到底部
    logContainer.scrollTop = logContainer.scrollHeight;
}

// 添加日志到系统日志区域
function addSystemLog(message, level = 'info') {
    const systemLog = document.getElementById('system-log');

    // 检查日志级别过滤
    if (logLevels.indexOf(level) < logLevels.indexOf(currentLogLevel)) {
        return;
    }

    // 如果是第一条日志，清除占位内容
    if (systemLog.querySelector('.text-center.text-muted')) {
        systemLog.innerHTML = '';
    }

    // 创建日志条目
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    logEntry.dataset.level = level;

    // 处理不同格式的日志消息
    let timestamp, content;

    // 检查是否是后端格式的日志（包含时间戳、级别和消息）
    const backendLogPattern = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?) - (\w+) - (.+)$/;
    const match = typeof message === 'string' ? message.match(backendLogPattern) : null;

    if (match) {
        // 如果是后端格式的日志，提取时间戳、级别和消息
        const [_, timestampStr, logLevel, logMessage] = match;

        // 添加时间戳
        timestamp = document.createElement('span');
        timestamp.className = 'log-entry-timestamp';
        timestamp.textContent = timestampStr;
        logEntry.appendChild(timestamp);

        // 添加级别标记
        const levelSpan = document.createElement('span');
        levelSpan.className = `log-level ${logLevel.toLowerCase()}`;
        levelSpan.textContent = `[${logLevel}] `;
        logEntry.appendChild(levelSpan);

        // 添加日志内容
        content = document.createTextNode(logMessage);
        logEntry.appendChild(content);

        // 根据日志级别更新条目样式
        if (logLevel.toLowerCase() === 'error') {
            logEntry.className = 'log-entry error';
        } else if (logLevel.toLowerCase() === 'warning') {
            logEntry.className = 'log-entry warning';
        } else if (logLevel.toLowerCase() === 'info') {
            logEntry.className = 'log-entry info';
        } else if (logLevel.toLowerCase() === 'debug') {
            logEntry.className = 'log-entry debug';
        }
    } else {
        // 如果是前端格式的日志，使用当前时间作为时间戳
        timestamp = document.createElement('span');
        timestamp.className = 'log-entry-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        logEntry.appendChild(timestamp);

        // 添加日志内容
        content = document.createTextNode(message);
        logEntry.appendChild(content);
    }

    // 添加到日志容器
    systemLog.appendChild(logEntry);

    // 如果启用了自动滚动，则滚动到底部
    if (autoScrollEnabled) {
        systemLog.scrollTop = systemLog.scrollHeight;
    }

    // 限制日志条目数量，避免内存占用过多
    const entries = systemLog.querySelectorAll('.log-entry');
    if (entries.length > maxLogEntries) {
        // 删除最旧的日志条目
        const removeCount = entries.length - maxLogEntries;
        for (let i = 0; i < removeCount; i++) {
            systemLog.removeChild(entries[i]);
        }

        // 添加日志清理提示
        const cleanupMsg = document.createElement('div');
        cleanupMsg.className = 'log-entry info';
        cleanupMsg.textContent = `已清理 ${removeCount} 条旧日志`;
        systemLog.insertBefore(cleanupMsg, systemLog.firstChild);
    }
}

// 清空系统日志
function clearSystemLogs() {
    const systemLog = document.getElementById('system-log');
    const logCount = systemLog.querySelectorAll('.log-entry').length;

    systemLog.innerHTML = `
        <div class="text-center text-muted py-5">
            <i class="bi bi-terminal" style="font-size: 2rem;"></i>
            <p class="mt-2">系统日志已清空</p>
            <p class="text-muted small">已清除 ${logCount} 条日志记录</p>
        </div>
    `;

    // 记录清理操作
    const timestamp = new Date().toLocaleTimeString();
    addSystemLog(`[${timestamp}] 系统日志已清空，共清除 ${logCount} 条日志`, 'info');
}

// 切换自动滚动
function toggleAutoScroll() {
    autoScrollEnabled = !autoScrollEnabled;
    updateAutoScrollButton();

    // 如果启用了自动滚动，立即滚动到底部
    if (autoScrollEnabled) {
        const systemLog = document.getElementById('system-log');
        systemLog.scrollTop = systemLog.scrollHeight;
    }

    addSystemLog(`自动滚动已${autoScrollEnabled ? '启用' : '禁用'}`, 'info');
}

// 更新自动滚动按钮状态
function updateAutoScrollButton() {
    const button = document.getElementById('toggle-auto-scroll');
    if (autoScrollEnabled) {
        button.innerHTML = '<i class="bi bi-arrow-down-circle-fill"></i> 自动滚动';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-primary');
    } else {
        button.innerHTML = '<i class="bi bi-arrow-down-circle"></i> 自动滚动';
        button.classList.remove('btn-primary');
        button.classList.add('btn-outline-primary');
    }
}

// 更新翻译按钮状态
function updateTranslationButtonStatus(status) {
    const button = document.getElementById('start-translation-btn');
    const statusBadge = document.getElementById('translation-status');

    if (!button || !statusBadge) {
        console.error('翻译按钮或状态标签元素未找到');
        return;
    }

    // 清除之前的定时器
    if (buttonStatusTimeout) {
        clearTimeout(buttonStatusTimeout);
        buttonStatusTimeout = null;
    }

    console.log(`更新翻译按钮状态: ${status}`);

    switch (status) {
        case 'idle':
            // 空闲状态
            button.disabled = false;
            button.className = 'btn btn-success btn-icon';
            button.innerHTML = '<i class="bi bi-play-fill"></i> 开始翻译';
            statusBadge.className = 'badge bg-secondary';
            statusBadge.style.display = 'none';
            statusBadge.innerHTML = '<i class="bi bi-hourglass-split"></i> 准备中...';
            currentTaskId = null; // 清除当前任务ID
            break;

        case 'submitting':
            // 提交中状态
            button.disabled = true;
            button.className = 'btn btn-warning btn-icon';
            button.innerHTML = '<i class="bi bi-hourglass-split"></i> 提交中...';
            statusBadge.className = 'badge bg-warning';
            statusBadge.style.display = 'inline-block';
            statusBadge.innerHTML = '<i class="bi bi-upload"></i> 正在提交任务...';
            break;

        case 'processing':
            // 处理中状态
            button.disabled = true;
            button.className = 'btn btn-primary btn-icon';
            button.innerHTML = '<i class="bi bi-arrow-repeat"></i> 翻译中...';
            statusBadge.className = 'badge bg-primary';
            statusBadge.style.display = 'inline-block';
            statusBadge.innerHTML = '<i class="bi bi-gear-fill"></i> 正在翻译文档...';
            break;

        case 'completed':
            // 完成状态
            button.disabled = false;
            button.className = 'btn btn-success btn-icon';
            button.innerHTML = '<i class="bi bi-check-circle-fill"></i> 翻译完成';
            statusBadge.className = 'badge bg-success';
            statusBadge.style.display = 'inline-block';
            statusBadge.innerHTML = '<i class="bi bi-check-circle-fill"></i> 翻译已完成';

            // 记录状态变化
            addSystemLog('翻译任务已完成，3秒后恢复按钮状态', 'success');

            // 3秒后恢复到空闲状态
            buttonStatusTimeout = setTimeout(() => {
                console.log('定时器触发：恢复按钮到空闲状态');
                updateTranslationButtonStatus('idle');
            }, 3000);
            break;

        case 'failed':
            // 失败状态
            button.disabled = false;
            button.className = 'btn btn-danger btn-icon';
            button.innerHTML = '<i class="bi bi-x-circle-fill"></i> 翻译失败';
            statusBadge.className = 'badge bg-danger';
            statusBadge.style.display = 'inline-block';
            statusBadge.innerHTML = '<i class="bi bi-x-circle-fill"></i> 翻译失败';

            // 记录状态变化
            addSystemLog('翻译任务失败，5秒后恢复按钮状态', 'error');

            // 5秒后恢复到空闲状态
            buttonStatusTimeout = setTimeout(() => {
                console.log('定时器触发：恢复按钮到空闲状态');
                updateTranslationButtonStatus('idle');
            }, 5000);
            break;

        default:
            // 默认空闲状态
            console.log('未知状态，恢复到空闲状态');
            updateTranslationButtonStatus('idle');
    }
}

// 提交翻译任务
async function submitTranslation(event) {
    event.preventDefault();

    const fileInput = document.getElementById('file-upload');
    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;
    const useTerminology = document.getElementById('use-terminology').checked;
    const preprocessTerms = document.getElementById('preprocess-terms').checked;
    const exportPdf = document.getElementById('export-pdf').checked;
    const outputFormat = document.querySelector('input[name="output-format"]:checked').value;

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('请选择要翻译的文件');
        return;
    }

    // 更新按钮状态为提交中
    addSystemLog('用户点击开始翻译按钮', 'info');
    updateTranslationButtonStatus('submitting');

    // 确保WebSocket连接已初始化
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        initWebSocket();
    }

    // 确定翻译方向
    const translationDirection = document.getElementById('translation-direction').textContent;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('source_lang', sourceLang);
    formData.append('target_lang', targetLang);
    formData.append('use_terminology', useTerminology);
    formData.append('preprocess_terms', preprocessTerms);
    formData.append('export_pdf', exportPdf);
    formData.append('output_format', outputFormat);
    formData.append('client_id', clientId);  // 添加客户端ID
    formData.append('translation_direction', translationDirection);  // 添加翻译方向

    try {
        const response = await fetch('/api/translate', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            currentTaskId = data.task_id;
            console.log(`翻译任务已提交，任务ID: ${currentTaskId}`);

            // 更新按钮状态为处理中
            updateTranslationButtonStatus('processing');

            // 设置备用定时器，如果30秒后仍未收到完成或失败消息，则恢复按钮状态
            setTimeout(() => {
                const button = document.getElementById('start-translation-btn');
                if (button && button.disabled) {
                    console.log('备用定时器触发：30秒未收到任务完成消息，恢复按钮状态');
                    addSystemLog('翻译任务超时，恢复按钮状态。如果翻译仍在进行，请查看任务列表。', 'warning');
                    updateTranslationButtonStatus('idle');
                }
            }, 30000); // 30秒超时

            // 重置表单
            document.getElementById('translation-form').reset();

            // 恢复默认选项
            document.getElementById('use-terminology').checked = true;
            document.getElementById('preprocess-terms').checked = false;
            document.getElementById('export-pdf').checked = false;
            document.getElementById('bilingual').checked = true;

            // 刷新任务列表
            loadTasks();
        } else {
            const data = await response.json();
            alert('提交翻译任务失败: ' + data.detail);
            // 恢复按钮状态
            updateTranslationButtonStatus('idle');
        }
    } catch (error) {
        alert('提交翻译任务出错: ' + error.message);
        // 恢复按钮状态
        updateTranslationButtonStatus('idle');
    }
}

// 加载任务列表
async function loadTasks() {
    const tableBody = document.getElementById('tasks-table-body');
    tableBody.innerHTML = `
        <tr>
            <td colspan="4" class="text-center">
                <div class="py-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="mt-2">加载中...</p>
                </div>
            </td>
        </tr>
    `;

    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();

        if (tasks.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">
                        <div class="py-3">
                            <i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i>
                            <p class="mt-2 text-muted">暂无任务</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = '';
        tasks.forEach(task => {
            const row = document.createElement('tr');

            // 文件名
            const fileCell = document.createElement('td');
            const fileIcon = getFileIcon(task.filename);
            fileCell.innerHTML = `<i class="${fileIcon} me-2"></i> ${task.filename}`;
            row.appendChild(fileCell);

            // 状态
            const statusCell = document.createElement('td');
            const statusInfo = getStatusInfo(task.status);
            statusCell.innerHTML = `<span class="badge ${statusInfo.badgeClass}">${statusInfo.icon} ${getStatusText(task.status)}</span>`;
            row.appendChild(statusCell);

            // 进度
            const progressCell = document.createElement('td');
            const progressBar = document.createElement('div');
            progressBar.className = 'progress';

            // 根据状态设置进度条颜色
            let progressClass = 'bg-primary';
            if (task.status === 'completed') progressClass = 'bg-success';
            if (task.status === 'failed') progressClass = 'bg-danger';

            progressBar.innerHTML = `
                <div class="progress-bar ${progressClass}" role="progressbar"
                     style="width: ${task.progress * 100}%"
                     aria-valuenow="${task.progress * 100}"
                     aria-valuemin="0" aria-valuemax="100">
                    ${Math.round(task.progress * 100)}%
                </div>
            `;
            progressCell.appendChild(progressBar);
            row.appendChild(progressCell);

            // 操作
            const actionCell = document.createElement('td');
            if (task.status === 'completed' && task.output_file) {
                const downloadBtn = document.createElement('a');
                downloadBtn.href = `/api/download/${task.task_id}`;
                downloadBtn.className = 'btn btn-sm btn-primary btn-icon';

                // 获取文件名（如果是完整路径，只显示文件名部分）
                const fileName = task.output_file.split(/[\/\\]/).pop();
                downloadBtn.innerHTML = '<i class="bi bi-download"></i> 下载';
                downloadBtn.title = `下载 ${fileName}`;

                // 添加下载事件处理
                downloadBtn.addEventListener('click', function() {
                    // 显示下载中提示
                    const statusCell = row.querySelector('td:nth-child(2)');
                    if (statusCell) {
                        const originalText = statusCell.innerHTML;
                        statusCell.innerHTML = '<span class="badge bg-info">准备下载...</span>';

                        // 3秒后恢复原状态
                        setTimeout(() => {
                            statusCell.innerHTML = originalText;
                        }, 3000);
                    }
                });

                actionCell.appendChild(downloadBtn);

                // 添加查看状态按钮
                const statusBtn = document.createElement('button');
                statusBtn.className = 'btn btn-sm btn-outline-secondary btn-icon ms-1';
                statusBtn.innerHTML = '<i class="bi bi-info-circle"></i>';
                statusBtn.title = '查看详情';
                statusBtn.onclick = function() {
                    checkTaskStatus(task.task_id);
                };
                actionCell.appendChild(statusBtn);
            } else {
                const statusBtn = document.createElement('button');
                statusBtn.className = 'btn btn-sm btn-secondary btn-icon';
                statusBtn.innerHTML = '<i class="bi bi-info-circle"></i> 查看状态';
                statusBtn.onclick = function() {
                    checkTaskStatus(task.task_id);
                };
                actionCell.appendChild(statusBtn);
            }
            row.appendChild(actionCell);

            tableBody.appendChild(row);
        });
    } catch (error) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center">
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle-fill"></i> 加载任务失败: ${error.message}
                    </div>
                </td>
            </tr>
        `;
    }
}

// 根据文件名获取图标
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();

    const iconMap = {
        'docx': 'bi bi-file-earmark-word text-primary',
        'doc': 'bi bi-file-earmark-word text-primary',
        'pdf': 'bi bi-file-earmark-pdf text-danger',
        'xlsx': 'bi bi-file-earmark-excel text-success',
        'xls': 'bi bi-file-earmark-excel text-success',
        'txt': 'bi bi-file-earmark-text text-secondary',
        'md': 'bi bi-file-earmark-text text-secondary',
        'json': 'bi bi-file-earmark-code text-dark',
        'xml': 'bi bi-file-earmark-code text-dark',
        'html': 'bi bi-file-earmark-code text-dark',
        'css': 'bi bi-file-earmark-code text-dark',
        'js': 'bi bi-file-earmark-code text-dark'
    };

    return iconMap[ext] || 'bi bi-file-earmark';
}

// 获取状态信息
function getStatusInfo(status) {
    const statusMap = {
        'pending': {
            badgeClass: 'bg-secondary',
            icon: '<i class="bi bi-hourglass"></i>'
        },
        'processing': {
            badgeClass: 'bg-primary',
            icon: '<i class="bi bi-arrow-repeat"></i>'
        },
        'completed': {
            badgeClass: 'bg-success',
            icon: '<i class="bi bi-check-circle"></i>'
        },
        'failed': {
            badgeClass: 'bg-danger',
            icon: '<i class="bi bi-x-circle"></i>'
        }
    };

    return statusMap[status] || { badgeClass: 'bg-secondary', icon: '<i class="bi bi-question-circle"></i>' };
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

// 检查任务状态
async function checkTaskStatus(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const task = await response.json();

        alert(`任务状态: ${getStatusText(task.status)}\n进度: ${Math.round(task.progress * 100)}%`);
    } catch (error) {
        alert('获取任务状态失败: ' + error.message);
    }
}

// 更新翻译方向指示器
function updateTranslationDirection() {
    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;
    const directionIndicator = document.getElementById('translation-direction');

    // 根据源语言和目标语言确定翻译方向
    if (sourceLang === 'zh' || (sourceLang === 'auto' && targetLang !== 'zh')) {
        // 中文 → 外语
        directionIndicator.textContent = '中文→外语';
        directionIndicator.className = 'badge bg-info mt-1';
    } else {
        // 外语 → 中文
        directionIndicator.textContent = '外语→中文';
        directionIndicator.className = 'badge bg-warning mt-1';
    }

    // 如果源语言和目标语言相同，显示警告
    if (sourceLang !== 'auto' && sourceLang === targetLang) {
        directionIndicator.textContent = '源语言=目标语言';
        directionIndicator.className = 'badge bg-danger mt-1';
    }
}

// 当前选中的语言
let currentLanguage = '';

// 加载术语库
async function loadTerminology() {
    try {
        // 获取术语库编辑区域
        const terminologyEditor = document.getElementById('terminology-editor');

        // 清空编辑区域
        terminologyEditor.innerHTML = '';

        // 创建主布局
        const mainContainer = document.createElement('div');
        mainContainer.className = 'row';
        terminologyEditor.appendChild(mainContainer);

        // 创建左侧语言列表面板
        const leftPanel = document.createElement('div');
        leftPanel.className = 'col-md-3 mb-4';
        mainContainer.appendChild(leftPanel);

        // 创建右侧术语编辑面板
        const rightPanel = document.createElement('div');
        rightPanel.className = 'col-md-9';
        rightPanel.id = 'terminology-content';
        mainContainer.appendChild(rightPanel);

        // 创建语言列表卡片
        const langCard = document.createElement('div');
        langCard.className = 'card h-100';
        leftPanel.appendChild(langCard);

        const langCardHeader = document.createElement('div');
        langCardHeader.className = 'card-header bg-primary bg-opacity-10';
        langCardHeader.innerHTML = '<h5><i class="bi bi-translate"></i> 语言列表</h5>';
        langCard.appendChild(langCardHeader);

        const langCardBody = document.createElement('div');
        langCardBody.className = 'card-body';
        langCard.appendChild(langCardBody);

        // 创建语言列表
        const langList = document.createElement('div');
        langList.className = 'list-group';
        langList.id = 'language-list';
        langCardBody.appendChild(langList);

        // 添加新语言按钮
        const addLangButton = document.createElement('button');
        addLangButton.className = 'btn btn-outline-primary mt-3 w-100';
        addLangButton.innerHTML = '<i class="bi bi-plus-circle"></i> 添加新语言';
        addLangButton.onclick = addNewLanguage;
        langCardBody.appendChild(addLangButton);

        // 创建状态栏（在加载语言列表之前创建，确保元素存在）
        const statusBar = document.createElement('div');
        statusBar.className = 'alert alert-light mt-3 mb-0';
        statusBar.id = 'terminology-status';
        statusBar.textContent = '正在加载术语库...';
        terminologyEditor.appendChild(statusBar);

        // 加载语言列表
        await loadLanguageList();

    } catch (error) {
        const terminologyEditor = document.getElementById('terminology-editor');
        terminologyEditor.innerHTML = `<div class="alert alert-danger">加载术语库失败: ${error.message}</div>`;
    }
}

// 加载语言列表
async function loadLanguageList() {
    try {
        // 获取语言列表
        const response = await fetch('/api/terminology/languages');
        const data = await response.json();
        const languages = data.languages;

        // 获取语言列表元素
        const langList = document.getElementById('language-list');
        langList.innerHTML = '';

        // 如果没有语言
        if (languages.length === 0) {
            const emptyItem = document.createElement('div');
            emptyItem.className = 'list-group-item text-muted';
            emptyItem.textContent = '暂无语言';
            langList.appendChild(emptyItem);
            return;
        }

        // 添加语言到列表
        languages.forEach(lang => {
            const langItem = document.createElement('button');
            langItem.type = 'button';
            langItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            langItem.textContent = lang;

            // 添加删除按钮
            const deleteBtn = document.createElement('span');
            deleteBtn.className = 'badge bg-danger rounded-pill';
            deleteBtn.innerHTML = '<i class="bi bi-x"></i>';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                if (confirm(`确定要删除 "${lang}" 语言及其所有术语吗？`)) {
                    deleteLanguage(lang);
                }
            };
            langItem.appendChild(deleteBtn);

            // 点击语言项加载对应术语
            langItem.onclick = () => loadTermsForLanguage(lang);

            langList.appendChild(langItem);
        });

        // 如果有当前选中的语言，保持选中状态
        if (currentLanguage && languages.includes(currentLanguage)) {
            loadTermsForLanguage(currentLanguage);
        } else if (languages.length > 0) {
            // 否则选择第一个语言
            loadTermsForLanguage(languages[0]);
        } else {
            // 如果没有语言，更新状态栏
            const statusBar = document.getElementById('terminology-status');
            if (statusBar) {
                statusBar.textContent = '暂无术语库，请添加新语言或导入术语库';
                statusBar.className = 'alert alert-warning mt-3 mb-0';
            }
        }

    } catch (error) {
        console.error('加载语言列表失败:', error);
        const langList = document.getElementById('language-list');
        langList.innerHTML = `<div class="list-group-item text-danger">加载失败: ${error.message}</div>`;
    }
}

// 加载指定语言的术语
async function loadTermsForLanguage(language) {
    try {
        // 更新当前语言
        currentLanguage = language;

        // 更新语言列表选中状态
        const langItems = document.querySelectorAll('#language-list .list-group-item');
        langItems.forEach(item => {
            if (item.textContent.includes(language)) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // 获取术语内容区域
        const contentArea = document.getElementById('terminology-content');
        contentArea.innerHTML = '<div class="text-center my-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">加载中...</p></div>';

        // 获取指定语言的术语
        const response = await fetch(`/api/terminology/${language}`);
        const data = await response.json();
        const terms = data.terms;

        // 清空内容区域
        contentArea.innerHTML = '';

        // 创建术语卡片
        const termCard = document.createElement('div');
        termCard.className = 'card';
        contentArea.appendChild(termCard);

        const termCardHeader = document.createElement('div');
        termCardHeader.className = 'card-header bg-success bg-opacity-10 d-flex justify-content-between align-items-center';
        termCardHeader.innerHTML = `<h5><i class="bi bi-book"></i> ${language}术语库</h5>`;
        termCard.appendChild(termCardHeader);

        // 添加工具栏
        const toolbar = document.createElement('div');
        toolbar.className = 'btn-group';
        termCardHeader.appendChild(toolbar);

        // 添加术语按钮
        const addButton = document.createElement('button');
        addButton.className = 'btn btn-sm btn-success';
        addButton.innerHTML = '<i class="bi bi-plus-circle"></i> 添加术语';
        addButton.onclick = () => addNewTerm(language);
        toolbar.appendChild(addButton);

        // 导入按钮
        const importButton = document.createElement('button');
        importButton.className = 'btn btn-sm btn-outline-primary';
        importButton.innerHTML = '<i class="bi bi-upload"></i> 导入';
        importButton.onclick = () => importTerminology(language);
        toolbar.appendChild(importButton);

        // 导出按钮
        const exportButton = document.createElement('button');
        exportButton.className = 'btn btn-sm btn-outline-secondary';
        exportButton.innerHTML = '<i class="bi bi-download"></i> 导出';
        exportButton.onclick = function() {
            exportTerminologyToExcel(language);
        };
        toolbar.appendChild(exportButton);

        const termCardBody = document.createElement('div');
        termCardBody.className = 'card-body';
        termCard.appendChild(termCardBody);

        // 添加搜索框
        const searchDiv = document.createElement('div');
        searchDiv.className = 'input-group mb-3';
        termCardBody.appendChild(searchDiv);

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'form-control';
        searchInput.placeholder = '搜索术语...';
        searchInput.id = 'terminology-search';
        searchInput.oninput = filterTerminology;
        searchDiv.appendChild(searchInput);

        const searchButton = document.createElement('button');
        searchButton.className = 'btn btn-outline-secondary';
        searchButton.type = 'button';
        searchButton.innerHTML = '<i class="bi bi-search"></i>';
        searchDiv.appendChild(searchButton);

        // 如果术语为空
        if (Object.keys(terms).length === 0) {
            const emptyAlert = document.createElement('div');
            emptyAlert.className = 'alert alert-light text-center';
            emptyAlert.innerHTML = `<i class="bi bi-info-circle me-2"></i>${language}术语库为空，请添加术语`;
            termCardBody.appendChild(emptyAlert);
        } else {
            // 创建术语表格
            const tableResponsive = document.createElement('div');
            tableResponsive.className = 'table-responsive';
            termCardBody.appendChild(tableResponsive);

            const table = document.createElement('table');
            table.className = 'table table-striped table-hover';
            table.id = 'terminology-table';
            tableResponsive.appendChild(table);

            // 创建表头
            const thead = document.createElement('thead');
            thead.className = 'table-light';
            const headerRow = document.createElement('tr');

            const sourceHeader = document.createElement('th');
            sourceHeader.textContent = '中文术语';
            sourceHeader.style.width = '40%';
            sourceHeader.className = 'sortable';
            sourceHeader.onclick = () => sortTable(0);
            headerRow.appendChild(sourceHeader);

            const targetHeader = document.createElement('th');
            targetHeader.textContent = `${language}术语`;
            targetHeader.style.width = '40%';
            targetHeader.className = 'sortable';
            targetHeader.onclick = () => sortTable(1);
            headerRow.appendChild(targetHeader);

            const actionHeader = document.createElement('th');
            actionHeader.textContent = '操作';
            actionHeader.style.width = '20%';
            headerRow.appendChild(actionHeader);

            thead.appendChild(headerRow);
            table.appendChild(thead);

            // 创建表格内容
            const tbody = document.createElement('tbody');
            tbody.id = 'terminology-tbody';
            table.appendChild(tbody);

            // 添加术语到表格
            for (const [source, target] of Object.entries(terms)) {
                addTermToTable(tbody, source, target, language);
            }
        }

        // 更新状态栏
        updateStatusBar(language, Object.keys(terms).length);

        // 添加右键菜单
        setupContextMenu();

    } catch (error) {
        console.error(`加载${language}术语库失败:`, error);
        const contentArea = document.getElementById('terminology-content');
        contentArea.innerHTML = `<div class="alert alert-danger">加载${language}术语库失败: ${error.message}</div>`;
    }
}

// 添加术语到表格
function addTermToTable(tbody, source, target, language) {
    const row = document.createElement('tr');
    row.dataset.source = source;
    row.dataset.target = target;

    const sourceCell = document.createElement('td');
    sourceCell.textContent = source;
    row.appendChild(sourceCell);

    const targetCell = document.createElement('td');
    targetCell.textContent = target;
    row.appendChild(targetCell);

    const actionCell = document.createElement('td');

    // 编辑按钮
    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-sm btn-outline-primary me-1';
    editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
    editBtn.title = '编辑';
    editBtn.onclick = function() {
        editTerm(language, source, target);
    };
    actionCell.appendChild(editBtn);

    // 复制按钮
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn btn-sm btn-outline-secondary me-1';
    copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
    copyBtn.title = '复制';
    copyBtn.onclick = function() {
        copyTerm(source, target);
    };
    actionCell.appendChild(copyBtn);

    // 删除按钮
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-sm btn-outline-danger';
    deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
    deleteBtn.title = '删除';
    deleteBtn.onclick = function() {
        deleteTerm(language, source);
    };
    actionCell.appendChild(deleteBtn);

    row.appendChild(actionCell);
    tbody.appendChild(row);
}

// 更新状态栏
function updateStatusBar(language, count) {
    const statusBar = document.getElementById('terminology-status');
    if (statusBar) {
        statusBar.textContent = `${language}术语库中共有 ${count} 个术语`;
    } else {
        console.warn('术语库状态栏元素未找到，跳过状态更新');
    }
}

// 过滤术语库
function filterTerminology() {
    const searchText = document.getElementById('terminology-search').value.toLowerCase();
    const table = document.getElementById('terminology-table');
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const sourceText = rows[i].getElementsByTagName('td')[0].textContent.toLowerCase();
        const targetText = rows[i].getElementsByTagName('td')[1].textContent.toLowerCase();

        if (sourceText.includes(searchText) || targetText.includes(searchText)) {
            rows[i].style.display = '';
        } else {
            rows[i].style.display = 'none';
        }
    }
}

// 添加新语言
function addNewLanguage() {
    // 创建模态框
    const modalId = 'addLanguageModal';
    let modal = document.getElementById(modalId);

    if (!modal) {
        // 创建模态框
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = modalId;
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', `${modalId}Label`);
        modal.setAttribute('aria-hidden', 'true');

        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">添加新语言</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addLanguageForm">
                            <div class="mb-3">
                                <label for="languageNameInput" class="form-label">语言名称</label>
                                <input type="text" class="form-control" id="languageNameInput" required placeholder="例如：英语、日语、法语...">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" id="saveNewLanguageBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定保存按钮事件
        document.getElementById('saveNewLanguageBtn').addEventListener('click', function() {
            const languageName = document.getElementById('languageNameInput').value.trim();

            if (languageName) {
                saveNewLanguage(languageName);
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
            } else {
                alert('请输入语言名称');
            }
        });
    }

    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();

    // 清空输入框
    document.getElementById('languageNameInput').value = '';
}

// 保存新语言
async function saveNewLanguage(language) {
    try {
        // 获取当前术语库
        const response = await fetch('/api/terminology');
        const data = await response.json();
        const terminology = data.terminology;

        // 检查语言是否已存在
        if (terminology[language]) {
            alert(`语言 "${language}" 已存在`);
            return;
        }

        // 添加新语言
        terminology[language] = {};

        // 保存更新后的术语库
        const saveResponse = await fetch('/api/terminology', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(terminology)
        });

        if (saveResponse.ok) {
            // 重新加载语言列表
            await loadLanguageList();
            // 选择新添加的语言
            loadTermsForLanguage(language);
        } else {
            const errorData = await saveResponse.json();
            throw new Error(errorData.detail || '保存失败');
        }
    } catch (error) {
        alert('添加语言失败: ' + error.message);
    }
}

// 删除语言
async function deleteLanguage(language) {
    try {
        // 获取当前术语库
        const response = await fetch('/api/terminology');
        const data = await response.json();
        const terminology = data.terminology;

        // 删除语言
        delete terminology[language];

        // 保存更新后的术语库
        const saveResponse = await fetch('/api/terminology', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(terminology)
        });

        if (saveResponse.ok) {
            // 重新加载语言列表
            await loadLanguageList();
        } else {
            const errorData = await saveResponse.json();
            throw new Error(errorData.detail || '保存失败');
        }
    } catch (error) {
        alert('删除语言失败: ' + error.message);
    }
}

// 添加新术语
function addNewTerm(language) {
    // 创建模态框
    const modalId = 'addTermModal';
    let modal = document.getElementById(modalId);

    if (!modal) {
        // 创建模态框
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = modalId;
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', `${modalId}Label`);
        modal.setAttribute('aria-hidden', 'true');

        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">添加新术语</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addTermForm">
                            <input type="hidden" id="termLanguage">
                            <div class="mb-3">
                                <label for="sourceTermInput" class="form-label">中文术语</label>
                                <input type="text" class="form-control" id="sourceTermInput" required>
                            </div>
                            <div class="mb-3">
                                <label for="targetTermInput" class="form-label" id="targetTermLabel">目标术语</label>
                                <input type="text" class="form-control" id="targetTermInput" required>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" id="saveNewTermBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定保存按钮事件
        document.getElementById('saveNewTermBtn').addEventListener('click', function() {
            const language = document.getElementById('termLanguage').value;
            const sourceTerm = document.getElementById('sourceTermInput').value.trim();
            const targetTerm = document.getElementById('targetTermInput').value.trim();

            if (sourceTerm && targetTerm) {
                saveNewTerm(language, sourceTerm, targetTerm);
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
            } else {
                alert('请填写完整的术语信息');
            }
        });
    }

    // 更新语言相关信息
    document.getElementById('termLanguage').value = language;
    document.getElementById('targetTermLabel').textContent = `${language}术语`;

    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();

    // 清空输入框
    document.getElementById('sourceTermInput').value = '';
    document.getElementById('targetTermInput').value = '';
}

// 编辑术语
function editTerm(language, source, target) {
    // 创建模态框
    const modalId = 'editTermModal';
    let modal = document.getElementById(modalId);

    if (!modal) {
        // 创建模态框
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = modalId;
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', `${modalId}Label`);
        modal.setAttribute('aria-hidden', 'true');

        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">编辑术语</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editTermForm">
                            <input type="hidden" id="editTermLanguage">
                            <input type="hidden" id="originalSourceTerm">
                            <div class="mb-3">
                                <label for="editSourceTermInput" class="form-label">中文术语</label>
                                <input type="text" class="form-control" id="editSourceTermInput" required>
                            </div>
                            <div class="mb-3">
                                <label for="editTargetTermInput" class="form-label" id="editTargetTermLabel">目标术语</label>
                                <input type="text" class="form-control" id="editTargetTermInput" required>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" id="saveEditTermBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定保存按钮事件
        document.getElementById('saveEditTermBtn').addEventListener('click', function() {
            const language = document.getElementById('editTermLanguage').value;
            const originalSource = document.getElementById('originalSourceTerm').value;
            const sourceTerm = document.getElementById('editSourceTermInput').value.trim();
            const targetTerm = document.getElementById('editTargetTermInput').value.trim();

            if (sourceTerm && targetTerm) {
                updateTerm(language, originalSource, sourceTerm, targetTerm);
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
            } else {
                alert('请填写完整的术语信息');
            }
        });
    }

    // 更新语言相关信息
    document.getElementById('editTermLanguage').value = language;
    document.getElementById('editTargetTermLabel').textContent = `${language}术语`;

    // 填充数据
    document.getElementById('originalSourceTerm').value = source;
    document.getElementById('editSourceTermInput').value = source;
    document.getElementById('editTargetTermInput').value = target;

    // 显示模态框
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// 删除术语
function deleteTerm(language, source) {
    if (confirm(`确定要删除术语 "${source}" 吗？`)) {
        // 获取当前语言的术语库
        fetch(`/api/terminology/${language}`)
            .then(response => response.json())
            .then(data => {
                const terms = data.terms;

                // 删除术语
                delete terms[source];

                // 保存更新后的术语库
                return fetch(`/api/terminology/${language}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(terms)
                });
            })
            .then(response => {
                if (response.ok) {
                    // 重新加载当前语言的术语库
                    loadTermsForLanguage(language);
                } else {
                    return response.json().then(data => {
                        throw new Error(data.detail || '保存失败');
                    });
                }
            })
            .catch(error => {
                alert('删除术语失败: ' + error.message);
            });
    }
}

// 保存新术语
function saveNewTerm(language, source, target) {
    // 获取当前语言的术语库
    fetch(`/api/terminology/${language}`)
        .then(response => response.json())
        .then(data => {
            const terms = data.terms;

            // 检查是否已存在
            if (terms[source]) {
                if (!confirm(`术语 "${source}" 已存在，是否覆盖？`)) {
                    return Promise.reject(new Error('用户取消'));
                }
            }

            // 添加新术语
            terms[source] = target;

            // 保存更新后的术语库
            return fetch(`/api/terminology/${language}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(terms)
            });
        })
        .then(response => {
            if (response.ok) {
                // 重新加载当前语言的术语库
                loadTermsForLanguage(language);
            } else {
                return response.json().then(data => {
                    throw new Error(data.detail || '保存失败');
                });
            }
        })
        .catch(error => {
            if (error.message !== '用户取消') {
                alert('添加术语失败: ' + error.message);
            }
        });
}

// 更新术语
function updateTerm(language, originalSource, newSource, target) {
    // 获取当前语言的术语库
    fetch(`/api/terminology/${language}`)
        .then(response => response.json())
        .then(data => {
            const terms = data.terms;

            // 如果源术语发生变化，且新术语已存在
            if (originalSource !== newSource && terms[newSource]) {
                if (!confirm(`术语 "${newSource}" 已存在，是否覆盖？`)) {
                    return Promise.reject(new Error('用户取消'));
                }
            }

            // 删除原术语
            delete terms[originalSource];

            // 添加新术语
            terms[newSource] = target;

            // 保存更新后的术语库
            return fetch(`/api/terminology/${language}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(terms)
            });
        })
        .then(response => {
            if (response.ok) {
                // 重新加载当前语言的术语库
                loadTermsForLanguage(language);
            } else {
                return response.json().then(data => {
                    throw new Error(data.detail || '保存失败');
                });
            }
        })
        .catch(error => {
            if (error.message !== '用户取消') {
                alert('更新术语失败: ' + error.message);
            }
        });
}

// 设置右键菜单
function setupContextMenu() {
    // 创建右键菜单
    if (!document.getElementById('terminology-context-menu')) {
        const menu = document.createElement('div');
        menu.id = 'terminology-context-menu';
        menu.className = 'dropdown-menu';
        menu.style.position = 'absolute';
        menu.style.zIndex = '1000';
        menu.innerHTML = `
            <a class="dropdown-item" href="#" id="context-edit"><i class="bi bi-pencil me-2"></i>编辑</a>
            <a class="dropdown-item" href="#" id="context-copy"><i class="bi bi-clipboard me-2"></i>复制</a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item text-danger" href="#" id="context-delete"><i class="bi bi-trash me-2"></i>删除</a>
        `;
        document.body.appendChild(menu);

        // 点击其他地方关闭菜单
        document.addEventListener('click', function(e) {
            if (e.target.closest('#terminology-context-menu') === null) {
                menu.style.display = 'none';
            }
        });
    }

    // 绑定表格行的右键菜单
    const table = document.getElementById('terminology-table');
    if (table) {
        table.addEventListener('contextmenu', function(e) {
            e.preventDefault();

            // 获取点击的行
            const row = e.target.closest('tr');
            if (!row || !row.dataset.source) return;

            // 显示菜单
            const menu = document.getElementById('terminology-context-menu');
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';

            // 设置当前行数据
            menu.dataset.source = row.dataset.source;
            menu.dataset.target = row.dataset.target;

            // 绑定菜单项事件
            document.getElementById('context-edit').onclick = function() {
                editTerm(currentLanguage, row.dataset.source, row.dataset.target);
                menu.style.display = 'none';
            };

            document.getElementById('context-copy').onclick = function() {
                copyTerm(row.dataset.source, row.dataset.target);
                menu.style.display = 'none';
            };

            document.getElementById('context-delete').onclick = function() {
                deleteTerm(currentLanguage, row.dataset.source);
                menu.style.display = 'none';
            };
        });
    }
}

// 复制术语
function copyTerm(source, target) {
    try {
        const text = `${source}: ${target}`;

        // 使用现代的Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    // 显示提示
                    const statusBar = document.getElementById('terminology-status');
                    const originalText = statusBar.textContent;
                    statusBar.textContent = '已复制到剪贴板';

                    // 3秒后恢复原状态
                    setTimeout(() => {
                        statusBar.textContent = originalText;
                    }, 3000);
                })
                .catch(err => {
                    console.error('Clipboard API失败:', err);
                    fallbackCopy(text);
                });
        } else {
            // 回退到旧方法
            fallbackCopy(text);
        }
    } catch (error) {
        console.error('复制失败:', error);
        alert('复制失败: ' + error.message);
    }
}

// 回退的复制方法
function fallbackCopy(text) {
    // 创建临时文本区域
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = 0;
    document.body.appendChild(textarea);
    textarea.select();

    try {
        // 使用旧方法复制
        const successful = document.execCommand('copy');
        if (successful) {
            // 显示提示
            const statusBar = document.getElementById('terminology-status');
            const originalText = statusBar.textContent;
            statusBar.textContent = '已复制到剪贴板';

            // 3秒后恢复原状态
            setTimeout(() => {
                statusBar.textContent = originalText;
            }, 3000);
        } else {
            throw new Error('复制命令执行失败');
        }
    } catch (err) {
        console.error('回退复制方法失败:', err);
        alert('复制失败: ' + err.message);
    } finally {
        // 清理
        document.body.removeChild(textarea);
    }
}

// 表格排序
function sortTable(columnIndex) {
    const table = document.getElementById('terminology-table');
    const tbody = document.getElementById('terminology-tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // 获取当前排序方向
    const th = table.querySelector('th.sortable:nth-child(' + (columnIndex + 1) + ')');
    const currentDirection = th.dataset.direction || 'asc';
    const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';

    // 更新所有表头的排序方向
    table.querySelectorAll('th.sortable').forEach(header => {
        header.dataset.direction = '';
        header.classList.remove('sorted-asc', 'sorted-desc');
    });

    // 设置当前表头的排序方向
    th.dataset.direction = newDirection;
    th.classList.add(newDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');

    // 排序行
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim().toLowerCase();
        const bValue = b.cells[columnIndex].textContent.trim().toLowerCase();

        if (newDirection === 'asc') {
            return aValue.localeCompare(bValue, 'zh-CN');
        } else {
            return bValue.localeCompare(aValue, 'zh-CN');
        }
    });

    // 重新添加排序后的行
    rows.forEach(row => tbody.appendChild(row));
}

// 保存术语库
async function saveTerminology(language) {
    try {
        if (!language) {
            language = currentLanguage;
        }

        // 获取当前语言的术语库
        const response = await fetch(`/api/terminology/${language}`);
        const data = await response.json();
        const terms = data.terms;

        // 保存术语库
        const saveResponse = await fetch(`/api/terminology/${language}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(terms)
        });

        if (saveResponse.ok) {
            alert(`${language}术语库保存成功`);
        } else {
            const errorData = await saveResponse.json();
            alert(`保存${language}术语库失败: ` + errorData.detail);
        }
    } catch (error) {
        alert('保存术语库出错: ' + error.message);
    }
}

// 导出术语库到Excel
function exportTerminologyToExcel(language) {
    // 检查参数是否为事件对象，如果是则忽略它
    if (language && language.preventDefault) {
        // 这是一个事件对象，忽略它
        language = null;
    }

    // 如果没有指定语言，使用当前选中的语言
    if (!language) {
        language = currentLanguage;
    }

    // 确保有有效的语言名称
    if (!language) {
        alert('请先选择一个语言');
        return;
    }

    try {
        console.log(`正在导出术语库，语言: ${language}`);

        // 使用新的导出API
        const exportUrl = `/api/terminology/export/${encodeURIComponent(language)}`;

        // 显示状态消息
        const statusBar = document.getElementById('terminology-status');
        if (statusBar) {
            const originalText = statusBar.textContent;
            statusBar.textContent = `正在导出${language}术语库...`;

            // 使用fetch获取文件内容
            fetch(exportUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`导出失败: ${response.status} ${response.statusText}`);
                    }
                    return response.blob();
                })
                .then(blob => {
                    // 创建下载链接
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
                    link.href = url;
                    link.download = `${language}术语库_${timestamp}.csv`;

                    // 添加到文档并触发点击
                    document.body.appendChild(link);
                    link.click();

                    // 清理
                    setTimeout(() => {
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(link);
                        // 恢复状态栏
                        statusBar.textContent = originalText;
                    }, 100);
                })
                .catch(error => {
                    console.error('导出术语库失败:', error);
                    alert('导出术语库失败: ' + error.message);
                    // 恢复状态栏
                    statusBar.textContent = `导出失败: ${error.message}`;
                    setTimeout(() => {
                        statusBar.textContent = originalText;
                    }, 3000);
                });
        } else {
            // 如果没有状态栏，直接使用传统方法
            window.open(exportUrl, '_blank');
        }
    } catch (error) {
        console.error('导出术语库失败:', error);
        alert('导出术语库失败: ' + error.message);
    }
}

// 解析CSV行
function parseCSVLine(line) {
    // 简单的CSV解析，处理引号包裹的情况
    let inQuote = false;
    let currentValue = '';
    let values = [];

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            inQuote = !inQuote;
        } else if (char === ',' && !inQuote) {
            values.push(currentValue);
            currentValue = '';
        } else {
            currentValue += char;
        }
    }

    // 添加最后一个值
    values.push(currentValue);

    // 移除值两端的引号
    values = values.map(value => {
        if (value.startsWith('"') && value.endsWith('"')) {
            return value.substring(1, value.length - 1);
        }
        return value;
    });

    return values;
}

// 导入术语库
function importTerminology(language) {
    if (!language) {
        language = currentLanguage;
    }

    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.csv';
    fileInput.style.display = 'none';

    // 添加到文档
    document.body.appendChild(fileInput);

    // 监听文件选择
    fileInput.addEventListener('change', async function() {
        if (fileInput.files.length === 0) {
            return;
        }

        const file = fileInput.files[0];

        try {
            // 显示状态消息
            const statusBar = document.getElementById('terminology-status');
            if (statusBar) {
                statusBar.textContent = `正在导入${language}术语库...`;
            }

            // 使用FormData上传文件
            const formData = new FormData();
            formData.append('file', file);

            // 发送请求到新的导入API
            const response = await fetch(`/api/terminology/import/${language}`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                // 重新加载术语库
                loadTermsForLanguage(language);

                // 更新状态消息
                if (statusBar) {
                    statusBar.textContent = `导入成功: ${result.count} 个术语`;
                    // 3秒后清空状态
                    setTimeout(() => {
                        statusBar.textContent = '';
                    }, 3000);
                }
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || '导入失败');
            }
        } catch (error) {
            console.error('导入术语库失败:', error);
            alert('导入术语库失败: ' + error.message);

            // 更新状态消息
            const statusBar = document.getElementById('terminology-status');
            if (statusBar) {
                statusBar.textContent = `导入失败: ${error.message}`;
                // 3秒后清空状态
                setTimeout(() => {
                    statusBar.textContent = '';
                }, 3000);
            }
        } finally {
            // 清理
            document.body.removeChild(fileInput);
        }
    });

    // 触发文件选择
    fileInput.click();
}

// 导入术语库从Excel
function importTerminologyFromExcel() {
    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.csv,.xlsx,.xls';
    fileInput.style.display = 'none';

    // 添加到文档
    document.body.appendChild(fileInput);

    // 监听文件选择
    fileInput.addEventListener('change', function() {
        if (fileInput.files.length === 0) {
            return;
        }

        const file = fileInput.files[0];
        const reader = new FileReader();

        reader.onload = function(e) {
            try {
                const content = e.target.result;

                // 解析CSV内容
                const lines = content.split('\n');
                const terminology = {};

                // 跳过标题行
                for (let i = 1; i < lines.length; i++) {
                    if (!lines[i].trim()) continue;

                    // 处理CSV行，考虑引号包裹的情况
                    let [source, target] = parseCSVLine(lines[i]);

                    if (source && target) {
                        terminology[source] = target;
                    }
                }

                // 如果解析出的术语为空
                if (Object.keys(terminology).length === 0) {
                    alert('未能从文件中解析出有效的术语');
                    return;
                }

                // 确认导入
                if (confirm(`从文件中解析出 ${Object.keys(terminology).length} 个术语，是否导入？\n注意：这将覆盖当前的术语库！`)) {
                    // 保存术语库
                    fetch('/api/terminology', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(terminology)
                    })
                    .then(response => {
                        if (response.ok) {
                            alert('术语库导入成功');
                            // 重新加载术语库
                            loadTerminology();
                        } else {
                            return response.json().then(data => {
                                throw new Error(data.detail || '导入失败');
                            });
                        }
                    })
                    .catch(error => {
                        alert('导入术语库失败: ' + error.message);
                    });
                }
            } catch (error) {
                alert('解析文件失败: ' + error.message);
            }
        };

        reader.onerror = function() {
            alert('读取文件失败');
        };

        reader.readAsText(file);

        // 清理
        document.body.removeChild(fileInput);
    });

    // 触发文件选择
    fileInput.click();
}

// 解析CSV行，处理引号包裹的情况
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }

    // 添加最后一个字段
    result.push(current);

    // 移除字段中的引号
    return result.map(field => field.replace(/^"(.*)"$/, '$1'));
}

// 启动实时日志监控
function startRealtimeLogMonitoring() {
    // 如果已经有轮询定时器，先清除
    if (logPollingInterval) {
        clearInterval(logPollingInterval);
    }

    // 每2秒轮询一次新日志
    logPollingInterval = setInterval(async () => {
        try {
            await fetchRealtimeLogs();
        } catch (error) {
            console.error('获取实时日志失败:', error);
        }
    }, 2000);

    addSystemLog('实时日志监控已启动', 'info');
}

// 获取实时日志
async function fetchRealtimeLogs() {
    try {
        let url = '/api/logs/realtime?count=50';

        // 如果有最后一条日志的时间戳，只获取之后的日志
        if (lastLogTimestamp) {
            url = `/api/logs/since?since=${encodeURIComponent(lastLogTimestamp)}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.success && data.logs && data.logs.length > 0) {
            // 处理新日志
            data.logs.forEach(log => {
                processRealtimeLog(log);
                // 更新最后一条日志的时间戳
                lastLogTimestamp = log.timestamp;
            });
        }
    } catch (error) {
        console.error('获取实时日志失败:', error);
        // 不在系统日志中显示这个错误，避免日志循环
    }
}

// 处理实时日志
function processRealtimeLog(log) {
    // 格式化日志消息
    let logMessage = log.message;
    if (log.location) {
        logMessage = `[${log.location}] ${logMessage}`;
    }

    // 根据日志级别确定样式
    let logLevel = 'info';
    if (log.level === 'ERROR') {
        logLevel = 'error';
        exceptionCount++;
        lastExceptionTime = new Date();
    } else if (log.level === 'WARNING') {
        logLevel = 'warning';
    } else if (log.level === 'DEBUG') {
        logLevel = 'debug';
    }

    // 添加到系统日志显示
    addSystemLog(logMessage, logLevel);
}

// 启动异常状态监控
function startExceptionMonitoring() {
    // 每5秒检查一次异常状态
    setInterval(async () => {
        try {
            await updateExceptionStatus();
        } catch (error) {
            console.error('更新异常状态失败:', error);
        }
    }, 5000);

    // 在系统日志区域添加异常状态显示
    addExceptionStatusIndicator();
}

// 更新异常状态
async function updateExceptionStatus() {
    try {
        const response = await fetch('/api/logs/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.success && data.stats) {
            updateExceptionIndicator(data.stats);
        }
    } catch (error) {
        console.error('获取异常统计失败:', error);
    }
}

// 添加异常状态指示器
function addExceptionStatusIndicator() {
    const systemLogHeader = document.querySelector('#system-log').parentElement.previousElementSibling;
    if (systemLogHeader && !document.getElementById('exception-indicator')) {
        const indicatorHtml = `
            <div id="exception-indicator" class="ms-2">
                <span class="badge bg-success" id="exception-badge">
                    <i class="bi bi-check-circle"></i> 系统正常
                </span>
            </div>
        `;
        systemLogHeader.querySelector('div').insertAdjacentHTML('beforeend', indicatorHtml);
    }
}

// 更新异常指示器
function updateExceptionIndicator(stats) {
    const badge = document.getElementById('exception-badge');
    if (!badge) return;

    const hasRecentErrors = stats.last_error_time &&
        (new Date() - new Date(stats.last_error_time)) < 300000; // 5分钟内

    if (hasRecentErrors || stats.error_count > 0) {
        badge.className = 'badge bg-danger';
        badge.innerHTML = `<i class="bi bi-exclamation-triangle"></i> 检测到异常 (${stats.error_count}个错误)`;
        badge.title = `错误: ${stats.error_count}, 警告: ${stats.warning_count}, 总日志: ${stats.total_logs}`;
    } else if (stats.warning_count > 0) {
        badge.className = 'badge bg-warning';
        badge.innerHTML = `<i class="bi bi-exclamation-circle"></i> 有警告 (${stats.warning_count}个)`;
        badge.title = `警告: ${stats.warning_count}, 总日志: ${stats.total_logs}`;
    } else {
        badge.className = 'badge bg-success';
        badge.innerHTML = `<i class="bi bi-check-circle"></i> 系统正常`;
        badge.title = `总日志: ${stats.total_logs}`;
    }
}

// 停止实时日志监控
function stopRealtimeLogMonitoring() {
    if (logPollingInterval) {
        clearInterval(logPollingInterval);
        logPollingInterval = null;
        addSystemLog('实时日志监控已停止', 'warning');
    }
}

// 清空实时日志缓冲区
async function clearRealtimeLogs() {
    try {
        const response = await fetch('/api/logs/clear', {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                addSystemLog('实时日志缓冲区已清空', 'info');
                // 重置本地状态
                lastLogTimestamp = null;
                exceptionCount = 0;
                lastExceptionTime = null;
            }
        }
    } catch (error) {
        console.error('清空实时日志失败:', error);
        addSystemLog('清空实时日志失败: ' + error.message, 'error');
    }
}

// 打开输出目录
async function openOutputDirectory() {
    try {
        addSystemLog('正在打开输出目录...', 'info');

        const response = await fetch('/api/open-output-directory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            addSystemLog(`输出目录已打开: ${data.path}`, 'success');
        } else {
            const data = await response.json();
            addSystemLog(`打开输出目录失败: ${data.detail}`, 'error');
            alert('打开输出目录失败: ' + data.detail);
        }
    } catch (error) {
        addSystemLog(`打开输出目录出错: ${error.message}`, 'error');
        alert('打开输出目录出错: ' + error.message);
    }
}
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const voiceButton = document.getElementById('voice-button');
const loading = document.getElementById('loading');

async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) {
        return;
    }

    // 显示用户消息
    const userMessageDiv = createMessageDiv(question, 'user');
    chatMessages.appendChild(userMessageDiv);
    scrollToBottom();

    // 禁用按钮并显示加载动画
    disableButtons(true);
    showLoading(true);
    userInput.disabled = true;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        if (!response.ok) {
            throw new Error('网络请求出错，请检查网络连接。');
        }

        const data = await response.json();
        if (data.error) {
            showError(data.error);
        } else {
            // 显示 AI 回复
            const aiMessageDiv = createMessageDiv(data.answer, 'ai');
            chatMessages.appendChild(aiMessageDiv);
            scrollToBottom();
            speakAnswer(data.answer);
        }
    } catch (error) {
        showError(error.message);
    } finally {
        // 启用按钮并隐藏加载动画
        disableButtons(false);
        showLoading(false);
        userInput.disabled = false;
        userInput.value = '';
    }
}

function createMessageDiv(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.textContent = type === 'user' ? `你: ${content}` : `案例分析助手: ${content}`;
    return messageDiv;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function startVoiceInput() {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'zh-CN';

    recognition.onstart = function () {
        voiceButton.disabled = true;
        voiceButton.textContent = '正在聆听...';
    };

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        userInput.value = transcript;
        sendMessage();
    };

    recognition.onend = function () {
        voiceButton.disabled = false;
        voiceButton.textContent = '语音输入';
    };

    recognition.onerror = function (event) {
        showError(`语音识别出错: ${event.error}`);
        voiceButton.disabled = false;
        voiceButton.textContent = '语音输入';
    };

    recognition.start();
}

function speakAnswer(answer) {
    const synth = window.speechSynthesis;
    const utterance = new SpeechSynthesisUtterance(answer);
    utterance.lang = 'zh-CN';
    utterance.rate = 1.1;
    utterance.pitch = 1.2;
    synth.speak(utterance);
}

function disableButtons(disable) {
    sendButton.disabled = disable;
    voiceButton.disabled = disable;
}

function showLoading(show) {
    loading.style.display = show ? 'block' : 'none';
}

function showError(errorMessage) {
    const errorDiv = createMessageDiv(`错误: ${errorMessage}`, 'ai');
    errorDiv.style.backgroundColor = '#FF5252';
    chatMessages.appendChild(errorDiv);
    scrollToBottom();
}

function clearChat() {
    if (confirm('确定要清空聊天记录吗？')) {
        chatMessages.innerHTML = '';
    }
}
import React, { useState } from 'react';
import { Input, Button, Card, Spin, message, Tooltip } from 'antd';
import { SendOutlined, CopyOutlined, HistoryOutlined, FileTextOutlined, RobotOutlined } from '@ant-design/icons';
import { askQuestionStream } from '../services/qaService';
import './QAPage.css';

const { TextArea } = Input;

const aiModels = [
  { key: 'deepseek', name: 'DeepSeek', runtimeModel: 'deepseek-chat' },
  { key: 'kimi', name: 'Kimi', runtimeModel: 'deepseek-chat' },
];

const QAPage: React.FC = () => {
  const [messageApi, contextHolder] = message.useMessage();
  const [question, setQuestion] = useState('');
  const [displayAnswer, setDisplayAnswer] = useState('');
  const [fullAnswer, setFullAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(['关于宪法与民法典的区别', '劳动合同违约责任']);
  const [selectedModel, setSelectedModel] = useState('deepseek');

  const handleAsk = async () => {
    if (!question.trim()) {
      messageApi.error('请输入问题');
      return;
    }

    const selected = aiModels.find((m) => m.key === selectedModel) ?? aiModels[0];
    setLoading(true);
    setFullAnswer('');
    setDisplayAnswer('');

    try {
      let content = '';
      await askQuestionStream(
        {
          model: selected.runtimeModel,
          messages: [{ role: 'user', content: question }],
          temperature: 0.1,
          stream: true,
        },
        (chunk) => {
          content += chunk;
          setDisplayAnswer(content);
          setFullAnswer(content);
        },
      );
      setHistory((prev) => [question.slice(0, 15) + '...', ...prev.slice(0, 4)]);
    } catch {
      messageApi.error('获取回答失败');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(fullAnswer);
    messageApi.success('已复制到剪贴板');
  };

  return (
    <>
      {contextHolder}
      <div className="qa-layout">
        <aside className="qa-sidebar">
          <div className="sidebar-header">
            <HistoryOutlined /> <span>咨询历史</span>
          </div>
          <div className="history-list">
            {history.map((item, index) => (
              <div key={index} className="history-item" onClick={() => setQuestion(item.replace('...', ''))}>
                <FileTextOutlined style={{ marginRight: 8, color: '#2563eb' }} /> {item}
              </div>
            ))}
          </div>
        </aside>

        <main className="qa-main">
          <div className="qa-content">
            <Card className="qa-card" variant="borderless" styles={{ body: { padding: '20px 30px' } }}>
              <h2 className="main-title">智能法律问答</h2>

              <div className="model-selector-wrapper">
                <div className="model-selector-label">
                  <RobotOutlined style={{ marginRight: 8 }} />
                  <span>选择模型</span>
                </div>
                <div className="ai-models-group">
                  {aiModels.map((model) => (
                    <button
                      key={model.key}
                      className={`ai-model-btn ${selectedModel === model.key ? 'active' : ''}`}
                      onClick={() => setSelectedModel(model.key)}
                    >
                      {model.name}
                    </button>
                  ))}
                </div>
              </div>

              <TextArea
                rows={3}
                autoSize={{ minRows: 3, maxRows: 8 }}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="请输入需要咨询的法律或合同问题..."
                className="question-input"
              />

              <div className="action-bar">
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleAsk}
                  loading={loading}
                  className="submit-btn"
                  size="large"
                >
                  开始问答
                </Button>
              </div>
            </Card>

            {loading && (
              <div className="loading-state">
                <Spin tip="正在分析问题，请稍候..." />
              </div>
            )}

            {displayAnswer && (
              <Card
                className="answer-card"
                title={
                  <span style={{ fontWeight: 700, color: '#1e3e7e' }}>
                    <FileTextOutlined style={{ color: '#2563eb' }} /> 法律问答结果
                  </span>
                }
                extra={
                  <Tooltip title="复制全文">
                    <Button type="text" icon={<CopyOutlined style={{ color: '#2563eb' }} />} onClick={copyToClipboard} />
                  </Tooltip>
                }
                variant="borderless"
              >
                <div className="answer-text">
                  {displayAnswer}
                  {loading && <span className="cursor">|</span>}
                </div>
              </Card>
            )}
          </div>
        </main>
      </div>
    </>
  );
};

export default QAPage;

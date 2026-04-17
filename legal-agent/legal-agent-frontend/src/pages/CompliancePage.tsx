import React, { useState } from 'react';
import { Upload, Card, message, Spin, Tag, Button, Input, Select } from 'antd';
import {
  FileProtectOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  WarningOutlined,
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { mergeCompliance } from '../services/complianceService';
import { ComplianceResult } from '../types/compliance';
import './CompliancePage.css';

const { Dragger } = Upload;
const { TextArea } = Input;

type ReviewStatus = 'pending' | 'accepted' | 'rejected' | 'edited';

const CompliancePage: React.FC = () => {
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(false);
  const [merging, setMerging] = useState(false);
  const [results, setResults] = useState<ComplianceResult[] | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [focus, setFocus] = useState('standard');

  const uploadProps = {
    name: 'file',
    multiple: false,
    action: 'http://127.0.0.1:8000/compliance/deepseek',
    data: { focus },
    beforeUpload() {
      setLoading(true);
      setResults(null);
      setUploadedFile(null);
      return true;
    },
    onChange(info: any) {
      const { status, response, originFileObj } = info.file;
      if (status === 'done') {
        setLoading(false);
        const code = Number(response?.code ?? 0);
        const errMsg = response?.message || response?.error || '未知错误';
        const resultList = Array.isArray(response?.data?.result) ? response.data.result : [];

        if (code === 200) {
          setUploadedFile(originFileObj);
          const initResults = resultList.map((item: any) => ({
            ...item,
            status: 'pending',
            editedSuggestion: item.suggestion,
          }));
          setResults(initResults);
          if (initResults.length === 0) {
            messageApi.warning('审查完成，但当前未识别到明确需要修改的条款。');
          } else {
            messageApi.success(`${info.file.name} 审查完成`);
          }
        } else {
          messageApi.error(`审查失败：${errMsg}`);
        }
      } else if (status === 'error') {
        setLoading(false);
        messageApi.error(`${info.file.name} 上传或解析失败`);
      }
    },
  };

  const handleStatusChange = (index: number, status: ReviewStatus) => {
    const newResults = [...(results || [])];
    newResults[index].status = status;
    setResults(newResults);
  };

  const handleTextChange = (index: number, value: string) => {
    const newResults = [...(results || [])];
    newResults[index].editedSuggestion = value;
    setResults(newResults);
  };

  const handleGenerate = async () => {
    if (!uploadedFile || !results) {
      return;
    }

    const replacements = results
      .filter((r) => r.status === 'accepted' || r.status === 'edited')
      .map((r) => ({
        original: r.original,
        suggestion: r.status === 'edited' && r.editedSuggestion ? r.editedSuggestion : r.suggestion,
      }));

    if (replacements.length === 0) {
      messageApi.warning('请至少采纳或编辑一条建议后再生成合同。');
      return;
    }

    try {
      setMerging(true);
      await mergeCompliance(uploadedFile, replacements);
      messageApi.success('修订后的合同已生成，下载已开始。');
    } catch (error) {
      messageApi.error('生成失败，请稍后重试。');
    } finally {
      setMerging(false);
    }
  };

  return (
    <>
      {contextHolder}
      <div className="comp-page-wrapper">
        <div className="comp-bg-glow">
          <div className="glow-ball g1"></div>
          <div className="glow-ball g2"></div>
        </div>

        <div className="comp-main-container">
          <header className="comp-page-header">
            <div className="title-box">
              <FileProtectOutlined className="main-logo-icon" />
              <h1>合同合规审查</h1>
            </div>
            <p className="sub-description">基于 DeepSeek 对合同条款进行识别、风险解释和修订建议生成。</p>
          </header>

          <div className="comp-grid-layout">
            <div className="col-left">
              <Card className="mini-card upload-card" variant="borderless">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 className="mini-card-title" style={{ marginBottom: 0 }}>上传待审查合同</h3>
                  <Select
                    value={focus}
                    onChange={(val) => setFocus(val)}
                    style={{ width: 160 }}
                    options={[
                      { value: 'standard', label: '标准审查' },
                      { value: 'party_a', label: '偏向保护甲方' },
                      { value: 'party_b', label: '偏向保护乙方' },
                      { value: 'strict', label: '严格审查' },
                    ]}
                  />
                </div>
                <Dragger {...uploadProps} className="compact-dragger">
                  <p className="ant-upload-drag-icon">
                    <CloudUploadOutlined className="icon-drop" />
                  </p>
                  <p className="ant-upload-text" style={{ fontWeight: 600, color: '#1e3e7e' }}>
                    选择文件或拖拽文件到此处上传
                  </p>
                  <span className="ant-upload-hint" style={{ color: '#64748b' }}>
                    支持 DOCX / PDF 格式
                  </span>
                </Dragger>
              </Card>

              <Card className="mini-card advantage-card" variant="borderless" style={{ marginTop: 24 }}>
                <div className="adv-title-row">
                  <FileTextOutlined className="icon-shake" />
                  <h3 className="mini-card-title" style={{ marginBottom: 0 }}>审查能力</h3>
                </div>
                <ul className="mini-list">
                  <li>
                    <CheckCircleOutlined className="li-dot" /> 自动定位风险条款
                  </li>
                  <li>
                    <CheckCircleOutlined className="li-dot" /> 输出风险原因与修订建议
                  </li>
                  <li>
                    <CheckCircleOutlined className="li-dot" /> 一键导出修订后的合同文档
                  </li>
                </ul>
              </Card>
            </div>

            <div className="col-right">
              <Card className="mini-card preview-card" variant="borderless">
                <h3 className="mini-card-title">审查结果预览</h3>
                <div className="preview-viewport">
                  {loading ? (
                    <div className="loading-box">
                      <Spin size="large" />
                      <p style={{ marginTop: 12 }}>AI 正在进行合规审查，请稍候...</p>
                      <div className="scan-effect-bar"></div>
                    </div>
                  ) : results ? (
                    <div className="results-container">
                      <div className="results-list">
                        {results.map((item, index) => (
                          <div key={index} className={`result-item status-${item.status}`}>
                            <div className="result-item-header">
                              <Tag color={item.status === 'rejected' ? 'default' : '#ef4444'} style={{ borderRadius: '6px', fontWeight: 600 }}>
                                <WarningOutlined /> 风险点 {index + 1}
                              </Tag>
                              <span className="result-item-title">{item.risk?.substring(0, 20) || '潜在风险提示'}...</span>

                              {item.status === 'accepted' && (
                                <Tag color="success" className="status-badge" style={{ borderRadius: '6px' }}>
                                  已采纳
                                </Tag>
                              )}
                              {item.status === 'edited' && (
                                <Tag color="processing" className="status-badge" style={{ borderRadius: '6px' }}>
                                  已编辑
                                </Tag>
                              )}
                              {item.status === 'rejected' && (
                                <Tag color="default" className="status-badge" style={{ borderRadius: '6px' }}>
                                  已忽略
                                </Tag>
                              )}
                            </div>

                            <div className="result-item-content">
                              <p>
                                <strong>原始条款：</strong>
                                {item.original || '未提取到原文内容'}
                              </p>

                              {item.status === 'edited' ? (
                                <div className="edit-area">
                                  <strong>自定义修订：</strong>
                                  <TextArea
                                    value={item.editedSuggestion}
                                    onChange={(e) => handleTextChange(index, e.target.value)}
                                    autoSize={{ minRows: 2, maxRows: 6 }}
                                    className="custom-textarea"
                                    style={{ marginTop: '8px', borderRadius: '10px' }}
                                  />
                                </div>
                              ) : (
                                <p>
                                  <strong>修订建议：</strong>
                                  {item.suggestion}
                                </p>
                              )}
                            </div>

                            <div className="result-item-actions" style={{ marginTop: '16px' }}>
                              <Button
                                size="small"
                                type={item.status === 'accepted' ? 'primary' : 'default'}
                                style={item.status === 'accepted' ? { backgroundColor: '#10b981', borderColor: '#10b981' } : { borderRadius: '8px' }}
                                icon={<CheckOutlined />}
                                onClick={() => handleStatusChange(index, 'accepted')}
                              >
                                采纳建议
                              </Button>
                              <Button
                                size="small"
                                type={item.status === 'edited' ? 'primary' : 'default'}
                                style={{ borderRadius: '8px', marginLeft: '8px' }}
                                icon={<EditOutlined />}
                                onClick={() => handleStatusChange(index, 'edited')}
                              >
                                手动编辑
                              </Button>
                              <Button
                                size="small"
                                danger
                                type="text"
                                style={{ marginLeft: '8px' }}
                                icon={<CloseOutlined />}
                                onClick={() => handleStatusChange(index, 'rejected')}
                              >
                                忽略
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="generate-footer">
                        <Button
                          type="primary"
                          size="large"
                          icon={<DownloadOutlined />}
                          className="btn-generate"
                          loading={merging}
                          onClick={handleGenerate}
                        >
                          生成修订后合同
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="placeholder-content">
                      <FileSearchOutlined className="icon-radar" />
                      <p style={{ fontWeight: 500 }}>上传合同后，审查结果会显示在这里。</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default CompliancePage;

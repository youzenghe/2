import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileSearchOutlined,
  MessageOutlined,
  GlobalOutlined,
  FileTextOutlined,
  CalculatorOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const LegalAgent: React.FC = () => {
  const navigate = useNavigate();

  const colors = {
    primary: '#2563eb',
    deepNavy: '#1e3e7e',
    mainBg: '#f1f5f9',
    textSub: '#64748b',
  };

  const externalMap: Record<string, string> = {
    '/word': 'http://127.0.0.1:5003',
    '/laws': 'http://127.0.0.1:5002',
    '/calculate': 'http://127.0.0.1:5007',
    '/RiskAnalysis': 'http://127.0.0.1:5020',
  };

  const cards = [
    {
      title: '合同审查',
      desc: '基于 AI 对合同条款进行深入识别，自动定位风险点并生成修订建议。',
      icon: <FileSearchOutlined style={{ color: colors.primary }} />,
      path: '/compliance',
    },
    {
      title: '智能问答',
      desc: '面向法律和合同场景的问答助手，支持实时追问与连续对话。',
      icon: <MessageOutlined style={{ color: colors.primary }} />,
      path: '/qa',
    },
    {
      title: '知识图谱',
      desc: '以结构化方式查看法律知识和合同知识之间的关联关系。',
      icon: <GlobalOutlined style={{ color: colors.primary }} />,
      path: '/word',
    },
    {
      title: '文书模板',
      desc: '集中管理常用法律文书模板，支持在线查看和下载。',
      icon: <FileTextOutlined style={{ color: colors.primary }} />,
      path: '/laws',
    },
    {
      title: '合同计算器',
      desc: '用于计算利息、违约金、诉讼费等与合同场景相关的常见费用。',
      icon: <CalculatorOutlined style={{ color: colors.primary }} />,
      path: '/calculate',
    },
    {
      title: '风险评估',
      desc: '从金额、信用、履约周期、市场情况等多个维度输出风险评估结果。',
      icon: <CheckCircleOutlined style={{ color: colors.primary }} />,
      path: '/RiskAnalysis',
    },
  ];

  const handleCardClick = (path: string) => {
    if (externalMap[path]) {
      window.location.href = externalMap[path];
    } else {
      navigate(path);
    }
  };

  return (
    <div className="home-wrapper">
      <style>{`
        .home-wrapper {
          position: relative;
          height: calc(100vh - 64px);
          background-color: ${colors.mainBg};
          overflow: hidden;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
        }

        .bg-mesh {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 0;
          filter: blur(80px);
        }

        .mesh-ball {
          position: absolute;
          border-radius: 50%;
          animation: float 20s infinite alternate ease-in-out;
        }

        .ball-1 { width: 400px; height: 400px; background: #dbeafe; top: -100px; left: -100px; opacity: 0.6; }
        .ball-4 { width: 350px; height: 350px; background: ${colors.primary}; bottom: -100px; right: -50px; opacity: 0.05; }

        @keyframes float {
          0% { transform: translate(0, 0) scale(1); }
          100% { transform: translate(3%, 5%) scale(1.05); }
        }

        .home-content {
          position: relative;
          z-index: 10;
          text-align: center;
          width: 100%;
          max-width: 1100px;
          padding: 0 20px;
        }

        .main-title {
          font-size: 38px;
          font-weight: 800;
          color: ${colors.deepNavy};
          margin-bottom: 8px;
          letter-spacing: 2px;
        }

        .title-line {
          width: 48px;
          height: 4px;
          background: ${colors.primary};
          margin: 0 auto 15px;
          border-radius: 2px;
        }

        .sub-title {
          color: ${colors.textSub};
          font-size: 16px;
          margin-bottom: 35px;
          line-height: 1.5;
        }

        .card-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 25px;
        }

        .feature-card {
          background: rgba(255, 255, 255, 0.85);
          backdrop-filter: blur(20px);
          border-radius: 28px;
          height: 205px;
          padding: 24px;
          cursor: pointer;
          transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(255, 255, 255, 0.8);
          position: relative;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        }

        .feature-card:hover {
          transform: translateY(-10px);
          background: #fff;
          box-shadow: 0 20px 40px rgba(30, 62, 126, 0.1);
          border-color: ${colors.primary};
        }

        .card-inner {
          transition: 0.3s;
        }

        .card-hover-desc {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          padding: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          text-align: center;
          color: #475569;
          font-size: 14px;
          line-height: 1.6;
          opacity: 0;
          background: rgba(255, 255, 255, 0.98);
          border-radius: 28px;
          transition: 0.3s;
        }

        .feature-card:hover .card-inner { opacity: 0; transform: scale(0.9); }
        .feature-card:hover .card-hover-desc { opacity: 1; }

        .card-icon {
          font-size: 48px;
          margin-bottom: 15px;
          display: block;
          filter: drop-shadow(0 4px 6px rgba(37, 99, 235, 0.1));
        }

        .card-title {
          font-size: 20px;
          font-weight: 700;
          color: ${colors.deepNavy};
        }

        .card-line-small {
          width: 20px;
          height: 3px;
          background: #e2e8f0;
          margin: 12px auto 0;
          transition: 0.3s;
          border-radius: 2px;
        }

        .feature-card:hover .card-line-small {
          width: 45px;
          background: ${colors.primary};
        }
      `}</style>

      <div className="bg-mesh">
        <div className="mesh-ball ball-1"></div>
        <div className="mesh-ball ball-4"></div>
      </div>

      <div className="home-content">
        <h1 className="main-title">智审云枢</h1>
        <div className="title-line"></div>
        <p className="sub-title">聚合法律问答、合同审查、风险评估和模板能力，提供统一的法律智能工作台。</p>

        <div className="card-grid">
          {cards.map((card, index) => (
            <div key={index} className="feature-card" onClick={() => handleCardClick(card.path)}>
              <div className="card-inner">
                <span className="card-icon">{card.icon}</span>
                <div className="card-title">{card.title}</div>
                <div className="card-line-small"></div>
              </div>
              <div className="card-hover-desc">{card.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LegalAgent;

import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, ConfigProvider } from 'antd';
import {
    HomeOutlined,
    FileSearchOutlined,
    MessageOutlined,
    GlobalOutlined,
    FileTextOutlined,
    CalculatorOutlined,
    CheckCircleOutlined,
    LogoutOutlined
} from '@ant-design/icons';
import './App.css';
import CompliancePage from './pages/CompliancePage';
import QAPage from './pages/QAPage';
import LegalAgent from './pages/LegalAgent';

const { Header, Content } = Layout;

// 核心商务蓝色系
const colors = {
    headerBg: '#1e3e7e',
    primary: '#2563eb',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255,255,255,0.7)',
};

function App() {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { key: '/', label: '首页', icon: <HomeOutlined /> },
        { key: '/compliance', label: '合同审查', icon: <FileSearchOutlined /> },
        { key: '/qa', label: '咨询', icon: <MessageOutlined /> },
        { key: '/word', label: '合同知识图谱', icon: <GlobalOutlined />, isExternal: true, url: 'http://127.0.0.1:5003' },
        { key: '/laws', label: '文书模板', icon: <FileTextOutlined />, isExternal: true, url: 'http://127.0.0.1:5002' },
        { key: '/calculate', label: '计算器', icon: <CalculatorOutlined />, isExternal: true, url: 'http://127.0.0.1:5007' },
        { key: '/RiskAnalysis', label: '合同风险', icon: <CheckCircleOutlined />, isExternal: true, url: 'http://127.0.0.1:5020' },
    ];

    return (
        <ConfigProvider theme={{ token: { colorPrimary: colors.primary } }}>
            <Layout style={{ minHeight: '100vh', background: '#f1f5f9' }}>
                <Header style={{
                    height: 64,
                    background: colors.headerBg,
                    borderBottom: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0 40px',
                    position: 'fixed',
                    width: '100%',
                    zIndex: 1000,
                    boxShadow: '0 4px 15px rgba(30, 62, 126, 0.2)'
                }}>
                    {/* 左侧 Logo - 调大了一点 */}
                    <div onClick={() => navigate('/')} style={{ display: 'flex', alignItems: 'center', marginRight: 40, cursor: 'pointer' }}>
                        <div style={{
                            width: 40, height: 40, background: colors.primary, borderRadius: 10,
                            display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', marginRight: 12
                        }}><HomeOutlined style={{ fontSize: 22 }} /></div>
                        <span style={{ fontSize: 22, fontWeight: 800, color: colors.textPrimary, letterSpacing: '0.5px' }}>智审云枢</span>
                    </div>

                    <Menu
                        mode="horizontal"
                        theme="dark"
                        selectedKeys={[location.pathname]}
                        onClick={({ key }) => {
                            const item = menuItems.find(i => i.key === key);
                            if (item?.isExternal && item.url) {
                                window.location.href = item.url;
                            } else {
                                navigate(key);
                            }
                        }}
                        style={{ flex: 1, borderBottom: 'none', background: 'transparent', fontSize: '15px' }}
                        items={menuItems.map(item => ({ key: item.key, icon: item.icon, label: item.label }))}
                    />

                    {/* 注销改为退出系统：修改了这里的 href，指向 Flask 后端的 logout 路由 */}
                    <div onClick={() => window.location.href = 'http://127.0.0.1:5000/logout'} style={{ color: colors.textSecondary, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '14px' }}>
                        <LogoutOutlined /><span>退出系统</span>
                    </div>
                </Header>

                <Content style={{
                    marginTop: 64,
                    background: 'transparent',
                    backgroundImage: 'radial-gradient(circle at 5% 30%, #dbeafe 0%, transparent 45%)'
                }}>
                    <Routes>
                        <Route path="/" element={<LegalAgent />} />
                        <Route path="/compliance" element={<CompliancePage />} />
                        <Route path="/qa" element={<QAPage />} />
                    </Routes>
                </Content>
            </Layout>
        </ConfigProvider>
    );
}
export default App;
export interface ComplianceResult {
  original: string;    // 原条款
  risk: string;        // 风险说明
  suggestion: string;  // 合规改写建议
  status?: 'pending' | 'accepted' | 'rejected' | 'edited'; // 当前卡片的状态
  editedSuggestion?: string; // 用户手动修改后的建议文本
}

export interface ComplianceResponseData {
  compliance: boolean;
  result: ComplianceResult[];
}

export interface ComplianceResponse {
  message: string;
  code: number;
  data: ComplianceResponseData;
}

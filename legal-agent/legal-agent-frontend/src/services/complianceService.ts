import { ComplianceResponse } from '../types/compliance';

export const checkCompliance = async (file: File, provider: string): Promise<ComplianceResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`http://localhost:8000/compliance/${provider}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to check compliance');
  }

  return response.json();
};

export const mergeCompliance = async (file: File, replacements: { original: string; suggestion: string }[]): Promise<void> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('replacements', JSON.stringify(replacements));

  const response = await fetch('http://localhost:8000/compliance/merge', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to merge compliance');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'merged_contract.docx';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

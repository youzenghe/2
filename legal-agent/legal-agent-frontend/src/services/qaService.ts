import { QARequest, QAResponse } from '../types/qa';

const url = 'http://localhost:8012/v1/chat/completions';
const headers = { 'Content-Type': 'application/json' };

export const askQuestion = async (request: QARequest): Promise<QAResponse> => {
  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to get answer');
  }

  return response.json();
};

export const askQuestionStream = async (
  request: QARequest,
  onChunk: (contentChunk: string) => void,
): Promise<void> => {
  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok || !response.body) {
    throw new Error('Failed to get streaming answer');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() ?? '';

    for (const block of blocks) {
      const lines = block.split('\n');
      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith('data:')) {
          continue;
        }
        const payload = line.slice(5).trim();
        if (!payload) {
          continue;
        }
        if (payload === '[DONE]') {
          return;
        }

        let parsed: any = null;
        try {
          parsed = JSON.parse(payload);
        } catch {
          continue;
        }

        const chunk =
          parsed?.choices?.[0]?.delta?.content ??
          parsed?.choices?.[0]?.message?.content ??
          '';
        if (chunk) {
          onChunk(chunk);
        }
      }
    }
  }
};

export interface QARequest {
  model: string;
  messages: Array<{ role: string; content: string }>;
  temperature: number;
  top_p?: number;
  stream?: boolean;
}

export interface QAResponse {
  choices: Array<{ message: { content: string } }>;
}

export interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant';
    timestamp: string;
}

export interface Conversation {
    id: number;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ModelSettings {
    temperature: number;
    max_length: number;
    top_p: number;
    model?: string;
} 
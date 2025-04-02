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
    preview?: string | null;
} 
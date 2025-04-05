import { Message } from '../types';

export const API_BASE_URL = 'http://localhost:8000/api';

// Function to fetch messages for a specific chat
export const fetchChatMessages = async (chatId: string): Promise<Message[]> => {
    const response = await fetch(`${API_BASE_URL}/chat/${chatId}/messages`);
    if (!response.ok) {
        throw new Error('Failed to fetch messages');
    }
    return await response.json();
};

// WebSocket connection for bidirectional streaming chat
export class WebSocketChatManager {
    private ws: WebSocket | null = null;
    private isConnected: boolean = false;
    private reconnectAttempts: number = 0;
    private readonly maxReconnectAttempts: number = 3;
    private readonly reconnectDelay: number = 1000; // 1 second

    // Callbacks for different events
    private onTokenCallback: ((token: string) => void) | null = null;
    private onCompleteCallback: ((response: any) => void) | null = null;
    private onErrorCallback: ((error: string) => void) | null = null;

    constructor() {
        this.connect();
    }

    private connect(): void {
        if (this.ws) {
            this.ws.close();
        }

        // Create WebSocket connection
        // qwen-instruct
        // const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/qwen-instruct`;
        const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/gemma-3-1b-it`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connection established');
            this.isConnected = true;
            this.reconnectAttempts = 0;
        };

        this.ws.onclose = (event) => {
            this.isConnected = false;
            console.log(`WebSocket connection closed: ${event.code}`);

            // Attempt to reconnect if not intentionally closed
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                setTimeout(() => this.connect(), this.reconnectDelay);
            } else if (this.onErrorCallback) {
                this.onErrorCallback('WebSocket connection closed after max reconnect attempts');
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (this.onErrorCallback) {
                this.onErrorCallback('WebSocket connection error');
            }
        };

        this.ws.onmessage = (event) => {
            try {
                console.log('event', event);
                const data = JSON.parse(event.data);

                if (data.token) {
                    // Token received
                    if (this.onTokenCallback) {
                        this.onTokenCallback(data.token);
                    }
                } else if (data.status === 'complete') {
                    // Generation complete
                    if (this.onCompleteCallback) {
                        this.onCompleteCallback(data);
                    }
                } else if (data.error) {
                    // Error received
                    if (this.onErrorCallback) {
                        this.onErrorCallback(data.error);
                    }
                }
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
                if (this.onErrorCallback) {
                    this.onErrorCallback('Error processing message');
                }
            }
        };
    }

    public sendChatMessage(
        content: string,
        onToken: (token: string) => void,
        onComplete: (response: any) => void,
        onError: (error: string) => void,
        chatId?: number,
        options = { temperature: 0.7, max_length: 25, top_p: 0.9, model: 'mygpt' }
    ): void {
        // Set callbacks
        this.onTokenCallback = onToken;
        this.onCompleteCallback = onComplete;
        this.onErrorCallback = onError;

        // Ensure connection is active
        if (!this.isConnected) {
            this.connect();
            // Small delay to allow connection to establish
            setTimeout(() => this.sendMessageToServer(content, chatId, options), 500);
        } else {
            this.sendMessageToServer(content, chatId, options);
        }
    }

    private sendMessageToServer(
        content: string,
        chatId?: number,
        options = { temperature: 0.7, max_length: 25, top_p: 0.9, model: 'mygpt' }
    ): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            if (this.onErrorCallback) {
                this.onErrorCallback('WebSocket not connected');
            }
            return;
        }

        const payload = {
            command: 'generate',
            message: content,
            chat_id: chatId,
            temperature: options.temperature,
            max_length: options.max_length,
            top_p: options.top_p,
            model: options.model
        };
        console.log('client-ws-to-server-payload', payload);

        this.ws.send(JSON.stringify(payload));
    }

    public stopGeneration(): void {
        if (this.ws && this.isConnected) {
            const stopCommand = {
                command: 'stop'
            };
            this.ws.send(JSON.stringify(stopCommand));
        }
    }

    public disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Export a singleton instance for app-wide use
export const wsManager = new WebSocketChatManager(); 
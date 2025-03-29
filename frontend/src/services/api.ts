import { Conversation, Message } from '../types';

export const API_BASE_URL = 'http://localhost:8000/api';

// Function to fetch messages for a specific chat
export const fetchChatMessages = async (chatId: string): Promise<Message[]> => {
    const response = await fetch(`${API_BASE_URL}/chat/${chatId}/messages`);
    if (!response.ok) {
        throw new Error('Failed to fetch messages');
    }
    return await response.json();
};

// Function to fetch all conversations
export const fetchConversations = async (): Promise<Conversation[]> => {
    const response = await fetch(`${API_BASE_URL}/conversations`);
    if (!response.ok) {
        throw new Error('Failed to fetch conversations');
    }
    return await response.json();
};

// Function to send a normal chat message
export const sendChatMessage = async (content: string, chatId?: number): Promise<any> => {
    const payload = {
        message: content,
        chat_id: chatId
    };

    const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error('Failed to send message');
    }

    return await response.json();
};

// Function to send a streaming chat message
export const sendStreamingChatMessage = async (
    content: string,
    onToken: (token: string) => void,
    onComplete: () => void,
    onError: (error: string) => void,
    chatId?: number,
    options = { temperature: 0.7, max_length: 20, top_p: 0.9 }
): Promise<AbortController> => {
    const abortController = new AbortController();

    try {
        const payload = {
            message: content,
            chat_id: chatId,
            temperature: options.temperature,
            max_length: options.max_length,
            top_p: options.top_p
        };

        // Create the EventSource for SSE connection
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
            signal: abortController.signal
        });

        if (!response.body) {
            throw new Error('Response body is null');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let lastTokenEndsWithWord = false;
        let isDone = false;

        // Handle abort events
        abortController.signal.addEventListener('abort', () => {
            isDone = true;
            reader.cancel().catch(err => console.error('Error canceling reader:', err));
            onComplete();
        });

        const processStream = async () => {
            try {
                while (!isDone) {
                    const { done, value } = await reader.read();

                    if (done) {
                        if (!isDone) {
                            isDone = true;
                            onComplete();
                        }
                        break;
                    }

                    // Decode the received bytes to text
                    const text = decoder.decode(value, { stream: true });
                    buffer += text;

                    // Process the buffer line by line
                    while (buffer.includes('\n\n')) {
                        const lineEnd = buffer.indexOf('\n\n');
                        const line = buffer.slice(0, lineEnd);
                        buffer = buffer.slice(lineEnd + 2);

                        if (line.startsWith('data:')) {
                            const data = line.slice(5).trim();

                            if (data === '[DONE]') {
                                isDone = true;
                                onComplete();
                                return; // Exit immediately once we get DONE signal
                            } else if (data.startsWith('Error:')) {
                                onError(data);
                                isDone = true;
                                return;
                            } else {
                                // Smart token handling - add space if needed
                                const tokenText = data;

                                // Check if we need to add a space
                                const tokenStartsWithWord = /^[a-zA-Z0-9]/.test(tokenText);
                                const isPunctuation = /^[.,?!;:]/.test(tokenText);

                                // Add a space if the current token starts with a word character and the previous token
                                // ended with a word character, unless it's punctuation
                                let processedToken = tokenText;
                                if (tokenStartsWithWord && lastTokenEndsWithWord && !isPunctuation) {
                                    processedToken = ' ' + tokenText;
                                }

                                // Update lastTokenEndsWithWord state for next token
                                lastTokenEndsWithWord = /[a-zA-Z0-9]$/.test(tokenText);

                                onToken(processedToken);
                            }
                        }
                    }
                }
            } catch (error) {
                if (!isDone) {
                    isDone = true;
                    onError(error instanceof Error ? error.message : String(error));
                }
            } finally {
                // Ensure we clean up the reader if it's still active
                if (!isDone) {
                    isDone = true;
                    try {
                        reader.cancel();
                    } catch (e) {
                        console.error('Error canceling reader:', e);
                    }
                    onComplete();
                }
            }
        };

        processStream();
    } catch (error) {
        onError(error instanceof Error ? error.message : String(error));
    }

    return abortController;
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
    private onCompleteCallback: (() => void) | null = null;
    private onErrorCallback: ((error: string) => void) | null = null;

    constructor() {
        this.connect();
    }

    private connect(): void {
        if (this.ws) {
            this.ws.close();
        }

        // Create WebSocket connection
        const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/chat`;
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
                const data = JSON.parse(event.data);

                if (data.token) {
                    // Token received
                    if (this.onTokenCallback) {
                        this.onTokenCallback(data.token);
                    }
                } else if (data.status === 'complete') {
                    // Generation complete
                    if (this.onCompleteCallback) {
                        this.onCompleteCallback();
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
        onComplete: () => void,
        onError: (error: string) => void,
        chatId?: number,
        options = { temperature: 0.7, max_length: 20, top_p: 0.9 }
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
        options = { temperature: 0.7, max_length: 20, top_p: 0.9 }
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
            top_p: options.top_p
        };

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
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
    protected ws: WebSocket | null = null;
    protected isConnected: boolean = false;
    protected reconnectAttempts: number = 0;
    protected readonly maxReconnectAttempts: number = 3;
    protected readonly reconnectDelay: number = 1000; // 1 second

    // Callbacks for different events
    protected onTokenCallback: ((token: string) => void) | null = null;
    protected onCompleteCallback: ((response: any) => void) | null = null;
    protected onErrorCallback: ((error: string) => void) | null = null;

    constructor(autoConnect: boolean = false) {
        if (autoConnect) {
            this.connect();
        }
    }

    protected connect(): void {
        if (this.ws) {
            this.ws.close();
        }

        // Create WebSocket connection
        // qwen-instruct
        const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/qwen-instruct`;
        // const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/gemma-3-1b-it`;
        // const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/gemma-3-4b-it`;
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

                if (data.token || data.type === 'token') {
                    // Token received
                    if (this.onTokenCallback) {
                        this.onTokenCallback(data.token);
                    }
                } else if (data.status === 'complete' || data.type === 'end') {
                    // Generation complete
                    if (this.onCompleteCallback) {
                        this.onCompleteCallback(data);
                    }
                } else if (data.error || data.type === 'error') {
                    // Error received
                    const errorMessage = data.error || data.message || 'Unknown error';
                    if (this.onErrorCallback) {
                        this.onErrorCallback(errorMessage);
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

// WebSocket manager for vision model interactions
export class WebSocketVisionChatManager extends WebSocketChatManager {
    private modelId: string = 'smolvlm'; // Default vision model

    constructor(modelId?: string) {
        super(false);
        // Don't auto-connect in parent constructor
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
        }

        if (modelId) {
            this.modelId = modelId;
        }
        console.log('Initialized VisionChatManager with model ID:', this.modelId);
        // Don't connect yet - wait for the first message
    }

    // Override parent connect method
    protected override connect(): void {
        if (this.ws) {
            this.ws.close();
        }

        // Safety check - make sure model ID is set
        if (!this.modelId || this.modelId === 'undefined') {
            console.error('Cannot connect with empty or undefined model ID, using default');
            this.modelId = 'smolvlm';
        }

        // Create WebSocket connection to vision endpoint
        const wsUrl = `${API_BASE_URL.replace('http', 'ws').replace('/api', '')}/api/ws/vision/${this.modelId}`;
        console.log('Connecting to vision WebSocket URL:', wsUrl, 'with model ID:', this.modelId);
        this.ws = new WebSocket(wsUrl);

        // Setup event handlers - inherit from parent class
        this.ws.onopen = () => {
            console.log('Vision WebSocket connection established');
            this.isConnected = true;
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            try {
                console.log('Vision WebSocket event:', event);
                const data = JSON.parse(event.data);

                if (data.token || data.type === 'token') {
                    // Token received
                    if (this.onTokenCallback) {
                        this.onTokenCallback(data.token || '');
                    }
                } else if (data.status === 'complete' || data.type === 'end') {
                    // Generation complete
                    if (this.onCompleteCallback) {
                        this.onCompleteCallback(data);
                    }
                } else if (data.error || data.type === 'error') {
                    // Error received
                    const errorMessage = data.error || data.message || 'Unknown error';
                    console.error('Vision WebSocket error:', errorMessage);
                    if (this.onErrorCallback) {
                        this.onErrorCallback(errorMessage);
                    }
                }
            } catch (error) {
                console.error('Error processing Vision WebSocket message:', error);
                if (this.onErrorCallback) {
                    this.onErrorCallback('Error processing message');
                }
            }
        };

        // Other event handlers from parent
        this.ws.onclose = (event) => {
            this.isConnected = false;
            console.log(`Vision WebSocket connection closed: ${event.code}`);

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
            console.error('Vision WebSocket error:', error);
            if (this.onErrorCallback) {
                this.onErrorCallback('Vision WebSocket connection error');
            }
        };
    }

    public sendVisionChatMessage(
        content: string,
        imageUrl: string,
        onToken: (token: string) => void,
        onComplete: (response: any) => void,
        onError: (error: string) => void,
        chatId?: number,
        options: { temperature: number, max_length: number, top_p: number, model?: string } = {
            temperature: 0.7,
            max_length: 500,
            top_p: 0.9
        }
    ): void {
        // Update model ID if provided in options
        if (options.model) {
            this.setModelId(options.model);
        }

        // Set callbacks
        this.onTokenCallback = onToken;
        this.onCompleteCallback = onComplete;
        this.onErrorCallback = onError;

        // Ensure connection is active
        if (!this.isConnected) {
            this.connect(); // Connect with the current model ID
            // Small delay to allow connection to establish
            setTimeout(() => this.sendVisionMessageToServer(content, imageUrl, chatId, options), 1000);
        } else {
            this.sendVisionMessageToServer(content, imageUrl, chatId, options);
        }
    }

    private sendVisionMessageToServer(
        content: string,
        imageUrl: string,
        chatId?: number,
        options = { temperature: 0.7, max_length: 500, top_p: 0.9 }
    ): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            if (this.onErrorCallback) {
                this.onErrorCallback('Vision WebSocket not connected');
            }
            return;
        }

        const payload = {
            command: 'generate',
            message: content,
            image_url: imageUrl,
            chat_id: chatId,
            temperature: options.temperature,
            max_length: options.max_length,
            top_p: options.top_p
        };
        console.log('vision-ws-payload-to-server:', payload);

        this.ws.send(JSON.stringify(payload));
    }

    public setModelId(modelId: string): void {
        if (modelId && modelId !== this.modelId) {
            console.log(`Changing vision model from ${this.modelId} to ${modelId}`);
            this.modelId = modelId;
            // Reconnect with new model ID if already connected
            if (this.isConnected) {
                this.connect();
            }
        }
    }
}

// Export singleton instances for app-wide use
export const wsManager = new WebSocketChatManager(true); // Auto-connect for regular chat
export const wsVisionManager = new WebSocketVisionChatManager('smolvlm'); // Don't auto-connect for vision 
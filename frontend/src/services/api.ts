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
    protected messageQueue: string[] = [];
    protected modelId: string = 'qwen-instruct'; // Default model

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
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        if (this.ws?.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket already connecting');
            return;
        }

        // Create WebSocket connection with dynamic model ID
        const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/${this.modelId}`;
        console.log('Connecting to WebSocket URL:', wsUrl);

        // Close existing connection if any
        this.disconnect();

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connection established for model:', this.modelId);
            this.isConnected = true;
            this.reconnectAttempts = 0;

            // Process any queued messages
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                if (message && this.ws?.readyState === WebSocket.OPEN) {
                    this.ws.send(message);
                }
            }
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
        // Update model if needed
        if (options.model) {
            this.setModelId(options.model);
        }

        // Set callbacks
        this.onTokenCallback = onToken;
        this.onCompleteCallback = onComplete;
        this.onErrorCallback = onError;

        // Create the message payload
        const payload = {
            command: 'generate',
            message: content,
            chat_id: chatId,
            temperature: options.temperature,
            max_length: options.max_length,
            top_p: options.top_p,
            model: this.modelId // Use current modelId
        };

        const messageStr = JSON.stringify(payload);

        // If not connected, queue the message and connect
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.messageQueue.push(messageStr);
            this.connect();
        } else {
            // Send immediately if connected
            this.ws.send(messageStr);
        }
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
            this.ws.onclose = null; // Prevent reconnection attempts
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
        }
    }

    public setModelId(modelId: string): void {
        if (!modelId || modelId === this.modelId) {
            return;
        }

        const oldModel = this.modelId;
        this.modelId = modelId;
        console.log(`Changed model from ${oldModel} to ${modelId}`);

        // Don't automatically reconnect - wait for next message
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.disconnect();
        }
    }
}

// WebSocket manager for vision model interactions
export class WebSocketVisionChatManager extends WebSocketChatManager {
    protected modelId: string = 'smolvlm'; // Default vision model

    constructor(modelId?: string) {
        super(false); // Don't auto-connect in parent constructor
        if (modelId) {
            this.modelId = modelId;
        }
        console.log('Initialized VisionChatManager with model ID:', this.modelId);
    }

    // Override parent connect method
    protected override connect(): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('Vision WebSocket already connected');
            return;
        }

        if (this.ws?.readyState === WebSocket.CONNECTING) {
            console.log('Vision WebSocket already connecting');
            return;
        }

        // Close existing connection if any
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        // Safety check - make sure model ID is set
        if (!this.modelId || this.modelId === 'undefined') {
            console.error('Cannot connect with empty or undefined model ID, using default');
            this.modelId = 'smolvlm';
        }

        // Create WebSocket connection to vision endpoint
        const wsUrl = `${API_BASE_URL.replace('http', 'ws').replace('/api', '')}/api/ws/vision/${this.modelId}`;
        console.log('Connecting to vision WebSocket URL:', wsUrl);
        this.ws = new WebSocket(wsUrl);

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
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
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
}

// Export singleton instances for app-wide use
export const wsManager = new WebSocketChatManager(false); // Don't auto-connect
export const wsVisionManager = new WebSocketVisionChatManager(); // Don't auto-connect 
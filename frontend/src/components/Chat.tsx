import React, { useState, useEffect, useRef } from 'react';
import { Message, Conversation } from '../types';
import { fetchChatMessages, wsManager } from '../services/api';

interface ChatProps {
    chatId: string | null;
    onConversationUpdate: (conversation: Conversation) => void;
}

export const Chat: React.FC<ChatProps> = ({ chatId, onConversationUpdate }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    // Create a ref to track the current streaming content
    const streamingContentRef = useRef('');

    const fetchMessages = async () => {
        if (!chatId) {
            setMessages([]);
            return;
        }

        try {
            const data = await fetchChatMessages(chatId);
            setMessages(data);
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    };

    useEffect(() => {
        setMessages([]); // Clear messages when chatId changes
        fetchMessages();
    }, [chatId]);

    const sendMessage = async (content: string) => {
        if (!content.trim()) return;

        // Add user message to chat
        const userMessage: Message = {
            id: Date.now().toString(),
            content,
            role: 'user',
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setStreamingContent(''); // Reset streaming content
        streamingContentRef.current = ''; // Also reset the ref

        try {
            const chatIdNumber = chatId ? parseInt(chatId) : undefined;
            console.log('ws-send-chat-message-payload', content, chatIdNumber);
            // Use WebSocket implementation
            wsManager.sendChatMessage(
                content,
                (token) => {
                    // Update streaming content as tokens arrive
                    streamingContentRef.current += token;
                    setStreamingContent(streamingContentRef.current);
                },
                (response) => {
                    // On complete - stream is done
                    setIsLoading(false);

                    // Instead of fetching all messages again, add the assistant message directly
                    const finalContent = streamingContentRef.current;
                    if (finalContent) {
                        const assistantMessage: Message = {
                            id: `temp-${Date.now()}`,
                            content: finalContent,
                            role: 'assistant',
                            timestamp: new Date().toISOString()
                        };

                        setMessages(prev => [...prev, assistantMessage]);
                        setStreamingContent('');
                        streamingContentRef.current = '';
                    }

                    // Check if response contains the conversation data
                    if (response && response.conversation) {
                        // Use the conversation data directly from the WebSocket response
                        onConversationUpdate(response.conversation);
                    } else {
                        // Log a warning if no conversation data was received
                        console.warn('No conversation data received from backend');
                    }
                },
                (error) => {
                    console.error('WebSocket error:', error);
                    setIsLoading(false);
                },
                chatIdNumber
            );

        } catch (error) {
            console.error('Error sending message:', error);
            setIsLoading(false);
        }
    };

    const stopGeneration = () => {
        wsManager.stopGeneration();
        setIsLoading(false);
    };

    return (
        <div className="h-full flex flex-col">
            <div className="mb-4">
                <h2 className="text-xl font-semibold">
                    {chatId ? `Chat ${chatId}` : 'New Chat'}
                </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Chat messages */}
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`p-4 rounded-lg whitespace-pre-wrap ${message.role === 'user'
                            ? 'bg-blue-100 ml-auto max-w-[80%]'
                            : 'bg-gray-100 mr-auto max-w-[80%]'
                            }`}
                    >
                        {message.content}
                    </div>
                ))}

                {/* Streaming message */}
                {isLoading && streamingContent && (
                    <div className="bg-gray-100 p-4 rounded-lg mr-auto max-w-[80%] whitespace-pre-wrap">
                        {streamingContent}
                    </div>
                )}

                {/* Loading indicator */}
                {isLoading && !streamingContent && (
                    <div className="bg-gray-100 p-4 rounded-lg mr-auto">
                        <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input area */}
            <form onSubmit={(e) => {
                e.preventDefault();
                sendMessage(input);
            }} className="p-4 border-t mt-auto">
                <div className="flex space-x-4">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        className="flex-1 p-2 border rounded-lg"
                        placeholder="Type your message..."
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:bg-blue-300"
                    >
                        Send
                    </button>
                    {isLoading && (
                        <button
                            type="button"
                            onClick={stopGeneration}
                            className="px-4 py-2 bg-red-500 text-white rounded-lg"
                        >
                            Stop
                        </button>
                    )}
                </div>
            </form>
        </div>
    );
}; 
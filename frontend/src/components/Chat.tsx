import React, { useState, useEffect, useRef } from 'react';
import { Message, Conversation } from '../types';
import { fetchChatMessages, sendStreamingChatMessage, wsManager, API_BASE_URL, fetchConversations } from '../services/api';

interface ChatProps {
    chatId: string | null;
    onConversationUpdate: (conversation: Conversation) => void;
    useWebSocket?: boolean; // Option to toggle between WebSocket and SSE
}

export const Chat: React.FC<ChatProps> = ({ chatId, onConversationUpdate, useWebSocket = true }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    // Create a ref to track current request
    const activeStreamRef = useRef<AbortController | null>(null);
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

        // Cleanup function to abort any ongoing streams when component unmounts
        return () => {
            if (activeStreamRef.current) {
                activeStreamRef.current.abort();
                activeStreamRef.current = null;
            }
        };
    }, [chatId]);

    const sendMessage = async (content: string) => {
        if (!content.trim()) return;

        // Cancel any ongoing stream for SSE approach
        if (activeStreamRef.current) {
            activeStreamRef.current.abort();
            activeStreamRef.current = null;
        }

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

            if (useWebSocket) {
                // Use WebSocket implementation
                wsManager.sendChatMessage(
                    content,
                    (token) => {
                        // Update streaming content as tokens arrive
                        streamingContentRef.current += token;
                        setStreamingContent(streamingContentRef.current);
                    },
                    () => {
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

                        // Fetch the updated conversation and update the sidebar
                        if (chatIdNumber) {
                            fetchConversations()
                                .then(conversations => {
                                    const updatedConversation = conversations.find(
                                        conv => conv.id === chatIdNumber
                                    );
                                    if (updatedConversation) {
                                        onConversationUpdate(updatedConversation);
                                    }
                                })
                                .catch(err => console.error('Error fetching updated conversation:', err));
                        } else {
                            // This was a new conversation, fetch the latest conversations
                            // to get the newly created conversation ID
                            fetchConversations()
                                .then(conversations => {
                                    // The most recent conversation should be the first one
                                    if (conversations.length > 0) {
                                        onConversationUpdate(conversations[0]);
                                    }
                                })
                                .catch(err => console.error('Error fetching new conversation:', err));
                        }
                    },
                    (error) => {
                        console.error('WebSocket error:', error);
                        setIsLoading(false);
                    },
                    chatIdNumber
                );
            } else {
                // Use traditional SSE approach
                activeStreamRef.current = await sendStreamingChatMessage(
                    content,
                    (token) => {
                        // Update streaming content as tokens arrive
                        streamingContentRef.current += token;
                        setStreamingContent(streamingContentRef.current);
                    },
                    () => {
                        // On complete - stream is done
                        setIsLoading(false);
                        activeStreamRef.current = null;

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

                        // Fetch the updated conversation and update the sidebar
                        if (chatIdNumber) {
                            fetchConversations()
                                .then(conversations => {
                                    const updatedConversation = conversations.find(
                                        conv => conv.id === chatIdNumber
                                    );
                                    if (updatedConversation) {
                                        onConversationUpdate(updatedConversation);
                                    }
                                })
                                .catch(err => console.error('Error fetching updated conversation:', err));
                        } else {
                            // This was a new conversation, fetch the latest conversations
                            // to get the newly created conversation ID
                            fetchConversations()
                                .then(conversations => {
                                    // The most recent conversation should be the first one
                                    if (conversations.length > 0) {
                                        onConversationUpdate(conversations[0]);
                                    }
                                })
                                .catch(err => console.error('Error fetching new conversation:', err));
                        }
                    },
                    (error) => {
                        console.error('Streaming error:', error);
                        setIsLoading(false);
                        activeStreamRef.current = null;
                    },
                    chatIdNumber
                );
            }
        } catch (error) {
            console.error('Error sending message:', error);
            setIsLoading(false);
            activeStreamRef.current = null;
        }
    };

    const stopGeneration = () => {
        if (useWebSocket) {
            wsManager.stopGeneration();
        } else if (activeStreamRef.current) {
            activeStreamRef.current.abort();
            activeStreamRef.current = null;
        }
        setIsLoading(false);
    };

    return (
        <div className="h-full flex flex-col">
            <div className="mb-4">
                <h2 className="text-xl font-semibold">
                    {chatId ? `Chat ${chatId}` : 'New Chat'}
                </h2>
                <div className="mt-1 text-sm">
                    Using: {useWebSocket ? 'WebSocket (Bidirectional)' : 'Server-Sent Events'}
                </div>
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
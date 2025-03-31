import React, { useState, useEffect, useRef } from 'react';
import { Message, Conversation } from '../types';
import { fetchChatMessages, wsManager } from '../services/api';

interface ChatProps {
    chatId: string | null;
    onConversationUpdate: (conversation: Conversation) => void;
    isSidebarOpen: boolean;
}

// Input component for both new and existing chats
const ChatInput = ({
    input,
    setInput,
    sendMessage,
    isLoading,
    stopGeneration,
    className = ""
}: {
    input: string;
    setInput: (value: string) => void;
    sendMessage: (message: string) => void;
    isLoading: boolean;
    stopGeneration: () => void;
    className?: string;
}) => {
    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                sendMessage(input);
            }}
            className={`mx-4 ${className}`}
        >
            <div className="flex items-center space-x-2 bg-[#40414F] p-4 rounded-lg shadow-lg border border-gray-900/50">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="flex-1 bg-transparent text-white placeholder-gray-400 focus:outline-none"
                    placeholder="Type your message..."
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="p-1 rounded-lg text-gray-400 hover:bg-gray-600/30 hover:text-gray-200 disabled:hover:text-gray-400 transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
                        <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                    </svg>
                </button>
                {isLoading && (
                    <button
                        type="button"
                        onClick={stopGeneration}
                        className="p-1 rounded-lg text-gray-400 hover:bg-gray-600/30 hover:text-gray-200 transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
                            <path fillRule="evenodd" d="M4.5 7.5a3 3 0 013-3h9a3 3 0 013 3v9a3 3 0 01-3 3h-9a3 3 0 01-3-3v-9z" clipRule="evenodd" />
                        </svg>
                    </button>
                )}
            </div>
        </form>
    );
};

// New conversation component with welcome message and input
const NewConversation = ({
    input,
    setInput,
    sendMessage,
    isLoading,
    stopGeneration
}: {
    input: string;
    setInput: (value: string) => void;
    sendMessage: (message: string) => void;
    isLoading: boolean;
    stopGeneration: () => void;
}) => {
    return (
        <div className="flex flex-col items-center justify-center h-screen w-full">
            <div className="flex flex-col text-center space-y-6 mb-8">
                {/* <h1 className="text-4xl font-bold text-gray-800">ChatGPT</h1> */}
                <p className="text-2xl text-gray-300">How can I help you today?</p>
            </div>

            <div className="w-full max-w-[600px]">
                <ChatInput
                    input={input}
                    setInput={setInput}
                    sendMessage={sendMessage}
                    isLoading={isLoading}
                    stopGeneration={stopGeneration}
                />
            </div>
        </div>
    );
};

export const Chat: React.FC<ChatProps> = ({ chatId, onConversationUpdate, isSidebarOpen }) => {
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

    const isNewChat = !chatId && messages.length === 0;

    return (
        <div className="h-full flex flex-col">
            {!isNewChat && (
                <div className="max-w-[48rem] mx-auto w-full px-4">
                    <h2 className="text-xl font-semibold mb-4 text-gray-200">
                        {chatId ? `Chat ${chatId}` : 'New Chat'}
                    </h2>
                </div>
            )}

            {/* Messages area with padding at bottom to account for fixed input */}
            <div className="flex-1 overflow-y-auto">
                <div className={`${isNewChat ? 'h-full flex items-center justify-center' : 'max-w-[48rem] mx-auto w-full px-4 space-y-4 pb-32'}`}>
                    {isNewChat ? (
                        <NewConversation
                            input={input}
                            setInput={setInput}
                            sendMessage={sendMessage}
                            isLoading={isLoading}
                            stopGeneration={stopGeneration}
                        />
                    ) : (
                        <>
                            {/* Chat messages */}
                            {
                                messages.map((message) => (
                                    <div
                                        key={message.id}
                                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
                                    >
                                        <div
                                            className={`p-4 rounded-lg whitespace-pre-wrap ${message.role === 'user'
                                                ? 'bg-[#343541] text-white max-w-[80%]'
                                                : 'bg-[#444654] text-white max-w-[80%]'
                                                }`}
                                        >
                                            {message.content}
                                        </div>
                                    </div>
                                ))
                            }

                            {/* Streaming message */}
                            {isLoading && streamingContent && (
                                <div className="flex justify-start mb-4">
                                    <div className="bg-[#444654] text-white p-4 rounded-lg max-w-[80%] whitespace-pre-wrap">
                                        {streamingContent}
                                    </div>
                                </div>
                            )}

                            {/* Loading indicator */}
                            {isLoading && !streamingContent && (
                                <div className="flex justify-start mb-4">
                                    <div className="bg-[#444654] text-white p-4 rounded-lg">
                                        <div className="typing-indicator">
                                            <span></span>
                                            <span></span>
                                            <span></span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Input area - fixed for chat, inline for new chat */}
            {!isNewChat && (
                <div className={`fixed bottom-0 ${isSidebarOpen ? 'left-[260px]' : 'left-0'} right-0 bg-[#1E1E1E]`}>
                    <div className="max-w-[48rem] mx-auto w-full mb-8">
                        <ChatInput
                            input={input}
                            setInput={setInput}
                            sendMessage={sendMessage}
                            isLoading={isLoading}
                            stopGeneration={stopGeneration}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}; 
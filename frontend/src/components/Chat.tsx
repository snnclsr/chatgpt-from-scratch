import React, { useState } from 'react';
import { Message } from '../types';

interface ChatProps {
    chatId: string;
}

export const Chat: React.FC<ChatProps> = ({ chatId }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

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

        try {
            const response = await fetch('http://localhost:8000/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: content, chat_id: chatId }),
            });

            const data = await response.json();

            // Add assistant message to chat
            const assistantMessage: Message = {
                id: data.message_id.toString(),
                content: data.response,
                role: 'assistant',
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            // You might want to show an error message to the user here
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        sendMessage(input);
    };

    return (
        <div className="flex justify-center items-center min-h-screen bg-gray-50 p-4">
            <div className="w-full max-w-3xl bg-white rounded-lg shadow-lg flex flex-col h-[80vh]">
                {/* Chat messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`p-4 rounded-lg ${message.role === 'user'
                                ? 'bg-blue-100 ml-auto max-w-[80%]'
                                : 'bg-gray-100 mr-auto max-w-[80%]'
                                }`}
                        >
                            {message.content}
                        </div>
                    ))}
                    {isLoading && (
                        <div className="bg-gray-100 p-4 rounded-lg mr-auto">
                            Thinking...
                        </div>
                    )}
                </div>

                {/* Input area */}
                <form onSubmit={handleSubmit} className="p-4 border-t">
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
                    </div>
                </form>
            </div>
        </div>
    );
}; 
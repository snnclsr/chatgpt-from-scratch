import React, { useEffect } from 'react';
import { Conversation } from '../types';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    onNewChat: () => void;
    currentChatId: string;
    onSelectChat: (chatId: string) => void;
    conversations: Conversation[];
    setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>;
}

export const Sidebar: React.FC<SidebarProps> = ({
    isOpen,
    onClose,
    onNewChat,
    currentChatId,
    onSelectChat,
    conversations,
    setConversations,
}) => {
    useEffect(() => {
        const fetchInitialConversations = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/conversations');
                if (!response.ok) {
                    throw new Error('Failed to fetch conversations');
                }
                const data = await response.json();
                setConversations(data);
            } catch (error) {
                console.error('Error fetching conversations:', error);
            }
        };

        fetchInitialConversations();
    }, [setConversations]);

    if (!isOpen) return null;

    return (
        <div className="h-screen bg-white shadow-lg p-4">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Chats</h2>
                <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <button
                onClick={onNewChat}
                className="w-full mb-4 p-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
                New Chat
            </button>

            <div className="space-y-2">
                {conversations.map((conversation) => (
                    <button
                        key={conversation.id}
                        onClick={() => onSelectChat(conversation.id.toString())}
                        className={`w-full p-2 text-left rounded ${conversation.id.toString() === currentChatId
                            ? 'bg-gray-200'
                            : 'hover:bg-gray-100'
                            }`}
                    >
                        <div className="font-medium">{conversation.title || `Chat ${conversation.id}`}</div>
                        {conversation.preview && (
                            <div className="text-sm text-gray-500 truncate">
                                {conversation.preview}
                            </div>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}; 
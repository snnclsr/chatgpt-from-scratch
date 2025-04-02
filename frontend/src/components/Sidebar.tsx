import React, { useEffect, useState } from 'react';
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
    const [activeMenu, setActiveMenu] = useState<string | null>(null);

    const handleDeleteConversation = async (conversationId: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Failed to delete conversation');
            }

            // Remove the conversation from the local state
            setConversations(prevConversations =>
                prevConversations.filter(conv => conv.id.toString() !== conversationId)
            );

            // If the deleted conversation was the current one, trigger a new chat
            if (conversationId === currentChatId) {
                onNewChat();
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
        }
    };

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

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = () => setActiveMenu(null);
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    if (!isOpen) return null;

    const groupedConversations = groupConversationsByDate(conversations);
    return (
        <div className="h-screen bg-[#202123] shadow-lg p-4 flex flex-col border-r border-gray-700">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-white">Chats</h2>
                <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-800 rounded-lg text-gray-300"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <button
                onClick={onNewChat}
                className="w-full mb-4 p-2 bg-[#444654] text-white rounded hover:bg-[#565869]"
            >
                New Chat
            </button>

            <div className="space-y-4 overflow-y-auto flex-1">
                {groupedConversations.map(([group, chats]) => (
                    <div key={group} className="mb-2">
                        <h3 className="text-xl font-semibold text-gray-400 mb-2 px-2">{group}</h3>
                        <div className="space-y-2">
                            {chats.map((conversation) => (
                                <div
                                    key={conversation.id}
                                    className={`w-full p-2 rounded flex justify-between items-start group ${conversation.id.toString() === currentChatId
                                        ? 'bg-[#343541]'
                                        : 'hover:bg-[#2A2B32]'
                                        }`}
                                >
                                    <button
                                        onClick={() => onSelectChat(conversation.id.toString())}
                                        className="flex-1 text-left"
                                    >
                                        <div className="font-medium text-white">
                                            {conversation.title || `Chat ${conversation.id}`}
                                        </div>
                                        {/* {conversation.preview && (
                                            <div className="text-sm text-gray-400 truncate">
                                                {conversation.preview}
                                            </div>
                                        )} */}
                                    </button>
                                    <div className="relative ml-2 flex items-center">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setActiveMenu(activeMenu === conversation.id.toString() ? null : conversation.id.toString());
                                            }}
                                            className="p-1 hover:bg-gray-700 rounded text-white opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            ⋮
                                        </button>
                                        {activeMenu === conversation.id.toString() && (
                                            <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-[#2A2B32] ring-1 ring-black ring-opacity-5 z-50">
                                                <div className="py-1">
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDeleteConversation(conversation.id.toString());
                                                            setActiveMenu(null);
                                                        }}
                                                        className="w-full px-4 py-2 text-sm text-red-400 hover:bg-gray-700 flex items-center"
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                        </svg>
                                                        Delete
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Helper function to group conversations by date
function groupConversationsByDate(conversations: Conversation[]): [string, Conversation[]][] {
    // Get current date in local timezone
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const last7Days = new Date(today);
    last7Days.setDate(last7Days.getDate() - 7);

    const last30Days = new Date(today);
    last30Days.setDate(last30Days.getDate() - 30);

    const groups: Record<string, Conversation[]> = {
        'Today': [],
        'Yesterday': [],
        'Previous 7 Days': [],
        'Previous 30 Days': [],
        'Older': []
    };

    conversations.forEach(conversation => {
        try {
            // Convert string date to Date object
            const createdAt = new Date(conversation.created_at);

            // Check if date is valid before proceeding
            if (isNaN(createdAt.getTime())) {
                groups['Older'].push(conversation);
                return;
            }

            // Compare only the time portion of the dates
            const isToday = createdAt.getDate() === now.getDate() &&
                createdAt.getMonth() === now.getMonth();

            const isYesterday = createdAt.getDate() === yesterday.getDate() &&
                createdAt.getMonth() === yesterday.getMonth();

            // Calculate days difference ignoring year
            const timeDiff = now.getTime() - createdAt.getTime();
            const daysDiff = Math.floor(timeDiff / (1000 * 60 * 60 * 24));

            if (isToday) {
                groups['Today'].push(conversation);
            } else if (isYesterday) {
                groups['Yesterday'].push(conversation);
            } else if (daysDiff <= 7) {
                groups['Previous 7 Days'].push(conversation);
            } else if (daysDiff <= 30) {
                groups['Previous 30 Days'].push(conversation);
            } else {
                groups['Older'].push(conversation);
            }
        } catch (error) {
            console.error("Error processing date for conversation:", conversation.id, error);
            groups['Older'].push(conversation);
        }
    });

    // Return only groups that have conversations, sorted by conversations' created_at in descending order
    return Object.entries(groups)
        .filter(([_, groupConversations]) => groupConversations.length > 0)
        .map(([group, convs]) => [
            group,
            convs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        ]);
} 
import React, { useState, useCallback } from 'react';
import { Chat } from './components/Chat';
import { Sidebar } from './components/Sidebar';
import { Conversation } from './types';

function App() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);

    const updateConversations = useCallback((newConversation: Conversation) => {
        setConversations(prev => {
            // If conversation already exists, replace it
            const exists = prev.some(conv => conv.id === newConversation.id);
            if (exists) {
                return prev.map(conv =>
                    conv.id === newConversation.id ? newConversation : conv
                );
            }
            // Otherwise, add it to the beginning of the list
            return [newConversation, ...prev];
        });
        // Update current chat ID to the new conversation's ID
        setCurrentChatId(newConversation.id.toString());
    }, []);

    const createNewChat = () => {
        // Simply set currentChatId to null to indicate a new chat
        setCurrentChatId(null);
    };

    return (
        <div className="min-h-screen bg-gray-100 flex">
            {/* Sidebar */}
            <div className={`transition-all duration-300 ${isSidebarOpen ? 'w-64' : 'w-0'}`}>
                <Sidebar
                    isOpen={isSidebarOpen}
                    onClose={() => setIsSidebarOpen(false)}
                    onNewChat={createNewChat}
                    currentChatId={currentChatId}
                    onSelectChat={setCurrentChatId}
                    conversations={conversations}
                    setConversations={setConversations}
                />
            </div>

            {/* Main Content */}
            <div className="flex-1">
                <div className="p-4">
                    {!isSidebarOpen && (
                        <button
                            onClick={() => setIsSidebarOpen(true)}
                            className="mb-4 p-2 hover:bg-gray-200 rounded-lg"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                    )}
                    <Chat
                        chatId={currentChatId}
                        onConversationUpdate={updateConversations}
                    />
                </div>
            </div>
        </div>
    );
}

export default App; 
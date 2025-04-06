import React, { useState, useCallback } from 'react';
import { Chat } from './components/Chat';
import { Sidebar } from './components/Sidebar';
import { ModelSettings } from './components/ModelSettings';
import { Conversation, ModelSettings as ModelSettingsType } from './types';

function App() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [modelSettings, setModelSettings] = useState<ModelSettingsType>({
        temperature: 0.7,
        max_length: 100,
        top_p: 0.9,
        model: 'qwen-instruct'
    });

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
        <div className="min-h-screen bg-[#1E1E1E] text-white flex relative">
            {/* Overlay Sidebar */}
            <Sidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
                onNewChat={createNewChat}
                currentChatId={currentChatId}
                onSelectChat={setCurrentChatId}
                conversations={conversations}
                setConversations={setConversations}
            />

            {/* Main Content */}
            <div className="flex-1">
                <div className="p-4">
                    <Chat
                        chatId={currentChatId}
                        onConversationUpdate={updateConversations}
                        isSidebarOpen={isSidebarOpen}
                        modelSettings={modelSettings}
                    />
                </div>
            </div>

            {/* Fixed Sidebar Toggle Button */}
            {!isSidebarOpen && (
                <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="fixed top-4 left-4 p-2 hover:bg-gray-700 rounded-lg text-gray-200 z-10 bg-[#2E2E2E] shadow-lg"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
            )}

            {/* Fixed Settings Button */}
            <button
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                className="fixed top-4 right-4 p-2 hover:bg-gray-700 rounded-lg text-gray-200 z-10 bg-[#2E2E2E] shadow-lg"
            >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
            </button>

            {/* Settings Sidebar */}
            <ModelSettings
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                settings={modelSettings}
                onSettingsChange={setModelSettings}
            />
        </div>
    );
}

export default App;
import React from 'react';
import { Chat } from './components/Chat.tsx';

function App() {
    return (
        <div className="min-h-screen bg-gray-100">
            <Chat chatId="default" />
        </div>
    );
}

export default App; 
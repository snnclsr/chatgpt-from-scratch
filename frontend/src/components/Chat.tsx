import React, { useState, useEffect, useRef } from 'react';
import { Message, Conversation, ModelSettings } from '../types';
import { fetchChatMessages, wsManager, wsVisionManager, API_BASE_URL } from '../services/api';
import ModelSelector from './ModelSelector';
import ImageUpload from './ImageUpload';

interface ChatProps {
    chatId: string | null;
    onConversationUpdate: (conversation: Conversation) => void;
    isSidebarOpen: boolean;
    modelSettings: ModelSettings;
}

// Input component for both new and existing chats
const ChatInput = ({
    input,
    setInput,
    sendMessage,
    isLoading,
    stopGeneration,
    selectedImageFile,
    onImageSelected,
    clearSelectedImage,
    className = ""
}: {
    input: string;
    setInput: (value: string) => void;
    sendMessage: (message: string) => void;
    isLoading: boolean;
    stopGeneration: () => void;
    selectedImageFile: File | null;
    onImageSelected: (file: File | null) => void;
    clearSelectedImage: () => void;
    className?: string;
}) => {
    // Create a local preview URL for the selected image
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    // Update preview URL when selectedImageFile changes
    useEffect(() => {
        if (selectedImageFile) {
            const url = URL.createObjectURL(selectedImageFile);
            setPreviewUrl(url);

            // Clean up the URL when component unmounts or file changes
            return () => {
                URL.revokeObjectURL(url);
            };
        } else {
            setPreviewUrl(null);
        }
    }, [selectedImageFile]);

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                sendMessage(input);
            }}
            className={`mx-4 ${className}`}
        >
            <div className="flex flex-col bg-[#40414F] p-4 rounded-lg shadow-lg border border-gray-900/50">
                {/* Display selected image preview */}
                {previewUrl && (
                    <div className="mb-4 relative p-1 bg-gray-700 rounded-md inline-block">
                        <img
                            src={previewUrl}
                            alt="Preview"
                            className="max-w-full max-h-48 rounded"
                        />
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                clearSelectedImage();
                            }}
                            className="absolute top-2 right-2 p-1 bg-gray-800 text-white rounded-full opacity-80 hover:opacity-100"
                            disabled={isLoading}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                )}

                <div className="flex items-center space-x-2">
                    {/* Image upload button */}
                    {!selectedImageFile && (
                        <div className="flex-shrink-0">
                            <ImageUpload
                                onImageSelected={onImageSelected}
                                disabled={isLoading}
                            />
                        </div>
                    )}

                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        className="flex-1 bg-transparent text-white placeholder-gray-400 focus:outline-none"
                        placeholder={selectedImageFile ? "Ask about this image..." : "Type your message..."}
                        disabled={isLoading}
                    />

                    <button
                        type="submit"
                        disabled={isLoading || (!input.trim() && !selectedImageFile)}
                        className="p-1 rounded-lg text-gray-400 hover:bg-gray-600/30 hover:text-gray-200 disabled:hover:text-gray-400 transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
                            <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                        </svg>
                    </button>
                </div>
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
    stopGeneration,
    selectedImageFile,
    onImageSelected,
    clearSelectedImage
}: {
    input: string;
    setInput: (value: string) => void;
    sendMessage: (message: string) => void;
    isLoading: boolean;
    stopGeneration: () => void;
    selectedImageFile: File | null;
    onImageSelected: (file: File | null) => void;
    clearSelectedImage: () => void;
}) => {
    return (
        <div className="flex flex-col items-center justify-center h-screen w-full">
            <div className="flex flex-col text-center space-y-6 mb-8">
                <p className="text-2xl text-gray-300">How can I help you today?</p>
            </div>

            <div className="w-full max-w-[600px]">
                <ChatInput
                    input={input}
                    setInput={setInput}
                    sendMessage={sendMessage}
                    isLoading={isLoading}
                    stopGeneration={stopGeneration}
                    selectedImageFile={selectedImageFile}
                    onImageSelected={onImageSelected}
                    clearSelectedImage={clearSelectedImage}
                />
            </div>
        </div>
    );
};

export const Chat: React.FC<ChatProps> = ({ chatId, onConversationUpdate, isSidebarOpen, modelSettings }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    const [selectedModel, setSelectedModel] = useState('smolvlm');
    const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const streamingContentRef = useRef('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Add this function to scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    // Call scrollToBottom when messages change or streaming content updates
    useEffect(() => {
        scrollToBottom();
    }, [messages, streamingContent]);

    const fetchMessages = async () => {
        if (!chatId) {
            setMessages([]);
            return;
        }

        try {
            const data = await fetchChatMessages(chatId);
            setMessages(data);

            // Check if this conversation has any images and select vision model if so
            const hasImages = data.some(message => message.image_url);
            if (hasImages) {
                console.log("Conversation has images, setting model to 'smolvlm'");
                setSelectedModel('smolvlm');
            }
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    };

    useEffect(() => {
        setMessages([]); // Clear messages when chatId changes
        setSelectedImageFile(null); // Clear selected image
        fetchMessages();
    }, [chatId]);

    const handleImageSelected = (file: File | null) => {
        setSelectedImageFile(file);

        // Switch to vision model when an image is selected
        if (file) {
            console.log("Image selected, setting model to 'smolvlm'");
            setSelectedModel('smolvlm');
        }
    };

    const clearSelectedImage = () => {
        setSelectedImageFile(null);
    };

    // Upload image and return the image URL and conversation ID
    const uploadImage = async (file: File, existingChatId?: number): Promise<{ imageUrl: string, conversationId?: number } | null> => {
        setIsUploading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Add conversation ID if available
            if (existingChatId) {
                formData.append('conversation_id', existingChatId.toString());
            }

            // Ensure we're using the correct API endpoint
            const uploadUrl = `${API_BASE_URL.replace('/api', '')}/api/upload-image`;
            console.log('Uploading image to:', uploadUrl);

            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Upload response:', data);

            if (data.success) {
                return {
                    imageUrl: data.image_url,
                    conversationId: data.conversation_id
                };
            } else {
                throw new Error(data.message || 'Unknown error during upload');
            }
        } catch (err) {
            console.error('Image upload error:', err);
            return null;
        } finally {
            setIsUploading(false);
        }
    };

    const sendMessage = async (content: string) => {
        if (!content.trim() && !selectedImageFile) return;

        // Set default content if only an image was provided
        const messageContent = content.trim() || "What can you tell me about this image?";

        setIsLoading(true);

        try {
            // Determine which chat ID to use
            const chatIdNumber = chatId ? parseInt(chatId) : undefined;

            // Process based on whether we have an image
            if (selectedImageFile) {
                console.log('Sending message with image, file size:',
                    Math.round(selectedImageFile.size / 1024), 'KB',
                    'type:', selectedImageFile.type);

                // Upload the image first
                const uploadResult = await uploadImage(selectedImageFile, chatIdNumber);

                if (!uploadResult) {
                    // Handle upload failure
                    setIsLoading(false);
                    alert('Failed to upload image. Please try again.');
                    return;
                }

                const { imageUrl, conversationId } = uploadResult;
                const actualChatId = conversationId || chatIdNumber;

                console.log('Image uploaded successfully:', imageUrl, 'conversationId:', actualChatId);

                // Add user message to chat
                const userMessage: Message = {
                    id: Date.now().toString(),
                    content: messageContent,
                    role: 'user',
                    timestamp: new Date().toISOString(),
                    image_url: imageUrl
                };
                setMessages(prev => [...prev, userMessage]);
                setInput('');
                setStreamingContent('');
                streamingContentRef.current = '';

                // Use vision-specific WebSocket - make sure we're passing just the filename
                console.log("Using vision model:", selectedModel);
                wsVisionManager.sendVisionChatMessage(
                    messageContent,
                    imageUrl, // This should just be the filename, not the full path
                    (token) => {
                        streamingContentRef.current += token;
                        setStreamingContent(streamingContentRef.current);
                    },
                    (response) => {
                        // On complete
                        setIsLoading(false);

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

                        // Update conversation in sidebar if needed
                        if (response && response.conversation) {
                            onConversationUpdate(response.conversation);
                        } else if (conversationId) {
                            // Manually trigger a conversation update if we have a new conversation
                            onConversationUpdate({
                                id: conversationId,
                                title: 'Vision Chat',
                                created_at: new Date().toISOString(),
                                updated_at: new Date().toISOString()
                            });
                        }

                        // Clear the uploaded image after processing
                        clearSelectedImage();
                    },
                    (error) => {
                        console.error('Vision WebSocket error:', error);
                        setIsLoading(false);
                    },
                    actualChatId,
                    {
                        ...modelSettings,
                        max_length: 500, // Increase max length for vision responses
                        model: selectedModel // Pass the selected model explicitly
                    }
                );
            } else {
                // Regular chat without image
                // Add user message to chat
                const userMessage: Message = {
                    id: Date.now().toString(),
                    content: messageContent,
                    role: 'user',
                    timestamp: new Date().toISOString()
                };
                setMessages(prev => [...prev, userMessage]);
                setInput('');
                setStreamingContent('');
                streamingContentRef.current = '';

                console.log('Sending regular chat message', content, chatIdNumber, modelSettings, selectedModel);

                wsManager.sendChatMessage(
                    content,
                    (token) => {
                        streamingContentRef.current += token;
                        setStreamingContent(streamingContentRef.current);
                    },
                    (response) => {
                        // On complete
                        setIsLoading(false);

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

                        if (response && response.conversation) {
                            onConversationUpdate(response.conversation);
                        } else {
                            console.warn('No conversation data received from backend');
                        }
                    },
                    (error) => {
                        console.error('WebSocket error:', error);
                        setIsLoading(false);
                    },
                    chatIdNumber,
                    {
                        ...modelSettings,
                        model: selectedModel
                    }
                );
            }
        } catch (error) {
            console.error('Error sending message:', error);
            setIsLoading(false);
        }
    };

    const stopGeneration = () => {
        if (selectedImageFile) {
            wsVisionManager.stopGeneration();
        } else {
            wsManager.stopGeneration();
        }
        setIsLoading(false);
    };

    const isNewChat = !chatId && messages.length === 0;
    const conversationIdNumber = chatId ? parseInt(chatId) : undefined;

    return (
        <div className="h-full flex flex-col pt-2">
            {/* Loading indicator for image upload */}
            {isUploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
                    <div className="bg-gray-800 rounded-lg p-4 flex flex-col items-center">
                        <div className="loader mb-2"></div>
                        <div className="text-white">Uploading image...</div>
                    </div>
                </div>
            )}

            {!isNewChat && (
                <div className="max-w-[48rem] mx-auto w-full px-4 py-4 flex justify-between items-center">
                    <h2 className="text-xl font-semibold text-gray-200">
                        {chatId ? `Chat ${chatId}` : 'New Chat'}
                    </h2>
                    {/* <ModelSelector
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                    /> */}
                </div>
            )}

            {/* Messages area with padding at bottom to account for fixed input */}
            <div className="flex-1 overflow-y-auto pb-24">
                <div className={`${isNewChat ? 'h-full flex items-center justify-center' : 'max-w-[48rem] mx-auto w-full px-4 space-y-4'}`}>
                    {isNewChat ? (
                        <NewConversation
                            input={input}
                            setInput={setInput}
                            sendMessage={sendMessage}
                            isLoading={isLoading}
                            stopGeneration={stopGeneration}
                            selectedImageFile={selectedImageFile}
                            onImageSelected={handleImageSelected}
                            clearSelectedImage={clearSelectedImage}
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
                                            {message.image_url && (
                                                <div className="mb-3">
                                                    <img
                                                        src={`${API_BASE_URL.replace('/api', '')}/uploads/${message.image_url}`}
                                                        alt="Uploaded image"
                                                        className="max-w-full max-h-60 rounded"
                                                        onError={(e) => {
                                                            console.error('Error loading image:', e);
                                                            e.currentTarget.src = 'https://via.placeholder.com/400x300?text=Image+Not+Found';
                                                        }}
                                                    />
                                                </div>
                                            )}
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

                            {/* Add this invisible div for auto-scrolling */}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>
            </div>

            {/* Input area - fixed for chat, inline for new chat */}
            {!isNewChat && (
                <div className="fixed bottom-0 left-0 right-0 bg-[#1E1E1E] py-4 border-t border-gray-700">
                    <div className="max-w-[48rem] mx-auto w-full">
                        <ChatInput
                            input={input}
                            setInput={setInput}
                            sendMessage={sendMessage}
                            isLoading={isLoading}
                            stopGeneration={stopGeneration}
                            selectedImageFile={selectedImageFile}
                            onImageSelected={handleImageSelected}
                            clearSelectedImage={clearSelectedImage}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}; 
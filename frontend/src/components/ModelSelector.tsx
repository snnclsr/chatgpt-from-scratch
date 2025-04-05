import React from 'react';

interface ModelSelectorProps {
    selectedModel: string;
    onModelChange: (model: string) => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ selectedModel, onModelChange }) => {
    return (
        <div className="flex items-center space-x-2">
            <label htmlFor="model-select" className="text-gray-300 text-sm">Model:</label>
            <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => onModelChange(e.target.value)}
                className="bg-[#40414F] text-white rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-600"
            >
                <option value="mygpt">MyGPT</option>
                <option value="gemma">Gemma</option>
                <option value="qwen-instruct">Qwen</option>
            </select>
        </div>
    );
};

export default ModelSelector; 
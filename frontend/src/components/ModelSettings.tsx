import React from 'react';
import { ModelSettings as ModelSettingsType } from '../types';

interface ModelSettingsProps {
    isOpen: boolean;
    onClose: () => void;
    settings: ModelSettingsType;
    onSettingsChange: (settings: ModelSettingsType) => void;
}

export function ModelSettings({ isOpen, onClose, settings, onSettingsChange }: ModelSettingsProps) {
    return (
        <div
            className={`fixed right-0 top-0 h-full bg-[#2E2E2E] transition-all duration-300 ease-in-out border-l border-gray-700
                ${isOpen ? 'w-72 opacity-100' : 'w-0 opacity-0'}`}
            style={{ visibility: isOpen ? 'visible' : 'hidden' }}
        >
            <div className={`w-72 h-full p-4 overflow-y-auto ${isOpen ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}>
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-lg font-semibold text-gray-200">Model Settings</h2>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-gray-200"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-6">
                    <div>
                        <label className="block text-sm text-gray-300 mb-2">Model</label>
                        <select
                            value={settings.model}
                            onChange={(e) => onSettingsChange({
                                ...settings,
                                model: e.target.value
                            })}
                            className="w-full bg-[#40414F] text-white rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-600"
                        >
                            <option value="mygpt">MyGPT</option>
                            <option value="gemma">Gemma</option>
                            <option value="qwen-instruct">Qwen</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-300 mb-2">
                            Temperature: {settings.temperature.toFixed(2)}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={settings.temperature}
                            onChange={(e) => onSettingsChange({
                                ...settings,
                                temperature: parseFloat(e.target.value)
                            })}
                            className="w-full accent-blue-500"
                        />
                        <p className="text-xs text-gray-400 mt-1 break-words leading-relaxed">
                            Higher values make output more random, lower values more focused
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-300 mb-2">
                            Max Length: {settings.max_length}
                        </label>
                        <input
                            type="range"
                            min="1"
                            max="512"
                            value={settings.max_length}
                            onChange={(e) => onSettingsChange({
                                ...settings,
                                max_length: parseInt(e.target.value)
                            })}
                            className="w-full accent-blue-500"
                        />
                        <p className="text-xs text-gray-400 mt-1 break-words leading-relaxed">
                            Maximum number of tokens to generate
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-300 mb-2">
                            Top P: {settings.top_p.toFixed(2)}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={settings.top_p}
                            onChange={(e) => onSettingsChange({
                                ...settings,
                                top_p: parseFloat(e.target.value)
                            })}
                            className="w-full accent-blue-500"
                        />
                        <p className="text-xs text-gray-400 mt-1 break-words leading-relaxed">
                            Controls diversity via nucleus sampling
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
} 
import React from 'react';
import { Question } from '../../types';
import { QuestionMedia } from './QuestionMedia';

interface MultiChoiceProps {
    question: Question;
    currentAnswer: any; // expects array of numbers (indices)
    onAnswerChange: (answer: number[]) => void;
    isDarkMode: boolean;
    viewMode?: 'teacher' | 'student';
}

export const MultiChoiceQuestion: React.FC<MultiChoiceProps> = ({
    question,
    currentAnswer,
    onAnswerChange,
    isDarkMode,
    viewMode = 'student'
}) => {
    // helper to normalize currentAnswer to number[]
    const getAnswerArray = (): number[] => {
        if (Array.isArray(currentAnswer)) return currentAnswer;
        return [];
    };

    const answers = getAnswerArray();

    const toggleOption = (idx: number) => {
        const newAnswers = answers.includes(idx)
            ? answers.filter(a => a !== idx)
            : [...answers, idx].sort();
        onAnswerChange(newAnswers);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Question Text */}
            <div style={{ fontSize: '15px', fontWeight: '600', lineHeight: '1.5', color: isDarkMode ? '#F3F4F6' : '#111827' }}>
                {question.text}
            </div>

            {/* Media */}
            <QuestionMedia question={question} />

            {/* Instruction - Hide for Teacher if preferred, or keep */}
            {viewMode === 'student' && (
                <div style={{ fontSize: '14px', color: '#6B7280', marginBottom: '8px', fontStyle: 'italic' }}>
                    * Chọn tất cả đáp án đúng
                </div>
            )}

            {/* Options */}
            {question.options.map((option, idx) => {
                const isSelected = answers.includes(idx);
                const isCorrect = viewMode === 'teacher' && question.correct_answers?.includes(idx);

                return (
                    <button
                        key={idx}
                        onClick={() => viewMode !== 'teacher' && toggleOption(idx)}
                        style={{
                            padding: '16px',
                            textAlign: 'left',
                            borderRadius: '10px',
                            border: isCorrect
                                ? '2px solid #059669' // Green for correct
                                : isSelected
                                    ? '2px solid #4F46E5'
                                    : (isDarkMode ? '2px solid #374151' : '2px solid #E5E7EB'),
                            background: isCorrect
                                ? (isDarkMode ? 'rgba(5, 150, 105, 0.2)' : '#D1FAE5')
                                : isSelected
                                    ? (isDarkMode ? '#312E81' : '#EEF2FF')
                                    : (isDarkMode ? '#374151' : 'white'),
                            color: isDarkMode ? 'white' : 'inherit',
                            cursor: viewMode === 'teacher' ? 'default' : 'pointer',
                            fontSize: '15px',
                            transition: 'all 0.2s',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px'
                        }}
                    >
                        <div style={{
                            width: '20px', height: '20px',
                            borderRadius: '4px',
                            border: isCorrect ? 'none' : (isSelected ? 'none' : '2px solid #9CA3AF'),
                            background: isCorrect ? '#059669' : (isSelected ? '#4F46E5' : 'transparent'),
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'white', fontSize: '14px'
                        }}>
                            {(isSelected || isCorrect) && '✓'}
                        </div>
                        {option}
                    </button>
                );
            })}
        </div>
    );
};

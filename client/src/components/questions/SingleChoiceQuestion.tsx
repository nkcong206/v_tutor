import React from 'react';
import { Question } from '../../types';
import { QuestionMedia } from './QuestionMedia';

interface SingleChoiceProps {
    question: Question;
    currentAnswer: any;
    onAnswerChange: (answer: string) => void;
    isDarkMode: boolean;
    viewMode?: 'teacher' | 'student';
}

export const SingleChoiceQuestion: React.FC<SingleChoiceProps> = ({
    question,
    currentAnswer,
    onAnswerChange,
    isDarkMode,
    viewMode = 'student'
}) => {
    // Normalize correct answer to letter (A, B, C...)
    const getCorrectLetter = (): string => {
        if (typeof question.correct_answer === 'number') {
            return String.fromCharCode(65 + question.correct_answer);
        }
        return String(question.correct_answer || '');
    };
    const correctLetter = getCorrectLetter();

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Question Text */}
            <div style={{ fontSize: '15px', fontWeight: '600', lineHeight: '1.5', color: isDarkMode ? '#F3F4F6' : '#111827' }}>
                {question.text}
            </div>

            {/* Media */}
            <QuestionMedia question={question} />

            {/* Options */}
            {question.options.map((option, idx) => {
                const answerValue = String.fromCharCode(65 + idx); // A, B, C...
                const isSelected = currentAnswer === answerValue;
                const isCorrect = viewMode === 'teacher' && answerValue === correctLetter;

                return (
                    <button
                        key={idx}
                        onClick={() => viewMode !== 'teacher' && onAnswerChange(answerValue)}
                        style={{
                            padding: '16px',
                            textAlign: 'left',
                            borderRadius: '10px',
                            border: isCorrect
                                ? '2px solid #059669' // Green for correct answer in teacher view
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
                        <span style={{
                            fontWeight: '600',
                            color: isCorrect
                                ? '#059669'
                                : isSelected ? '#4F46E5' : '#9CA3AF',
                            minWidth: '24px'
                        }}>
                            {answerValue}.
                        </span>
                        {option}
                        {isCorrect && <span style={{ marginLeft: 'auto', color: '#059669' }}>✅</span>}
                    </button>
                );
            })}
        </div>
    );
};

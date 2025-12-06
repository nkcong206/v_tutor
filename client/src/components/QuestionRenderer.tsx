import React from 'react';
import { Question } from '../types';
import { SingleChoiceQuestion } from './questions/SingleChoiceQuestion';
import { MultiChoiceQuestion } from './questions/MultiChoiceQuestion';
import { FillInBlanksQuestion } from './questions/FillInBlanksQuestion';

interface Props {
    question: Question;
    currentAnswer: any;
    onAnswerChange: (answer: any) => void;
    isDarkMode: boolean;
    onCheckBlank?: (index: number, value: string) => boolean;
    viewMode?: 'teacher' | 'student';
    onAnswerCommit?: () => void;
}

export const QuestionRenderer: React.FC<Props> = ({
    question,
    currentAnswer,
    onAnswerChange,
    isDarkMode,
    onCheckBlank,
    viewMode = 'student',
    onAnswerCommit
}) => {
    const type = question.type || 'single_choice';

    if (type.includes('fill_in_blanks') || type.includes('fill_in')) {
        return (
            <FillInBlanksQuestion
                question={question}
                currentAnswer={currentAnswer}
                onAnswerChange={onAnswerChange}
                isDarkMode={isDarkMode}
                onCheckBlank={onCheckBlank}
                viewMode={viewMode}
                onAnswerCommit={onAnswerCommit}
            />
        );
    }

    if (type.includes('multi_choice') || type.includes('multi')) {
        return (
            <MultiChoiceQuestion
                question={question}
                currentAnswer={currentAnswer}
                onAnswerChange={onAnswerChange}
                isDarkMode={isDarkMode}
                viewMode={viewMode}
            />
        );
    }

    // Default: Single Choice
    return (
        <SingleChoiceQuestion
            question={question}
            currentAnswer={currentAnswer}
            onAnswerChange={onAnswerChange}
            isDarkMode={isDarkMode}
            viewMode={viewMode}
        />
    );
};

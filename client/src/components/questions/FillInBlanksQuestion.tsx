import React, { useMemo } from 'react';
import { Question } from '../../types';
import { QuestionMedia } from './QuestionMedia';
import { LatexText } from '../LatexText';

interface FillInBlanksProps {
    question: Question;
    currentAnswer: any; // expects array of strings
    onAnswerChange: (answer: string[]) => void;
    isDarkMode: boolean;
    onCheckBlank?: (index: number, value: string) => boolean;
    viewMode: 'teacher' | 'student';
    onAnswerCommit?: () => void;
}

export const FillInBlanksQuestion: React.FC<FillInBlanksProps> = ({
    question,
    currentAnswer,
    onAnswerChange,
    isDarkMode,
    onCheckBlank,
    viewMode,
    onAnswerCommit
}) => {
    // helper to normalize currentAnswer to string[]
    const getAnswerArray = (): string[] => {
        if (Array.isArray(currentAnswer)) return currentAnswer;
        if (typeof currentAnswer === 'string' && currentAnswer) {
            try { return JSON.parse(currentAnswer); } catch { return [currentAnswer]; }
        }
        return [];
    };

    const inputs = getAnswerArray();
    const correctAnswers = (question.correct_answers || []) as unknown as string[];
    const parts = question.text.split('___');

    // Memoize shuffled answers for student view
    const wordBank = useMemo(() => {
        if (viewMode === 'teacher') return correctAnswers;

        // Fisher-Yates shuffle
        const shuffled = [...correctAnswers];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }, [question.id, viewMode]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Media always at top? Current Renderer had: Media -> Text(with inputs). 
                Wait, previously we discussed Text -> Media -> Options.
                But for FiB, the text IS the options area.
                So: Media -> Text (with blanks).
                Let's stick to consistent placement: Media below text?
                Actually for FiB, usually text flows around content.
                Let's keep Media at Top for FiB as per previous logic, OR consistent Text -> Media.
                If Text -> Media, then "My name is [____]" -> [Image] -> [Word Bank].
                This seems reasonable.
                Wait, previous implementation in QuestionRenderer:
                renderFillInBlanks: 
                  renderMedia()
                  Text (parts.map)
                  Word Bank
                
                If we want consistent Text -> Media -> Options, then:
                Text (parts) -> Media -> WordBank.
                BUT Text contains the blanks (inputs). 
                If the text refers to the image, usually Image first is better context?
                "Describe the image: This is a [____]" -> Image first is standard.
                However, user wanted Consistency.
                Let's put Media ABOVE text for FiB (Standard). 
                And for others? SingleChoice: Text -> Media -> Options.
                
                Actually the user complained about "lẫn lộn" (mixed up).
                Let's stick to: Question Text (Prompt) -> Media -> Interaction Area.
                For Single/Multi: Prompt is `question.text`.
                For FiB: `question.text` is the sentence with blanks. It IS the interaction area.
                IS there a separate prompt? Usually no.
                So for FiB: Media -> Text (Interaction).
            */}

            <QuestionMedia question={question} />

            {/* Sentences with Blanks */}
            <div style={{ lineHeight: '2.5', fontSize: '15px', color: isDarkMode ? '#F3F4F6' : '#111827' }}>
                {parts.map((part, idx) => (
                    <React.Fragment key={idx}>
                        <span><LatexText>{part}</LatexText></span>
                        {idx < parts.length - 1 && (
                            <span style={{ position: 'relative', display: 'inline-block', margin: '0 8px' }}>
                                <input
                                    type="text"
                                    value={inputs[idx] || ''}
                                    placeholder={viewMode === 'teacher' ? `${correctAnswers[idx]}` : `${idx + 1}`}
                                    onChange={(e) => {
                                        const newInputs = [...inputs];
                                        newInputs[idx] = e.target.value;
                                        onAnswerChange(newInputs);
                                    }}
                                    onBlur={() => {
                                        if (onCheckBlank) {
                                            const correct = onCheckBlank(idx, inputs[idx]);
                                            const el = document.getElementById(`blank-feedback-${question.id}-${idx}`);
                                            if (el) {
                                                el.innerText = correct ? "✅ Chính xác!" : "❌ Sai rồi";
                                                el.style.color = correct ? "#059669" : "#DC2626";
                                            }
                                        }
                                        onAnswerCommit?.();
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            if (onCheckBlank) {
                                                const correct = onCheckBlank(idx, inputs[idx]);
                                                const el = document.getElementById(`blank-feedback-${question.id}-${idx}`);
                                                if (el) {
                                                    el.innerText = correct ? "✅ Chính xác!" : "❌ Sai rồi";
                                                    el.style.color = correct ? "#059669" : "#DC2626";
                                                }
                                            }
                                            onAnswerCommit?.();
                                        }
                                    }}
                                    style={{
                                        background: 'transparent',
                                        color: isDarkMode ? 'white' : 'black',
                                        textAlign: 'center',
                                        border: 'none',
                                        borderBottom: '2px solid #4F46E5',
                                        fontWeight: 'bold',
                                        width: `${Math.max(40, Math.max((inputs[idx] || '').length, viewMode === 'teacher' ? (correctAnswers[idx] || '').length + 2 : 2) * 12 + 10)}px`,
                                        minWidth: '40px',
                                        outline: 'none',
                                        margin: '0 4px',
                                        fontSize: '15px',
                                        padding: '0 4px'
                                    }}
                                />
                                <div
                                    id={`blank-feedback-${question.id}-${idx}`}
                                    style={{
                                        position: 'absolute',
                                        top: '100%', left: 0,
                                        fontSize: '12px', whiteSpace: 'nowrap'
                                    }}
                                />
                            </span>
                        )}
                    </React.Fragment>
                ))}
            </div>

            {/* Word Bank */}
            {correctAnswers.length > 0 && (
                <div style={{
                    marginTop: '20px',
                    padding: '12px',
                    background: isDarkMode ? 'rgba(255,255,255,0.03)' : '#F9FAFB',
                    borderRadius: '8px'
                }}>
                    <div style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        color: isDarkMode ? '#9CA3AF' : '#6B7280',
                        marginBottom: '6px',
                        textTransform: 'uppercase',
                    }}>
                        {viewMode === 'teacher' ? 'Đáp án:' : 'Gợi ý:'}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {wordBank.map((word: string, idx: number) => (
                            <div key={idx} style={{
                                padding: '4px 8px',
                                background: isDarkMode ? '#374151' : '#F3F4F6',
                                borderRadius: '4px',
                                fontSize: '13px',
                                color: isDarkMode ? '#D1D5DB' : '#4B5563',
                            }}>
                                {viewMode === 'teacher' && <span style={{ marginRight: '4px' }}>{idx + 1}.</span>}
                                <LatexText>{word}</LatexText>
                            </div>
                        ))}
                    </div>
                </div>
            )}


        </div>
    );
};

import React, { useState } from 'react';
import { QuestionRenderer } from '../components/QuestionRenderer';
import { useTheme } from '../contexts/ThemeContext';
import { Question } from '../types';

export function UIPreviewPage() {
    const { theme, toggleTheme } = useTheme();
    const isDarkMode = theme === 'dark';
    const [viewMode, setViewMode] = useState<'teacher' | 'student'>('student');

    // Mock Questions for 9 Scenarios (3 Types x 3 Media)

    // 1. Single Choice
    const qSingleNone: Question = {
        id: 1, type: 'single_choice', text: 'Single Choice (No Media)',
        options: ['Option A', 'Option B', 'Option C'], correct_answer: 'A'
    };
    const qSingleImage: Question = {
        id: 2, type: 'image_single_choice', text: 'Single Choice (Image)',
        options: ['Apple', 'Banana', 'Orange'], correct_answer: 'A',
        image_url: 'https://placehold.co/600x400/png?text=Mock+Image'
    };
    const qSingleAudio: Question = {
        id: 3, type: 'audio_single_choice', text: 'Single Choice (Audio)',
        options: ['Hear A', 'Hear B', 'Hear C'], correct_answer: 'A',
        audio_url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    };

    // 2. Multi Choice
    const qMultiNone: Question = {
        id: 4, type: 'multi_choice', text: 'Multi Choice (No Media)',
        options: ['Option A', 'Option B', 'Option C', 'Option D'], correct_answers: [0, 2]
    };
    const qMultiImage: Question = {
        id: 5, type: 'image_multi_choice', text: 'Multi Choice (Image)',
        options: ['Cat', 'Dog', 'Fish', 'Bird'], correct_answers: [0, 1],
        image_url: 'https://placehold.co/600x400/png?text=Pet+Image'
    };
    const qMultiAudio: Question = {
        id: 6, type: 'audio_multi_choice', text: 'Multi Choice (Audio)',
        options: ['Sound 1', 'Sound 2', 'Sound 3'], correct_answers: [0, 2],
        audio_url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    };

    // 3. Fill In Blanks
    const qFillNone: Question = {
        id: 7, type: 'fill_in_blanks', text: 'The sky is ___ and grass is ___',
        options: [], correct_answers: ['blue', 'green'] as any
    };
    const qFillImage: Question = {
        id: 8, type: 'image_fill_in_blanks' as any, text: 'This is a ___ and that is a ___',
        options: [], correct_answers: ['dog', 'cat'] as any,
        image_url: 'https://placehold.co/600x400/png?text=Animals'
    };
    const qFillAudio: Question = {
        id: 9, type: 'audio_fill_in_blanks' as any, text: 'Listen and fill: The word is ___',
        options: [], correct_answers: ['hello'] as any,
        audio_url: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    };

    // 4. Math Questions (LaTeX)
    const qMathSingle: Question = {
        id: 10, type: 'single_choice',
        text: 'Giải phương trình: $x^2 - 4 = 0$. Tìm $x$?',
        options: ['$x = 2$', '$x = -2$', '$x = \\pm 2$', '$x = 4$'],
        correct_answer: 2
    };
    const qMathMulti: Question = {
        id: 11, type: 'multi_choice',
        text: 'Chọn tất cả các biểu thức tương đương với $\\frac{a^2 - b^2}{a - b}$ (với $a \\neq b$):',
        options: ['$a + b$', '$a - b$', '$(a+b)(a-b)$', '$\\frac{(a-b)(a+b)}{a-b}$'],
        correct_answers: [0, 3]
    };
    const qMathFill: Question = {
        id: 12, type: 'fill_in_blanks',
        text: 'Tính: $2^3 = $ ___ và $\\sqrt{16} = $ ___',
        options: [],
        correct_answers: ['8', '4'] as any
    };

    const allQuestions = [
        qSingleNone, qSingleImage, qSingleAudio,
        qMultiNone, qMultiImage, qMultiAudio,
        qFillNone, qFillImage, qFillAudio,
        qMathSingle, qMathMulti, qMathFill
    ];

    const [answers, setAnswers] = useState<Record<number, any>>({});

    return (
        <div style={{ padding: '20px', background: isDarkMode ? '#111827' : '#F3F4F6', minHeight: '100vh', color: isDarkMode ? 'white' : 'black' }}>
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
                    <h1>UI Preview (12 Types - including Math/LaTeX)</h1>

                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        {/* View Mode Toggle */}
                        <div style={{ display: 'flex', background: isDarkMode ? '#374151' : '#E5E7EB', borderRadius: '8px', padding: '4px' }}>
                            <button
                                onClick={() => setViewMode('student')}
                                style={{
                                    padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                                    background: viewMode === 'student' ? (isDarkMode ? '#4B5563' : 'white') : 'transparent',
                                    color: isDarkMode ? 'white' : 'black', fontWeight: viewMode === 'student' ? 'bold' : 'normal',
                                    boxShadow: viewMode === 'student' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                    transition: 'all 0.2s'
                                }}
                            >
                                Học sinh
                            </button>
                            <button
                                onClick={() => setViewMode('teacher')}
                                style={{
                                    padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                                    background: viewMode === 'teacher' ? (isDarkMode ? '#4B5563' : 'white') : 'transparent',
                                    color: isDarkMode ? 'white' : 'black', fontWeight: viewMode === 'teacher' ? 'bold' : 'normal',
                                    boxShadow: viewMode === 'teacher' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                    transition: 'all 0.2s'
                                }}
                            >
                                Giáo viên
                            </button>
                        </div>

                        <button onClick={toggleTheme} style={{ padding: '8px 12px', borderRadius: '8px', cursor: 'pointer' }}>
                            {theme === 'light' ? '🌙' : '☀️'}
                        </button>
                    </div>
                </div>

                {allQuestions.map((q, idx) => (
                    <div key={q.id} style={{
                        marginBottom: '30px',
                        padding: '20px',
                        background: isDarkMode ? '#1F2937' : 'white',
                        borderRadius: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}>
                        <div style={{ marginBottom: '10px', fontSize: '12px', color: '#888', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Typ: <code>{q.type}</code></span>
                            <span>ID: {q.id}</span>
                        </div>
                        <QuestionRenderer
                            question={q}
                            currentAnswer={answers[q.id]}
                            onAnswerChange={(ans) => setAnswers({ ...answers, [q.id]: ans })}
                            isDarkMode={isDarkMode}
                            viewMode={viewMode}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';

const API_BASE_URL = 'http://localhost:8000';

interface Question {
    id: number;
    text: string;
    options: string[];
    correct_answer?: string;
}

interface ExamResult {
    student_name: string;
    score: number;
    total: number;
    percentage: number;
    answers: Record<string, {
        student_answer: string;
        correct_answer: string;
        is_correct: boolean;
        explanation: string;
        question_text: string;
    }>;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export function StudentPage() {
    const { examId } = useParams<{ examId: string }>();
    const [studentName, setStudentName] = useState('');
    const [isStarted, setIsStarted] = useState(false);
    const [questions, setQuestions] = useState<Question[]>([]);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState<ExamResult | null>(null);

    // AI Tutor state
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [chatInput, setChatInput] = useState('');
    const [isChatLoading, setIsChatLoading] = useState(false);
    const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([
        "Em chưa hiểu đề bài lắm",
        "Giải thích từ khóa trong đề",
        "Gợi ý cách làm",
        "Hỏi thêm"
    ]);
    const [attemptCounts, setAttemptCounts] = useState<Record<number, number>>({});
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [latestBubble, setLatestBubble] = useState<string | null>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    useEffect(() => {
        if (examId && isStarted) {
            loadExam();
        }
    }, [examId, isStarted]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages]);

    const loadExam = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/exam/${examId}`);
            if (!response.ok) {
                throw new Error('Không tìm thấy bài kiểm tra');
            }
            const data = await response.json();
            setQuestions(data.questions);
            // Add welcome message from AI
            setChatMessages([{
                role: 'assistant',
                content: `Chào ${studentName}! 👋 Mình là AI Tutor, sẽ đồng hành cùng em trong bài kiểm tra này. Em có thể hỏi mình bất cứ lúc nào nhé! Nhớ là mình sẽ gợi ý cho em suy nghĩ, chứ không nói đáp án đâu nhé! 😊`
            }]);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleStart = () => {
        if (!studentName.trim()) {
            setError('Vui lòng nhập họ tên');
            return;
        }
        setError('');
        setIsStarted(true);
    };

    const selectAnswer = (questionId: number, answer: string) => {
        const prevAnswer = answers[questionId.toString()];
        const isNewAnswer = prevAnswer !== answer;

        setAnswers({ ...answers, [questionId.toString()]: answer });

        if (isNewAnswer) {
            // Update attempt count
            const newAttempts = (attemptCounts[questionId] || 0) + 1;
            setAttemptCounts({ ...attemptCounts, [questionId]: newAttempts });

            // Check if answer is correct
            const question = questions.find(q => q.id === questionId);
            if (question) {
                // Check if answer is correct (handle "A" vs "A. Answer content")
                const isCorrect = question.correct_answer === answer || question.correct_answer?.startsWith(answer + '.');

                // DEBUG LOG
                console.log('=== DEBUG SELECT ANSWER ===');
                console.log('Question:', question.text);
                console.log('Selected answer:', answer);
                console.log('Correct answer from API:', question.correct_answer);
                console.log('Is correct:', isCorrect);
                console.log('Options:', question.options);
                console.log('===========================');

                // Send context to AI silently (don't show "Em chọn X" in chat)
                sendContextToAI(questionId, answer, isCorrect, newAttempts);
            }
        }
    };

    // Silent context update - only shows AI response, not the trigger
    const sendContextToAI = async (
        questionId: number,
        selectedAnswer: string,
        isCorrect: boolean,
        attemptCount: number
    ) => {
        const question = questions.find(q => q.id === questionId);
        if (!question) return;

        // Find the full option text (e.g., "A. 3" from answer "A")
        const selectedOption = question.options.find((opt: string) => opt.startsWith(selectedAnswer + '.')) || selectedAnswer;
        const correctOption = question.options.find((opt: string) => opt.startsWith(question.correct_answer + '.')) || question.correct_answer;

        // Abort previous request if exists
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // Create new controller
        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsChatLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/tutor/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    exam_id: examId,
                    question_id: questionId,
                    student_name: studentName,
                    message: `[Học sinh chọn: ${selectedOption}]`,
                    question_text: question.text,
                    options: question.options,
                    selected_answer: selectedOption,
                    correct_answer: correctOption,
                    is_correct: isCorrect,
                    attempt_count: attemptCount
                })
            });

            if (response.ok) {
                const data = await response.json();
                const aiMessage = data.response;
                setChatMessages(prev => [...prev, { role: 'assistant', content: aiMessage }]);
                setSuggestedPrompts(data.suggested_prompts);

                if (!isChatOpen) {
                    setLatestBubble(aiMessage);
                }
            }
        } catch (err: any) {
            if (err.name === 'AbortError') return;
            console.error('Chat error:', err);
        } finally {
            if (abortControllerRef.current === controller) {
                setIsChatLoading(false);
                abortControllerRef.current = null;
            }
        }
    };

    // User-initiated chat message (visible in chat)
    const sendChatMessage = async (message: string) => {
        if (!message.trim()) return;

        const question = questions[currentQuestion];
        if (!question) return;

        // Add user message to visible chat
        setChatMessages(prev => [...prev, { role: 'user', content: message }]);
        setChatInput('');
        setIsChatLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/tutor/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exam_id: examId,
                    question_id: question.id,
                    student_name: studentName,
                    message: message,
                    question_text: question.text,
                    options: question.options,
                    selected_answer: answers[question.id.toString()],
                    is_correct: question.correct_answer === answers[question.id.toString()] || question.correct_answer?.startsWith(answers[question.id.toString()] + '.'),
                    attempt_count: attemptCounts[question.id] || 0
                })
            });

            if (response.ok) {
                const data = await response.json();
                setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
                setSuggestedPrompts(data.suggested_prompts);
            }
        } catch (err) {
            console.error('Chat error:', err);
        } finally {
            setIsChatLoading(false);
        }
    };

    const handleSubmit = async () => {
        // Calculate result on CLIENT SIDE for instant UI
        let correct = 0;
        const answerDetails: Record<string, {
            student_answer: string;
            correct_answer: string;
            is_correct: boolean;
            explanation: string;
            question_text: string;
        }> = {};

        for (const q of questions) {
            const qId = String(q.id);
            const studentAnswer = answers[qId] || '';
            const isCorrect = studentAnswer.toUpperCase() === q.correct_answer.toUpperCase();

            if (isCorrect) correct++;

            answerDetails[qId] = {
                student_answer: studentAnswer,
                correct_answer: q.correct_answer,
                is_correct: isCorrect,
                explanation: q.explanation || '',
                question_text: q.text
            };
        }

        const total = questions.length;
        const percentage = total > 0 ? (correct / total * 100) : 0;

        // Build result object (same structure as server response)
        const clientResult = {
            student_name: studentName,
            score: correct,
            total: total,
            percentage: Math.round(percentage * 10) / 10,
            answers: answerDetails,
            submitted_at: new Date().toISOString()
        };

        // Show result IMMEDIATELY (optimistic UI)
        setResult(clientResult);

        // Sync to server in BACKGROUND (don't wait)
        fetch(`${API_BASE_URL}/api/exam/exam/${examId}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_name: studentName, answers }),
        }).catch(err => {
            console.error('Background sync error:', err);
            // Don't show error to user since they already see their result
        });
    };

    const { theme, toggleTheme } = useTheme();
    const isDarkMode = theme === 'dark';

    // Helper for Theme Toggle Button
    const ThemeToggle = () => (
        <button
            onClick={toggleTheme}
            style={{
                position: 'fixed',
                top: '20px',
                right: '20px',
                background: isDarkMode ? '#374151' : 'white',
                border: isDarkMode ? '1px solid #4B5563' : '1px solid #E5E7EB',
                borderRadius: '50%',
                width: '40px',
                height: '40px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                zIndex: 1000,
                fontSize: '20px'
            }}
            title={isDarkMode ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
        >
            {isDarkMode ? '☀️' : '🌙'}
        </button>
    );

    // Name Entry Screen
    if (!isStarted) {
        return (
            <div style={{
                minHeight: '100vh',
                background: isDarkMode ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)' : 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px'
            }}>
                <ThemeToggle />
                <div style={{
                    background: isDarkMode ? '#374151' : 'white',
                    borderRadius: '20px',
                    padding: '40px',
                    maxWidth: '400px',
                    width: '100%',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                    textAlign: 'center',
                    color: isDarkMode ? 'white' : '#1F2937'
                }}>
                    <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>🎓</h1>
                    <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
                        Bài kiểm tra
                    </h2>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: isDarkMode ? '#D1D5DB' : '#374151' }}>
                            Nhập họ và tên của bạn:
                        </label>
                        <input
                            placeholder="VD: Nguyễn Văn A"
                            value={studentName}
                            onChange={(e) => setStudentName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                            style={{
                                width: '100%',
                                padding: '14px',
                                borderRadius: '10px',
                                border: '2px solid #E5E7EB',
                                fontSize: '16px',
                                textAlign: 'center',
                                boxSizing: 'border-box',
                                background: isDarkMode ? '#1F2937' : 'white',
                                color: isDarkMode ? 'white' : 'black'
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            padding: '12px',
                            background: '#FEE2E2',
                            borderRadius: '8px',
                            color: '#DC2626',
                            marginBottom: '16px'
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        onClick={handleStart}
                        disabled={!studentName.trim()}
                        style={{
                            width: '100%',
                            padding: '14px',
                            background: studentName.trim() ? (isDarkMode ? '#10B981' : 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)') : '#D1D5DB',
                            color: 'white',
                            border: 'none',
                            borderRadius: '10px',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            cursor: studentName.trim() ? 'pointer' : 'not-allowed'
                        }}
                    >
                        Bắt đầu làm bài →
                    </button>
                </div>
            </div>
        );
    }

    // Loading Screen
    if (isLoading) {
        return (
            <div style={{
                minHeight: '100vh',
                background: isDarkMode ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)' : 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}>
                <ThemeToggle />
                <div style={{ textAlign: 'center', color: 'white' }}>
                    <p style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</p>
                    <p style={{ fontSize: '18px' }}>Đang tải bài kiểm tra...</p>
                </div>
            </div>
        );
    }

    // Error Screen
    if (error && !result) {
        return (
            <div style={{
                minHeight: '100vh',
                background: '#FEE2E2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px'
            }}>
                <ThemeToggle />
                <div style={{
                    background: 'white',
                    borderRadius: '16px',
                    padding: '40px',
                    textAlign: 'center',
                    maxWidth: '400px'
                }}>
                    <p style={{ fontSize: '48px', marginBottom: '16px' }}>❌</p>
                    <h2 style={{ color: '#DC2626', marginBottom: '8px' }}>Có lỗi xảy ra</h2>
                    <p style={{ color: '#6B7280' }}>{error}</p>
                </div>
            </div>
        );
    }

    // Result Screen
    if (result) {
        // Use neutral colors for both light and dark mode
        const bgColor = isDarkMode ? '#4B5563' : '#F3F4F6';
        const textColor = isDarkMode
            ? '#F9FAFB'
            : (result.percentage >= 80 ? '#059669' : result.percentage >= 50 ? '#D97706' : '#DC2626');
        const emoji = result.percentage >= 80 ? '🎉' : result.percentage >= 50 ? '👍' : '💪';

        return (
            <div style={{
                minHeight: '100vh',
                background: isDarkMode ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                padding: '20px'
            }}>
                <ThemeToggle />
                <div style={{ maxWidth: '700px', margin: '0 auto' }}>
                    <div style={{
                        background: isDarkMode ? '#374151' : 'white',
                        borderRadius: '20px',
                        padding: '32px',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                        color: isDarkMode ? 'white' : '#1F2937'
                    }}>
                        <h1 style={{ textAlign: 'center', marginBottom: '8px' }}>
                            Kết quả bài kiểm tra
                        </h1>
                        <p style={{ textAlign: 'center', color: isDarkMode ? '#D1D5DB' : '#6B7280', marginBottom: '24px' }}>
                            Học sinh: {result.student_name}
                        </p>

                        {/* Score */}
                        <div style={{
                            background: bgColor,
                            borderRadius: '16px',
                            padding: '32px',
                            textAlign: 'center',
                            marginBottom: '24px'
                        }}>
                            <p style={{ fontSize: '48px', fontWeight: 'bold', color: textColor }}>
                                {result.score}/{result.total}
                            </p>
                            <p style={{ fontSize: '28px', fontWeight: 'bold', color: textColor }}>
                                {result.percentage}%
                            </p>
                            <p style={{ fontSize: '24px', marginTop: '8px', color: isDarkMode ? 'white' : '#1F2937' }}>
                                {emoji} {result.percentage >= 80 ? 'Xuất sắc!' : result.percentage >= 50 ? 'Khá tốt!' : 'Cần cố gắng thêm!'}
                            </p>
                        </div>

                        {/* Detailed Answers */}
                        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>Chi tiết từng câu:</h2>
                        {Object.entries(result.answers).map(([qId, answer]) => (
                            <div
                                key={qId}
                                style={{
                                    padding: '16px',
                                    borderRadius: '12px',
                                    background: isDarkMode ? '#4B5563' : '#F3F4F6',
                                    marginBottom: '12px',
                                    color: isDarkMode ? 'white' : '#1F2937'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                                    <span style={{ fontSize: '20px' }}>{answer.is_correct ? '✅' : '❌'}</span>
                                    <div style={{ flex: 1 }}>
                                        <p style={{ fontWeight: '500', marginBottom: '8px' }}>Câu {qId}: {answer.question_text}</p>
                                        <p style={{ fontSize: '14px', color: isDarkMode ? '#D1D5DB' : '#374151' }}>
                                            Bạn chọn: <strong>{answer.student_answer || '(Chưa trả lời)'}</strong>
                                        </p>
                                        {!answer.is_correct && (
                                            <p style={{ fontSize: '14px', color: '#059669' }}>
                                                Đáp án đúng: <strong>{answer.correct_answer}</strong>
                                            </p>
                                        )}
                                        <p style={{ fontSize: '13px', color: isDarkMode ? '#9CA3AF' : '#6B7280', marginTop: '8px', fontStyle: 'italic' }}>
                                            {answer.explanation}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // Exam Screen with Floating AI Tutor
    const question = questions[currentQuestion];
    const progress = ((currentQuestion + 1) / questions.length) * 100;
    const answeredCount = Object.keys(answers).length;

    return (
        <div style={{ minHeight: '100vh', background: isDarkMode ? '#111827' : '#F3F4F6', position: 'relative' }}>
            <ThemeToggle />
            {/* Header */}
            <div style={{
                background: isDarkMode ? '#1F2937' : 'white',
                borderBottom: isDarkMode ? '1px solid #374151' : '1px solid #E5E7EB',
                padding: '16px 24px',
                color: isDarkMode ? 'white' : 'inherit',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{ flex: 1, maxWidth: '800px', margin: '0 auto', display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                        <p style={{ fontSize: '14px', color: isDarkMode ? '#9CA3AF' : '#6B7280' }}>Học sinh: {studentName}</p>
                        <p style={{ fontWeight: '500' }}>Câu {currentQuestion + 1}/{questions.length}</p>
                    </div>
                    <div style={{ textAlign: 'right', display: 'flex', gap: '16px', alignItems: 'center' }}>
                        <div>
                            <p style={{ fontSize: '14px', color: isDarkMode ? '#9CA3AF' : '#6B7280' }}>Đã trả lời</p>
                            <p style={{ fontWeight: '500' }}>{answeredCount}/{questions.length}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Progress Bar Container */}
            <div style={{ background: isDarkMode ? '#1F2937' : 'white', paddingBottom: '12px' }}>
                <div style={{ maxWidth: '800px', margin: '0 auto', height: '4px', background: isDarkMode ? '#374151' : '#E5E7EB', borderRadius: '2px' }}>
                    <div style={{ width: `${progress}%`, height: '100%', background: '#4F46E5', borderRadius: '2px', transition: 'width 0.3s' }} />
                </div>
            </div>

            {/* Question */}
            <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
                {question && (
                    <div style={{
                        background: isDarkMode ? '#1F2937' : 'white',
                        borderRadius: '16px',
                        padding: '32px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                        color: isDarkMode ? 'white' : 'inherit'
                    }}>
                        <h2 style={{ fontSize: '18px', marginBottom: '24px' }}>
                            <span style={{ color: '#4F46E5' }}>Câu {currentQuestion + 1}:</span> {question.text}
                        </h2>

                        {/* Options */}
                        <div style={{ marginBottom: '32px' }}>
                            {question.options.map((option: string, idx: number) => {
                                const optionLetter = option.charAt(0);
                                const isSelected = answers[question.id.toString()] === optionLetter;

                                return (
                                    <button
                                        key={idx}
                                        onClick={() => selectAnswer(question.id, optionLetter)}
                                        style={{
                                            width: '100%',
                                            padding: '16px',
                                            textAlign: 'left',
                                            borderRadius: '10px',
                                            border: isSelected ? '2px solid #4F46E5' : (isDarkMode ? '2px solid #374151' : '2px solid #E5E7EB'),
                                            background: isSelected ? (isDarkMode ? '#312E81' : '#EEF2FF') : (isDarkMode ? '#374151' : 'white'),
                                            color: isDarkMode ? 'white' : 'inherit',
                                            marginBottom: '12px',
                                            cursor: 'pointer',
                                            fontSize: '15px',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        {option}
                                    </button>
                                );
                            })}
                        </div>

                        {/* Navigation */}
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            paddingTop: '24px',
                            borderTop: isDarkMode ? '1px solid #374151' : '1px solid #E5E7EB'
                        }}>
                            <button
                                onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
                                disabled={currentQuestion === 0}
                                style={{
                                    padding: '12px 24px',
                                    background: currentQuestion === 0 ? (isDarkMode ? '#374151' : '#E5E7EB') : (isDarkMode ? '#4B5563' : 'white'),
                                    color: isDarkMode ? 'white' : 'inherit',
                                    border: isDarkMode ? 'none' : '1px solid #D1D5DB',
                                    borderRadius: '8px',
                                    cursor: currentQuestion === 0 ? 'not-allowed' : 'pointer'
                                }}
                            >
                                ← Câu trước
                            </button>
                            {currentQuestion < questions.length - 1 ? (
                                <button
                                    onClick={() => setCurrentQuestion(currentQuestion + 1)}
                                    style={{
                                        padding: '12px 24px',
                                        background: '#4F46E5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    Câu tiếp →
                                </button>
                            ) : (
                                <button
                                    onClick={handleSubmit}
                                    disabled={isSubmitting || answeredCount < questions.length}
                                    style={{
                                        padding: '12px 24px',
                                        background: (isSubmitting || answeredCount < questions.length) ? '#9CA3AF' : '#059669',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: (isSubmitting || answeredCount < questions.length) ? 'not-allowed' : 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    {isSubmitting ? '⏳ Đang nộp...' : '✓ Nộp bài'}
                                </button>
                            )}
                        </div>

                        {/* Question Navigation Dots */}
                        <div style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '8px',
                            justifyContent: 'center',
                            marginTop: '24px',
                            paddingTop: '24px',
                            borderTop: isDarkMode ? '1px solid #374151' : '1px solid #E5E7EB'
                        }}>
                            {questions.map((q: Question, idx: number) => {
                                const isAnswered = answers[q.id.toString()];
                                const isCurrent = idx === currentQuestion;

                                return (
                                    <button
                                        key={idx}
                                        onClick={() => setCurrentQuestion(idx)}
                                        style={{
                                            width: '36px',
                                            height: '36px',
                                            borderRadius: '50%',
                                            border: 'none',
                                            background: isCurrent ? '#4F46E5' : isAnswered ? '#059669' : (isDarkMode ? '#374151' : '#E5E7EB'),
                                            color: (isCurrent || isAnswered) ? 'white' : (isDarkMode ? '#D1D5DB' : '#374151'),
                                            fontWeight: '500',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        {idx + 1}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            {/* Floating AI Tutor Bubble Notification */}
            {latestBubble && !isChatOpen && (
                <div
                    onClick={() => { setIsChatOpen(true); setLatestBubble(null); }}
                    style={{
                        position: 'fixed',
                        bottom: '100px',
                        right: '24px',
                        maxWidth: '280px',
                        padding: '12px 16px',
                        background: 'white',
                        borderRadius: '16px 16px 4px 16px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                        cursor: 'pointer',
                        animation: 'slideIn 0.3s ease',
                        zIndex: 999
                    }}
                >
                    <p style={{ fontSize: '13px', color: '#1F2937', margin: 0, lineHeight: 1.4 }}>
                        🤖 {latestBubble.length > 100 ? latestBubble.slice(0, 100) + '...' : latestBubble}
                    </p>
                </div>
            )}

            {/* Floating Chat Button */}
            <button
                onClick={() => { setIsChatOpen(!isChatOpen); setLatestBubble(null); }}
                style={{
                    position: 'fixed',
                    bottom: '24px',
                    right: '24px',
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    border: 'none',
                    boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
                    cursor: 'pointer',
                    fontSize: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    transition: 'transform 0.2s'
                }}
            >
                {isChatOpen ? '✕' : '🤖'}
            </button>

            {/* Chat Popup */}
            {isChatOpen && (
                <div style={{
                    position: 'fixed',
                    bottom: '100px',
                    right: '24px',
                    width: '360px',
                    height: '500px',
                    background: 'white',
                    borderRadius: '16px',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    zIndex: 999
                }}>
                    {/* Chat Header */}
                    <div style={{
                        padding: '16px 20px',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white'
                    }}>
                        <h3 style={{ fontSize: '16px', fontWeight: '600', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                            🤖 AI Tutor
                        </h3>
                        <p style={{ fontSize: '12px', opacity: 0.9, marginTop: '4px', marginBottom: 0 }}>
                            Hỏi mình bất cứ điều gì!
                        </p>
                    </div>

                    {/* Chat Messages */}
                    <div style={{
                        flex: 1,
                        overflow: 'auto',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px'
                    }}>
                        {chatMessages.map((msg: ChatMessage, idx: number) => (
                            <div
                                key={idx}
                                style={{
                                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                    maxWidth: '85%'
                                }}
                            >
                                <div style={{
                                    padding: '10px 14px',
                                    borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                                    background: msg.role === 'user' ? '#4F46E5' : '#F3F4F6',
                                    color: msg.role === 'user' ? 'white' : '#1F2937',
                                    fontSize: '13px',
                                    lineHeight: '1.4'
                                }}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                        {isChatLoading && (
                            <div style={{ alignSelf: 'flex-start' }}>
                                <div style={{
                                    padding: '10px 14px',
                                    borderRadius: '14px 14px 14px 4px',
                                    background: '#F3F4F6',
                                    color: '#6B7280',
                                    fontSize: '13px'
                                }}>
                                    Đang suy nghĩ... 🤔
                                </div>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Suggested Prompts */}
                    <div style={{
                        padding: '10px 14px',
                        borderTop: '1px solid #E5E7EB',
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '8px',
                    }}>
                        {suggestedPrompts.slice(0, 4).map((prompt: string, idx: number) => (
                            <button
                                key={idx}
                                onClick={() => sendChatMessage(prompt)}
                                disabled={isChatLoading}
                                style={{
                                    width: 'calc(50% - 4px)', // Force 2 items per row (accounting for gap)
                                    padding: '6px 10px',
                                    background: '#EEF2FF',
                                    color: '#4F46E5',
                                    border: '1px solid #C7D2FE',
                                    borderRadius: '12px',
                                    fontSize: '11px',
                                    cursor: isChatLoading ? 'not-allowed' : 'pointer',
                                    opacity: isChatLoading ? 0.5 : 1,
                                    whiteSpace: 'normal', // Allow text wrapping
                                    textAlign: 'left',
                                    lineHeight: '1.3'
                                }}
                            >
                                {prompt}
                            </button>
                        ))}
                    </div>

                    {/* Chat Input */}
                    <div style={{
                        padding: '12px',
                        borderTop: '1px solid #E5E7EB',
                        display: 'flex',
                        gap: '8px'
                    }}>
                        <input
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    if (!isChatLoading && chatInput.trim()) {
                                        sendChatMessage(chatInput);
                                    }
                                }
                            }}
                            placeholder="Hỏi AI Tutor..."
                            disabled={isChatLoading}
                            style={{
                                flex: 1,
                                padding: '10px',
                                borderRadius: '8px',
                                border: '1px solid #E5E7EB',
                                fontSize: '13px',
                                outline: 'none'
                            }}
                        />
                        <button
                            onClick={() => sendChatMessage(chatInput)}
                            disabled={isChatLoading || !chatInput.trim()}
                            style={{
                                padding: '10px 14px',
                                background: (isChatLoading || !chatInput.trim()) ? '#E5E7EB' : '#4F46E5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: (isChatLoading || !chatInput.trim()) ? 'not-allowed' : 'pointer',
                                fontWeight: '500',
                                fontSize: '13px'
                            }}
                        >
                            Gửi
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

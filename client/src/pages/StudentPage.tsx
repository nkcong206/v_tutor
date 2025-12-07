import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { QuestionRenderer } from '../components/QuestionRenderer';
import { Question } from '../types';

const API_BASE_URL = 'http://localhost:8000';



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
    analysis?: {
        summary: string;
        score: number;
    };
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

// Helper to normalize correct_answer to string (handles both letter and index formats)
const normalizeCorrectAnswer = (answer: string | number | undefined, options: string[]): string => {
    if (answer === undefined) return '';
    if (typeof answer === 'number') {
        // Index-based: return the letter (A, B, C, D)
        return String.fromCharCode(65 + answer); // 0 -> A, 1 -> B, etc.
    }
    // Already a string (letter or "A. Content")
    return answer.charAt(0).toUpperCase();
};

// Helper to check if answer is correct
const isAnswerCorrect = (
    studentAnswer: any, // Can be string, number, or array for multi-choice
    correctAnswer: string | number | number[] | undefined,
    options: string[]
): boolean => {
    try {
        // Handle multi-choice: studentAnswer and correctAnswer are both arrays of indices
        if (Array.isArray(studentAnswer) && Array.isArray(correctAnswer)) {
            const sortedStudent = [...studentAnswer].sort();
            const sortedCorrect = [...correctAnswer].sort();
            return JSON.stringify(sortedStudent) === JSON.stringify(sortedCorrect);
        }

        // Handle single choice: convert to string for comparison
        if (typeof studentAnswer !== 'string') {
            studentAnswer = String(studentAnswer);
        }

        const normalizedCorrect = normalizeCorrectAnswer(correctAnswer as string | number | undefined, options);
        return studentAnswer.toUpperCase() === normalizedCorrect;
    } catch (error) {
        console.error('[isAnswerCorrect] Error:', error);
        return false;
    }
};

// Helper to check if question is a media type
const isMediaQuestion = (type?: string): boolean => {
    return type?.includes('image') || type?.includes('audio') || false;
};

// Helper to check if question is multi-choice
const isMultiChoiceQuestion = (type?: string): boolean => {
    return type?.includes('multi') || false;
};

export function StudentPage() {
    const { examId } = useParams<{ examId: string }>();
    const [studentName, setStudentName] = useState('');
    const [isStarted, setIsStarted] = useState(false);
    const [questions, setQuestions] = useState<Question[]>([]);
    const [answers, setAnswers] = useState<Record<string, any>>({});
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

    const selectAnswer = (questionId: number, answer: any) => {
        const prevAnswer = answers[questionId.toString()];

        // Deep compare for arrays
        const isNewAnswer = JSON.stringify(prevAnswer) !== JSON.stringify(answer);

        setAnswers({ ...answers, [questionId.toString()]: answer });

        if (isNewAnswer) {
            // Update attempt count
            const newAttempts = (attemptCounts[questionId] || 0) + 1;
            setAttemptCounts({ ...attemptCounts, [questionId]: newAttempts });

            // Check if answer is correct
            const question = questions.find(q => q.id === questionId);
            if (question) {
                // Determine correctness based on type
                let isCorrect = false;
                if (question.type?.includes('multi')) {
                    // Compare arrays of indices
                    const correctArr = question.correct_answers || [];
                    const selectedArr = answer || [];
                    isCorrect = JSON.stringify(correctArr.sort()) === JSON.stringify(selectedArr.sort());
                } else if (question.type?.includes('fill_in')) {
                    // Check if ALL blanks are correct
                    const correctArr = question.correct_answers || [];
                    const selectedArr = answer || [];
                    isCorrect = correctArr.every((ans: any, idx: number) =>
                        String(selectedArr[idx] || '').trim().toLowerCase() === String(ans).toLowerCase()
                    );
                } else {
                    // Standard Single Choice
                    isCorrect = isAnswerCorrect(answer, question.correct_answer, question.options);
                }

                // Send context to AI silently
                // For Fill-in-Blanks, handled by onAnswerCommit to avoid keystroke spam
                if (!question.type?.includes('fill_in')) {
                    sendContextToAI(questionId, Array.isArray(answer) ? JSON.stringify(answer) : String(answer), isCorrect, newAttempts);
                }
            }
        }
    };

    // Silent context update - only shows AI response, not the trigger
    const sendContextToAI = async (
        questionId: number,
        selectedAnswer: any,
        isCorrect: boolean,
        attemptCount: number
    ) => {
        const question = questions.find(q => q.id === questionId);
        if (!question) return;

        // Abort previous request FIRST, before creating new controller
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            setIsChatLoading(true);

            const response = await fetch(`${API_BASE_URL}/api/tutor/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exam_id: examId,
                    question_id: questionId,
                    student_name: studentName,
                    message: `[Học sinh chọn: ${JSON.stringify(selectedAnswer)}]`,
                    question_text: question.text,
                    options: question.options || [],
                    selected_answer: selectedAnswer,
                    correct_answer: question.correct_answer,
                    is_correct: isCorrect,
                    attempt_count: attemptCount
                }),
                signal: controller.signal
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
            // Only clear loading if this is still the active controller
            if (abortControllerRef.current === controller) {
                setIsChatLoading(false);
                abortControllerRef.current = null;
            }
        }
    };

    // User-initiated chat message (visible in chat)
    const sendChatMessage = async (message: string) => {
        console.log('[AI Tutor Chat] === sendChatMessage START ===');
        console.log('[AI Tutor Chat] Message:', message);

        if (!message.trim()) {
            console.log('[AI Tutor Chat] ❌ Empty message, returning');
            return;
        }

        const question = questions[currentQuestion];
        if (!question) {
            console.log('[AI Tutor Chat] ❌ No current question, returning');
            return;
        }

        // Get current answer state
        const currentAnswer = answers[question.id.toString()];
        const hasAnswered = currentAnswer !== undefined && currentAnswer !== '' && currentAnswer !== null;

        // Only check is_correct if student has answered
        let isCorrect: boolean | undefined = undefined;
        if (hasAnswered) {
            isCorrect = isAnswerCorrect(currentAnswer, question.correct_answer, question.options);
        }

        const attemptCount = attemptCounts[question.id] || 0;

        console.log('[AI Tutor Chat] Question:', question.id, '-', question.text?.substring(0, 50) + '...');
        console.log('[AI Tutor Chat] Has Answered:', hasAnswered);
        console.log('[AI Tutor Chat] Current Answer:', currentAnswer);
        console.log('[AI Tutor Chat] Is Correct:', isCorrect);
        console.log('[AI Tutor Chat] Attempt Count:', attemptCount);

        // Add user message to visible chat
        setChatMessages(prev => [...prev, { role: 'user', content: message }]);
        setChatInput('');
        setIsChatLoading(true);

        try {
            const requestBody = {
                exam_id: examId,
                question_id: question.id,
                student_name: studentName,
                message: message,
                question_text: question.text,
                options: question.options,
                selected_answer: hasAnswered ? currentAnswer : null,
                is_correct: isCorrect, // Will be undefined if not answered
                attempt_count: attemptCount
            };

            console.log('[AI Tutor Chat] Request Body:', JSON.stringify(requestBody, null, 2));

            const response = await fetch(`${API_BASE_URL}/api/tutor/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            console.log('[AI Tutor Chat] Response Status:', response.status);

            if (response.ok) {
                const data = await response.json();
                console.log('[AI Tutor Chat] ✅ Response Data:', data);
                setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
                setSuggestedPrompts(data.suggested_prompts);
            } else {
                const errorText = await response.text();
                console.error('[AI Tutor Chat] ❌ Response Error:', response.status, errorText);
            }
        } catch (err) {
            console.error('[AI Tutor Chat] ❌ Fetch Error:', err);
        } finally {
            setIsChatLoading(false);
            console.log('[AI Tutor Chat] === sendChatMessage END ===');
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
            const studentAnswer = answers[qId];
            let isCorrect = false;

            if (q.type?.includes('multi')) {
                const correctArr = (q.correct_answers || []).map(Number).sort((a, b) => a - b);
                const selectedArr = (studentAnswer || []).map(Number).sort((a: number, b: number) => a - b);
                isCorrect = JSON.stringify(correctArr) === JSON.stringify(selectedArr);
            } else if (q.type?.includes('fill_in')) {
                const correctArr = q.correct_answers || [];
                const selectedArr = studentAnswer || [];
                if (Array.isArray(correctArr) && correctArr.length > 0) {
                    isCorrect = correctArr.every((ans: any, idx: number) =>
                        String(selectedArr[idx] || '').trim().toLowerCase() === String(ans).toLowerCase()
                    );
                }
            } else {
                isCorrect = isAnswerCorrect(studentAnswer || '', q.correct_answer, q.options);
            }

            if (isCorrect) correct++;

            // Format for display
            let correctAnswerStr = '';
            let displayStudentAnswer = '';

            if (q.type?.includes('multi')) {
                // Convert indices to Letters (0->A)
                correctAnswerStr = (q.correct_answers || []).map((i: any) => String.fromCharCode(65 + Number(i))).join(', ');
                displayStudentAnswer = (studentAnswer || []).map((i: any) => String.fromCharCode(65 + Number(i))).join(', ');
            } else if (q.type?.includes('fill_in')) {
                correctAnswerStr = (q.correct_answers || []).join(' | ');
                displayStudentAnswer = (studentAnswer || []).join(' | ');
            } else {
                correctAnswerStr = normalizeCorrectAnswer(q.correct_answer, q.options);
                displayStudentAnswer = studentAnswer || '';
            }

            answerDetails[qId] = {
                student_answer: displayStudentAnswer,
                correct_answer: correctAnswerStr,
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
        // SEND CHAT HISTORY FOR AI ANALYSIS
        fetch(`${API_BASE_URL}/api/exam/exam/${examId}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_name: studentName,
                answers: answers, // Send raw answers to server
                chat_history: chatMessages // Send chat logs
            }),
        }).then(res => res.json()).then(data => {
            // Update result with AI Analysis if available
            if (data.analysis) {
                setResult(prev => prev ? { ...prev, analysis: data.analysis } : prev);
            }
        }).catch(err => {
            console.error('Background sync error:', err);
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
                background: isDarkMode ? '#1E2447' : 'white',
                border: isDarkMode ? '1px solid #2D3250' : '1px solid #E5E7EB',
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
                background: isDarkMode
                    ? 'linear-gradient(135deg, #0A0F1C 0%, #131629 50%, #1E2447 100%)'
                    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                position: 'relative',
                overflow: 'hidden'
            }}>
                {/* Decorative glow orbs */}
                <div style={{
                    position: 'absolute',
                    width: '400px',
                    height: '400px',
                    background: 'radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%)',
                    top: '-100px',
                    right: '-100px',
                    borderRadius: '50%',
                    pointerEvents: 'none'
                }} />
                <div style={{
                    position: 'absolute',
                    width: '300px',
                    height: '300px',
                    background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%)',
                    bottom: '-50px',
                    left: '-50px',
                    borderRadius: '50%',
                    pointerEvents: 'none'
                }} />

                <ThemeToggle />
                <div style={{
                    background: isDarkMode
                        ? 'rgba(30, 36, 71, 0.8)'
                        : 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: '24px',
                    padding: '48px 40px',
                    maxWidth: '420px',
                    width: '100%',
                    boxShadow: isDarkMode
                        ? '0 25px 80px rgba(0,0,0,0.5), 0 0 40px rgba(124, 58, 237, 0.1)'
                        : '0 25px 80px rgba(0,0,0,0.15)',
                    textAlign: 'center',
                    color: isDarkMode ? 'white' : '#131629',
                    border: isDarkMode ? '1px solid rgba(124, 58, 237, 0.2)' : 'none'
                }}>
                    {/* Animated icon */}
                    <div style={{
                        fontSize: '56px',
                        marginBottom: '16px',
                        animation: 'float 3s ease-in-out infinite'
                    }}>
                        🎓
                    </div>
                    <style>{`
                        @keyframes float {
                            0%, 100% { transform: translateY(0px); }
                            50% { transform: translateY(-10px); }
                        }
                        @keyframes pulse {
                            0%, 100% { box-shadow: 0 0 20px rgba(124, 58, 237, 0.4); }
                            50% { box-shadow: 0 0 40px rgba(124, 58, 237, 0.6); }
                        }
                        @keyframes shimmer {
                            0% { background-position: -200% center; }
                            100% { background-position: 200% center; }
                        }
                    `}</style>
                    <h2 style={{
                        fontSize: '28px',
                        fontWeight: '700',
                        marginBottom: '8px',
                        color: isDarkMode ? '#A855F7' : '#7C3AED'
                    }}>
                        ✨ Bài kiểm tra
                    </h2>
                    <p style={{
                        color: isDarkMode ? '#9CA3AF' : '#6B7280',
                        marginBottom: '32px',
                        fontSize: '15px'
                    }}>
                        Nhập tên để bắt đầu làm bài
                    </p>

                    <div style={{ marginBottom: '24px' }}>
                        <input
                            placeholder="Nhập họ và tên..."
                            value={studentName}
                            onChange={(e) => setStudentName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                            style={{
                                width: '100%',
                                padding: '16px 20px',
                                borderRadius: '14px',
                                border: isDarkMode
                                    ? '2px solid rgba(124, 58, 237, 0.3)'
                                    : '2px solid #E5E7EB',
                                fontSize: '16px',
                                textAlign: 'center',
                                boxSizing: 'border-box',
                                background: isDarkMode ? 'rgba(19, 22, 41, 0.8)' : 'white',
                                color: isDarkMode ? 'white' : 'black',
                                outline: 'none',
                                transition: 'all 0.3s ease'
                            }}
                            onFocus={(e) => {
                                e.target.style.borderColor = '#7C3AED';
                                e.target.style.boxShadow = '0 0 20px rgba(124, 58, 237, 0.2)';
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = isDarkMode ? 'rgba(124, 58, 237, 0.3)' : '#E5E7EB';
                                e.target.style.boxShadow = 'none';
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            padding: '14px',
                            background: isDarkMode ? 'rgba(239, 68, 68, 0.15)' : '#FEE2E2',
                            borderRadius: '12px',
                            color: '#EF4444',
                            marginBottom: '20px',
                            fontSize: '14px',
                            border: '1px solid rgba(239, 68, 68, 0.2)'
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    <button
                        onClick={handleStart}
                        disabled={!studentName.trim()}
                        style={{
                            width: '100%',
                            padding: '16px',
                            background: studentName.trim()
                                ? 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)'
                                : (isDarkMode ? '#2D3250' : '#D1D5DB'),
                            color: 'white',
                            border: 'none',
                            borderRadius: '14px',
                            fontSize: '17px',
                            fontWeight: '600',
                            cursor: studentName.trim() ? 'pointer' : 'not-allowed',
                            transition: 'all 0.3s ease',
                            boxShadow: studentName.trim()
                                ? '0 10px 30px rgba(124, 58, 237, 0.3)'
                                : 'none'
                        }}
                        onMouseEnter={(e) => {
                            if (studentName.trim()) {
                                e.currentTarget.style.transform = 'translateY(-2px)';
                                e.currentTarget.style.boxShadow = '0 15px 40px rgba(124, 58, 237, 0.4)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            if (studentName.trim()) {
                                e.currentTarget.style.boxShadow = '0 10px 30px rgba(124, 58, 237, 0.3)';
                            }
                        }}
                    >
                        ✨ Bắt đầu làm bài
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
                background: isDarkMode ? 'linear-gradient(135deg, #0A0F1C 0%, #131629 100%)' : 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)',
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
                    <p style={{ color: '#6B7280' }}>{error}</p>
                </div>
            </div>
        );
    }

    // Result Screen
    if (result) {
        // Use neutral colors for both light and dark mode
        const bgColor = isDarkMode ? '#2D3250' : '#F3F4F6';
        const textColor = isDarkMode
            ? '#F9FAFB'
            : (result.percentage >= 80 ? '#10B981' : result.percentage >= 50 ? '#D97706' : '#DC2626');
        const emoji = result.percentage >= 80 ? '🎉' : result.percentage >= 50 ? '👍' : '💪';

        return (
            <div style={{
                minHeight: '100vh',
                background: isDarkMode ? 'linear-gradient(135deg, #0A0F1C 0%, #131629 100%)' : 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)',
                padding: '20px'
            }}>
                <ThemeToggle />
                <div style={{ maxWidth: '900px', margin: '0 auto' }}>
                    <div style={{
                        background: isDarkMode ? '#1E2447' : 'white',
                        borderRadius: '20px',
                        padding: '32px',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                        color: isDarkMode ? 'white' : '#131629'
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
                            <p style={{ fontSize: '24px', marginTop: '8px', color: isDarkMode ? 'white' : '#131629' }}>
                                {emoji} {result.percentage >= 80 ? 'Xuất sắc!' : result.percentage >= 50 ? 'Khá tốt!' : 'Cần cố gắng thêm!'}
                            </p>
                        </div>

                        {/* AI Analysis */}
                        {result.analysis && (
                            <div style={{
                                marginTop: '24px',
                                padding: '24px',
                                background: isDarkMode ? 'rgba(59, 130, 246, 0.2)' : '#EFF6FF',
                                borderRadius: '16px',
                                border: `1px solid ${isDarkMode ? '#3B82F6' : '#BFDBFE'}`,
                                marginBottom: '24px'
                            }}>
                                <h3 style={{
                                    display: 'flex', alignItems: 'center', gap: '8px',
                                    fontSize: '18px', fontWeight: 'bold',
                                    color: isDarkMode ? '#93C5FD' : '#1E40AF',
                                    marginBottom: '12px'
                                }}>
                                    <span>🤖</span> Đánh giá từ AI Tutor
                                </h3>
                                <div style={{ display: 'flex', gap: '16px', flexDirection: 'column' }}>
                                    <div>
                                        <span style={{ fontWeight: 'bold', color: isDarkMode ? '#BFDBFE' : '#1E3A8A' }}>
                                            Điểm thái độ: {result.analysis.score}/10
                                        </span>
                                        <div style={{
                                            height: '8px', width: '100%', background: isDarkMode ? '#131629' : 'white',
                                            borderRadius: '4px', marginTop: '4px', overflow: 'hidden'
                                        }}>
                                            <div style={{
                                                height: '100%', width: `${result.analysis.score * 10}%`,
                                                background: result.analysis.score >= 8 ? '#10B981' : result.analysis.score >= 5 ? '#F59E0B' : '#EF4444',
                                                borderRadius: '4px', transition: 'width 0.5s ease'
                                            }} />
                                        </div>
                                    </div>
                                    <p style={{
                                        lineHeight: '1.6',
                                        color: isDarkMode ? '#D1D5DB' : '#1E2447',
                                        fontStyle: 'italic'
                                    }}>
                                        "{result.analysis.summary}"
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Detailed Answers */}
                        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>Chi tiết từng câu:</h2>
                        {Object.entries(result.answers).map(([qId, answer]) => (
                            <div
                                key={qId}
                                style={{
                                    padding: '16px',
                                    borderRadius: '12px',
                                    background: isDarkMode ? '#2D3250' : '#F3F4F6',
                                    marginBottom: '12px',
                                    color: isDarkMode ? 'white' : '#131629'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                                    <span style={{ fontSize: '20px' }}>{answer.is_correct ? '✅' : '❌'}</span>
                                    <div style={{ flex: 1 }}>
                                        <p style={{ fontWeight: '500', marginBottom: '8px' }}>Câu {qId}: {answer.question_text}</p>
                                        <p style={{ fontSize: '14px', color: isDarkMode ? '#D1D5DB' : '#1E2447' }}>
                                            Bạn chọn: <strong>{answer.student_answer || '(Chưa trả lời)'}</strong>
                                        </p>
                                        {!answer.is_correct && (
                                            <p style={{ fontSize: '14px', color: '#10B981' }}>
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
        <div style={{ minHeight: '100vh', background: isDarkMode ? '#0A0F1C' : '#F3F4F6', position: 'relative' }}>
            <ThemeToggle />
            {/* Header */}
            <div style={{
                background: isDarkMode ? '#131629' : 'white',
                borderBottom: isDarkMode ? '1px solid #1E2447' : '1px solid #E5E7EB',
                padding: '16px 24px',
                color: isDarkMode ? 'white' : 'inherit',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{ flex: 1, maxWidth: '900px', margin: '0 auto', display: 'flex', justifyContent: 'space-between' }}>
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
            <div style={{ background: isDarkMode ? '#131629' : 'white', paddingBottom: '12px' }}>
                <div style={{ maxWidth: '900px', margin: '0 auto', height: '4px', background: isDarkMode ? '#1E2447' : '#E5E7EB', borderRadius: '2px' }}>
                    <div style={{ width: `${progress}%`, height: '100%', background: '#7C3AED', borderRadius: '2px', transition: 'width 0.3s' }} />
                </div>
            </div>

            {/* Question */}
            <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
                {question && (
                    <div style={{
                        background: isDarkMode ? '#131629' : 'white',
                        borderRadius: '16px',
                        padding: '32px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                        color: isDarkMode ? 'white' : 'inherit'
                    }}>


                        {/* Image Display for image questions */}


                        {/* Audio Player for audio questions */}


                        {/* Question Type Badge */}
                        {/* Question Type Badge */}
                        {(() => {
                            let badgeInfo = { label: '', icon: '', bgLight: '', bgDark: '', colorLight: '', colorDark: '' };
                            const t = question.type || 'single_choice';

                            switch (t) {
                                // Text Questions
                                case 'single_choice':
                                    badgeInfo = { label: 'Chọn 1 câu trả lời', icon: '📝', bgLight: '#F3F4F6', bgDark: '#1E2447', colorLight: '#1E2447', colorDark: '#A5B4FC' };
                                    break;
                                case 'multi_choice':
                                    badgeInfo = { label: 'Chọn nhiều câu trả lời', icon: '📝', bgLight: '#E0E7FF', bgDark: '#312E81', colorLight: '#3730A3', colorDark: '#C4B5FD' };
                                    break;
                                case 'fill_in_blanks':
                                    badgeInfo = { label: 'Điền từ vào chỗ trống', icon: '✏️', bgLight: '#FCE7F3', bgDark: '#4C1D4F', colorLight: '#9D174D', colorDark: '#F9A8D4' };
                                    break;

                                // Image Questions
                                case 'image_single_choice':
                                    badgeInfo = { label: 'Nhìn ảnh và chọn 1 câu trả lời', icon: '🖼️', bgLight: '#DBEAFE', bgDark: '#1E3A5F', colorLight: '#1E40AF', colorDark: '#93C5FD' };
                                    break;
                                case 'image_multi_choice':
                                    badgeInfo = { label: 'Nhìn ảnh và chọn nhiều câu trả lời', icon: '🖼️', bgLight: '#DBEAFE', bgDark: '#1E3A5F', colorLight: '#1E40AF', colorDark: '#93C5FD' };
                                    break;
                                case 'image_fill_in_blanks':
                                    badgeInfo = { label: 'Nhìn ảnh và điền từ vào chỗ trống', icon: '🖼️', bgLight: '#DBEAFE', bgDark: '#1E3A5F', colorLight: '#1E40AF', colorDark: '#93C5FD' };
                                    break;

                                // Audio Questions
                                case 'audio_single_choice':
                                    badgeInfo = { label: 'Lắng nghe và chọn 1 câu trả lời', icon: '🔊', bgLight: '#FEF3C7', bgDark: '#422006', colorLight: '#92400E', colorDark: '#FCD34D' };
                                    break;
                                case 'audio_multi_choice':
                                    badgeInfo = { label: 'Lắng nghe và chọn nhiều câu trả lời', icon: '🔊', bgLight: '#FEF3C7', bgDark: '#422006', colorLight: '#92400E', colorDark: '#FCD34D' };
                                    break;
                                case 'audio_fill_in_blanks':
                                    badgeInfo = { label: 'Lắng nghe và điền từ phù hợp vào chỗ trống', icon: '🔊', bgLight: '#FEF3C7', bgDark: '#422006', colorLight: '#92400E', colorDark: '#FCD34D' };
                                    break;

                                default:
                                    badgeInfo = { label: t, icon: '❓', bgLight: '#E5E7EB', bgDark: '#1E2447', colorLight: '#1E2447', colorDark: '#D1D5DB' };
                            }

                            return (
                                <div style={{
                                    marginBottom: '16px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    padding: '6px 14px',
                                    borderRadius: '20px',
                                    fontSize: '13px',
                                    fontWeight: '600',
                                    background: isDarkMode ? badgeInfo.bgDark : badgeInfo.bgLight,
                                    color: isDarkMode ? badgeInfo.colorDark : badgeInfo.colorLight,
                                    border: isDarkMode ? '1px solid rgba(124, 58, 237, 0.2)' : 'none',
                                    transform: 'translateX(-2px)', // Visual alignment
                                }}>
                                    <span>{badgeInfo.icon}</span>
                                    <span>{badgeInfo.label}</span>
                                </div>
                            );
                        })()}
                        {/* Options / Answer Area */}
                        <div style={{ marginBottom: '32px' }}>
                            <QuestionRenderer
                                question={question}
                                currentAnswer={answers[question.id.toString()] || (question.type?.includes('multi') ? [] : '')}
                                onAnswerChange={(ans) => selectAnswer(question.id, ans)}
                                isDarkMode={isDarkMode}
                                onCheckBlank={(index, value) => {
                                    if (question.correct_answers && question.correct_answers[index]) {
                                        const correct = question.correct_answers[index];
                                        return String(value).trim().toLowerCase() === String(correct).toLowerCase();
                                    }
                                    return false;
                                }}
                                onAnswerCommit={() => {
                                    // Manually trigger AI for Fill-in-Blanks commit
                                    const ans = answers[question.id.toString()];
                                    let isCorrect = false;
                                    const correctArr = question.correct_answers || [];
                                    const selectedArr = ans || [];

                                    // Re-calculate correctness for the commit
                                    if (Array.isArray(correctArr)) {
                                        isCorrect = correctArr.every((c: any, idx: number) =>
                                            String(selectedArr[idx] || '').trim().toLowerCase() === String(c).toLowerCase()
                                        );
                                    }

                                    sendContextToAI(
                                        question.id,
                                        ans,
                                        isCorrect,
                                        (attemptCounts[question.id] || 0)
                                    );
                                }}
                            />
                        </div>

                        {/* Navigation */}
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            paddingTop: '24px',
                            borderTop: isDarkMode ? '1px solid #1E2447' : '1px solid #E5E7EB'
                        }}>
                            <button
                                onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
                                disabled={currentQuestion === 0}
                                style={{
                                    padding: '12px 24px',
                                    background: currentQuestion === 0 ? (isDarkMode ? '#1E2447' : '#E5E7EB') : (isDarkMode ? '#2D3250' : 'white'),
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
                                        background: '#7C3AED',
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
                                        background: (isSubmitting || answeredCount < questions.length) ? '#9CA3AF' : '#10B981',
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
                            borderTop: isDarkMode ? '1px solid #1E2447' : '1px solid #E5E7EB'
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
                                            background: isCurrent ? '#7C3AED' : isAnswered ? '#10B981' : (isDarkMode ? '#1E2447' : '#E5E7EB'),
                                            color: (isCurrent || isAnswered) ? 'white' : (isDarkMode ? '#D1D5DB' : '#1E2447'),
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
                        background: isDarkMode ? '#1E2447' : 'white',
                        borderRadius: '16px 16px 4px 16px',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                        cursor: 'pointer',
                        animation: 'slideIn 0.3s ease',
                        zIndex: 999
                    }}
                >
                    <p style={{ fontSize: '13px', color: isDarkMode ? 'white' : '#131629', margin: 0, lineHeight: 1.4 }}>
                        🤖 {latestBubble.length > 100 ? latestBubble.slice(0, 100) + '...' : latestBubble}
                    </p>
                </div>
            )}

            {/* Floating Chat Button */}
            <style>{`
                @keyframes float-chat {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                @keyframes pulse-glow {
                    0%, 100% { box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4); }
                    50% { box-shadow: 0 4px 35px rgba(124, 58, 237, 0.6); }
                }
            `}</style>
            <button
                onClick={() => { setIsChatOpen(!isChatOpen); setLatestBubble(null); }}
                style={{
                    position: 'fixed',
                    bottom: '24px',
                    right: '24px',
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)',
                    color: 'white',
                    border: '2px solid rgba(168, 85, 247, 0.3)',
                    boxShadow: '0 4px 25px rgba(124, 58, 237, 0.5)',
                    cursor: 'pointer',
                    fontSize: '28px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    transition: 'all 0.3s ease',
                    animation: isChatOpen ? 'none' : 'float-chat 3s ease-in-out infinite, pulse-glow 2s ease-in-out infinite'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.1)';
                    e.currentTarget.style.boxShadow = '0 6px 35px rgba(124, 58, 237, 0.6)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.boxShadow = '0 4px 25px rgba(124, 58, 237, 0.5)';
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
                    width: '380px',
                    height: '520px',
                    background: isDarkMode ? 'rgba(19, 22, 41, 0.95)' : 'white',
                    backdropFilter: 'blur(20px)',
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
                        background: 'linear-gradient(135deg, #7C3AED 0%, #A855F7 100%)',
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
                                    background: msg.role === 'user' ? '#7C3AED' : (isDarkMode ? '#1E2447' : '#F3F4F6'),
                                    color: msg.role === 'user' ? 'white' : (isDarkMode ? 'white' : '#131629'),
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
                                    background: isDarkMode ? '#1E2447' : '#F3F4F6',
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
                        borderTop: isDarkMode ? '1px solid #1E2447' : '1px solid #E5E7EB',
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
                                    background: isDarkMode ? '#3B2E81' : '#EDE9FE',
                                    color: isDarkMode ? '#A78BFA' : '#7C3AED',
                                    border: isDarkMode ? '1px solid #6D28D9' : '1px solid #C4B5FD',
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
                        borderTop: isDarkMode ? '1px solid #1E2447' : '1px solid #E5E7EB',
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
                                border: isDarkMode ? '1px solid #2D3250' : '1px solid #E5E7EB',
                                background: isDarkMode ? '#1E2447' : 'white',
                                color: isDarkMode ? 'white' : 'inherit',
                                fontSize: '13px',
                                outline: 'none'
                            }}
                        />
                        <button
                            onClick={() => sendChatMessage(chatInput)}
                            disabled={isChatLoading || !chatInput.trim()}
                            style={{
                                padding: '10px 14px',
                                background: (isChatLoading || !chatInput.trim())
                                    ? (isDarkMode ? '#1E2447' : '#E5E7EB')
                                    : '#7C3AED',
                                color: (isChatLoading || !chatInput.trim())
                                    ? '#9CA3AF'
                                    : 'white',
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

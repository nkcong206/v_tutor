import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8000';

interface Question {
    id: number;
    text: string;
    options: string[];
    correct_answer: string;
    explanation: string;
}

interface ExamInfo {
    exam_id: string;
    prompt: string;
    question_count: number;
    student_count: number;
    student_url: string;
    created_at: string;
}

interface ExamFull {
    exam_id: string;
    prompt: string;
    questions: Question[];
    created_at: string;
}

interface ExamResult {
    exam_id: string;
    teacher_id: string;
    student_url: string;
    teacher_url: string;
    questions: Question[];
}

interface StudentResult {
    student_name: string;
    score: number;
    total: number;
    percentage: number;
    submitted_at: string;
}

interface ExamStats {
    exam_id: string;
    prompt: string;
    total_students: number;
    statistics: {
        average_score: number;
        highest_score: number;
        lowest_score: number;
    };
    students: StudentResult[];
}

export function TeacherPage() {
    const { teacherName: urlTeacherId } = useParams<{ teacherName?: string }>();
    const navigate = useNavigate();

    // Login state
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [teacherName, setTeacherName] = useState('');  // Display name (original case)
    const [teacherId, setTeacherId] = useState('');      // UUID for URL
    const [loginError, setLoginError] = useState('');

    // Exam creation state
    const [prompt, setPrompt] = useState('');
    const [questionCount, setQuestionCount] = useState(5);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState('');
    const [examResult, setExamResult] = useState<ExamResult | null>(null);
    const [copiedNew, setCopiedNew] = useState(false);
    const [copiedExamId, setCopiedExamId] = useState<string | null>(null);

    // Teacher exams state
    const [teacherExams, setTeacherExams] = useState<ExamInfo[]>([]);
    const [selectedExam, setSelectedExam] = useState<string | null>(null);

    // Right panel state
    const [viewMode, setViewMode] = useState<'questions' | 'stats'>('questions');
    const [examFull, setExamFull] = useState<ExamFull | null>(null);
    const [examStats, setExamStats] = useState<ExamStats | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // Check if teacher_id in URL
    useEffect(() => {
        if (urlTeacherId) {
            setTeacherId(urlTeacherId);
            loadTeacherExams(urlTeacherId);
            setIsLoggedIn(true);
        }
    }, [urlTeacherId]);

    const loadTeacherExams = async (id: string) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/teacher/${encodeURIComponent(id)}`);
            if (response.ok) {
                const data = await response.json();
                setTeacherExams(data.exams || []);
                if (data.teacher_name) {
                    setTeacherName(data.teacher_name);
                }
            }
        } catch (err) {
            console.error('Error loading teacher exams:', err);
        }
    };

    const handleLogin = async () => {
        if (!teacherName.trim()) {
            setLoginError('Vui lòng nhập tên giáo viên');
            return;
        }

        try {
            // Register teacher and get teacher_id
            const response = await fetch(`${API_BASE_URL}/api/exam/register-teacher`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ teacher_name: teacherName.trim() })
            });

            if (response.ok) {
                const data = await response.json();
                setTeacherId(data.teacher_id);
                setIsLoggedIn(true);
                navigate(`/giao_vien/${data.teacher_id}`);
            } else {
                setLoginError('Không thể đăng ký giáo viên');
            }
        } catch (err) {
            setLoginError('Lỗi kết nối server');
        }
    };

    const handleGenerate = async () => {
        if (!prompt.trim()) {
            setError('Vui lòng nhập nội dung bài kiểm tra');
            return;
        }

        setIsGenerating(true);
        setError('');
        setExamResult(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/create-exam`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    teacher_id: teacherId,
                    teacher_name: teacherName.trim(),
                    prompt: prompt.trim(),
                    question_count: questionCount
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Không thể tạo bài kiểm tra');
            }

            const result = await response.json();
            setExamResult(result);

            // Reload the exams list
            loadTeacherExams(teacherId);
        } catch (err: any) {
            setError(err.message || 'Có lỗi xảy ra');
        } finally {
            setIsGenerating(false);
        }
    };

    const copyNewExamLink = () => {
        if (examResult) {
            const fullUrl = `${window.location.origin}${examResult.student_url}`;
            navigator.clipboard.writeText(fullUrl);
            setCopiedNew(true);
            setTimeout(() => setCopiedNew(false), 2000);
        }
    };

    const copyExamLink = (examId: string, url: string) => {
        const fullUrl = `${window.location.origin}${url}`;
        navigator.clipboard.writeText(fullUrl);
        setCopiedExamId(examId);
        setTimeout(() => setCopiedExamId(null), 2000);
    };

    const loadExamFull = async (examId: string) => {
        setIsLoading(true);
        setSelectedExam(examId);
        setViewMode('questions');
        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/exam/${examId}/full`);
            if (response.ok) {
                const data = await response.json();
                setExamFull(data);
            }
        } catch (err) {
            console.error('Error loading exam:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const loadStats = async (examId: string) => {
        setIsLoading(true);
        setSelectedExam(examId);
        setViewMode('stats');
        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/exam/${examId}/results`);
            if (response.ok) {
                const data = await response.json();
                setExamStats(data);
            }
        } catch (err) {
            console.error('Error loading stats:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const deleteQuestion = async (questionId: number) => {
        if (!selectedExam || !confirm('Bạn có chắc muốn xóa câu hỏi này?')) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/exam/${selectedExam}/question/${questionId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                loadExamFull(selectedExam);
                if (teacherId) loadTeacherExams(teacherId);
            }
        } catch (err) {
            console.error('Error deleting question:', err);
        }
    };

    // Login Screen
    if (!isLoggedIn) {
        return (
            <div style={{
                minHeight: '100vh',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px'
            }}>
                <div style={{
                    background: 'white',
                    borderRadius: '20px',
                    padding: '40px',
                    maxWidth: '400px',
                    width: '100%',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                    textAlign: 'center'
                }}>
                    <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>🎓</h1>
                    <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1F2937', marginBottom: '24px' }}>
                        V-Tutor - Giáo viên
                    </h2>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
                            Nhập tên của bạn để bắt đầu:
                        </label>
                        <input
                            placeholder="VD: Nguyễn Văn A"
                            value={teacherName}
                            onChange={(e) => setTeacherName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                            style={{
                                width: '100%',
                                padding: '14px',
                                borderRadius: '10px',
                                border: '2px solid #E5E7EB',
                                fontSize: '16px',
                                textAlign: 'center',
                                boxSizing: 'border-box'
                            }}
                        />
                        <p style={{ fontSize: '12px', color: '#6B7280', marginTop: '8px' }}>
                            Bạn sẽ nhận được link riêng để quản lý sau khi tạo bài đầu tiên
                        </p>
                    </div>

                    {loginError && (
                        <div style={{
                            padding: '12px',
                            background: '#FEE2E2',
                            borderRadius: '8px',
                            color: '#DC2626',
                            marginBottom: '16px'
                        }}>
                            {loginError}
                        </div>
                    )}

                    <button
                        onClick={handleLogin}
                        disabled={!teacherName.trim()}
                        style={{
                            width: '100%',
                            padding: '14px',
                            background: teacherName.trim() ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#D1D5DB',
                            color: 'white',
                            border: 'none',
                            borderRadius: '10px',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            cursor: teacherName.trim() ? 'pointer' : 'not-allowed'
                        }}
                    >
                        Bắt đầu tạo bài →
                    </button>
                </div>
            </div>
        );
    }

    // Main Dashboard
    return (
        <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '20px' }}>
            {/* Header */}
            <div style={{ maxWidth: '1400px', margin: '0 auto', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <h1 style={{ color: 'white', fontSize: '24px', fontWeight: 'bold' }}>
                        🎓 V-Tutor - Xin chào, {teacherName}
                    </h1>
                    {teacherId && (
                        <div style={{ background: 'rgba(255,255,255,0.2)', padding: '8px 16px', borderRadius: '8px', color: 'white', fontSize: '13px' }}>
                            Link quản lý: <strong>{window.location.origin}/giao_vien/{teacherId}</strong>
                        </div>
                    )}
                </div>
            </div>

            <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: '20px' }}>
                {/* Column 1: Create Exam */}
                <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', color: '#4F46E5' }}>
                        ✨ Tạo bài kiểm tra mới
                    </h2>

                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Mô tả nội dung:
                        </label>
                        <textarea
                            placeholder="VD: Tạo 5 câu hỏi về phương trình bậc nhất cho lớp 8..."
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    if (!isGenerating && prompt.trim()) {
                                        handleGenerate();
                                    }
                                }
                            }}
                            style={{
                                width: '100%',
                                minHeight: '100px',
                                padding: '12px',
                                borderRadius: '8px',
                                border: '2px solid #E5E7EB',
                                fontSize: '14px',
                                resize: 'vertical',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Số câu hỏi:
                        </label>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={questionCount}
                            onChange={(e) => setQuestionCount(parseInt(e.target.value) || 5)}
                            style={{ width: '80px', padding: '8px 12px', borderRadius: '8px', border: '2px solid #E5E7EB', fontSize: '14px' }}
                        />
                    </div>

                    {error && (
                        <div style={{ padding: '12px', background: '#FEE2E2', borderRadius: '8px', color: '#DC2626', marginBottom: '16px', fontSize: '14px' }}>
                            {error}
                        </div>
                    )}

                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating || !prompt.trim()}
                        style={{
                            width: '100%',
                            padding: '14px',
                            background: isGenerating ? '#9CA3AF' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '10px',
                            fontSize: '14px',
                            fontWeight: 'bold',
                            cursor: isGenerating ? 'not-allowed' : 'pointer'
                        }}
                    >
                        {isGenerating ? '⏳ Đang tạo...' : '✨ Tạo bài kiểm tra'}
                    </button>

                    {examResult && (
                        <div style={{ marginTop: '16px', padding: '12px', background: '#ECFDF5', borderRadius: '8px' }}>
                            <p style={{ fontWeight: 'bold', color: '#059669', marginBottom: '8px', fontSize: '14px' }}>✅ Đã tạo xong!</p>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <input
                                    value={`${window.location.origin}${examResult.student_url}`}
                                    readOnly
                                    style={{ flex: 1, padding: '8px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '11px' }}
                                />
                                <button
                                    onClick={copyNewExamLink}
                                    style={{ padding: '8px 12px', background: copiedNew ? '#059669' : '#4F46E5', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                                >
                                    {copiedNew ? '✓' : '📋'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Column 2: My Exams */}
                <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', color: '#4F46E5' }}>
                        📚 Bài kiểm tra của tôi ({teacherExams.length})
                    </h2>

                    <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                        {teacherExams.length === 0 ? (
                            <p style={{ textAlign: 'center', color: '#6B7280', padding: '40px 0' }}>
                                Chưa có bài kiểm tra nào
                            </p>
                        ) : (
                            teacherExams.map((exam) => (
                                <div
                                    key={exam.exam_id}
                                    style={{
                                        padding: '14px',
                                        background: selectedExam === exam.exam_id ? '#EEF2FF' : '#F9FAFB',
                                        borderRadius: '10px',
                                        marginBottom: '10px',
                                        border: selectedExam === exam.exam_id ? '2px solid #4F46E5' : '2px solid transparent'
                                    }}
                                >
                                    <p style={{ fontWeight: '500', fontSize: '14px', marginBottom: '6px' }}>
                                        {exam.prompt.length > 40 ? exam.prompt.substring(0, 40) + '...' : exam.prompt}
                                    </p>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6B7280', marginBottom: '10px' }}>
                                        <span>{exam.question_count} câu</span>
                                        <span>{exam.student_count} học sinh</span>
                                    </div>

                                    {/* Action buttons */}
                                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                        <button
                                            onClick={() => loadExamFull(exam.exam_id)}
                                            style={{
                                                padding: '6px 10px',
                                                background: viewMode === 'questions' && selectedExam === exam.exam_id ? '#4F46E5' : '#E5E7EB',
                                                color: viewMode === 'questions' && selectedExam === exam.exam_id ? 'white' : '#374151',
                                                border: 'none',
                                                borderRadius: '6px',
                                                fontSize: '11px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            👁 Xem câu hỏi
                                        </button>
                                        <button
                                            onClick={() => loadStats(exam.exam_id)}
                                            style={{
                                                padding: '6px 10px',
                                                background: viewMode === 'stats' && selectedExam === exam.exam_id ? '#059669' : '#E5E7EB',
                                                color: viewMode === 'stats' && selectedExam === exam.exam_id ? 'white' : '#374151',
                                                border: 'none',
                                                borderRadius: '6px',
                                                fontSize: '11px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            📊 Thống kê
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); copyExamLink(exam.exam_id, exam.student_url); }}
                                            style={{
                                                padding: '6px 10px',
                                                background: copiedExamId === exam.exam_id ? '#059669' : '#E5E7EB',
                                                color: copiedExamId === exam.exam_id ? 'white' : '#374151',
                                                border: 'none',
                                                borderRadius: '6px',
                                                fontSize: '11px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            {copiedExamId === exam.exam_id ? '✓ Copied' : '📋 Copy link'}
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Column 3: View Questions / Stats */}
                <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
                    {isLoading ? (
                        <p style={{ textAlign: 'center', color: '#6B7280', padding: '60px 0' }}>⏳ Đang tải...</p>
                    ) : !selectedExam ? (
                        <div style={{ textAlign: 'center', color: '#6B7280', padding: '60px 0' }}>
                            <p style={{ fontSize: '48px', marginBottom: '16px' }}>👆</p>
                            <p>Chọn một bài kiểm tra để xem chi tiết</p>
                        </div>
                    ) : viewMode === 'questions' && examFull ? (
                        <>
                            <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px', color: '#4F46E5' }}>
                                📝 Câu hỏi ({examFull.questions.length})
                            </h2>
                            <div style={{ maxHeight: '550px', overflowY: 'auto' }}>
                                {examFull.questions.map((q, idx) => (
                                    <div key={q.id} style={{ padding: '14px', background: '#F9FAFB', borderRadius: '10px', marginBottom: '12px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                            <p style={{ fontWeight: '600', fontSize: '14px', color: '#1F2937' }}>
                                                Câu {idx + 1}: {q.text}
                                            </p>
                                            <button
                                                onClick={() => deleteQuestion(q.id)}
                                                style={{
                                                    padding: '4px 8px',
                                                    background: '#FEE2E2',
                                                    color: '#DC2626',
                                                    border: 'none',
                                                    borderRadius: '4px',
                                                    fontSize: '11px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                🗑
                                            </button>
                                        </div>
                                        <div style={{ marginLeft: '12px', fontSize: '13px' }}>
                                            {q.options.map((opt, i) => (
                                                <p key={i} style={{
                                                    padding: '4px 8px',
                                                    marginBottom: '4px',
                                                    background: opt.startsWith(q.correct_answer) ? '#ECFDF5' : 'white',
                                                    borderRadius: '4px',
                                                    border: opt.startsWith(q.correct_answer) ? '1px solid #86EFAC' : '1px solid #E5E7EB'
                                                }}>
                                                    {opt} {opt.startsWith(q.correct_answer) && '✓'}
                                                </p>
                                            ))}
                                        </div>
                                        <p style={{ fontSize: '12px', color: '#6B7280', marginTop: '8px', fontStyle: 'italic' }}>
                                            💡 {q.explanation}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : viewMode === 'stats' && examStats ? (
                        <>
                            <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px', color: '#059669' }}>
                                📊 Thống kê ({examStats.total_students} học sinh)
                            </h2>

                            {examStats.total_students > 0 ? (
                                <>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '20px' }}>
                                        <div style={{ padding: '16px', background: '#EFF6FF', borderRadius: '10px', textAlign: 'center' }}>
                                            <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#2563EB' }}>{examStats.statistics.average_score}%</p>
                                            <p style={{ fontSize: '12px', color: '#6B7280' }}>Trung bình</p>
                                        </div>
                                        <div style={{ padding: '16px', background: '#ECFDF5', borderRadius: '10px', textAlign: 'center' }}>
                                            <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#059669' }}>{examStats.statistics.highest_score}%</p>
                                            <p style={{ fontSize: '12px', color: '#6B7280' }}>Cao nhất</p>
                                        </div>
                                        <div style={{ padding: '16px', background: '#FEF3C7', borderRadius: '10px', textAlign: 'center' }}>
                                            <p style={{ fontSize: '28px', fontWeight: 'bold', color: '#D97706' }}>{examStats.statistics.lowest_score}%</p>
                                            <p style={{ fontSize: '12px', color: '#6B7280' }}>Thấp nhất</p>
                                        </div>
                                    </div>

                                    <p style={{ fontSize: '14px', fontWeight: '500', marginBottom: '12px' }}>Chi tiết từng học sinh:</p>
                                    <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                        {examStats.students.map((student, idx) => (
                                            <div key={idx} style={{
                                                padding: '12px',
                                                background: '#F9FAFB',
                                                borderRadius: '8px',
                                                marginBottom: '8px',
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center'
                                            }}>
                                                <div>
                                                    <p style={{ fontWeight: '500', fontSize: '14px' }}>{student.student_name}</p>
                                                    <p style={{ fontSize: '11px', color: '#6B7280' }}>
                                                        {new Date(student.submitted_at).toLocaleString('vi-VN')}
                                                    </p>
                                                </div>
                                                <div style={{
                                                    fontSize: '18px',
                                                    fontWeight: 'bold',
                                                    color: student.percentage >= 80 ? '#059669' : student.percentage >= 50 ? '#D97706' : '#DC2626'
                                                }}>
                                                    {student.score}/{student.total} ({student.percentage}%)
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            ) : (
                                <p style={{ textAlign: 'center', color: '#6B7280', padding: '60px 0' }}>
                                    Chưa có học sinh nào làm bài này
                                </p>
                            )}
                        </>
                    ) : null}
                </div>
            </div>
        </div>
    );
}

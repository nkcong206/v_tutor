import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { QuestionRenderer } from '../components/QuestionRenderer';
import { Question } from '../types';

const API_BASE_URL = 'http://localhost:8000';

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
    analysis?: {
        score: number;
        summary: string;
    };
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
    const { theme, toggleTheme } = useTheme();
    const isDarkMode = theme === 'dark';

    // Login state
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [teacherName, setTeacherName] = useState('');  // Display name (original case)
    const [teacherId, setTeacherId] = useState('');      // UUID for URL
    const [loginError, setLoginError] = useState('');
    const [sessionId, setSessionId] = useState(() => Math.random().toString(36).substring(7));
    const [temperature, setTemperature] = useState<number>(0.7);
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // Exam creation state
    const [prompt, setPrompt] = useState('');
    const [questionCount, setQuestionCount] = useState<number | string>(5);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState('');
    const [examResult, setExamResult] = useState<ExamResult | null>(null);
    const [copiedNew, setCopiedNew] = useState(false);
    const [copiedExamId, setCopiedExamId] = useState<string | null>(null);
    const [copiedTeacherLink, setCopiedTeacherLink] = useState(false);

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
                    question_count: Number(questionCount) || 5,
                    session_id: sessionId,
                    temperature: temperature
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

    const copyTeacherLink = () => {
        const fullUrl = `${window.location.origin}/giao_vien/${teacherId}`;
        navigator.clipboard.writeText(fullUrl);
        setCopiedTeacherLink(true);
        setTimeout(() => setCopiedTeacherLink(false), 2000);
    };

    const handleFiles = async (files: FileList | File[]) => {
        if (!files.length) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('session_id', sessionId);

        Array.from(files).forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/upload`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                setUploadedFiles((prev: string[]) => [...prev, ...data.files]);
            }
        } catch (err) {
            console.error('Upload error:', err);
        } finally {
            setIsUploading(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            handleFiles(e.target.files);
            e.target.value = ''; // Reset input
        }
    };

    const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const onDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files) {
            handleFiles(e.dataTransfer.files);
        }
    };

    // Helper to get file extension icon/color
    const getFileIcon = (filename: string) => {
        const ext = filename.split('.').pop()?.toLowerCase() || '';
        if (['pdf'].includes(ext)) return { icon: '📄', color: '#EF4444', label: 'PDF' };
        if (['doc', 'docx'].includes(ext)) return { icon: '📝', color: '#2563EB', label: 'DOC' };
        if (['ppt', 'pptx'].includes(ext)) return { icon: '📊', color: '#D97706', label: 'PPT' };
        if (['xls', 'xlsx'].includes(ext)) return { icon: '📉', color: '#059669', label: 'XLS' };
        if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) return { icon: '🖼️', color: '#9333EA', label: 'IMG' };
        if (['py', 'js', 'html', 'css'].includes(ext)) return { icon: '💻', color: '#4B5563', label: 'CODE' };
        return { icon: '📁', color: '#6B7280', label: ext.toUpperCase() };
    };

    const handleDeleteFile = async (filename: string) => {
        try {
            const formData = new FormData();
            formData.append('session_id', sessionId);
            formData.append('filename', filename);

            await fetch(`${API_BASE_URL}/api/exam/file`, {
                method: 'DELETE',
                body: formData
            });

            setUploadedFiles((prev: string[]) => prev.filter((f: string) => f !== filename));
        } catch (err) {
            console.error('Delete error:', err);
        }
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

    // SSE Connection for real-time updates
    useEffect(() => {
        if (!selectedExam) return;

        const eventSource = new EventSource(`${API_BASE_URL}/api/exam/events/${selectedExam}`);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'new_question') {
                    const newQuestion = data.data;
                    setExamFull((prev: ExamFull | null) => {
                        if (!prev) return prev;
                        // Avoid duplicates if SSE sends same question multiple times
                        if (prev.questions.some((q: Question) => q.id === newQuestion.id)) return prev;

                        return {
                            ...prev,
                            questions: [...prev.questions, newQuestion]
                        };
                    });
                } else if (data.type === 'new_submission') {
                    const newResult = data.data;

                    // Update Exam List state (teacherExams) to reflect new student count immediately
                    setTeacherExams(prevExams => prevExams.map(exam => {
                        // Note: We infer exam_id from context or data. 
                        // Check if data.data has exam_id. If not, we can only update the CURRENTLY selected exam.
                        // But we know 'newResult' is for 'selectedExam' because SSE is scoped to 'selectedExam'.
                        if (exam.exam_id === selectedExam) {
                            return { ...exam, student_count: exam.student_count + 1 };
                        }
                        return exam;
                    }));

                    setExamStats((prev: ExamStats | null) => {
                        if (!prev) return prev;
                        // Avoid duplicates locally
                        if (prev.students.some(s => s.student_name === newResult.student_name)) return prev;

                        const newStudents = [...prev.students, newResult];
                        const scores = newStudents.map(s => s.percentage);
                        const avg = scores.reduce((a, b) => a + b, 0) / scores.length;

                        return {
                            ...prev,
                            total_students: newStudents.length,
                            statistics: {
                                average_score: Number(avg.toFixed(1)),
                                highest_score: Math.max(...scores),
                                lowest_score: Math.min(...scores)
                            },
                            students: newStudents
                        };
                    });
                } else if (data.type === 'error') {
                    console.error(" SSE Error reported:", data.message);
                    alert(`Lỗi tạo câu hỏi bù: ${data.message}`);
                }
            } catch (e) {
                console.error("Error parsing SSE message:", e);
            }
        };

        eventSource.onerror = (e) => {
            // console.error("SSE Error:", e);
            // EventSource auto-reconnects, so usually fine to ignore minor errors
            // or just log. Closing it might stop reconnection logic.
        };

        return () => {
            eventSource.close();
        };
    }, [selectedExam]);

    const [deletingQuestionId, setDeletingQuestionId] = useState<number | null>(null);

    const deleteQuestion = async (questionId: number) => {
        if (!selectedExam) return;

        // Instant delete - no confirmation needed
        setExamFull((prev: ExamFull | null) => {
            if (!prev) return prev;
            return {
                ...prev,
                questions: prev.questions.filter((q: Question) => q.id !== questionId)
            };
        });

        try {
            const response = await fetch(`${API_BASE_URL}/api/exam/exam/${selectedExam}/question/${questionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error("Failed to delete");
            }

        } catch (err) {
            console.error('Error deleting question:', err);
            alert('Có lỗi xảy ra khi xóa câu hỏi. Vui lòng tải lại trang.');
            // Revert UI if needed? Complex. For now, alert to reload.
        }
    };

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


    if (!isLoggedIn) {
        return (
            <div style={{
                minHeight: '100vh',
                background: isDarkMode ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px'
            }}>
                <ThemeToggle />
                <div style={{
                    background: isDarkMode ? '#1F2937' : 'white',
                    borderRadius: '20px',
                    padding: '40px',
                    maxWidth: '400px',
                    width: '100%',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                    textAlign: 'center',
                    color: isDarkMode ? 'white' : 'inherit'
                }}>
                    <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>🎓</h1>
                    <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: isDarkMode ? 'white' : '#1F2937', marginBottom: '24px' }}>
                        V-Tutor - Giáo viên
                    </h2>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: isDarkMode ? '#D1D5DB' : '#374151' }}>
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
                                border: isDarkMode ? '2px solid #374151' : '2px solid #E5E7EB',
                                fontSize: '16px',
                                textAlign: 'center',
                                boxSizing: 'border-box',
                                background: isDarkMode ? '#374151' : 'white',
                                color: isDarkMode ? 'white' : 'inherit'
                            }}
                        />
                        <p style={{ fontSize: '12px', color: isDarkMode ? '#9CA3AF' : '#6B7280', marginTop: '8px' }}>
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
        <div style={{
            minHeight: '100vh',
            background: isDarkMode ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '20px',
            color: isDarkMode ? 'white' : 'inherit'
        }}>
            <ThemeToggle />
            {/* Header */}
            <div style={{ maxWidth: '1600px', margin: '0 auto', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <h1 style={{ color: 'white', fontSize: '24px', fontWeight: 'bold' }}>
                            🎓 V-Teacher - Xin chào, {teacherName}
                        </h1>
                    </div>

                    {teacherId && (
                        <div style={{
                            background: 'rgba(255, 255, 255, 0.2)',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            color: 'white',
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            backdropFilter: 'blur(5px)',
                            border: '1px solid rgba(255, 255, 255, 0.1)'
                        }}>
                            <code style={{ fontFamily: 'monospace', color: '#FFF' }}>
                                {window.location.origin}/giao_vien/{teacherId}
                            </code>
                            <button
                                onClick={copyTeacherLink}
                                style={{
                                    background: copiedTeacherLink ? '#10B981' : 'rgba(255,255,255,0.2)',
                                    border: 'none',
                                    borderRadius: '4px',
                                    width: '24px',
                                    height: '24px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                    padding: 0,
                                    color: 'white',
                                    transition: 'all 0.2s'
                                }}
                                title="Copy link"
                            >
                                {copiedTeacherLink ? '✓' : '📋'}
                            </button>
                        </div>
                    )}
                </div>
            </div>

            <div style={{ maxWidth: '1600px', margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: '20px' }}>
                {/* Column 1: Create Exam */}
                <div style={{
                    background: isDarkMode ? '#1F2937' : 'white',
                    borderRadius: '16px',
                    padding: '24px',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
                }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', color: isDarkMode ? '#818CF8' : '#4F46E5' }}>
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
                                border: isDarkMode ? '2px solid #374151' : '2px solid #E5E7EB',
                                fontSize: '14px',
                                resize: 'vertical',
                                boxSizing: 'border-box',
                                background: isDarkMode ? '#374151' : 'white',
                                color: isDarkMode ? 'white' : 'inherit'
                            }}
                        />
                    </div>

                    {/* File Upload Section */}
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Tài liệu tham khảo:
                        </label>

                        {/* Drag & Drop Area */}
                        <div
                            onDragOver={onDragOver}
                            onDragLeave={onDragLeave}
                            onDrop={onDrop}
                            onClick={() => document.getElementById('file-upload')?.click()}
                            style={{
                                border: `2px dashed ${isDragging ? '#4F46E5' : (isDarkMode ? '#4B5563' : '#D1D5DB')}`,
                                borderRadius: '12px',
                                padding: '20px',
                                textAlign: 'center',
                                background: isDragging ? (isDarkMode ? '#374151' : '#EEF2FF') : (isDarkMode ? '#111827' : '#F9FAFB'),
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                marginBottom: '12px'
                            }}
                        >
                            <input
                                id="file-upload"
                                type="file"
                                multiple
                                onChange={handleFileUpload}
                                style={{ display: 'none' }}
                            />
                            <p style={{ fontSize: '24px', marginBottom: '8px' }}>☁️</p>
                            <p style={{ fontSize: '13px', color: isDarkMode ? '#D1D5DB' : '#4B5563', marginBottom: '4px' }}>
                                Kéo thả file hoặc <span style={{ color: '#4F46E5', fontWeight: 'bold' }}>click để chọn</span>
                            </p>
                            <p style={{ fontSize: '11px', color: '#9CA3AF' }}>
                                Hỗ trợ PDF, DOCX, Hình ảnh...
                            </p>
                            {isUploading && (
                                <div style={{ marginTop: '8px', fontSize: '12px', color: '#4F46E5', fontWeight: 'bold' }}>
                                    ⏳ Đang tải lên...
                                </div>
                            )}
                        </div>

                        {/* Horizontal File List */}
                        {uploadedFiles.length > 0 && (
                            <div style={{
                                display: 'flex',
                                gap: '10px',
                                overflowX: 'auto',
                                paddingBottom: '8px',
                                scrollbarWidth: 'thin'
                            }}>
                                {uploadedFiles.map((file: string, idx: number) => {
                                    const fileInfo = getFileIcon(file);
                                    return (
                                        <div
                                            key={idx}
                                            title={file} // Tooltip showing full filename
                                            style={{
                                                flexShrink: 0,
                                                background: isDarkMode ? '#374151' : 'white',
                                                border: isDarkMode ? 'none' : '1px solid #E5E7EB',
                                                color: isDarkMode ? 'white' : '#1F2937',
                                                borderRadius: '8px',
                                                padding: '10px',
                                                width: '140px',
                                                display: 'flex',
                                                flexDirection: 'column',
                                                justifyContent: 'space-between',
                                                position: 'relative',
                                                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                                <span style={{ fontSize: '16px' }}>{fileInfo.icon}</span>
                                                <span style={{
                                                    fontSize: '10px',
                                                    fontWeight: 'bold',
                                                    color: fileInfo.color,
                                                    background: isDarkMode ? 'rgba(255,255,255,0.1)' : '#F3F4F6',
                                                    padding: '2px 6px',
                                                    borderRadius: '4px'
                                                }}>
                                                    {fileInfo.label}
                                                </span>
                                            </div>

                                            <div style={{ fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '4px' }}>
                                                {file}
                                            </div>

                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDeleteFile(file);
                                                }}
                                                style={{
                                                    position: 'absolute',
                                                    top: '4px',
                                                    right: '4px',
                                                    background: isDarkMode ? 'rgba(255,255,255,0.2)' : '#F3F4F6',
                                                    border: 'none',
                                                    borderRadius: '50%',
                                                    width: '20px',
                                                    height: '20px',
                                                    color: '#F87171',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    fontSize: '10px'
                                                }}
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Temperature Slider */}
                    <div style={{ marginBottom: '24px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <label style={{ fontWeight: '500', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                🌡️ Độ sáng tạo
                            </label>
                            <span style={{
                                background: isDarkMode ? '#374151' : '#EEF2FF',
                                color: isDarkMode ? 'white' : '#4F46E5',
                                padding: '4px 12px',
                                borderRadius: '12px',
                                fontSize: '14px',
                                fontWeight: 'bold',
                                border: isDarkMode ? '1px solid #4B5563' : '1px solid #C7D2FE'
                            }}>
                                {temperature}
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={temperature}
                            onChange={(e) => setTemperature(parseFloat(e.target.value))}
                            style={{
                                width: '100%',
                                height: '6px',
                                background: isDarkMode ? '#374151' : '#E5E7EB',
                                borderRadius: '5px',
                                outline: 'none',
                                cursor: 'pointer',
                                accentColor: '#4F46E5'
                            }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: '#9CA3AF' }}>
                            <span>Chính xác (0.0)</span>
                            <span>Cân bằng (0.5)</span>
                            <span>Sáng tạo (1.0)</span>
                        </div>
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                            Số lượng câu hỏi:
                        </label>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={questionCount}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (val === '') {
                                    setQuestionCount('');
                                } else {
                                    setQuestionCount(parseInt(val));
                                }
                            }}
                            style={{
                                width: '80px',
                                padding: '8px 12px',
                                borderRadius: '8px',
                                border: isDarkMode ? '2px solid #374151' : '2px solid #E5E7EB',
                                fontSize: '14px',
                                background: isDarkMode ? '#374151' : 'white',
                                color: isDarkMode ? 'white' : 'inherit'
                            }}
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


                </div>

                {/* Column 2: My Exams */}
                <div style={{
                    background: isDarkMode ? '#1F2937' : 'white',
                    borderRadius: '16px',
                    padding: '24px',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
                }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', color: isDarkMode ? '#818CF8' : '#4F46E5' }}>
                        📚 Bài kiểm tra của tôi ({teacherExams.length})
                    </h2>

                    <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                        {teacherExams.length === 0 ? (
                            <p style={{ textAlign: 'center', color: '#6B7280', padding: '40px 0' }}>
                                Chưa có bài kiểm tra nào
                            </p>
                        ) : (
                            teacherExams.map((exam: ExamInfo) => <div
                                key={exam.exam_id}
                                style={{
                                    padding: '14px',
                                    background: selectedExam === exam.exam_id ? (isDarkMode ? '#312E81' : '#EEF2FF') : (isDarkMode ? '#374151' : '#F9FAFB'),
                                    borderRadius: '10px',
                                    marginBottom: '10px',
                                    border: selectedExam === exam.exam_id ? '2px solid #4F46E5' : '2px solid transparent'
                                }}
                            >
                                <p style={{ fontWeight: '500', fontSize: '14px', marginBottom: '6px', color: isDarkMode ? 'white' : 'inherit' }}>
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
                        }
                    </div>
                </div>

                {/* Column 3: View Questions / Stats */}
                <div style={{
                    background: isDarkMode ? '#1F2937' : 'white',
                    borderRadius: '16px',
                    padding: '24px',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                    height: 'calc(100vh - 120px)',  // Fixed height to fit page
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    {isLoading ? (
                        <p style={{ textAlign: 'center', color: '#6B7280', padding: '60px 0' }}>⏳ Đang tải...</p>
                    ) : !selectedExam ? (
                        <div style={{ textAlign: 'center', color: '#6B7280', padding: '60px 0' }}>
                            <p style={{ fontSize: '48px', marginBottom: '16px' }}>👆</p>
                            <p>Chọn một bài kiểm tra để xem chi tiết</p>
                        </div>
                    ) : viewMode === 'questions' && examFull ? (
                        <>
                            <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px', color: isDarkMode ? '#818CF8' : '#4F46E5' }}>
                                📝 Câu hỏi ({examFull.questions.length})
                            </h2>
                            <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
                                {examFull.questions.map((q: Question, idx: number) => (
                                    <div key={`${q.id}-${idx}`} style={{ padding: '14px', background: isDarkMode ? '#374151' : '#F9FAFB', borderRadius: '10px', marginBottom: '12px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                            <p style={{ fontWeight: '600', fontSize: '14px', color: isDarkMode ? 'white' : '#1F2937' }}>
                                                Câu {idx + 1}:
                                            </p>
                                            <button
                                                onClick={(e: React.MouseEvent) => {
                                                    e.stopPropagation();
                                                    deleteQuestion(q.id);
                                                }}
                                                disabled={deletingQuestionId === q.id}
                                                style={{
                                                    padding: '4px 8px',
                                                    background: deletingQuestionId === q.id ? '#E5E7EB' : '#FEE2E2',
                                                    color: deletingQuestionId === q.id ? '#6B7280' : '#DC2626',
                                                    border: 'none',
                                                    borderRadius: '4px',
                                                    fontSize: '11px',
                                                    cursor: deletingQuestionId === q.id ? 'not-allowed' : 'pointer',
                                                    minWidth: '24px'
                                                }}
                                            >
                                                {deletingQuestionId === q.id ? '⏳' : '🗑'}
                                            </button>
                                        </div>

                                        {/* Render Question Content & Correct Answer */}
                                        <div style={{ marginBottom: '12px' }}>
                                            <QuestionRenderer
                                                question={q}
                                                // User requested not to show answers in the blanks for Teacher View
                                                currentAnswer={undefined}
                                                onAnswerChange={() => { }} // Read only
                                                isDarkMode={isDarkMode}
                                                viewMode="teacher"
                                            />
                                        </div>

                                        <p style={{ fontSize: '12px', color: '#6B7280', marginTop: '8px', fontStyle: 'italic', borderTop: '1px solid #E5E7EB', paddingTop: '8px' }}>
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
                                    <div style={{
                                        marginTop: '16px',
                                        flex: 1,
                                        overflowY: 'auto',
                                        paddingRight: '6px'
                                    }}>
                                        {examStats.students.map((student: StudentResult, idx: number) => (
                                            <div key={idx} style={{
                                                padding: '12px',
                                                background: isDarkMode ? '#374151' : '#F9FAFB',
                                                borderRadius: '8px',
                                                marginBottom: '8px',
                                                border: isDarkMode ? '1px solid #4B5563' : 'none'
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <div>
                                                        <p style={{ fontWeight: '500', fontSize: '14px', color: isDarkMode ? 'white' : '#1F2937' }}>{student.student_name}</p>
                                                        <p style={{ fontSize: '11px', color: isDarkMode ? '#D1D5DB' : '#6B7280' }}>
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

                                                {/* AI Analysis Display */}
                                                {student.analysis && (
                                                    <div style={{
                                                        marginTop: '10px',
                                                        padding: '10px',
                                                        borderRadius: '6px',
                                                        background: isDarkMode ? 'rgba(59, 130, 246, 0.2)' : '#EFF6FF',
                                                        border: `1px solid ${isDarkMode ? '#3B82F6' : '#BFDBFE'}`
                                                    }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                                            <span style={{ fontSize: '14px' }}>🤖</span>
                                                            <span style={{ fontSize: '12px', fontWeight: 'bold', color: isDarkMode ? '#93C5FD' : '#1E40AF' }}>
                                                                AI đánh giá: {student.analysis.score}/10
                                                            </span>
                                                        </div>
                                                        <p style={{ fontSize: '12px', color: isDarkMode ? '#D1D5DB' : '#374151', fontStyle: 'italic', lineHeight: '1.4' }}>
                                                            "{student.analysis.summary}"
                                                        </p>
                                                    </div>
                                                )}
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
            </div >
        </div >
    );
}

import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TeacherPage } from './pages/TeacherPage';
import { StudentPage } from './pages/StudentPage';
import { UIPreviewPage } from './pages/UIPreviewPage';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/giao_vien" replace />} />
        <Route path="/giao_vien" element={<TeacherPage />} />
        <Route path="/giao_vien/:teacherName" element={<TeacherPage />} />
        <Route path="/hoc_sinh/:examId" element={<StudentPage />} />
        <Route path="/ui-preview" element={<UIPreviewPage />} />
      </Routes>
    </BrowserRouter>
  );
}


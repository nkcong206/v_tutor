import React from 'react';
import { Question } from '../../types';

interface QuestionMediaProps {
    question: Question;
}

export const QuestionMedia: React.FC<QuestionMediaProps> = ({ question }) => {
    return (
        <div style={{ marginBottom: '16px' }}>
            {/* Image */}
            {(question.image_base64 || question.image_url) && (
                <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
                    <img
                        src={question.image_base64
                            ? `data:image/png;base64,${question.image_base64}`
                            : question.image_url!}
                        alt="Question Media"
                        style={{
                            width: '100%',
                            maxHeight: '250px', // Reduced to prevent scrolling
                            objectFit: 'contain',
                            borderRadius: '8px'
                        }}
                    />
                </div>
            )}

            {/* Audio */}
            {question.audio_url && (
                <div style={{ marginBottom: '12px', width: '100%' }}>
                    <audio controls style={{ width: '100%' }} key={`audio-${question.id}`}>
                        <source src={question.audio_url} type="audio/mpeg" />
                        Trình duyệt không hỗ trợ audio.
                    </audio>
                </div>
            )}
        </div>
    );
};

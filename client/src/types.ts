export interface Question {
    id: number;
    text: string;
    options: string[];
    correct_answer?: string | number;
    correct_answers?: (number | string)[];
    type?: 'single_choice' | 'multi_choice' | 'fill_in_blanks' |
    'image_single_choice' | 'image_multi_choice' | 'image_fill_in_blanks' |
    'audio_single_choice' | 'audio_multi_choice' | 'audio_fill_in_blanks';
    image_url?: string | null;
    image_base64?: string | null;
    audio_url?: string | null;
    blanks?: string[];
    explanation?: string;
    audio_text?: string;
    image_description?: string;
    audio_script_text?: string;
}

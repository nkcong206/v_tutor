import React from 'react';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

interface LatexTextProps {
    children: string;
    className?: string;
    style?: React.CSSProperties;
}

/**
 * Renders text with LaTeX math expressions.
 * Supports:
 * - Inline math: $...$ or \(...\)
 * - Display/block math: $$...$$ or \[...\]
 */
export const LatexText: React.FC<LatexTextProps> = ({ children, className, style }) => {
    if (!children || typeof children !== 'string') {
        return <span className={className} style={style}>{children}</span>;
    }

    // Split text into parts: regular text and LaTeX expressions
    const parts: React.ReactNode[] = [];
    let remaining = children;
    let key = 0;

    // Regex patterns for LaTeX
    // Display math: $$...$$ or \[...\]
    // Inline math: $...$ (not $$) or \(...\)
    const displayMathRegex = /\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]/;
    const inlineMathRegex = /\$([^\$]+?)\$|\\\(([^\)]+?)\\\)/;

    while (remaining.length > 0) {
        // Try to find display math first (it uses $$)
        const displayMatch = remaining.match(displayMathRegex);
        const inlineMatch = remaining.match(inlineMathRegex);

        // Determine which match comes first
        let match: RegExpMatchArray | null = null;
        let isDisplay = false;

        if (displayMatch && inlineMatch) {
            if ((displayMatch.index ?? Infinity) <= (inlineMatch.index ?? Infinity)) {
                match = displayMatch;
                isDisplay = true;
            } else {
                match = inlineMatch;
                isDisplay = false;
            }
        } else if (displayMatch) {
            match = displayMatch;
            isDisplay = true;
        } else if (inlineMatch) {
            match = inlineMatch;
            isDisplay = false;
        }

        if (match && match.index !== undefined) {
            // Add text before the match
            if (match.index > 0) {
                parts.push(<span key={key++}>{remaining.slice(0, match.index)}</span>);
            }

            // Extract the LaTeX content (from either capture group)
            const latex = match[1] || match[2];

            try {
                if (isDisplay) {
                    parts.push(
                        <BlockMath key={key++} math={latex} />
                    );
                } else {
                    parts.push(
                        <InlineMath key={key++} math={latex} />
                    );
                }
            } catch (e) {
                // If LaTeX parsing fails, show original text
                parts.push(<span key={key++} style={{ color: 'red' }}>{match[0]}</span>);
            }

            // Continue with remaining text
            remaining = remaining.slice(match.index + match[0].length);
        } else {
            // No more LaTeX, add remaining text
            parts.push(<span key={key++}>{remaining}</span>);
            break;
        }
    }

    return <span className={className} style={style}>{parts}</span>;
};

export default LatexText;

// frontend/src/components/DecryptedText.jsx
import React, { useState, useEffect, useRef } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*()';

export default function DecryptedText({ text, speed = 40, delay = 600, className = '', animateOn = 'hover' }) {
  const [displayText, setDisplayText] = useState(text);
  const [isAnimating, setIsAnimating] = useState(false);
  const intervalRef = useRef(null);

  const startAnimation = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    
    let currentIteration = 0;
    const originalText = text;
    
    clearInterval(intervalRef.current);
    
    intervalRef.current = setInterval(() => {
      setDisplayText(
        originalText
          .split('')
          .map((char, index) => {
            if (char === ' ') return ' ';
            if (index < currentIteration) {
              return originalText[index];
            }
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          })
          .join('')
      );
      
      currentIteration += 1/3;
      if (currentIteration >= originalText.length + 1) {
        clearInterval(intervalRef.current);
        setDisplayText(originalText);
        setIsAnimating(false);
      }
    }, speed);
  };

  useEffect(() => {
    if (animateOn === 'mount') {
      const t = setTimeout(() => {
        startAnimation();
      }, delay);
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <span
      className={className}
      onMouseEnter={animateOn === 'hover' ? startAnimation : undefined}
      style={{ display: 'inline-block' }}
    >
      {displayText}
    </span>
  );
}

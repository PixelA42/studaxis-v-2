/**
 * Convert quiz JSON to PDF for teacher download.
 * Same data shape as quizToDocx: quiz_title, topic, difficulty, questions with options and correct_answer.
 */

import { jsPDF } from 'jspdf';

interface QuizQuestion {
  question?: string;
  text?: string;
  options?: string[];
  correct_answer?: string;
  answer?: string;
  explanation?: string;
}

interface QuizData {
  quiz_title?: string;
  quizTitle?: string;
  topic?: string;
  difficulty?: string;
  questions?: QuizQuestion[];
}

function getQuestions(quizData: Record<string, unknown>): unknown[] {
  let raw = quizData;
  const q = raw.questions ?? raw.Questions;
  if (Array.isArray(q) && q.length > 0) return q;
  if (raw.quiz && typeof raw.quiz === 'object') {
    const inner = (raw.quiz as Record<string, unknown>).questions ?? (raw.quiz as Record<string, unknown>).Questions;
    return Array.isArray(inner) ? inner : [];
  }
  if (raw.data && typeof raw.data === 'object') {
    const inner = (raw.data as Record<string, unknown>).questions ?? (raw.data as Record<string, unknown>).Questions;
    return Array.isArray(inner) ? inner : [];
  }
  return Array.isArray(q) ? q : [];
}

function normalizeOptions(opts: unknown): string[] {
  if (!opts || !Array.isArray(opts)) return [];
  return opts.map((o) => {
    if (typeof o === 'string') return o;
    if (o && typeof o === 'object' && 'text' in o) return String((o as { text?: string }).text ?? '');
    if (o && typeof o === 'object' && 'option' in o) return String((o as { option?: string }).option ?? '');
    return String(o);
  }).filter(Boolean);
}

function normalizeQuestion(q: unknown): QuizQuestion {
  if (!q || typeof q !== 'object') return {};
  const raw = q as Record<string, unknown>;
  return {
    question: String(raw.question ?? raw.text ?? ''),
    options: normalizeOptions(raw.options),
    correct_answer: String(raw.correct_answer ?? raw.answer ?? raw.correct ?? ''),
    explanation: String(raw.explanation ?? ''),
  };
}

function normalizeQuiz(quiz: unknown): QuizData {
  if (!quiz || typeof quiz !== 'object') return {};
  let raw = quiz as Record<string, unknown>;
  if (raw.quiz && typeof raw.quiz === 'object') raw = raw.quiz as Record<string, unknown>;
  else if (raw.data && typeof raw.data === 'object') raw = raw.data as Record<string, unknown>;
  else if (raw.body && typeof raw.body === 'object') raw = raw.body as Record<string, unknown>;
  const questionsRaw = raw.questions ?? raw.Questions;
  const questions = Array.isArray(questionsRaw) ? questionsRaw.map(normalizeQuestion) : [];
  return {
    quiz_title: String(raw.quiz_title ?? raw.quizTitle ?? raw.title ?? 'Quiz'),
    topic: String(raw.topic ?? ''),
    difficulty: String(raw.difficulty ?? ''),
    questions,
  };
}

const MARGIN = 20;
const PAGE_WIDTH = 210; // A4
const MAX_WIDTH = PAGE_WIDTH - 2 * MARGIN;
const LINE_HEIGHT = 6;
const TITLE_SIZE = 18;
const HEADING_SIZE = 12;
const BODY_SIZE = 10;

/** Wrap text to fit width and return array of lines; advance y by (lines.length * lineHeight). */
function addWrappedText(
  doc: jsPDF,
  text: string,
  x: number,
  y: number,
  options: { maxWidth?: number; fontSize?: number; lineHeight?: number }
): number {
  const maxWidth = options.maxWidth ?? MAX_WIDTH;
  const fontSize = options.fontSize ?? BODY_SIZE;
  const lineHeight = options.lineHeight ?? LINE_HEIGHT;
  doc.setFontSize(fontSize);
  const lines = doc.splitTextToSize(text, maxWidth);
  doc.text(lines, x, y);
  return y + lines.length * lineHeight;
}

/**
 * Export quiz JSON to PDF and trigger download.
 */
export function exportToPdf(quizData: QuizData | Record<string, unknown> | null | undefined, filename?: string): void {
  if (!quizData || typeof quizData !== 'object') {
    throw new Error('No quiz data. Generate a quiz first.');
  }
  const questions = getQuestions(quizData as Record<string, unknown>);
  if (questions.length === 0) {
    throw new Error('Quiz has no questions. Cannot generate an empty PDF.');
  }

  const normalized = normalizeQuiz(quizData);
  const title = normalized.quiz_title || 'Quiz';
  const topic = normalized.topic || '';
  const difficulty = (normalized.difficulty || '').charAt(0).toUpperCase() + (normalized.difficulty || '').slice(1);
  const questionsList = normalized.questions || [];

  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  let y = MARGIN;

  // Title
  doc.setFontSize(TITLE_SIZE);
  doc.setFont('helvetica', 'bold');
  doc.text('Studaxis Generated Quiz', PAGE_WIDTH / 2, y, { align: 'center' });
  y += 10;

  doc.setFontSize(BODY_SIZE);
  doc.setFont('helvetica', 'normal');
  const meta: string[] = [];
  if (topic) meta.push(`Topic: ${topic}`);
  if (difficulty) meta.push(`Difficulty: ${difficulty}`);
  if (meta.length > 0) {
    doc.text(meta.join('  ·  '), PAGE_WIDTH / 2, y, { align: 'center' });
    y += 10;
  }
  y += 4;

  // Questions
  for (let i = 0; i < questionsList.length; i++) {
    const q = questionsList[i];
    const qText = q.question || q.text || `Question ${i + 1}`;
    const options = q.options || [];

    if (y > 270) {
      doc.addPage();
      y = MARGIN;
    }

    doc.setFontSize(HEADING_SIZE);
    doc.setFont('helvetica', 'bold');
    y = addWrappedText(doc, `${i + 1}. ${qText}`, MARGIN, y, { fontSize: HEADING_SIZE, lineHeight: 6 }) + 2;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(BODY_SIZE);
    if (options.length > 0) {
      options.forEach((opt, j) => {
        const optStr = typeof opt === 'string' ? opt : String(opt);
        y = addWrappedText(doc, `   ${String.fromCharCode(65 + j)}. ${optStr}`, MARGIN, y, { lineHeight: 5 }) + 1;
      });
    } else {
      y = addWrappedText(doc, '   _________________________________________________________', MARGIN, y, { lineHeight: 5 }) + 4;
    }
    y += 4;
  }

  // Answer key on new page
  doc.addPage();
  y = MARGIN;

  doc.setFontSize(TITLE_SIZE);
  doc.setFont('helvetica', 'bold');
  doc.text('Answer Key', PAGE_WIDTH / 2, y, { align: 'center' });
  y += 12;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(BODY_SIZE);

  questionsList.forEach((q, i) => {
    if (y > 270) {
      doc.addPage();
      y = MARGIN;
    }
    const qText = q.question || q.text || `Question ${i + 1}`;
    const correct = q.correct_answer || q.answer || '';
    const explanation = q.explanation || '';

    doc.setFont('helvetica', 'bold');
    y = addWrappedText(doc, `${i + 1}. ${qText.slice(0, 70)}${qText.length > 70 ? '...' : ''}`, MARGIN, y, { fontSize: BODY_SIZE, lineHeight: 5 }) + 1;
    doc.setFont('helvetica', 'normal');
    if (correct) {
      y = addWrappedText(doc, `   Correct: ${correct}`, MARGIN, y, { lineHeight: 5 }) + 1;
    }
    if (explanation) {
      y = addWrappedText(doc, `   Explanation: ${explanation}`, MARGIN, y, { lineHeight: 5 }) + 2;
    }
    y += 2;
  });

  const fname = filename || `quiz-${Date.now()}.pdf`;
  doc.save(fname);
}

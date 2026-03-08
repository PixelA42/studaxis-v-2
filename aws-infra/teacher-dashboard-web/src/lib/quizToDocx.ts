/**
 * Convert quiz JSON to Word (.docx) format for teacher download
 * Handles multiple API/S3 response shapes (snake_case, camelCase, nested)
 *
 * Layout:
 * - Header: "Studaxis Generated Quiz" title, subtitle for topic + difficulty
 * - Body: Question text only; MCQ options A-D; blank space for subjective
 * - Answer Key (after page break): Correct answers + AI explanations
 */

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  PageBreak,
} from 'docx';
import { saveAs } from 'file-saver';

interface QuizQuestion {
  question?: string;
  text?: string;
  options?: string[] | { text?: string; option?: string }[];
  correct_answer?: string;
  answer?: string;
  correct?: string | number;
  explanation?: string;
  question_type?: string;
}

export interface QuizData {
  quiz_title?: string;
  quizTitle?: string;
  topic?: string;
  difficulty?: string;
  questions?: QuizQuestion[];
}

function normalizeQuestion(q: unknown): QuizQuestion {
  if (!q || typeof q !== 'object') return {};
  const raw = q as Record<string, unknown>;
  return {
    question: String(raw.question ?? raw.text ?? ''),
    options: normalizeOptions(raw.options),
    correct_answer: String(raw.correct_answer ?? raw.answer ?? raw.correct ?? ''),
    explanation: String(raw.explanation ?? ''),
    question_type: String(raw.question_type ?? 'mcq'),
  };
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

function normalizeQuiz(quiz: unknown): QuizData {
  if (!quiz || typeof quiz !== 'object') return {};
  let raw = quiz as Record<string, unknown>;
  // Unwrap common response shapes: { quiz: {...} }, { data: {...} }, { body: {...} }
  if (raw.quiz && typeof raw.quiz === 'object') raw = raw.quiz as Record<string, unknown>;
  else if (raw.data && typeof raw.data === 'object') raw = raw.data as Record<string, unknown>;
  else if (raw.body && typeof raw.body === 'object') raw = raw.body as Record<string, unknown>;

  const questionsRaw = raw.questions ?? raw.Questions;
  const questions = Array.isArray(questionsRaw)
    ? questionsRaw.map(normalizeQuestion)
    : [];
  return {
    quiz_title: String(raw.quiz_title ?? raw.quizTitle ?? raw.title ?? ''),
    topic: String(raw.topic ?? ''),
    difficulty: String(raw.difficulty ?? ''),
    questions,
  };
}

/**
 * Builds a Word document with quiz body (no answers) and Answer Key at the end.
 */
export function buildQuizDocx(quiz: QuizData | unknown): Document {
  const normalized = normalizeQuiz(quiz);
  const topic = normalized.topic || '';
  const difficulty = (normalized.difficulty || '').charAt(0).toUpperCase() + (normalized.difficulty || '').slice(1);
  const questions = normalized.questions || [];

  const children: Paragraph[] = [
    // Header: Main title
    new Paragraph({
      text: 'Studaxis Generated Quiz',
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { after: 400 },
    }),
  ];

  // Subtitle: topic and difficulty
  const meta: string[] = [];
  if (topic) meta.push(`Topic: ${topic}`);
  if (difficulty) meta.push(`Difficulty: ${difficulty}`);
  if (meta.length > 0) {
    children.push(
      new Paragraph({
        text: meta.join('  ·  '),
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 },
      })
    );
  }

  // Body: Questions only (no answers in body)
  questions.forEach((q, i) => {
    const qText = q.question || q.text || `Question ${i + 1}`;
    const options = q.options || [];
    const isMcq = options.length > 0;

    children.push(
      new Paragraph({
        text: `${i + 1}. ${qText}`,
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 400, after: 200 },
      })
    );

    if (isMcq) {
      options.forEach((opt, j) => {
        const optStr = typeof opt === 'string' ? opt : String(opt);
        children.push(
          new Paragraph({
            children: [new TextRun({ text: `   ${String.fromCharCode(65 + j)}. ${optStr}` })],
            spacing: { after: 100 },
          })
        );
      });
    } else {
      // Subjective/open-ended: leave blank space for answers
      children.push(
        new Paragraph({
          text: '_______________________________________________________________',
          spacing: { before: 100, after: 100 },
        })
      );
      children.push(
        new Paragraph({
          text: '_______________________________________________________________',
          spacing: { after: 200 },
        })
      );
    }

    children.push(
      new Paragraph({
        text: '',
        spacing: { after: 200 },
      })
    );
  });

  // Page break before Answer Key
  children.push(
    new Paragraph({
      children: [new PageBreak()],
    })
  );

  // Answer Key section
  children.push(
    new Paragraph({
      text: 'Answer Key',
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 400 },
    })
  );

  questions.forEach((q, i) => {
    const correct = q.correct_answer || q.answer || '';
    const explanation = q.explanation || '';
    const qText = q.question || q.text || `Question ${i + 1}`;

    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: `${i + 1}. `, bold: true }),
          new TextRun({ text: qText.slice(0, 80) + (qText.length > 80 ? '...' : ''), italics: true }),
        ],
        spacing: { before: 300, after: 100 },
      })
    );

    if (correct) {
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: 'Correct Answer: ', bold: true }),
            new TextRun({ text: correct }),
          ],
          spacing: { after: 100 },
        })
      );
    }
    if (explanation) {
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: 'Explanation: ', bold: true }),
            new TextRun({ text: explanation }),
          ],
          spacing: { after: 200 },
        })
      );
    }
  });

  return new Document({
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });
}

function getQuestionsFromPayload(data: Record<string, unknown>): unknown[] {
  let raw = data;
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

/**
 * Export quiz to DOCX and trigger download.
 * Failsafe: throws if quizData or questions is null/empty (do not generate blank file).
 */
export async function exportToDocx(quizData: QuizData | Record<string, unknown> | null | undefined, filename?: string): Promise<void> {
  if (!quizData || typeof quizData !== 'object') {
    throw new Error('No quiz data. Generate a quiz first.');
  }

  const questions = getQuestionsFromPayload(quizData as Record<string, unknown>);
  if (questions.length === 0) {
    throw new Error('Quiz has no questions. Cannot generate an empty document.');
  }

  const doc = buildQuizDocx(quizData);
  const blob = await Packer.toBlob(doc);
  const fname = filename || `quiz-${Date.now()}.docx`;
  saveAs(blob, fname);
}

/** @deprecated Use exportToDocx for failsafe behavior. Kept for compatibility. */
export async function downloadQuizAsDocx(quiz: QuizData | unknown, filename?: string): Promise<void> {
  await exportToDocx(quiz as QuizData | Record<string, unknown>, filename);
}

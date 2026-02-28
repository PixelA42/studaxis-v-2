"""
Ollama Client Wrapper
Handles communication with local Ollama instance
"""

import ollama
import time
from typing import Dict, List, Optional


class OllamaClient:
    """Wrapper for Ollama API with error handling and optimization"""
    
    def __init__(self, model: str = "llama3:3b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.client = ollama.Client(host=host)
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verify Ollama is running and model is available"""
        try:
            models = self.client.list()
            available_models = [m['name'] for m in models.get('models', [])]
            
            if self.model not in available_models:
                raise ValueError(
                    f"Model '{self.model}' not found. Available: {available_models}\n"
                    f"Run: ollama pull {self.model}"
                )
            return True
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                f"Ensure Ollama is running.\nError: {str(e)}"
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout: int = 30
    ) -> Dict:
        """
        Generate response from Ollama
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response tokens
            timeout: Timeout in seconds
        
        Returns:
            Dict with 'response', 'tokens', 'duration'
        """
        start_time = time.time()
        
        try:
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            
            duration = time.time() - start_time
            
            return {
                'response': response['message']['content'],
                'tokens': response.get('eval_count', 0),
                'duration': round(duration, 2),
                'model': self.model
            }
        
        except Exception as e:
            return {
                'response': None,
                'error': str(e),
                'duration': time.time() - start_time
            }
    
    def generate_with_rag(
        self,
        query: str,
        context_chunks: List[str],
        system_prompt: Optional[str] = None,
        max_tokens: int = 512
    ) -> Dict:
        """
        Generate response with RAG context
        
        Args:
            query: User query
            context_chunks: Retrieved textbook chunks
            system_prompt: System instructions
            max_tokens: Maximum response tokens
        
        Returns:
            Dict with response and metadata
        """
        # Build RAG prompt
        context = "\n\n".join([f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(context_chunks)])
        
        rag_prompt = f"""Context from textbook:
{context}

Question: {query}

Answer the question using ONLY the information from the context above. Include source references [Source N] in your answer."""
        
        return self.generate(
            prompt=rag_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
    
    def grade_answer(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        max_score: float = 10.0
    ) -> Dict:
        """
        Grade subjective answer using AI
        
        Returns:
            Dict with 'score', 'feedback', 'errors'
        """
        grading_prompt = f"""You are an AI grader. Grade the following answer:

Question: {question}

Correct Answer: {correct_answer}

Student Answer: {student_answer}

Provide:
1. Score out of {max_score} (use 0.5 increments)
2. Specific feedback on what was correct/incorrect
3. List of errors with corrections (Red Pen style)

Format your response as:
SCORE: [number]
FEEDBACK: [your feedback]
ERRORS:
- [error 1]: [correction]
- [error 2]: [correction]
"""
        
        result = self.generate(
            prompt=grading_prompt,
            system_prompt="You are a fair and constructive teacher. Be specific and helpful.",
            temperature=0.3,  # Lower temperature for consistent grading
            max_tokens=512
        )
        
        if result.get('error'):
            return {'score': 0, 'feedback': 'Grading failed', 'errors': []}
        
        # Parse response
        response_text = result['response']
        score = self._extract_score(response_text, max_score)
        feedback = self._extract_section(response_text, 'FEEDBACK')
        errors = self._extract_errors(response_text)
        
        return {
            'score': score,
            'feedback': feedback,
            'errors': errors,
            'raw_response': response_text
        }
    
    def _extract_score(self, text: str, max_score: float) -> float:
        """Extract score from grading response"""
        try:
            for line in text.split('\n'):
                if line.startswith('SCORE:'):
                    score_str = line.replace('SCORE:', '').strip()
                    score = float(score_str.split()[0])
                    return min(max(score, 0), max_score)
        except:
            pass
        return 0.0
    
    def _extract_section(self, text: str, section: str) -> str:
        """Extract section from response"""
        lines = text.split('\n')
        capturing = False
        content = []
        
        for line in lines:
            if line.startswith(f'{section}:'):
                capturing = True
                content.append(line.replace(f'{section}:', '').strip())
            elif capturing and line.startswith(('SCORE:', 'ERRORS:', 'FEEDBACK:')):
                break
            elif capturing:
                content.append(line.strip())
        
        return ' '.join(content).strip()
    
    def _extract_errors(self, text: str) -> List[Dict]:
        """Extract error list from response"""
        errors = []
        lines = text.split('\n')
        capturing = False
        
        for line in lines:
            if line.startswith('ERRORS:'):
                capturing = True
            elif capturing and line.strip().startswith('-'):
                error_text = line.strip()[1:].strip()
                if ':' in error_text:
                    error, correction = error_text.split(':', 1)
                    errors.append({
                        'error': error.strip(),
                        'correction': correction.strip()
                    })
        
        return errors


# Standalone test
if __name__ == "__main__":
    print("Testing Ollama Client...")
    
    try:
        client = OllamaClient()
        print("✅ Connected to Ollama")
        
        # Test simple generation
        result = client.generate("What is 2+2?", max_tokens=50)
        print(f"\nTest Query: What is 2+2?")
        print(f"Response: {result['response']}")
        print(f"Duration: {result['duration']}s")
        
        # Test grading
        grade_result = client.grade_answer(
            question="What is photosynthesis?",
            correct_answer="Photosynthesis is the process by which plants convert light energy into chemical energy.",
            student_answer="Plants make food using sunlight."
        )
        print(f"\nGrading Test:")
        print(f"Score: {grade_result['score']}/10")
        print(f"Feedback: {grade_result['feedback']}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

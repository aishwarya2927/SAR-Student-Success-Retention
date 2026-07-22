import os
import json
import logging
from google import genai
from database import (
    get_student,
    get_student_tasks,
    toggle_task_completion,
    save_mentor_tasks,
    get_connection,
    save_chat_log
)
from tools.search_support_resources import search_support_resources
from tools.search_company_resources import search_company_resources

logger = logging.getLogger(__name__)

def _get_client():
    from llm.gemini_client import get_gemini_client
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_PLACEMENT")
    return get_gemini_client(api_key=api_key)

def process_student_chat(student_id: str, student_message: str, chat_history: list[dict]) -> str:
    """
    Core handler for student chat.
    Uses RAG, checks tasks, and simulates interactive mock interviews.
    """
    client = _get_client()
    msg_lower = student_message.strip().lower()

    # ----------------------------------------------------
    # 1. State Analysis: Check if currently in an active Mock Interview
    # ----------------------------------------------------
    active_interview_company = None
    interview_started_idx = -1
    
    for idx, log in enumerate(chat_history):
        if log["sender"] == "agent" and "[SYSTEM: Mock Interview Started for" in log["message"]:
            active_interview_company = log["message"].split("for")[1].replace("]", "").strip()
            interview_started_idx = idx
        elif log["sender"] == "agent" and "[SYSTEM: Mock Interview Finished]" in log["message"]:
            active_interview_company = None # Reset if finished
            
    # If student asks to exit interview
    if active_interview_company and any(w in msg_lower for w in ["exit", "stop", "quit", "cancel", "end interview"]):
        save_chat_log(student_id, "agent", "[SYSTEM: Mock Interview Finished]")
        return "I have ended your mock interview session. Let me know if you want to prepare for another company or have other questions!"

    # ----------------------------------------------------
    # 2. Handle Mock Interview Mode
    # ----------------------------------------------------
    if active_interview_company:
        # Calculate how many questions have been asked in this session
        questions_asked = []
        answers_given = []
        
        current_question = None
        for log in chat_history[interview_started_idx + 1:]:
            if log["sender"] == "agent":
                # Filter out system tags
                if not log["message"].startswith("[SYSTEM"):
                    current_question = log["message"]
                    questions_asked.append(current_question)
            elif log["sender"] == "student" and current_question:
                answers_given.append(log["message"])
                current_question = None
                
        # The current message is the student's answer to the latest question
        answers_given.append(student_message)
        
        num_questions = len(questions_asked)
        
        if num_questions < 3:
            # Ask the next question
            prompt = f"""
            You are conducting a strict technical and behavioral mock interview for a student targeting {active_interview_company}.
            So far, you have asked these questions:
            {json.dumps(questions_asked, indent=2)}
            
            The student has answered:
            {json.dumps(answers_given, indent=2)}
            
            Please ask the next relevant interview question (Question {num_questions + 1}) for {active_interview_company}.
            Keep your question clear, professional, and matching the company's expected standard.
            Ask ONLY the question directly. Do not include introductory notes or friendly chit-chat.
            """
            try:
                resp = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt
                )
                return resp.text.strip()
            except Exception as e:
                logger.error(f"Error generating next interview question: {e}")
                return "I ran into an issue generating the next question. Please try saying something again."
        else:
            # We have 3 questions and 3 answers. Evaluate!
            save_chat_log(student_id, "agent", "[SYSTEM: Mock Interview Finished]")
            
            prompt = f"""
            You are an expert technical interviewer evaluating a student's mock interview performance for {active_interview_company}.
            Here are the questions asked:
            {json.dumps(questions_asked, indent=2)}
            
            Here are the student's answers:
            {json.dumps(answers_given, indent=2)}
            
            Please provide a structured feedback report.
            Your output should include:
            1. An overall score (out of 10)
            2. Strong areas
            3. Weak areas requiring improvement
            4. Recommended learning steps or concrete revision tasks.
            
            Keep the tone professional, constructive, and highly motivating.
            Also, format your response in clean markdown.
            """
            try:
                resp = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt
                )
                evaluation_text = resp.text.strip()
                
                # Automatically save the feedback to the faculty database as a comment
                conn = get_connection()
                cursor = conn.cursor()
                comment_text = f"[MOCK INTERVIEW FEEDBACK - {active_interview_company}]\n{evaluation_text[:800]}"
                cursor.execute("""
                    INSERT INTO dashboard_comments (student_id, faculty_name, comment_text)
                    VALUES (?, 'AI Mock Interviewer', ?)
                """, (student_id, comment_text))
                
                # Also, generate a couple of new targeted tasks for the student based on the weaknesses
                # We will append these tasks to the student_tasks checklist
                cursor.execute("SELECT COUNT(*) FROM student_tasks WHERE student_id = ?", (student_id,))
                task_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO student_tasks (student_id, task_index, title, duration, priority, detail, completed)
                    VALUES (?, ?, ?, '1 week', 'primary', ?, 0)
                """, (student_id, task_count, f"Revise {active_interview_company} feedback topics", f"Review mock interview weaknesses: {evaluation_text[:200]}..."))
                
                conn.commit()
                conn.close()
                
                return f"### 🎉 Mock Interview Completed!\n\nHere is your evaluation report:\n\n{evaluation_text}\n\n*Note: I have saved this feedback for your mentor and added a revision task to your placement checklist.*"
            except Exception as e:
                logger.error(f"Error completing mock interview: {e}")
                return "Interview completed, but I ran into a minor issue compiling the feedback details. Excellent job practicing!"

    # ----------------------------------------------------
    # 3. Trigger Mock Interview
    # ----------------------------------------------------
    if any(w in msg_lower for w in ["mock interview", "simulate interview", "start interview", "practice interview"]):
        # Determine target company
        company = "General Software Engineering"
        for word in student_message.split():
            clean_word = word.strip(",.!?").lower()
            if clean_word in ["tcs", "google", "microsoft", "amazon", "infosys", "wipro", "accenture", "flipkart", "ibm"]:
                company = clean_word.upper()
                break
                
        save_chat_log(student_id, "agent", f"[SYSTEM: Mock Interview Started for {company}]")
        
        # Ask first question
        prompt = f"""
        You are conducting a professional mock technical/HR interview for a university student student targeting {company}.
        Please start the interview by asking Question 1. Keep it relevant, professional, and matching the expected standard of {company}.
        Ask ONLY the question directly. Do not output instructions, introduction, or polite fluff.
        """
        try:
            resp = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            first_q = resp.text.strip()
            return f"### 🚀 Starting Mock Interview for {company}\n\nI will ask you 3 questions sequentially. Type your answers below. Type **'exit'** at any time to cancel.\n\n**Question 1:** {first_q}"
        except Exception as e:
            logger.error(f"Error starting interview: {e}")
            return f"I would love to help you mock interview for {company}, but I couldn't connect to the AI model right now. Please try again in a few moments!"

    # ----------------------------------------------------
    # 4. Handle Conversational Task Updates
    # ----------------------------------------------------
    if any(w in msg_lower for w in ["complete", "done", "check off", "checked", "finished", "completed"]):
        tasks = get_student_tasks(student_id)
        if tasks:
            task_titles = [f"{t['task_index']}: {t['title']}" for t in tasks]
            prompt = f"""
            The student says: "{student_message}"
            Here is their checklist of tasks:
            {json.dumps(task_titles, indent=2)}
            
            Which task index did they claim to complete?
            Return ONLY a JSON object containing:
            - "task_index": integer (or null if not found or matches none)
            - "reason": brief string explaining the choice
            
            Do not include markdown blocks or other text.
            """
            try:
                resp = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt
                )
                raw_text = resp.text.strip()
                if "```" in raw_text:
                    # strip markdown wrappers if present
                    raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
                result = json.loads(raw_text)
                
                t_idx = result.get("task_index")
                if t_idx is not None:
                    t_idx = int(t_idx)
                    # Toggle completion
                    toggle_task_completion(student_id, t_idx, True)
                    matched_task = next((t for t in tasks if t["task_index"] == t_idx), None)
                    task_name = matched_task["title"] if matched_task else f"Task #{t_idx}"
                    return f"✅ **Checklist Updated!** I have marked your task **\"{task_name}\"** as completed. Keep up the great work!"
            except Exception as e:
                logger.error(f"Error parsing task toggle: {e}")
                # Fallback to general chat if parsing fails

    # ----------------------------------------------------
    # 5. RAG FAQs & Institutional Query
    # ----------------------------------------------------
    context_docs = []
    
    # Simple keyword routing for RAG
    if any(w in msg_lower for w in ["attendance", "policy", "counselling", "exam", "probation", "scholarship", "financial"]):
        for k, query in [
            ("attendance", "attendance_policy"),
            ("probation", "probation"),
            ("counselling", "counselling"),
            ("exam", "exam_support"),
            ("scholarship", "scholarship"),
            ("financial", "financial_assistance")
        ]:
            if k in msg_lower:
                context_docs.extend(search_support_resources(query))
                
    # Also look up target company preparation context
    student_profile = get_student(student_id) or {}
    target_cos = student_profile.get("target_companies", [])
    for co in target_cos:
        if co.lower() in msg_lower:
            docs, _ = search_company_resources(co)
            context_docs.extend(docs)

    context_str = "\n\n".join(context_docs) if context_docs else "No specific institutional guidelines found for this query."
    
    prompt = f"""
    You are a friendly, expert Student Success AI Advisor at SPIT University.
    Your student ID is {student_id}.
    
    Here is some relevant context from the university's support databases:
    ---
    {context_str}
    ---
    
    Student query: "{student_message}"
    
    Please answer their question accurately and helpfully.
    - Ground your answers in the university context provided above when possible.
    - If you are answering about policies (like attendance or probation), make sure to quote requirements clearly.
    - If the context doesn't contain the answer, answer politely using general academic knowledge.
    - Keep your answer direct and supportive. Format with clean markdown list items if helpful.
    """
    try:
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
        return resp.text.strip()
    except Exception as e:
        logger.error(f"Error generating chat answer: {e}")
        return "I'm here to support you, but I ran into a network error answering your query. Please ask me again!"

import { create } from 'zustand';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
}

export interface ConversationInfo {
  id: string;
  title: string;
  created_at: string;
}

// Quiz structured types
export interface QuizQuestion {
  question: string;
  options: { A: string; B: string; C: string; D: string };
  answer: string; // "A" | "B" | "C" | "D"
  explanation?: string; // Brief explanation of the correct answer
}

export interface QuizItem {
  id: string;
  questions: QuizQuestion[];
  score: string | null;
  answers: Record<number, string>;
  submitted: boolean;
}

interface WorkspaceState {
  // Authentication
  token: string | null;
  user: User | null;

  // Active Video & Conversation
  videoId: string | null;
  conversationId: string | null;
  messages: Message[];
  conversations: ConversationInfo[];
  loading: boolean;
  transcriptStatus: 'idle' | 'processing' | 'success' | 'error';

  // Generative content (synced with conversation memory)
  notesContent: string;
  notesLoading: boolean;
  quizzes: QuizItem[];
  activeQuizId: string | null;
  quizLoading: boolean;
  quizError: string;
  projectContent: string;
  projectPrompt: string;
  projectLoading: boolean;
  projectError: string;

  // API Config
  backendUrl: string;

  // Actions
  setToken: (token: string | null, user?: User | null) => void;
  setVideoId: (videoId: string | null) => void;
  setMessages: (messages: Message[]) => void;
  clearChat: () => void;
  ingestVideo: (videoId: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  loadHistory: (videoId: string) => Promise<void>;
  loadConversations: (videoId: string) => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  startNewChat: () => void;
  deleteConversation: (conversationId: string) => Promise<void>;

  // Generative content actions
  setProjectPrompt: (prompt: string) => void;
  generateNotes: (format: 'summary' | 'detailed', forceNew?: boolean) => Promise<void>;
  generateQuiz: () => Promise<void>;
  generateProject: (prompt: string) => Promise<void>;

  // Quiz interaction actions
  selectQuizAnswer: (questionIndex: number, option: string) => void;
  submitQuiz: () => Promise<void>;
  retakeQuiz: () => void;
  startQuiz: (quizId: string) => void;
  generateNewQuiz: () => Promise<void>;
  setActiveQuizId: (quizId: string | null) => void;
}

// Helper to parse quiz JSON from backend
function parseQuizList(raw: string): QuizItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      if (parsed.length > 0 && parsed[0].questions && parsed[0].id) {
        return parsed as QuizItem[];
      }
      if (parsed.length > 0 && parsed[0].question && parsed[0].options) {
        return [{
          id: 'quiz_1',
          questions: parsed as QuizQuestion[],
          score: null,
          answers: {},
          submitted: false
        }];
      }
    }
  } catch {
    // Legacy/malformed quiz — return empty
  }
  return [];
}

// Helper to poll background jobs from Celery
const pollJob = async (
  jobId: string,
  backendUrl: string,
  token: string | null,
  onProgress: (progress: number, message: string) => void
): Promise<any> => {
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${backendUrl}/jobs/status/${jobId}`, {
          headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          }
        });
        if (!response.ok) {
          clearInterval(interval);
          reject(new Error(`Polling status check failed: ${response.statusText}`));
          return;
        }
        const data = await response.json();
        if (data.status === 'success') {
          clearInterval(interval);
          resolve(data.result);
        } else if (data.status === 'failure') {
          clearInterval(interval);
          reject(new Error(data.error || 'Job failed'));
        } else {
          onProgress(data.progress || 0, data.message || 'Processing');
        }
      } catch (e) {
        clearInterval(interval);
        reject(e);
      }
    }, 1500);
  });
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  videoId: null,
  conversationId: null,
  messages: [],
  conversations: [],
  loading: false,
  transcriptStatus: 'idle',
  backendUrl: 'http://localhost:8000/api/v1', // Configurable backend address

  // Generative content defaults
  notesContent: '',
  notesLoading: false,
  quizzes: [],
  activeQuizId: null,
  quizLoading: false,
  quizError: '',
  projectContent: '',
  projectPrompt: 'Build the application demonstrated in this video.',
  projectLoading: false,
  projectError: '',

  setToken: (token, user = null) => {
    if (token) {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      set({ token, user });
    } else {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      set({ token: null, user: null });
    }
  },

  setVideoId: (videoId) => {
    if (videoId !== get().videoId) {
      set({
        videoId,
        messages: [],
        conversationId: null,
        transcriptStatus: 'idle',
        conversations: [],
        // Clear generative content on video change
        notesContent: '',
        quizzes: [],
        activeQuizId: null,
        projectContent: '',
        projectPrompt: 'Build the application demonstrated in this video.',
      });
      if (videoId) {
        get().loadHistory(videoId);
        get().loadConversations(videoId);
      }
    }
  },

  setMessages: (messages) => set({ messages }),

  clearChat: () => set({ messages: [], conversationId: null }),

  ingestVideo: async (videoId) => {
    const { backendUrl, token } = get();
    set({ transcriptStatus: 'processing', loading: true });

    try {
      const response = await fetch(`${backendUrl}/video/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ video_id: videoId }),
      });

      if (!response.ok) throw new Error('Ingestion failed');

      const data = await response.json();

      if (data.status === 'success') {
        set({ transcriptStatus: 'success', loading: false });
      } else if (data.status === 'processing' && data.job_id) {
        try {
          await pollJob(data.job_id, backendUrl, token, (progress, message) => {
            console.log(`Video ingestion progress: ${progress}% - ${message}`);
          });
          set({ transcriptStatus: 'success', loading: false });
        } catch (pollError) {
          console.error('Ingestion polling error:', pollError);
          set({ transcriptStatus: 'error', loading: false });
        }
      } else {
        set({ transcriptStatus: 'error', loading: false });
      }
    } catch (e) {
      console.error('Error during video ingestion:', e);
      set({ transcriptStatus: 'error', loading: false });
    }
  },

  loadHistory: async (videoId) => {
    const { backendUrl, token } = get();
    set({ loading: true });
    try {
      const response = await fetch(`${backendUrl}/chat/history/${videoId}`, {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.messages) {
          const quizRaw = data.quiz_content || '';
          const parsedQuizzes = parseQuizList(quizRaw);
          const lastQuiz = parsedQuizzes[parsedQuizzes.length - 1];
          set({
            messages: data.messages,
            conversationId: data.id === "new-chat" ? null : data.id,
            transcriptStatus: 'success',
            loading: false,
            // Restore generative content from conversation memory
            notesContent: data.notes_summary || data.notes_detailed || '',
            quizzes: parsedQuizzes,
            activeQuizId: lastQuiz ? lastQuiz.id : null,
            projectContent: data.project_content || '',
            projectPrompt: data.project_prompt || 'Build the application demonstrated in this video.',
          });
          return;
        }
      }

      set({ loading: false });
      await get().ingestVideo(videoId);
    } catch (e) {
      console.error('Error loading history:', e);
      set({ loading: false });
      await get().ingestVideo(videoId);
    }
  },

  loadConversations: async (videoId) => {
    const { backendUrl, token } = get();
    try {
      const response = await fetch(`${backendUrl}/chat/conversations/${videoId}`, {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      if (response.ok) {
        const data = await response.json();
        set({ conversations: data });
      }
    } catch (e) {
      console.error('Error loading conversations:', e);
    }
  },

  selectConversation: async (conversationId) => {
    const { backendUrl, token } = get();
    set({ loading: true });
    try {
      const response = await fetch(`${backendUrl}/chat/conversation/${conversationId}`, {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      if (response.ok) {
        const data = await response.json();
        const quizRaw = data.quiz_content || '';
        set({
          messages: data.messages,
          conversationId: data.id,
          loading: false,
          // Restore generative content from conversation memory
          notesContent: data.notes_summary || data.notes_detailed || '',
          quizzes: parseQuizList(quizRaw),
          activeQuizId: null,
          projectContent: data.project_content || '',
          projectPrompt: data.project_prompt || 'Build the application demonstrated in this video.',
        });
      } else {
        set({ loading: false });
      }
    } catch (e) {
      console.error('Error selecting conversation:', e);
      set({ loading: false });
    }
  },

  startNewChat: () => {
    set({
      messages: [],
      conversationId: null,
      // Clear generative content for the new chat
      notesContent: '',
      quizzes: [],
      activeQuizId: null,
      projectContent: '',
      projectPrompt: 'Build the application demonstrated in this video.',
    });
  },

  deleteConversation: async (conversationId) => {
    const { backendUrl, token, videoId, conversationId: activeId } = get();
    try {
      const response = await fetch(`${backendUrl}/chat/conversation/${conversationId}`, {
        method: 'DELETE',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      if (response.ok) {
        if (conversationId === activeId) {
          set({
            conversationId: null,
            messages: [],
            notesContent: '',
            quizzes: [],
            activeQuizId: null,
            projectContent: '',
            projectPrompt: 'Build the application demonstrated in this video.',
          });
        }
        if (videoId) {
          await get().loadConversations(videoId);
        }
      }
    } catch (e) {
      console.error('Error deleting conversation:', e);
    }
  },

  sendMessage: async (text) => {
    const { backendUrl, token, videoId, conversationId, messages } = get();
    if (!videoId) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };

    set({ messages: [...messages, userMessage], loading: true });

    const assistantMessageId = crypto.randomUUID();
    const tempAssistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    };

    set({ messages: [...messages, userMessage, tempAssistantMessage] });

    try {
      const response = await fetch(`${backendUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          message: text,
          model: 'gemini'
        })
      });

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('No readable stream');

      let accumulatedResponse = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.substring(6));
              if (parsed.text) {
                accumulatedResponse += parsed.text;

                set((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, content: accumulatedResponse }
                      : m
                  )
                }));
              }
              if (parsed.conversation_id && !get().conversationId) {
                set({ conversationId: parsed.conversation_id });
                get().loadConversations(videoId);
              }
            } catch (e) {
              // Ignore parsing errors
            }
          }
        }
      }

      set({ loading: false });
    } catch (e) {
      console.error('Error during chat stream:', e);
      set((state) => ({
        loading: false,
        messages: state.messages.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: 'Error sending message. Please make sure the backend is running and model keys are set.' }
            : m
        )
      }));
    }
  },

  // --- Generative content actions ---

  setProjectPrompt: (prompt) => set({ projectPrompt: prompt }),

  generateNotes: async (format, forceNew = false) => {
    const { backendUrl, token, videoId, conversationId } = get();
    if (!videoId) return;
    set({ notesLoading: true });
    try {
      const response = await fetch(`${backendUrl}/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          format: format,
          force_new: forceNew
        })
      });
      if (!response.ok) throw new Error('Failed to initiate notes generation');
      const data = await response.json();

      if (data.conversation_id && !get().conversationId) {
        set({ conversationId: data.conversation_id });
        get().loadConversations(videoId);
      }

      if (data.status === 'success' || data.notes) {
        set({ notesContent: data.notes || 'Failed to generate notes.' });
      } else if (data.status === 'processing' && data.job_id) {
        set({ notesContent: 'Synthesizing study guide in background... please wait.' });
        try {
          const result = await pollJob(data.job_id, backendUrl, token, (progress, message) => {
            set({ notesContent: `Generating Study Guide: ${progress}% - ${message}...` });
          });
          if (result && result.notes) {
            set({ notesContent: result.notes });
          } else {
            set({ notesContent: 'Finished generating notes, but no content returned.' });
          }
        } catch (pollError: any) {
          console.error('Notes polling error:', pollError);
          set({ notesContent: `Failed: ${pollError?.message || 'Error generating notes.'}` });
        }
      } else {
        set({ notesContent: 'Failed to generate notes.' });
      }
    } catch (e) {
      set({ notesContent: 'Error contacting backend. Make sure the server is running.' });
    } finally {
      set({ notesLoading: false });
    }
  },

  generateQuiz: async () => {
    const { backendUrl, token, videoId, conversationId } = get();
    if (!videoId) return;
    set({ quizLoading: true, quizError: '' });
    try {
      const response = await fetch(`${backendUrl}/quiz`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          force_new: false
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail || `Server error (${response.status})`;
        console.error('Quiz generation failed:', errMsg);
        set({ quizError: errMsg, quizzes: [] });
        return;
      }

      const data = await response.json();

      if (data.conversation_id && !get().conversationId) {
        set({ conversationId: data.conversation_id });
        get().loadConversations(videoId);
      }

      if (data.status === 'success' || data.quiz) {
        const content = data.quiz || '[]';
        set({ quizzes: parseQuizList(content), quizError: '' });
      } else if (data.status === 'processing' && data.job_id) {
        set({ quizError: 'Generating quiz questions...' });
        try {
          const result = await pollJob(data.job_id, backendUrl, token, (progress, message) => {
            set({ quizError: `Generating Quiz: ${progress}% - ${message}...` });
          });
          if (result && result.quiz) {
            set({ quizzes: parseQuizList(result.quiz), quizError: '' });
          } else {
            set({ quizError: 'Finished generating quiz, but no content returned.', quizzes: [] });
          }
        } catch (pollError: any) {
          console.error('Quiz polling error:', pollError);
          set({ quizError: `Failed: ${pollError?.message || 'Error generating quiz.'}`, quizzes: [] });
        }
      } else {
        set({ quizError: 'Failed to generate quiz.', quizzes: [] });
      }
    } catch (e) {
      console.error('Quiz generation error:', e);
      set({ quizzes: [], quizError: 'Error connecting to backend. Make sure the server is running.' });
    } finally {
      set({ quizLoading: false });
    }
  },

  generateProject: async (prompt) => {
    const { backendUrl, token, videoId, conversationId } = get();
    if (!videoId) return;
    set({ projectLoading: true, projectError: '' });
    try {
      const response = await fetch(`${backendUrl}/project`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          prompt: prompt
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData.detail || `Server error (${response.status})`;
        console.error('Project generation failed:', errMsg);
        set({ projectError: errMsg, projectContent: '' });
        return;
      }

      const data = await response.json();

      if (data.conversation_id && !get().conversationId) {
        set({ conversationId: data.conversation_id });
        get().loadConversations(videoId);
      }

      if (data.status === 'success' || data.project_files) {
        set({ projectContent: data.project_files || '', projectError: '' });
      } else if (data.status === 'processing' && data.job_id) {
        set({ projectContent: 'Architecting project files in background... please wait.', projectError: '' });
        try {
          const result = await pollJob(data.job_id, backendUrl, token, (progress, message) => {
            set({ projectContent: `Generating Blueprint: ${progress}% - ${message}...` });
          });
          if (result && result.project_files) {
            set({ projectContent: result.project_files, projectError: '' });
          } else {
            set({ projectContent: '', projectError: 'Finished generating project, but no files returned.' });
          }
        } catch (pollError: any) {
          console.error('Project polling error:', pollError);
          set({ projectContent: '', projectError: `Failed: ${pollError?.message || 'Error generating project.'}` });
        }
      } else {
        set({ projectContent: '', projectError: 'Failed to generate project.' });
      }
    } catch (e) {
      console.error('Project generation error:', e);
      set({ projectContent: '', projectError: 'Error connecting to backend. Make sure the server is running.' });
    } finally {
      set({ projectLoading: false });
    }
  },

  // --- Quiz interaction actions ---

  selectQuizAnswer: (questionIndex, option) => {
    const { quizzes } = get();
    let { activeQuizId } = get();
    if (!activeQuizId && quizzes.length > 0) {
      activeQuizId = quizzes[quizzes.length - 1].id;
      set({ activeQuizId });
    }
    if (!activeQuizId) return;
    const activeQuiz = quizzes.find(q => q.id === activeQuizId);
    if (!activeQuiz || activeQuiz.submitted) return; // Can't change answers after submission

    const updatedQuizzes = quizzes.map((q) => {
      if (q.id === activeQuizId) {
        return {
          ...q,
          answers: { ...q.answers, [questionIndex]: option }
        };
      }
      return q;
    });

    set({ quizzes: updatedQuizzes });
  },

  submitQuiz: async () => {
    const { backendUrl, token, videoId, conversationId, quizzes } = get();
    let { activeQuizId } = get();
    if (!activeQuizId && quizzes.length > 0) {
      activeQuizId = quizzes[quizzes.length - 1].id;
      set({ activeQuizId });
    }
    if (!videoId || !conversationId || !activeQuizId) return;

    const activeQuiz = quizzes.find(q => q.id === activeQuizId);
    if (!activeQuiz) return;

    const correctCount = activeQuiz.questions.filter((q, i) => activeQuiz.answers[i] === q.answer).length;
    const total = activeQuiz.questions.length;
    const scoreStr = `${correctCount}/${total}`;

    // Mark as submitted locally first
    const updatedQuizzes = quizzes.map((q) => {
      if (q.id === activeQuizId) {
        return {
          ...q,
          submitted: true,
          score: scoreStr
        };
      }
      return q;
    });
    set({ quizzes: updatedQuizzes });

    // Send attempt details to backend to persist it
    try {
      const response = await fetch(`${backendUrl}/quiz/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          quiz_id: activeQuizId,
          answers: activeQuiz.answers,
          score: scoreStr
        })
      });

      if (response.ok) {
        const data = await response.json();
        const content = data.quiz || '[]';
        set({ quizzes: parseQuizList(content) });
      }
    } catch (e) {
      console.error('Failed to submit quiz attempt to backend:', e);
    }
  },

  retakeQuiz: () => {
    const { quizzes } = get();
    let { activeQuizId } = get();
    if (!activeQuizId && quizzes.length > 0) {
      activeQuizId = quizzes[quizzes.length - 1].id;
      set({ activeQuizId });
    }
    if (!activeQuizId) return;

    const updatedQuizzes = quizzes.map((q) => {
      if (q.id === activeQuizId) {
        return {
          ...q,
          answers: {},
          score: null,
          submitted: false
        };
      }
      return q;
    });

    set({ quizzes: updatedQuizzes });
  },

  startQuiz: (quizId) => {
    set({ activeQuizId: quizId });
  },

  setActiveQuizId: (quizId) => {
    set({ activeQuizId: quizId });
  },

  generateNewQuiz: async () => {
    const { backendUrl, token, videoId, conversationId } = get();
    if (!videoId) return;
    set({ quizLoading: true, quizError: '' });
    try {
      const response = await fetch(`${backendUrl}/quiz`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          video_id: videoId,
          conversation_id: conversationId,
          force_new: true
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        set({ quizError: errData.detail || `Server error (${response.status})` });
        return;
      }

      const data = await response.json();

      if (data.conversation_id && !get().conversationId) {
        set({ conversationId: data.conversation_id });
        get().loadConversations(videoId);
      }

      if (data.status === 'success' || data.quiz) {
        const content = data.quiz || '[]';
        const parsedQuizzes = parseQuizList(content);
        const lastQuiz = parsedQuizzes[parsedQuizzes.length - 1];
        set({
          quizzes: parsedQuizzes,
          activeQuizId: lastQuiz ? lastQuiz.id : null,
          quizError: '',
        });
      } else if (data.status === 'processing' && data.job_id) {
        set({ quizError: 'Generating new quiz questions in background...' });
        try {
          const result = await pollJob(data.job_id, backendUrl, token, (progress, message) => {
            set({ quizError: `Generating New Quiz: ${progress}% - ${message}...` });
          });
          if (result && result.quiz) {
            const parsedQuizzes = parseQuizList(result.quiz);
            const lastQuiz = parsedQuizzes[parsedQuizzes.length - 1];
            set({
              quizzes: parsedQuizzes,
              activeQuizId: lastQuiz ? lastQuiz.id : null,
              quizError: '',
            });
          } else {
            set({ quizError: 'Finished generating quiz, but no content returned.' });
          }
        } catch (pollError: any) {
          console.error('Quiz polling error:', pollError);
          set({ quizError: `Failed: ${pollError?.message || 'Error generating quiz.'}` });
        }
      } else {
        set({ quizError: 'Failed to generate quiz.' });
      }
    } catch (e) {
      console.error('New quiz generation error:', e);
      set({ quizError: 'Error connecting to backend.' });
    } finally {
      set({ quizLoading: false });
    }
  },
}));

import React, { useEffect, useState, useRef } from 'react';
import { useWorkspaceStore } from '../store/store';
import JSZip from 'jszip';
import {
  Send, BookOpen, Code, Layers, Settings, MessageSquare, AlertCircle,
  Sparkles, FileText, Download, Plus, Trash2, X,
  Paperclip, Smile, Search, Menu, ChevronDown, ChevronUp, CornerUpRight,
  CheckCircle, RefreshCw, FolderDown
} from 'lucide-react';

export const SidePanel: React.FC = () => {
  const {
    videoId,
    messages,
    loading,
    transcriptStatus,
    setVideoId,
    sendMessage,
    backendUrl,
    token,
    conversations,
    conversationId,
    selectConversation,
    startNewChat,
    deleteConversation,
    // Generative content (synced with conversation memory)
    notesContent,
    notesLoading,
    quizzes,
    activeQuizId,
    quizLoading,
    quizError,
    projectContent,
    projectPrompt,
    projectLoading,
    projectError,
    setProjectPrompt,
    generateNotes,
    generateQuiz,
    generateProject,
    selectQuizAnswer,
    submitQuiz,
    retakeQuiz,
    startQuiz,
    generateNewQuiz,
    setActiveQuizId,
    loadHistory
  } = useWorkspaceStore();

  const [activeTab, setActiveTab] = useState<'chat' | 'notes' | 'projects' | 'quiz' | 'settings'>('chat');
  const [inputText, setInputText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Notes tab local state (only for format selection)
  const [noteType, setNoteType] = useState<'summary' | 'detailed'>('summary');

  // Sync Video ID from extension runtime
  useEffect(() => {
    const handleMessage = (message: any) => {
      if (message.action === 'set_video_id' && message.videoId) {
        setVideoId(message.videoId);
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab?.url) {
        const url = new URL(activeTab.url);
        if (url.hostname.includes('youtube.com') && url.pathname === '/watch') {
          const v = url.searchParams.get('v');
          if (v) setVideoId(v);
        }
      }
    });

    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, [setVideoId]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || loading) return;
    const text = inputText;
    setInputText('');
    await sendMessage(text);
  };

  const handleGenerateNotes = async () => {
    await generateNotes(noteType, !!notesContent);
  };

  const handleGenerateProject = async () => {
    await generateProject(projectPrompt);
  };

  const handleGenerateQuiz = async () => {
    await generateQuiz();
  };

  const handleDownloadPDF = () => {
    if (!videoId) return;
    const url = `${backendUrl}/pdf/export?video_id=${videoId}${token ? `&token=${token}` : ''}`;
    // Open in new tab — the backend returns a PDF download
    window.open(url, '_blank');
  };

  const handleDownloadZip = async () => {
    if (!projectContent) return;
    const zip = new JSZip();

    // Language keyword → file extension map
    const langExtensions: Record<string, string> = {
      python: '.py', javascript: '.js', typescript: '.ts', js: '.js',
      ts: '.ts', jsx: '.jsx', tsx: '.tsx', json: '.json', html: '.html',
      css: '.css', scss: '.scss', yaml: '.yml', yml: '.yml', toml: '.toml',
      bash: '.sh', shell: '.sh', sh: '.sh', sql: '.sql', markdown: '.md',
      md: '.md', java: '.java', cpp: '.cpp', c: '.c', go: '.go',
      rust: '.rs', ruby: '.rb', php: '.php', swift: '.swift',
      kotlin: '.kt', text: '.txt', xml: '.xml', dockerfile: '',
    };

    // Known extensionless filenames
    const namedFiles = new Set([
      'dockerfile', 'makefile', 'procfile', 'gemfile', 'rakefile',
      '.gitignore', '.env', '.env.example', '.dockerignore',
    ]);

    // Helper: check if a string looks like a real filename
    const isFilename = (s: string) =>
      s.includes('.') || namedFiles.has(s.toLowerCase());

    // Helper: extract a filename from the markdown text preceding a code block
    // Looks for patterns like: ### `app.py`, **requirements.txt**, #### File: main.js, etc.
    const extractFilenameFromContext = (textBefore: string): string | null => {
      // Get the last few lines before the code block
      const lines = textBefore.split('\n').filter(l => l.trim()).slice(-3);
      for (let i = lines.length - 1; i >= 0; i--) {
        const line = lines[i].trim();
        // Try to find a filename-like token in the line
        // Match backtick-wrapped: `filename.ext`
        const backtickMatch = line.match(/`([^`]+\.[a-zA-Z0-9]+)`/);
        if (backtickMatch && isFilename(backtickMatch[1])) return backtickMatch[1];
        // Match bold-wrapped: **filename.ext**
        const boldMatch = line.match(/\*\*([^*]+\.[a-zA-Z0-9]+)\*\*/);
        if (boldMatch && isFilename(boldMatch[1])) return boldMatch[1];
        // Match heading with filename: ### filename.ext or #### path/to/file.ext
        const headingMatch = line.match(/^#{1,6}\s+(?:File:\s*)?(.+\.[a-zA-Z0-9]+)/i);
        if (headingMatch && isFilename(headingMatch[1].replace(/[`*]/g, '').trim()))
          return headingMatch[1].replace(/[`*]/g, '').trim();
        // Match "File:" or "Filename:" prefix
        const filePrefixMatch = line.match(/^(?:file|filename)\s*:\s*[`*]*([^\s`*]+\.[a-zA-Z0-9]+)/i);
        if (filePrefixMatch) return filePrefixMatch[1];
        // Match standalone path-like: src/app.py or just app.py at end of line
        const pathMatch = line.match(/(?:^|\s)([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)\s*$/);
        if (pathMatch && isFilename(pathMatch[1]) && !pathMatch[1].startsWith('e.g'))
          return pathMatch[1];
      }
      return null;
    };

    // Helper: derive a name from code content (class names, function names, etc.)
    const deriveNameFromContent = (code: string, ext: string): string | null => {
      // Python: class ClassName or def function_name
      const pyClass = code.match(/^class\s+(\w+)/m);
      if (pyClass) return pyClass[1].replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase() + ext;
      const pyFunc = code.match(/^def\s+(\w+)/m);
      if (pyFunc && pyFunc[1] !== '__init__') return pyFunc[1] + ext;
      // JS/TS: export default function/class, function name, const Component
      const jsExport = code.match(/export\s+(?:default\s+)?(?:function|class)\s+(\w+)/m);
      if (jsExport) return jsExport[1].replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase() + ext;
      const jsConst = code.match(/(?:const|let|var)\s+(\w+)\s*=/m);
      if (jsConst && jsConst[1].length > 2) return jsConst[1].replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase() + ext;
      // Java/Kotlin: public class ClassName
      const javaClass = code.match(/(?:public\s+)?class\s+(\w+)/m);
      if (javaClass) return javaClass[1] + ext;
      return null;
    };

    const fileRegex = /```(\S+)\n([\s\S]*?)```/g;
    const usedNames = new Set<string>();
    let match;
    let fileCount = 0;

    while ((match = fileRegex.exec(projectContent)) !== null) {
      const token = match[1].replace(/^(language-|lang-)/, '');
      const content = match[2];
      const tokenLower = token.toLowerCase();

      let fname: string;

      if (isFilename(token)) {
        // Code fence already has a real filename (```app.py)
        fname = token;
      } else {
        // Bare language label (```python) — try to find the real name
        const ext = langExtensions[tokenLower] || '.txt';

        // 1. Check the markdown text above this code block for a filename
        const textBefore = projectContent.substring(0, match.index);
        const contextName = extractFilenameFromContext(textBefore);

        if (contextName) {
          fname = contextName;
        } else {
          // 2. Try to derive from code content
          const derivedName = deriveNameFromContent(content, ext);
          if (derivedName) {
            fname = derivedName;
          } else {
            // 3. Last resort fallback
            fname = `file_${fileCount + 1}${ext}`;
          }
        }
      }

      // Deduplicate: if name already used, add a suffix
      let finalName = fname;
      let dupIdx = 2;
      while (usedNames.has(finalName.toLowerCase())) {
        const dotIdx = fname.lastIndexOf('.');
        if (dotIdx > 0) {
          finalName = `${fname.substring(0, dotIdx)}_${dupIdx}${fname.substring(dotIdx)}`;
        } else {
          finalName = `${fname}_${dupIdx}`;
        }
        dupIdx++;
      }
      usedNames.add(finalName.toLowerCase());

      zip.file(finalName, content);
      fileCount++;
    }

    // If no code blocks found, save raw content as README
    if (fileCount === 0) {
      zip.file('project_blueprint.md', projectContent);
    }
    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `project_${videoId}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeConversation = conversations.find(c => c.id === conversationId);
  const chatHeading = activeConversation?.title || "YouTube Workspace";

  if (!videoId) {
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6 text-center bg-[#F8FAFC] text-slate-800 font-sans">
        <div className="bg-white border-2 border-slate-200 p-6 rounded-2xl shadow-[4px_4px_0px_0px_rgba(148,163,184,0.3)] max-w-sm">
          <AlertCircle size={48} className="text-indigo-500 mx-auto mb-4 animate-bounce" />
          <h2 className="text-base font-bold mb-2 uppercase tracking-wide">No Video Detected</h2>
          <p className="text-xs text-slate-500 leading-relaxed">
            Open a YouTube video page, and we will automatically load the interactive workspace here.
          </p>
        </div>
      </div>
    );
  }

  // Seeks the YouTube video to a specific second via content script
  const seekVideo = (seconds: number) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      if (tabId) {
        chrome.tabs.sendMessage(tabId, { action: 'seek_video', seconds });
      }
    });
  };

  // Format seconds → MM:SS display label
  const fmtTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  // Renders notes content with ss_ screenshot cards, headings, code blocks, bullets
  const renderNotesContent = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeLines: string[] = [];

    const flushCode = (key: string) => {
      elements.push(
        <pre key={key} className="bg-slate-900 text-emerald-300 rounded-lg p-3 text-[10px] font-mono overflow-x-auto my-2 border border-slate-700 leading-relaxed">
          {codeLines.join('\n')}
        </pre>
      );
      codeLines = [];
    };

    lines.forEach((line, i) => {
      const key = `ln-${i}`;
      const stripped = line.trim();

      // Code block toggle
      if (stripped.startsWith('```')) {
        if (inCodeBlock) {
          flushCode(key);
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        return;
      }
      if (inCodeBlock) {
        codeLines.push(line);
        return;
      }

      // Screenshot marker: ![caption](ss_SECONDS)
      const ssMatch = stripped.match(/^!\[(.*)\]\(ss_(\d+)\)$/);
      if (ssMatch) {
        const caption = ssMatch[1] || 'Screenshot';
        const seconds = parseInt(ssMatch[2], 10);
        const timeLabel = fmtTime(seconds);
        const thumbUrl = videoId ? `https://img.youtube.com/vi/${videoId}/mqdefault.jpg` : '';
        elements.push(
          <div key={key} className="my-3 rounded-xl overflow-hidden border border-indigo-200 shadow-[2px_2px_0px_rgba(99,102,241,0.2)] bg-white">
            {thumbUrl && (
              <div className="relative">
                <img
                  src={thumbUrl}
                  alt={caption}
                  className="w-full object-cover opacity-90"
                  style={{ maxHeight: 140 }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <span className="absolute bottom-2 left-2 text-white text-[9px] font-bold bg-black/50 px-1.5 py-0.5 rounded-md font-mono">
                  ⏱ {timeLabel}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between px-3 py-2 bg-indigo-50">
              <span className="text-[10px] font-semibold text-indigo-700 truncate flex-1 mr-2">{caption}</span>
              <button
                onClick={() => seekVideo(seconds)}
                className="shrink-0 text-[9px] font-bold uppercase tracking-wide bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white px-2.5 py-1.5 rounded-lg transition-all shadow-sm flex items-center gap-1"
              >
                ▶ Jump to {timeLabel}
              </button>
            </div>
          </div>
        );
        return;
      }

      if (!stripped) {
        elements.push(<div key={key} className="h-2" />);
        return;
      }

      // ALL CAPS heading (e.g. "DEEP DIVE:" or "THE GAME PLAN:")
      if (
        stripped.toUpperCase() === stripped &&
        stripped.length > 3 &&
        stripped.length < 70 &&
        !stripped.startsWith('- ')
      ) {
        const label = stripped.endsWith(':') ? stripped.slice(0, -1) : stripped;
        elements.push(
          <h3 key={key} className="text-[11px] font-black uppercase tracking-widest text-indigo-700 border-b border-indigo-100 pb-1 mt-4 mb-1">
            {label}
          </h3>
        );
        return;
      }

      // Legacy # heading
      if (stripped.startsWith('# ')) {
        elements.push(<h3 key={key} className="text-[11px] font-black uppercase tracking-widest text-indigo-700 border-b border-indigo-100 pb-1 mt-4 mb-1">{stripped.slice(2)}</h3>);
        return;
      }
      if (stripped.startsWith('## ')) {
        elements.push(<h4 key={key} className="text-[10px] font-bold text-slate-700 mt-3 mb-0.5">{stripped.slice(3)}</h4>);
        return;
      }

      // Bullet point
      if (stripped.startsWith('- ') || stripped.startsWith('* ')) {
        elements.push(
          <div key={key} className="flex items-start gap-1.5 text-[10px] text-slate-700 leading-relaxed ml-2">
            <span className="text-indigo-400 mt-0.5 shrink-0">•</span>
            <span>{stripped.slice(2)}</span>
          </div>
        );
        return;
      }

      // Normal paragraph
      elements.push(
        <p key={key} className="text-[10px] text-slate-700 leading-relaxed">{stripped}</p>
      );
    });

    // Flush any unclosed code block
    if (inCodeBlock && codeLines.length > 0) flushCode('code-end');

    return <div className="space-y-1">{elements}</div>;
  };

  const renderMessageBody = (content: string) => {
    if (content.includes('[project_ready_download_zip:')) {
      return (
        <div className="flex flex-col gap-2">
          <span className="whitespace-pre-wrap font-sans text-xs">
            {content.replace(/\[project_ready_download_zip:.*?\]/, '')}
          </span>
          <button
            onClick={handleDownloadZip}
            className="mt-2 w-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold uppercase tracking-wider text-[10px] py-2 rounded-lg shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] transition-all flex items-center justify-center gap-2"
          >
            <FolderDown size={14} /> Download ZIP Workspace
          </button>
        </div>
      );
    }
    if (content.includes('[notes_ready_download_pdf:')) {
      return (
        <div className="flex flex-col gap-2">
          <span className="whitespace-pre-wrap font-sans text-xs">
            {content.replace(/\[notes_ready_download_pdf:.*?\]/, '')}
          </span>
          <button
            onClick={handleDownloadPDF}
            className="mt-2 w-full border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold uppercase tracking-wider text-[10px] py-2 rounded-lg shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] transition-all flex items-center justify-center gap-2"
          >
            <Download size={14} /> Download PDF Notes
          </button>
        </div>
      );
    }
    if (content.includes('[quiz_ready:')) {
      const latestQuiz = quizzes[quizzes.length - 1];
      if (!latestQuiz) {
        return (
          <div className="flex flex-col gap-2">
            <span className="whitespace-pre-wrap font-sans text-xs">
              {content.replace(/\[quiz_ready:.*?\]/, '')}
            </span>
            <button
              onClick={() => videoId && loadHistory(videoId)}
              className="mt-2 w-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold uppercase tracking-wider text-[10px] py-2 rounded-lg shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] transition-all flex items-center justify-center gap-2"
            >
              <Layers size={14} /> Load Interactive Quiz
            </button>
          </div>
        );
      }
      const { questions, answers, submitted, score } = latestQuiz;
      const attemptedCount = Object.keys(answers).length;
      const totalQuestions = questions.length;

      return (
        <div className="flex flex-col gap-3 mt-1">
          <span className="whitespace-pre-wrap font-sans text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 p-2 rounded-lg mb-2">
            {content.replace(/\[quiz_ready:.*?\]/, '').trim() || 'Interactive Quiz Ready!'}
          </span>

          {questions.map((q, qIdx) => {
            const userAnswer = answers[qIdx];
            const isCorrect = userAnswer === q.answer;
            return (
              <div key={qIdx} className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
                <p className="text-[10px] font-bold text-slate-800 mb-2 leading-relaxed">
                  <span className="text-indigo-500 mr-1">{qIdx + 1}.</span> {q.question}
                </p>
                <div className="space-y-1.5">
                  {(['A', 'B', 'C', 'D'] as const).map((opt) => {
                    const isSelected = userAnswer === opt;
                    const isCorrectOption = q.answer === opt;
                    let optStyle = 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100';
                    let dotStyle = 'bg-white border-slate-300 text-slate-500';

                    if (submitted) {
                      if (isCorrectOption) {
                        optStyle = 'bg-emerald-50 border-emerald-400 text-emerald-800';
                        dotStyle = 'bg-emerald-500 border-emerald-600 text-white';
                      }
                      else if (isSelected) {
                        optStyle = 'bg-red-50 border-red-400 text-red-800';
                        dotStyle = 'bg-red-500 border-red-600 text-white';
                      }
                      else {
                        optStyle = 'bg-slate-50 border-slate-200 text-slate-400 opacity-60';
                      }
                    } else if (isSelected) {
                      optStyle = 'bg-indigo-50 border-indigo-400 text-indigo-800';
                      dotStyle = 'bg-indigo-500 border-indigo-600 text-white';
                    }

                    return (
                      <button
                        key={opt}
                        onClick={() => selectQuizAnswer(qIdx, opt)}
                        disabled={submitted}
                        className={`w-full text-left flex items-start gap-2 p-2 rounded-md border text-[10px] font-semibold transition-all ${optStyle} ${submitted ? 'cursor-default' : ''}`}
                      >
                        <span className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[8px] font-bold shrink-0 ${dotStyle}`}>
                          {submitted && isCorrectOption ? '✓' : submitted && isSelected ? '✗' : opt}
                        </span>
                        <span className="flex-1 mt-[1px]">{q.options[opt]}</span>
                      </button>
                    );
                  })}
                </div>
                {submitted && userAnswer && !isCorrect && q.explanation && (
                  <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-md text-[9px] text-amber-800">
                    <span className="font-bold">💡 Explanation: </span>{q.explanation}
                  </div>
                )}
              </div>
            );
          })}

          {!submitted ? (
            <button
              onClick={submitQuiz}
              disabled={attemptedCount < totalQuestions}
              className="w-full mt-2 border border-emerald-300 bg-emerald-600 hover:bg-emerald-700 text-white font-bold uppercase tracking-wider text-[10px] py-2 rounded-lg shadow-sm disabled:opacity-40 flex items-center justify-center gap-1.5 transition-all"
            >
              <CheckCircle size={12} /> Submit Answers ({attemptedCount}/{totalQuestions})
            </button>
          ) : (
            <div className="mt-2 flex items-center justify-between bg-indigo-50 border border-indigo-200 p-2 rounded-lg">
              <span className="text-[10px] font-bold text-indigo-800">Score: {score}</span>
              <button onClick={() => { setActiveTab('quiz'); setActiveQuizId(latestQuiz.id); }} className="text-[9px] font-bold uppercase text-indigo-600 hover:text-indigo-800 flex items-center gap-1 bg-white px-2 py-1 rounded border border-indigo-200 shadow-sm transition-transform active:scale-95">
                Go to Quiz Tab <CornerUpRight size={10} />
              </button>
            </div>
          )}
        </div>
      );
    }
    return <pre className="whitespace-pre-wrap font-sans text-xs">{content || '...'}</pre>;
  };

  const filteredMessages = messages.filter(m =>
    m.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden">

      {/* 1. Sidebar - Collapsible History (Figma Option A Softer Dark Theme) */}
      <div
        className={`flex flex-col h-full border-r border-slate-800/20 z-30 transition-all duration-300 absolute md:relative ${showHistory ? 'left-0 w-64' : '-left-64 md:-left-64 w-0 border-r-0'
          }`}
        style={{
          backgroundColor: '#0F172A',
          color: '#E2E8F0'
        }}
      >
        {showHistory && (
          <div className="flex flex-col h-full p-4 justify-between">
            <div>
              {/* Sidebar Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <span className="font-bold text-xs uppercase tracking-wider text-slate-100 flex items-center gap-1.5">
                  <Menu size={14} className="text-indigo-400" /> BroTell
                </span>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-slate-400 hover:text-slate-100 border border-slate-800 bg-[#1E293B] p-1 rounded transition-colors"
                >
                  <X size={12} />
                </button>
              </div>

              {/* New Chat Button */}
              <button
                onClick={() => {
                  startNewChat();
                  setShowHistory(false);
                }}
                className="w-full border border-slate-700 bg-[#1E293B] hover:bg-[#334155] text-white py-2 px-3 rounded-xl font-bold flex items-center justify-center gap-2 shadow-[2px_2px_0px_rgba(100,116,139,0.3)] transition-all active:translate-x-[1px] active:translate-y-[1px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] mb-6 text-xs"
              >
                <div className="w-5 h-5 rounded-lg bg-slate-800 flex items-center justify-center">
                  <Plus size={12} />
                </div>
                <span>New Chat</span>
              </button>

              {/* Recent Chats Dropdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-slate-400">
                  <span className="uppercase tracking-wider">Recent Chats</span>
                  <div className="w-5 h-5 rounded-full bg-[#1E293B] flex items-center justify-center text-slate-200">
                    <ChevronDown size={10} />
                  </div>
                </div>

                <div className="overflow-y-auto max-h-[55vh] space-y-2 pr-1">
                  {conversations.length === 0 ? (
                    <div className="text-center text-slate-500 text-xs py-8">
                      No saved sessions.
                    </div>
                  ) : (
                    conversations.map((c) => (
                      <div
                        key={c.id}
                        onClick={() => {
                          selectConversation(c.id);
                          setShowHistory(false);
                        }}
                        className={`flex items-center justify-between p-2 rounded-xl border cursor-pointer group transition-all text-xs ${conversationId === c.id
                          ? 'bg-indigo-900/40 border-indigo-500 text-indigo-200'
                          : 'bg-[#1E293B] border-slate-800 hover:bg-[#334155] text-slate-355'
                          }`}
                      >
                        <div className="flex flex-col truncate pr-2">
                          <span className="font-semibold truncate text-[11px]">
                            {c.title || `Chat session`}
                          </span>
                          <span className="text-[9px] text-slate-550 mt-0.5">
                            {new Date(c.created_at).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric'
                            })}
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Are you sure you want to delete this chat?")) {
                              deleteConversation(c.id);
                            }
                          }}
                          className="text-slate-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Profile Widget at Bottom */}
            <div className="bg-white border border-slate-200 p-2 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] text-black flex items-center justify-between mt-auto">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-orange-100 text-orange-700 border border-slate-200 flex items-center justify-center font-bold text-xs">
                  S
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-450 leading-none font-semibold">Welcome back,</span>
                  <span className="text-xs font-bold leading-tight">Suvigya</span>
                </div>
              </div>
              <ChevronUp size={14} className="text-slate-400 cursor-pointer" />
            </div>
          </div>
        )}
      </div>

      {/* 2. Main Content Feed Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">

        {/* Top Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white z-10">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="md:block border border-slate-250 bg-white hover:bg-slate-50 p-1.5 rounded-lg shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all mr-1"
            >
              <Menu size={14} />
            </button>
            <Sparkles className="text-indigo-500" size={18} />
            <span className="font-bold text-xs uppercase tracking-wider truncate max-w-[180px]">{chatHeading}</span>
          </div>
          <div className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200 px-2 py-1 rounded-md">
            ID: {videoId}
          </div>
        </div>

        {/* Tab Menu */}
        <div className="flex border-b border-slate-200 bg-white text-[10px] uppercase font-bold tracking-wider z-10">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex-1 py-3 flex items-center justify-center gap-1.5 border-r border-slate-100 transition-colors ${activeTab === 'chat' ? 'bg-indigo-50 text-indigo-600 border-b-2 border-b-indigo-500' : 'text-slate-500 hover:text-indigo-500 hover:bg-slate-50'
              }`}
          >
            <MessageSquare size={12} />
            Chat
          </button>
          <button
            onClick={() => setActiveTab('notes')}
            className={`flex-1 py-3 flex items-center justify-center gap-1.5 border-r border-slate-100 transition-colors ${activeTab === 'notes' ? 'bg-indigo-50 text-indigo-600 border-b-2 border-b-indigo-500' : 'text-slate-500 hover:text-indigo-500 hover:bg-slate-50'
              }`}
          >
            <BookOpen size={12} />
            Notes
          </button>
          <button
            onClick={() => setActiveTab('projects')}
            className={`flex-1 py-3 flex items-center justify-center gap-1.5 border-r border-slate-100 transition-colors ${activeTab === 'projects' ? 'bg-indigo-50 text-indigo-600 border-b-2 border-b-indigo-500' : 'text-slate-500 hover:text-indigo-500 hover:bg-slate-50'
              }`}
          >
            <Code size={12} />
            Project
          </button>
          <button
            onClick={() => setActiveTab('quiz')}
            className={`flex-1 py-3 flex items-center justify-center gap-1.5 border-r border-slate-100 transition-colors ${activeTab === 'quiz' ? 'bg-indigo-50 text-indigo-600 border-b-2 border-b-indigo-500' : 'text-slate-500 hover:text-indigo-500 hover:bg-slate-50'
              }`}
          >
            <Layers size={12} />
            Quiz
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex-1 py-3 flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'settings' ? 'bg-indigo-50 text-indigo-600 border-b-2 border-b-indigo-500' : 'text-slate-500 hover:text-indigo-500 hover:bg-slate-50'
              }`}
          >
            <Settings size={12} />
            Setup
          </button>
        </div>

        {/* Dynamic Feed Body */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col bg-[#F8FAFC]">
          {activeTab === 'chat' && (
            <div className="flex flex-col h-full justify-between gap-4">

              {/* Header Controls (Search and Quick Actions) */}
              <div className="flex items-center justify-between bg-white border border-slate-200 p-2 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                <div className="relative flex-1 max-w-[150px]">
                  <Search size={12} className="absolute left-2.5 top-2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-full pl-7 pr-2.5 py-1 text-[10px] focus:outline-none focus:bg-white text-slate-800"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (confirm("Are you sure you want to delete this active chat thread?")) {
                        startNewChat();
                      }
                    }}
                    className="w-7 h-7 rounded-full border border-slate-200 bg-red-50 hover:bg-red-100 flex items-center justify-center text-red-500 transition-transform active:scale-95"
                    title="Clear Active Chat"
                  >
                    <Trash2 size={12} />
                  </button>
                  <button
                    onClick={() => setActiveTab('settings')}
                    className="w-7 h-7 rounded-full border border-slate-200 bg-indigo-50 hover:bg-indigo-100 flex items-center justify-center text-indigo-600 transition-transform active:scale-95"
                    title="Setup Details"
                  >
                    <AlertCircle size={12} />
                  </button>
                </div>
              </div>

              {/* Status Banner */}
              {transcriptStatus === 'processing' && (
                <div className="bg-white border border-slate-200 rounded-xl p-3 text-xs text-yellow-600 flex items-center gap-2 shadow-[2px_2px_0px_rgba(148,163,184,0.2)]">
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-400 animate-ping border border-yellow-500" />
                  <span>Analyzing transcript context...</span>
                </div>
              )}
              {transcriptStatus === 'error' && (
                <div className="bg-white border border-slate-200 rounded-xl p-3 text-xs text-red-600 flex items-center gap-2 shadow-[2px_2px_0px_rgba(148,163,184,0.2)]">
                  <AlertCircle size={14} className="text-red-500" />
                  <span>Failed context indexing. Please configure valid API keys under setup.</span>
                </div>
              )}

              {/* Chat Message Lists */}
              <div className="flex-1 space-y-4 overflow-y-auto max-h-[58vh] pr-1 py-1">
                {filteredMessages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 text-center py-12">
                    <div className="w-12 h-12 bg-indigo-50 border border-slate-200 rounded-xl flex items-center justify-center mb-3 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)] text-indigo-500">
                      <Sparkles size={24} />
                    </div>
                    <p className="text-xs font-bold text-slate-800 uppercase tracking-wide">Workspace Ingestion Success</p>
                    <p className="text-[10px] text-slate-500 mt-1 max-w-[200px]">Ask specific questions or generate summary guides below.</p>
                    <div className="flex flex-col gap-2 mt-4 w-full max-w-[200px]">
                      <button
                        onClick={() => setInputText('Summarize the main concepts in this video.')}
                        className="text-[10px] font-bold bg-white hover:bg-slate-50 text-slate-700 px-3 py-2 rounded-xl border border-slate-250 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all"
                      >
                        Summarize Material
                      </button>
                      <button
                        onClick={() => setInputText('Explain the code and logic reference in detail.')}
                        className="text-[10px] font-bold bg-white hover:bg-slate-50 text-slate-700 px-3 py-2 rounded-xl border border-slate-250 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all"
                      >
                        Explain Code Logic
                      </button>
                    </div>
                  </div>
                ) : (
                  filteredMessages.map((m) => {
                    const isUser = m.role === 'user';
                    return (
                      <div
                        key={m.id}
                        className={`flex items-start ${isUser ? 'justify-end' : 'justify-start'} gap-2.5`}
                      >
                        {/* Bot Avatar (Left) */}
                        {!isUser && (
                          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-slate-200 flex items-center justify-center font-bold text-xs text-indigo-600 shrink-0 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)]">
                            🤖
                          </div>
                        )}

                        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[78%] group`}>
                          {/* Sender name label above the bubble */}
                          <span className={`text-[9px] font-bold mb-0.5 px-1 uppercase tracking-wider ${isUser ? 'text-slate-450' : 'text-indigo-500'
                            }`}>
                            {isUser ? 'You' : 'Bro'}
                          </span>

                          <div className={`p-3 rounded-xl text-xs leading-relaxed border border-slate-250 relative transition-all ${isUser
                            ? 'bg-white text-slate-800 shadow-[2px_2px_0px_rgba(148,163,184,0.3)]'
                            : 'bg-white text-slate-800 border-l-[4px] border-l-indigo-400 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)]'
                            }`}>

                            {/* Message content */}
                            {renderMessageBody(m.content || '...')}

                            {/* Reply Action Arrow */}
                            <div className={`absolute top-2.5 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer text-slate-400 hover:text-indigo-600 ${isUser ? '-left-6' : '-right-6'
                              }`}>
                              <CornerUpRight size={12} />
                            </div>
                          </div>
                          <span className="text-[8px] text-slate-400 mt-1 px-1">
                            {new Date(m.created_at).toLocaleTimeString(undefined, {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>

                        {/* User Avatar (Right) */}
                        {isUser && (
                          <div className="w-8 h-8 rounded-lg bg-orange-50 border border-slate-200 flex items-center justify-center font-bold text-xs text-orange-600 shrink-0 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)]">
                            👦
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
                {loading && (
                  <div className="flex items-center gap-1.5 text-slate-400 text-[10px] px-2 py-1 font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]" />
                    <span>Thinking...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Bottom Input Area Form */}
              <form
                onSubmit={handleSend}
                className="bg-white border border-slate-200 p-2.5 rounded-xl shadow-[3px_3px_0px_rgba(148,163,184,0.3)] flex items-center gap-2 mt-auto"
              >
                <button type="button" className="text-slate-400 hover:text-slate-600 p-1 transition-transform hover:scale-110">
                  <Paperclip size={16} />
                </button>
                <input
                  type="text"
                  placeholder="Type your message here..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  className="flex-1 bg-transparent border-0 outline-none text-xs text-slate-700 font-bold px-1"
                />
                <button type="button" className="text-slate-400 hover:text-slate-600 p-1 transition-transform hover:scale-110">
                  <Smile size={16} />
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="border border-slate-350 bg-[#0F172A] hover:bg-[#1E293B] disabled:opacity-50 text-white p-2 rounded-xl shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all"
                >
                  <Send size={13} />
                </button>
              </form>

            </div>
          )}

          {activeTab === 'notes' && (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                <h3 className="font-bold text-sm flex items-center gap-1.5 uppercase tracking-wide">
                  <FileText size={16} className="text-indigo-500" /> Study Notes Generator
                </h3>
                <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                  Compile summaries directly grounded in the material using our token-optimized parser.
                </p>
              </div>

              {/* Format selection */}
              <div className="flex gap-2 bg-slate-50 p-1.5 rounded-xl border border-slate-200 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)] text-xs">
                <button
                  onClick={() => setNoteType('summary')}
                  className={`flex-1 py-2 rounded-lg font-bold uppercase transition-all ${noteType === 'summary'
                    ? 'bg-white text-slate-800 border border-slate-200 shadow-[1px_1px_0px_rgba(148,163,184,0.2)]'
                    : 'text-slate-500 hover:text-slate-800'
                    }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setNoteType('detailed')}
                  className={`flex-1 py-2 rounded-lg font-bold uppercase transition-all ${noteType === 'detailed'
                    ? 'bg-white text-slate-800 border border-slate-200 shadow-[1px_1px_0px_rgba(148,163,184,0.2)]'
                    : 'text-slate-500 hover:text-slate-800'
                    }`}
                >
                  Detailed
                </button>
              </div>

              <button
                onClick={handleGenerateNotes}
                disabled={notesLoading}
                className="w-full border border-slate-300 bg-[#0F172A] hover:bg-[#1E293B] text-white font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all disabled:opacity-50"
              >
                {notesLoading ? 'Synthesizing...' : notesContent ? 'Regenerate Notes' : 'Generate Notes'}
              </button>

              {notesContent && (
                <div className="space-y-3">
                  {/* Notes Ready header + PDF button */}
                  <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)]">
                        <CheckCircle size={18} className="text-emerald-500" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-800 uppercase tracking-wide">Notes Ready</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">{noteType === 'summary' ? 'Summary' : 'Detailed'} study guide — screenshots jump to video timestamp.</p>
                      </div>
                    </div>
                    <button
                      onClick={handleDownloadPDF}
                      className="w-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold uppercase tracking-wider text-xs py-2 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all flex items-center justify-center gap-2"
                    >
                      <Download size={13} /> Download as PDF
                    </button>
                  </div>

                  {/* Inline Notes Renderer */}
                  <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                    <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-3 border-b border-slate-100 pb-2">📖 Study Notes — Click screenshots to jump to timestamp</p>
                    {renderNotesContent(notesContent)}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'projects' && (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                <h3 className="font-bold text-sm flex items-center gap-1.5 uppercase tracking-wide">
                  <Code size={16} className="text-indigo-500" /> Full Project Blueprint
                </h3>
                <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                  Compile Docker containers, dependency trees, files, and deployment README instructions.
                </p>
              </div>

              <div className="space-y-2">
                <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-600">Project Requirements:</label>
                <textarea
                  value={projectPrompt}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setProjectPrompt(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-xs text-slate-800 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)] focus:outline-none focus:bg-slate-50"
                  rows={3}
                />
              </div>

              <button
                onClick={handleGenerateProject}
                disabled={projectLoading}
                className="w-full border border-slate-300 bg-[#0F172A] hover:bg-[#1E293B] text-white font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all disabled:opacity-50"
              >
                {projectLoading ? 'Generating structure...' : 'Generate Blueprint'}
              </button>

              {projectError && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700 flex items-center gap-2 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)]">
                  <AlertCircle size={14} className="text-red-500 shrink-0" />
                  <span className="font-semibold">{projectError}</span>
                </div>
              )}

              {projectContent && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-[3px_3px_0px_rgba(148,163,184,0.3)]">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)]">
                      <CheckCircle size={20} className="text-emerald-500" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 uppercase tracking-wide">Blueprint Ready</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Project files generated and packaged.</p>
                    </div>
                  </div>
                  <button
                    onClick={handleDownloadZip}
                    className="w-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all flex items-center justify-center gap-2"
                  >
                    <FolderDown size={14} /> Download as ZIP
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'quiz' && (
            <div className="space-y-4">

              {/* LOBBY STATE: No quiz generated yet */}
              {quizzes.length === 0 && !quizLoading && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-[3px_3px_0px_rgba(148,163,184,0.3)] text-center">
                  <div className="w-14 h-14 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center mx-auto mb-4 shadow-[2px_2px_0px_rgba(148,163,184,0.2)]">
                    <Layers size={28} className="text-indigo-500" />
                  </div>
                  <h3 className="font-bold text-sm uppercase tracking-wide text-slate-800 mb-1">Interactive Quiz</h3>
                  <p className="text-[10px] text-slate-500 leading-relaxed mb-4 max-w-[220px] mx-auto">
                    Generate a 5-question multiple choice quiz based on this video's content.
                  </p>
                  <button
                    onClick={handleGenerateQuiz}
                    disabled={quizLoading}
                    className="w-full border border-slate-300 bg-[#0F172A] hover:bg-[#1E293B] text-white font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all disabled:opacity-50"
                  >
                    {quizLoading ? 'Generating quiz...' : 'Generate Quiz'}
                  </button>
                </div>
              )}

              {/* LOADING STATE */}
              {quizLoading && (
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-[2px_2px_0px_rgba(148,163,184,0.3)] text-center">
                  <div className="flex items-center justify-center gap-1.5 text-slate-500 text-xs font-bold mb-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" />
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]" />
                  </div>
                  <p className="text-[10px] text-slate-500">Generating your quiz questions...</p>
                </div>
              )}

              {/* ERROR STATE */}
              {quizError && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700 flex items-center gap-2 shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.2)]">
                  <AlertCircle size={14} className="text-red-500 shrink-0" />
                  <span className="font-semibold">{quizError}</span>
                </div>
              )}

              {/* LIST VIEW / LOBBY: Quizzes exist, none is active */}
              {quizzes.length > 0 && activeQuizId === null && !quizLoading && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-xs uppercase tracking-wider text-slate-700">Quiz History</h3>
                    <span className="bg-indigo-50 border border-indigo-200 text-indigo-700 text-[9px] font-bold px-2 py-0.5 rounded-full">
                      {quizzes.length} {quizzes.length === 1 ? 'Quiz' : 'Quizzes'}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {quizzes.map((quiz, idx) => {
                      const isAttempted = quiz.score !== null && quiz.score !== undefined;
                      return (
                        <div
                          key={quiz.id}
                          className="bg-white border border-slate-200 rounded-xl p-4 shadow-[2px_2px_0px_rgba(148,163,184,0.25)] flex items-center justify-between transition-all hover:border-slate-350"
                        >
                          <div>
                            <h4 className="font-bold text-xs text-slate-800">Quiz {idx + 1}</h4>
                            <p className="text-[9px] text-slate-405 mt-0.5">{quiz.questions.length} questions</p>
                          </div>

                          <div className="flex items-center gap-2.5">
                            {isAttempted ? (
                              <>
                                <span className="bg-emerald-50 border border-emerald-250 text-emerald-700 text-[10px] font-bold px-2 py-1 rounded-md">
                                  Score: {quiz.score}
                                </span>
                                <button
                                  onClick={() => {
                                    setActiveQuizId(quiz.id);
                                    setTimeout(() => retakeQuiz(), 0);
                                  }}
                                  className="border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold uppercase tracking-wider text-[9px] px-2.5 py-1.5 rounded-lg transition-all"
                                >
                                  Start Again
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => startQuiz(quiz.id)}
                                className="border border-emerald-300 bg-emerald-600 hover:bg-emerald-700 text-white font-bold uppercase tracking-wider text-[9px] px-2.5 py-1.5 rounded-lg transition-all"
                              >
                                Start Quiz
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <button
                    onClick={generateNewQuiz}
                    disabled={quizLoading}
                    className="w-full border border-dashed border-indigo-300 hover:border-indigo-400 bg-indigo-50/50 hover:bg-indigo-50 text-indigo-700 font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl transition-all flex items-center justify-center gap-1.5"
                  >
                    <Plus size={14} /> Generate New Quiz
                  </button>
                </div>
              )}

              {/* ACTIVE QUIZ VIEW */}
              {activeQuizId !== null && (() => {
                const activeQuiz = quizzes.find(q => q.id === activeQuizId);
                if (!activeQuiz) return null;

                const { questions, answers, submitted, score } = activeQuiz;
                const attemptedCount = Object.keys(answers).length;
                const totalQuestions = questions.length;

                return (
                  <div className="space-y-4">
                    {/* Header bar inside active quiz */}
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                      <button
                        onClick={() => setActiveQuizId(null)}
                        className="text-slate-500 hover:text-slate-800 font-bold text-[10px] uppercase tracking-wide flex items-center gap-1"
                      >
                        ← Back to History
                      </button>
                      <span className="font-bold text-xs text-slate-700">
                        Quiz {quizzes.findIndex(q => q.id === activeQuizId) + 1}
                      </span>
                    </div>

                    {/* Score banner (after submission) */}
                    {submitted && score && (() => {
                      const correctCount = questions.filter((q, i) => answers[i] === q.answer).length;
                      const pct = Math.round((correctCount / totalQuestions) * 100);
                      return (
                        <div className={`border rounded-xl p-4 shadow-[2px_2px_0px_rgba(148,163,184,0.2)] flex items-center gap-3 ${pct >= 60 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm border ${pct >= 60 ? 'bg-emerald-100 border-emerald-300 text-emerald-700' : 'bg-red-100 border-red-300 text-red-700'}`}>
                            {score}
                          </div>
                          <div>
                            <p className={`text-xs font-bold uppercase tracking-wide ${pct >= 60 ? 'text-emerald-700' : 'text-red-700'}`}>
                              {pct >= 80 ? 'Excellent!' : pct >= 60 ? 'Good Job!' : pct >= 40 ? 'Keep Practicing' : 'Needs Review'}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-0.5">You scored {pct}% on this assessment.</p>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Questions */}
                    {questions.map((q, qIdx) => {
                      const userAnswer = answers[qIdx];
                      const isCorrect = userAnswer === q.answer;

                      return (
                        <div key={qIdx} className="bg-white border border-slate-200 rounded-xl p-4 shadow-[2px_2px_0px_rgba(148,163,184,0.2)]">
                          <p className="text-xs font-bold text-slate-800 mb-3 leading-relaxed">
                            <span className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-600 text-[10px] font-bold mr-2">
                              {qIdx + 1}
                            </span>
                            {q.question}
                          </p>
                          <div className="space-y-2">
                            {(['A', 'B', 'C', 'D'] as const).map((opt) => {
                              const optionText = q.options[opt];
                              const isSelected = userAnswer === opt;
                              const isCorrectOption = q.answer === opt;

                              let optStyle = 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300 cursor-pointer';
                              let dotStyle = 'bg-white border-slate-300 text-slate-500';

                              if (submitted) {
                                if (isCorrectOption) {
                                  optStyle = 'bg-emerald-50 border-emerald-400 text-emerald-800';
                                  dotStyle = 'bg-emerald-500 border-emerald-600 text-white';
                                } else if (isSelected) {
                                  optStyle = 'bg-red-50 border-red-400 text-red-800';
                                  dotStyle = 'bg-red-500 border-red-600 text-white';
                                } else {
                                  optStyle = 'bg-slate-50 border-slate-200 text-slate-400';
                                  dotStyle = 'bg-white border-slate-200 text-slate-300';
                                }
                              } else if (isSelected) {
                                optStyle = 'bg-indigo-50 border-indigo-400 text-indigo-800';
                                dotStyle = 'bg-indigo-500 border-indigo-600 text-white';
                              }

                              return (
                                <button
                                  key={opt}
                                  onClick={() => selectQuizAnswer(qIdx, opt)}
                                  disabled={submitted}
                                  className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg border text-xs font-semibold transition-all ${optStyle} ${submitted ? 'cursor-default' : ''}`}
                                >
                                  <span className={`w-5 h-5 rounded-md border flex items-center justify-center text-[10px] font-bold shrink-0 ${dotStyle}`}>
                                    {submitted && isCorrectOption ? '✓' : submitted && isSelected ? '✗' : opt}
                                  </span>
                                  <span className="text-left">{optionText}</span>
                                </button>
                              );
                            })}
                          </div>

                          {/* Explanation shown after submission for wrong answers */}
                          {submitted && userAnswer && !isCorrect && q.explanation && (
                            <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-[10px] text-amber-800 leading-relaxed">
                              <span className="font-bold uppercase tracking-wider text-amber-700">💡 Explanation: </span>
                              {q.explanation}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Submit button */}
                    {!submitted && (
                      <button
                        onClick={submitQuiz}
                        disabled={attemptedCount < totalQuestions}
                        className="w-full border border-emerald-300 bg-emerald-600 hover:bg-emerald-700 text-white font-bold uppercase tracking-wider text-xs py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all disabled:opacity-40 flex items-center justify-center gap-2"
                      >
                        <CheckCircle size={13} /> Submit Answers ({attemptedCount}/{totalQuestions})
                      </button>
                    )}

                    {/* Post-submission actions */}
                    {submitted && (
                      <div className="flex gap-2">
                        <button
                          onClick={retakeQuiz}
                          className="flex-1 border border-slate-300 bg-[#0F172A] hover:bg-[#1E293B] text-white font-bold uppercase tracking-wider text-[10px] py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all flex items-center justify-center gap-1.5"
                        >
                          <RefreshCw size={11} /> Retake
                        </button>
                        <button
                          onClick={generateNewQuiz}
                          disabled={quizLoading}
                          className="flex-1 border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold uppercase tracking-wider text-[10px] py-2.5 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.2)] active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-[0px_0px_0px_rgba(0,0,0,0)] transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                        >
                          <Sparkles size={11} /> New Quiz
                        </button>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-4 text-xs">
              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)]">
                <h3 className="font-bold text-sm flex items-center gap-1.5 uppercase tracking-wide">
                  <Settings size={16} className="text-indigo-500" /> Workspace Configurations
                </h3>
              </div>

              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-[2px_2px_0px_rgba(148,163,184,0.3)] space-y-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">Backend Server Address:</label>
                  <input
                    type="text"
                    value={backendUrl}
                    disabled
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-400 font-bold"
                  />
                </div>

                <div className="bg-yellow-50 border border-yellow-200 p-3.5 rounded-xl shadow-[1.5px_1.5px_0px_rgba(148,163,184,0.1)] text-black">
                  <h4 className="font-bold uppercase tracking-wider text-xs mb-1.5 flex items-center gap-1 text-yellow-700">
                    <AlertCircle size={13} className="text-yellow-600" /> API Keys Notice
                  </h4>
                  <p className="text-[10px] leading-relaxed font-semibold text-slate-600">
                    Make sure to configure your <span className="font-mono text-indigo-500 underline">GROQ_API_KEY</span> or <span className="font-mono text-indigo-500 underline">GEMINI_API_KEY</span> in the backend server's <span className="font-mono text-blue-600">.env</span> file to utilize live generation.
                  </p>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};


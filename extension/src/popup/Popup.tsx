import React, { useEffect, useState } from 'react';
import { Sparkles, AlertCircle } from 'lucide-react';

export const Popup: React.FC = () => {
  const [isOnYoutube, setIsOnYoutube] = useState(false);
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null);

  useEffect(() => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab?.url) {
        const url = new URL(activeTab.url);
        if (url.hostname.includes('youtube.com') && url.pathname === '/watch') {
          setIsOnYoutube(true);
          const v = url.searchParams.get('v');
          setCurrentVideoId(v);
        }
      }
    });
  }, []);

  const openSidepanel = () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (activeTab?.id) {
        chrome.runtime.sendMessage({
          action: 'open_sidepanel',
          videoId: currentVideoId
        }, () => {
          window.close(); // Close the popup
        });
      }
    });
  };

  return (
    <div className="w-80 p-5 bg-slate-950 text-slate-100 font-sans border border-slate-800 rounded-lg">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="text-blue-500" size={24} />
        <h1 className="text-base font-bold">YouTube AI Workspace</h1>
      </div>

      {isOnYoutube ? (
        <div className="space-y-4">
          <p className="text-xs text-slate-350 leading-relaxed">
            Ready to learn! Click below to toggle the workspace side panel and begin interacting with this video.
          </p>
          <button
            onClick={openSidepanel}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-4 rounded text-xs transition-colors shadow-lg shadow-blue-900/40"
          >
            Open Sidepanel Workspace
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-start gap-2 bg-slate-900/60 p-3 border border-slate-850 rounded">
            <AlertCircle className="text-amber-500 mt-0.5 shrink-0" size={16} />
            <p className="text-[11px] text-slate-400 leading-relaxed">
              To use the interactive AI Workspace, navigate to any video watch page on <span className="text-blue-400">youtube.com</span>.
            </p>
          </div>
          <a
            href="https://www.youtube.com"
            target="_blank"
            rel="noreferrer"
            className="block text-center w-full bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-bold py-2 rounded text-xs transition-colors"
          >
            Go to YouTube
          </a>
        </div>
      )}
    </div>
  );
};

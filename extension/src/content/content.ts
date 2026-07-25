// Content Script for YouTube AI Workspace

let currentVideoId: string | null = null;
let launcherBtn: HTMLButtonElement | null = null;

// Function to extract video ID from YouTube watch URL
function getVideoId(url: string): string | null {
  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.hostname.includes("youtube.com") && parsedUrl.pathname === "/watch") {
      return parsedUrl.searchParams.get("v");
    }
  } catch (e) {
    console.error("Error parsing URL in content script:", e);
  }
  return null;
}

// Function to create and inject the floating launcher button
function injectLauncher() {
  if (launcherBtn) return; // Already exists

  launcherBtn = document.createElement("button");
  launcherBtn.id = "yt-ai-workspace-launcher";
  
  // High-end premium styles for floating button
  Object.assign(launcherBtn.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    backgroundColor: "#2563eb", // Deep premium blue
    color: "#ffffff",
    border: "none",
    boxShadow: "0 4px 14px rgba(37, 99, 235, 0.4)",
    cursor: "pointer",
    zIndex: "99999",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px",
    transition: "transform 0.2s ease, background-color 0.2s ease",
  });

  launcherBtn.innerHTML = "🤖";
  launcherBtn.title = "Open YouTube AI Workspace";

  // Hover effects
  launcherBtn.addEventListener("mouseenter", () => {
    if (launcherBtn) {
      launcherBtn.style.transform = "scale(1.1)";
      launcherBtn.style.backgroundColor = "#1d4ed8";
    }
  });

  launcherBtn.addEventListener("mouseleave", () => {
    if (launcherBtn) {
      launcherBtn.style.transform = "scale(1)";
      launcherBtn.style.backgroundColor = "#2563eb";
    }
  });

  // Click action: Notify background script to open sidepanel
  launcherBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "open_sidepanel", videoId: currentVideoId });
  });

  document.body.appendChild(launcherBtn);
}

// Function to remove the floating launcher button
function removeLauncher() {
  if (launcherBtn) {
    launcherBtn.remove();
    launcherBtn = null;
  }
}

// Check the current page and manage launcher state
function checkPage() {
  const url = window.location.href;
  const videoId = getVideoId(url);

  if (videoId) {
    if (videoId !== currentVideoId) {
      currentVideoId = videoId;
      console.log("YouTube AI Workspace: Detected video ID:", videoId);
      // Notify components about new video ID
      chrome.runtime.sendMessage({ action: "video_changed", videoId });
    }
    injectLauncher();
  } else {
    currentVideoId = null;
    removeLauncher();
  }
}

// Watch for SPA transitions on YouTube (custom events and fallback polling)
document.addEventListener("yt-navigate-finish", checkPage);
window.addEventListener("popstate", checkPage);

// Initial check when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", checkPage);
} else {
  checkPage();
}

// Fallback interval check to handle DOM changes
setInterval(checkPage, 1000);

// Listen for seek_video messages from side panel
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === 'seek_video' && typeof message.seconds === 'number') {
    const video = document.querySelector<HTMLVideoElement>('video');
    if (video) {
      video.currentTime = message.seconds;
      video.play();
    }
  }
});

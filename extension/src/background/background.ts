// Background Service Worker

// Ensure sidePanel opens on clicking extension icon
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("Error setting panel behavior:", error));

// Store active video state per tab
const activeTabsVideo: Record<number, string> = {};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "open_sidepanel") {
    const tabId = sender.tab?.id;
    if (tabId) {
      // Set the side panel options for this tab
      chrome.sidePanel.open({ tabId })
        .then(() => {
          console.log("Opened side panel for tab:", tabId);
          // Send video info to the side panel once opened
          setTimeout(() => {
            chrome.runtime.sendMessage({
              action: "set_video_id",
              videoId: message.videoId || activeTabsVideo[tabId]
            }).catch(() => {
              // Sidepanel might not be fully loaded yet, which is fine
            });
          }, 500);
          sendResponse({ status: "success" });
        })
        .catch((err) => {
          console.error("Failed to open side panel:", err);
          sendResponse({ status: "error", error: err.message });
        });
      return true; // Keep message channel open for async response
    }
  }

  if (message.action === "video_changed") {
    const tabId = sender.tab?.id;
    if (tabId && message.videoId) {
      activeTabsVideo[tabId] = message.videoId;
      console.log(`Tab ${tabId} changed video to: ${message.videoId}`);
      
      // Forward the event to the sidepanel if it is already open and listening
      chrome.runtime.sendMessage({
        action: "set_video_id",
        videoId: message.videoId
      }).catch(() => {
        // Ignored if sidepanel isn't open
      });
    }
  }
});

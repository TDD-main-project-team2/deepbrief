import { useRef } from "react";

import { chatFeatureConfig } from "../config/chatFeatureConfig.js";
import {
  appendConversationMessage,
  updateConversationMessage,
} from "../utils/conversationMessages.js";
import { getAccessToken, getAuthSessionVersion } from "../utils/tokenStorage.js";

export default function useConversationMessages({
  activeConversation,
  setConversations,
  onLogout,
}) {
  const pendingFeatures = useRef(new Set());

  async function sendMessage(messageText, action, templateId) {
    const { api: featureApi, pendingText } = chatFeatureConfig[action] ?? chatFeatureConfig.qa;

    if (pendingFeatures.current.has(activeConversation?.id)) return;

    if (featureApi && activeConversation && messageText.trim()) {
      const conversationId = activeConversation.id;
      const token = getAccessToken();
      const requestSessionVersion = getAuthSessionVersion();
      const requestId = crypto.randomUUID();

      pendingFeatures.current.add(conversationId);

      const updateMessage = (changes) =>
        setConversations((items) =>
          updateConversationMessage(items, conversationId, requestId, changes),
        );

      setConversations((items) =>
        appendConversationMessage(items, conversationId, {
          requestId,
          question: messageText.trim(),
          answer: "",
          pending: true,
          pendingText,
        }),
      );

      try {
        const response = await featureApi(
          { conversationId, content: messageText.trim(), templateId },
          token,
        );

        if (getAuthSessionVersion() !== requestSessionVersion) return;
        if (typeof response?.content !== "string" || !response.content.trim()) {
          throw new Error("Empty feature response");
        }

        updateMessage({
          answer: `“${messageText}” 요청을 받았습니다.\n\n${response.content}`,
          pending: false,
        });
      } catch (error) {
        if (getAuthSessionVersion() !== requestSessionVersion) return;

        updateMessage({
          pending: false,
          error: "요청을 완료하지 못했습니다. 잠시 후 다시 시도해주세요.",
        });

        if (error.response?.status === 401) void onLogout();
      } finally {
        pendingFeatures.current.delete(conversationId);
      }
    }
  }

  function isConversationPending(conversationId) {
    return pendingFeatures.current.has(conversationId);
  }

  return { sendMessage, isConversationPending };
}
